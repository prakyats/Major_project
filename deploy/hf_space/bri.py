"""
bri.py - Board Recoverability Index (BRI): from detections to damage score, usable area and grade.

Implements the guide's six-step model (BRI_Model_Code_and_Worked_Example), with one change for this
dataset's geometry (documented in NOTES.md section 17):

  Step 1  union of boxes, no double counting               A_def = |R_1 U ... U R_n|
  Step 2  severity weight per class                        w_c in (0, 1]
  Step 3  position penalty from the nearest TRIMMABLE edge p_i = 1 - exp(-d_i / lambda)
  Step 4  confidence-weighted influence                    s_i = w_c * conf_i * p_i
  Step 5  impact map (max rule) and damage score           I(x,y) = max_i s_i 1[(x,y) in R_i]
                                                           DIS = sum I / A_board,  A_rec = A_board (1 - DIS)
  Step 6  grade from thresholds                            A < t1 <= B < t2 <= C < t3 <= Reject

Geometry: in these line-scan images the board runs top to bottom and the left/right ~150-190 px is black
conveyor. The trimmable edges are the board's side edges, so d_i is measured from the box centre to the
nearest side edge of the board (found per image with a board mask), and A_board is the board area, not
the image area. The image top/bottom are tile cuts along the board length, not board ends. The guide's
original edges='all' rule (image borders) is kept as edges='image' for comparison.

Severity weights are the guide's placeholders (crack worst, resin mildest) restricted to the classes a
model predicts; they must be confirmed by an expert before publication. Thresholds are fitted on the
VALIDATION boards (quartiles of the ground-truth damage score) and never on test.
"""
import numpy as np
import cv2

SEVERITY = {            # guide's placeholders, w_c in (0, 1]
    "Crack": 1.00, "Knot_with_crack": 0.90, "Dead_Knot": 0.60, "Knot_missing": 0.55,
    "Marrow": 0.50, "Live_Knot": 0.40, "Resin": 0.30, "Quartzity": 0.25,
}
GRADES = ["A", "B", "C", "Reject"]
LAMBDA = 250.0          # px at native 2800 x 1024 resolution


def board_extent(img_bgr, thr=60):
    """(mask, x_left, x_right) of the board. Dark regions connected to the image sides are conveyor;
    dark regions enclosed by wood (knots, resin) stay board."""
    h, w = img_bgr.shape[:2]
    g = cv2.resize(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY), (max(1, w // 4), max(1, h // 4)),
                   interpolation=cv2.INTER_AREA)
    _, lab = cv2.connectedComponents((g <= thr).astype(np.uint8), connectivity=4)
    side = (set(np.unique(lab[:, 0])) | set(np.unique(lab[:, -1]))) - {0}
    board = (~np.isin(lab, list(side))).astype(np.uint8)
    n, lab2, st, _ = cv2.connectedComponentsWithStats(board, connectivity=4)
    if n < 2 or st[1:, cv2.CC_STAT_AREA].max() < 0.2 * board.size:
        full = np.ones((h, w), bool)                 # photo without conveyor: whole image is board
        return full, 0, w
    board = (lab2 == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    cols = np.nonzero(board.mean(0) > 0.5)[0]
    xl, xr = int(cols[0]) * 4, int(cols[-1] + 1) * 4
    mask = cv2.resize(board, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    return mask, xl, xr


def union_area(boxes, w, h):
    m = np.zeros((h, w), bool)
    for x1, y1, x2, y2 in boxes:
        m[max(0, int(y1)):min(h, int(np.ceil(y2))), max(0, int(x1)):min(w, int(np.ceil(x2)))] = True
    return int(m.sum())


def position_penalty(box, w, h, xl, xr, lam=LAMBDA, edges="board"):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    if edges == "board":
        d = max(0.0, min(cx - xl, xr - cx))           # nearest side edge of the board
    else:                                             # guide's original rule: nearest image border
        d = min(cx, w - cx, cy, h - cy)
    return 1.0 - float(np.exp(-d / lam))


def board_report(dets, img_shape, board=None, severity=SEVERITY, lam=LAMBDA, edges="board",
                 taus=(0.002, 0.006, 0.015)):
    """dets: list of (class_name, confidence, (x1, y1, x2, y2)) in pixels of the original image.
    board: (mask, x_left, x_right) from board_extent, or None to use the whole image."""
    h, w = img_shape[:2]
    if board is None:
        mask, xl, xr = np.ones((h, w), bool), 0, w
    else:
        mask, xl, xr = board
    a_board = max(1, int(mask.sum()))
    I = np.zeros((h, w), np.float32)
    parts = []
    for name, conf, (x1, y1, x2, y2) in dets:
        wc = severity.get(name)
        if wc is None:
            continue
        p = position_penalty((x1, y1, x2, y2), w, h, xl, xr, lam, edges)
        s = wc * float(conf) * p
        ya, yb = max(0, int(round(y1))), min(h, int(round(y2)))
        xa, xb = max(0, int(round(x1))), min(w, int(round(x2)))
        if xb > xa and yb > ya:
            I[ya:yb, xa:xb] = np.maximum(I[ya:yb, xa:xb], s)
        parts.append(dict(cls=name, conf=round(float(conf), 3), w=wc, p=round(p, 3), s=round(s, 4)))
    I *= mask
    dis = float(I.sum() / a_board)
    boxes = [d[2] for d in dets if d[0] in severity]
    return dict(n_defects=len(parts), union_px=union_area(boxes, w, h), board_px=a_board,
                coverage_pct=round(100 * union_area(boxes, w, h) / a_board, 2),
                DIS=dis, recoverable_pct=round(100 * (1 - dis), 2), grade=grade(dis, taus), defects=parts)


def grade(dis, taus):
    t1, t2, t3 = taus
    return "A" if dis < t1 else "B" if dis < t2 else "C" if dis < t3 else "Reject"


def quadratic_weighted_kappa(a, b, k=4):
    """Agreement of two ordinal gradings: 1 = perfect, 0 = chance (guide's Section 5)."""
    a, b = np.asarray(a), np.asarray(b)
    O = np.zeros((k, k))
    for i, j in zip(a, b):
        O[i, j] += 1
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    den = (W * E).sum()
    return 1.0 - (W * O).sum() / den if den else 1.0


if __name__ == "__main__":
    # the guide's worked example (Section 7): image-border rule, whole image as board -> DIS 0.020860, grade B
    W, H = 2800, 1024
    dets = [("Crack", 0.90, (1300, 480, 1700, 600)), ("Knot_with_crack", 0.85, (1600, 500, 1900, 640)),
            ("Live_Knot", 0.85, (60, 300, 180, 420)), ("Resin", 0.60, (2500, 60, 2620, 130))]
    r = board_report(dets, (H, W), None, edges="image", taus=(0.01, 0.03, 0.06))
    print({k: r[k] for k in ("n_defects", "union_px", "DIS", "recoverable_pct", "grade")})
    assert abs(r["DIS"] - 0.020860) < 1e-5 and r["grade"] == "B" and r["union_px"] == 102800
    print("worked example reproduced: DIS 0.020860, grade B, union 102,800 px")
