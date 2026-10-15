"""
app.py -- local demo / presentation UI for the wood-defect detectors.

Run:  python app.py        then open http://127.0.0.1:7860
Needs: weights/yolo11m_final.pt and weights/yolo11s_baseline.pt (see README), CPU is enough.
Optional: dataset_clean/test/ (or samples/) for the "Test boards" tab (ground truth vs prediction).
"""
import glob
import json
import os
import random
import tempfile
import time
from datetime import datetime
from pathlib import Path

import cv2
import gradio as gr
import numpy as np
from ultralytics import YOLO

import bri
from math_model import wbf_image

ROOT = Path(__file__).parent
WEIGHTS = {
    "YOLO11s 4-class balanced (subset)": ROOT / "weights" / "yolo11s_4cls_balanced.pt",
    "YOLO11m (final, run 2)": ROOT / "weights" / "yolo11m_final.pt",
    "YOLO11s (baseline, same config)": ROOT / "weights" / "yolo11s_baseline.pt",
}
WEIGHTS = {k: p for k, p in WEIGHTS.items() if p.exists()} or WEIGHTS   # list only models that are present
NAMES = ["Quartzity", "Live_Knot", "Marrow", "Resin", "Dead_Knot", "Knot_with_crack", "Knot_missing", "Crack"]
DESCR = {
    "Quartzity": "faint streak along the grain (rare: 125 training boxes)",
    "Live_Knot": "healthy, intergrown knot",
    "Marrow": "pith line, long streak along the grain",
    "Resin": "resin pocket, elongated dark patch",
    "Dead_Knot": "dark, loose or encased knot",
    "Knot_with_crack": "knot with a radial crack",
    "Knot_missing": "hole left by a fallen knot",
    "Crack": "long thin fissure along the grain",
}
# one fixed colour per class (BGR for cv2), identical for ground truth and predictions
COLORS = {
    "Quartzity": (200, 120, 0), "Live_Knot": (0, 200, 0), "Marrow": (255, 0, 200), "Resin": (0, 165, 255),
    "Dead_Knot": (0, 0, 230), "Knot_with_crack": (230, 200, 0), "Knot_missing": (128, 0, 128), "Crack": (0, 230, 230),
}
IMGSZ = 1024
_models = {}
GRADE_COLOURS = {"A": "#2e7d32", "B": "#9e9d24", "C": "#ef6c00", "Reject": "#c62828"}
CFT_MM3 = 28316846.6     # one cubic foot in cubic millimetres


# weighted box fusion (mathematical model; settings chosen on validation by math_model.py)
PART_WEIGHTS = {   # members of the fusions, not listed on their own
    "full 1024": ROOT / "weights" / "yolo11s_full4_1024.pt",
    "full 1280": ROOT / "weights" / "yolo11s_full4_1280.pt",
    "4cls plain 1024": ROOT / "weights" / "yolo11s_4cls_plain.pt",
    "4cls sqrt 1280": ROOT / "weights" / "yolo11s_4cls_sqrt_1280.pt",
    "4cls plain 1280": ROOT / "weights" / "yolo11s_4cls_plain_1280.pt",
}
NAMES4 = ["Live_Knot", "Dead_Knot", "Resin", "Crack"]


def _cfg(name, default):
    f = ROOT / "eval" / "math_model" / name
    return json.loads(f.read_text())["chosen"] if f.exists() else default


FUSIONS = {
    "Final: fusion of two YOLO11s 4-class models, full dataset (deployed)": dict(
        parts=[("full 1024", 1024), ("full 1280", 1280)],
        cfg=_cfg("full_dataset.json", {"t_iou": 0.65, "weights": [1, 1]}), names=NAMES4, bri="fusion_full_1024"),
    "Fusion of four 4-class YOLO11s models (4,000-image subset)": dict(
        parts=[("YOLO11s 4-class balanced (subset)", 1024), ("4cls plain 1024", 1024), ("4cls sqrt 1280", 1280), ("4cls plain 1280", 1280)],
        cfg=_cfg("4cls_fusion.json", {"t_iou": 0.55, "weights": [2, 1, 1, 1]}), names=NAMES4, bri="fusion4_1024"),
    "Fusion (WBF): YOLO11m + YOLO11s, 8 classes": dict(
        parts=[("YOLO11m (final, run 2)", 1024), ("YOLO11s (baseline, same config)", 1024)],
        cfg=_cfg("8cls_m_s.json", {"t_iou": 0.65, "weights": [1, 1]}), names=NAMES, bri=None),
}
ALL_WEIGHTS = {**WEIGHTS, **PART_WEIGHTS}
FUSIONS = {k: v for k, v in FUSIONS.items() if all(ALL_WEIGHTS.get(m, Path("x")).exists() for m, _ in v["parts"])}
MODEL_CHOICES = list(FUSIONS)[:1] + list(WEIGHTS) + list(FUSIONS)[1:]


def train_imgsz(key):
    """Input size the model was trained at (1280 for the high-resolution runs, else 1024)."""
    if key in FUSIONS:
        return IMGSZ
    return 1280 if "1280" in ALL_WEIGHTS[key].stem else IMGSZ


def bri_cfg(key):
    """Grade thresholds fitted on the validation boards by bri_validate.py (detector and reference)."""
    tag = FUSIONS[key]["bri"] if key in FUSIONS else f"{ALL_WEIGHTS[key].stem}_{train_imgsz(key)}"
    f = ROOT / "eval" / "bri" / f"bri_validation_{tag}.json"
    if f.exists():
        d = json.loads(f.read_text())
        return tuple(d["tau_detector"]), tuple(d["tau_reference"]), True
    return (0.002, 0.006, 0.015), (0.002, 0.006, 0.015), False


def grade_badge(g):
    return (f"<span style='background:{GRADE_COLOURS[g]};color:#fff;padding:2px 10px;border-radius:6px;"
            f"font-weight:700'>Grade {g}</span>")


# ---------------------------------------------------------------- model + drawing
def get_model(key):
    if key not in _models:
        p = ALL_WEIGHTS[key]
        if not p.exists():
            raise gr.Error(f"Missing weights file {p}. Download best.pt from Kaggle into weights/ (see README).")
        _models[key] = YOLO(str(p))
    return _models[key]


def draw_boxes(img_bgr, boxes, labels, thickness=None):
    out = img_bgr.copy()
    h, w = out.shape[:2]
    fs = min(1.4, max(0.4, w / 1400))
    thickness = thickness or (1 if w < 600 else 2 if w < 1500 else 3)
    tt = 1 if w < 900 else 2
    for (x1, y1, x2, y2), lab in zip(boxes, labels):
        cls = lab.split(" ")[0]
        c = COLORS.get(cls, (255, 255, 255))
        cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), c, thickness)
        (tw, th), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, fs, tt)
        y0 = int(y1) - 4 if y1 > th + 8 else int(y2) + th + 4
        cv2.rectangle(out, (int(x1), y0 - th - 3), (int(x1) + tw + 4, y0 + 3), c, -1)
        cv2.putText(out, lab, (int(x1) + 2, y0), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), tt, cv2.LINE_AA)
    return out


def heatmap(img_bgr, boxes, confs):
    """Confidence-weighted Gaussian blob per detection, blended over a dimmed image (presentation view)."""
    h, w = img_bgr.shape[:2]
    acc = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for (x1, y1, x2, y2), p in zip(boxes, confs):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        sx, sy = max((x2 - x1) / 2.5, 6), max((y2 - y1) / 2.5, 6)
        acc += float(p) * np.exp(-(((xx - cx) ** 2) / (2 * sx ** 2) + ((yy - cy) ** 2) / (2 * sy ** 2)))
    if acc.max() > 0:
        acc = acc / acc.max()
    hm = cv2.applyColorMap((acc * 255).astype(np.uint8), cv2.COLORMAP_JET)
    base = (img_bgr * 0.55).astype(np.uint8)
    alpha = (acc[..., None] * 0.85)
    return (base * (1 - alpha) + hm * alpha).astype(np.uint8)


def pick_imgsz(img_bgr, choice, base=IMGSZ):
    """Training used 2800-px-wide strips at imgsz 1024 (scale 0.37). Upscaling a small photo to 1024 makes
    defects 2-3x larger than anything seen in training and produces spurious boxes, so small inputs run
    closer to native resolution."""
    if choice != "Auto":
        return int(choice)
    side = max(img_bgr.shape[:2])
    if side >= 1600:
        return base
    return int(min(base, max(416, round(side * 1.6 / 32) * 32)))


def run_one(model, img_bgr, conf, iou, imgsz=IMGSZ):
    t = time.time()
    r = model.predict(img_bgr, imgsz=imgsz, conf=conf, iou=iou, verbose=False, device="cpu")[0]
    dt = time.time() - t
    n = len(r.boxes)
    boxes = r.boxes.xyxy.cpu().numpy() if n else np.zeros((0, 4))
    cls = r.boxes.cls.cpu().numpy().astype(int) if n else np.zeros(0, int)
    confs = r.boxes.conf.cpu().numpy() if n else np.zeros(0)
    order = np.argsort(-confs)
    boxes, cls, confs = boxes[order], cls[order], confs[order]
    dets = [dict(cls=model.names[int(c)], conf=round(float(p), 3), x1=int(b[0]), y1=int(b[1]), x2=int(b[2]), y2=int(b[3]),
                 w=int(b[2] - b[0]), h=int(b[3] - b[1])) for c, p, b in zip(cls, confs, boxes)]
    return dict(boxes=boxes, confs=confs, dets=dets, dt=dt, speed=r.speed, imgsz=imgsz)


def run_fused(fkey, img_bgr, conf, iou, size_choice="Auto"):
    """Every member at a low threshold and its own input size, fused with WBF, then the user's threshold."""
    F = FUSIONS[fkey]; names = F["names"]
    parts, dt, inf = [], 0.0, 0.0
    for k, base in F["parts"]:
        r = run_one(get_model(k), img_bgr, min(conf, 0.05), iou, pick_imgsz(img_bgr, size_choice, base))
        parts.append(dict(pred_boxes=r["boxes"].tolist(), pred_conf=r["confs"].tolist(),
                          pred_cls=[names.index(d["cls"]) for d in r["dets"]]))
        dt += r["dt"]; inf += r["speed"]["inference"]
    b, c, k = wbf_image(parts, F["cfg"]["weights"], F["cfg"]["t_iou"])
    NAMES_ = names
    keep = [i for i in np.argsort(-np.asarray(c)) if c[i] >= conf] if c else []
    boxes = np.array([b[i] for i in keep]).reshape(-1, 4); confs = np.array([c[i] for i in keep])
    dets = [dict(cls=NAMES_[k[i]], conf=round(float(c[i]), 3), x1=int(b[i][0]), y1=int(b[i][1]), x2=int(b[i][2]),
                 y2=int(b[i][3]), w=int(b[i][2] - b[i][0]), h=int(b[i][3] - b[i][1])) for i in keep]
    return dict(boxes=boxes, confs=confs, dets=dets, dt=dt, speed={"inference": inf}, imgsz="per member")


def predict_any(key, img_bgr, conf, iou, imgsz, size_choice="Auto"):
    """(result, class names the model can detect) for a single model or a fusion."""
    if key in FUSIONS:
        return run_fused(key, img_bgr, conf, iou, size_choice), set(FUSIONS[key]["names"])
    m = get_model(key)
    return run_one(m, img_bgr, conf, iou, imgsz), set(m.names.values())


def per_class(dets, img_shape):
    """Count and area share per class. Area = union of boxes of that class (mask), so overlaps are not double counted."""
    h, w = img_shape[:2]
    rows, total = [], np.zeros((h, w), bool)
    for name in NAMES:
        ds = [d for d in dets if d["cls"] == name]
        if not ds:
            continue
        m = np.zeros((h, w), bool)
        for d in ds:
            m[d["y1"]:d["y2"], d["x1"]:d["x2"]] = True
        total |= m
        rows.append([name, len(ds), round(float(100 * m.mean()), 2), round(float(np.mean([d["conf"] for d in ds])), 3)])
    return rows, round(float(100 * total.mean()), 2)


def summarize(dets):
    if not dets:
        return "**No defects detected at this confidence.** The board section looks clean, or lower the threshold."
    counts = {}
    for d in dets:
        counts[d["cls"]] = counts.get(d["cls"], 0) + 1
    return f"**{len(dets)} defect(s):** " + ", ".join(f"**{k}** x{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))


# ---------------------------------------------------------------- detect tab
def detect(image, model_key, conf, iou, compare, size_choice, show_heat,
           price=1500.0, length=2400.0, width=150.0, thick=25.0, fA=1.0, fB=0.85, fC=0.65, fR=0.30):
    if image is None:
        raise gr.Error("Upload a board image first.")
    img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    keys = list(WEIGHTS) if compare else [model_key]
    det_rows, cls_rows, grade_rows, notes = [], [], [], []
    board = bri.board_extent(img_bgr)
    vol_cft = float(length) * float(width) * float(thick) / CFT_MM3
    factor = {"A": fA, "B": fB, "C": fC, "Reject": fR}
    report = dict(generated=datetime.now().isoformat(timespec="seconds"), input_size=[int(image.shape[1]), int(image.shape[0])],
                  conf=conf, iou=iou, price_inputs=dict(price_per_cft=price, length_mm=length, width_mm=width,
                  thickness_mm=thick, grade_factors=factor), models={})
    shots = []          # (label, RGB image) in display order
    for k in keys:
        imgsz = pick_imgsz(img_bgr, size_choice, train_imgsz(k))
        res, _ = predict_any(k, img_bgr, conf, iou, imgsz, size_choice)
        labels = [f"{d['cls']} {d['conf']:.2f}" for d in res["dets"]]
        shots.append((f"{k} - detections", cv2.cvtColor(draw_boxes(img_bgr, res["boxes"], labels), cv2.COLOR_BGR2RGB)))
        if show_heat:
            shots.append((f"{k} - defect heatmap", cv2.cvtColor(heatmap(img_bgr, res["boxes"], res["confs"]), cv2.COLOR_BGR2RGB)))
        short = "Fusion" if k in FUSIONS else k.split(" ")[0]
        det_rows += [[short, d["cls"], d["conf"], d["x1"], d["y1"], d["x2"], d["y2"], d["w"], d["h"]] for d in res["dets"]]
        pc, cov = per_class(res["dets"], img_bgr.shape)
        cls_rows += [[short] + r for r in pc]
        taus, _, calibrated = bri_cfg(k)
        g = bri.board_report([(d["cls"], d["conf"], (d["x1"], d["y1"], d["x2"], d["y2"])) for d in res["dets"]],
                             img_bgr.shape, board, taus=taus)
        full = vol_cft * float(price) * float(fA)
        value = vol_cft * g["recoverable_pct"] / 100 * float(price) * float(factor[g["grade"]])
        grade_rows.append([short, g["grade"], round(g["DIS"], 5), g["recoverable_pct"], g["coverage_pct"], g["n_defects"],
                           round(value), round(full - value)])
        notes.append(f"**{k}**: {summarize(res['dets'])}  \n{grade_badge(g['grade'])} damage score **{g['DIS']:.4f}**, "
                     f"recoverable **{g['recoverable_pct']:.1f}%** of the board area, estimated value **Rs {value:,.0f}** "
                     f"(Rs {full - value:,.0f} lost to defects)"
                     + ("" if calibrated else " _(grade thresholds not yet calibrated for this model)_") + "  \n"
                     f"_{res['dt']*1000:.0f} ms on CPU (inference {res['speed']['inference']:.0f} ms), run at imgsz {imgsz}_")
        report["models"][k] = dict(imgsz=imgsz, detections=res["dets"],
                                   per_class=[dict(cls=r[0], count=r[1], area_pct=r[2], mean_conf=r[3]) for r in pc],
                                   coverage_pct=cov, grading=dict(grade=g["grade"], damage_score=g["DIS"],
                                   recoverable_pct=g["recoverable_pct"], thresholds=taus, defects=g["defects"]),
                                   estimated_value_rs=round(value), latency_ms=round(res["dt"] * 1000),
                                   inference_ms=round(res["speed"]["inference"], 1))
    if image.shape[1] < 1000:
        notes.append("_Note: the models were trained on 2800x1024 line-scan strips under even lighting. Small photos, "
                     "screenshots or stock images are outside that domain; treat these boxes as indicative only. "
                     "Watermarks and printed text tend to be reported as Resin._")
    fd, path = tempfile.mkstemp(prefix="wood_report_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    # fill the six image slots; hide the ones not used so nothing is cropped or squeezed
    slots = []
    for i in range(6):
        if i < len(shots):
            slots.append(gr.update(value=shots[i][1], label=shots[i][0], visible=True))
        else:
            slots.append(gr.update(value=None, visible=False))
    return (*slots, "\n\n".join(notes), grade_rows, cls_rows, det_rows, path)


# ---------------------------------------------------------------- test-board tab
TEST_IMG = sorted(glob.glob(str(ROOT / "dataset_clean" / "test" / "images" / "*.jpg")))
if not TEST_IMG:  # deployed copy ships a small sample in samples/{images,labels}
    TEST_IMG = sorted(glob.glob(str(ROOT / "samples" / "images" / "*.jpg")))


def load_gt(img_path):
    lbl = Path(img_path).parent.parent / "labels" / (Path(img_path).stem + ".txt")
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    boxes, labels = [], []
    if lbl.exists():
        for line in lbl.read_text().splitlines():
            p = line.split()
            if len(p) < 5:
                continue
            c, cx, cy, bw, bh = int(p[0]), *map(float, p[1:5])
            boxes.append(((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h))
            labels.append(NAMES[c])
    return img, boxes, labels


def test_board(pick, model_key, conf, iou):
    if not TEST_IMG:
        raise gr.Error("No test images found (dataset_clean/test or samples/ next to app.py).")
    path = random.choice(TEST_IMG) if pick == "random" else pick
    img, gboxes, glabels = load_gt(path)
    res, known = predict_any(model_key, img, conf, iou, train_imgsz(model_key))   # 4-class models: own classes only
    other = [l for l in glabels if l not in known]
    gboxes = [b for b, l in zip(gboxes, glabels) if l in known]
    glabels = [l for l in glabels if l in known]
    gt_vis = draw_boxes(img, gboxes, glabels)
    vis = draw_boxes(img, res["boxes"], [f"{d['cls']} {d['conf']:.2f}" for d in res["dets"]])
    board = Path(path).stem.split("_")[-1][:4]
    gt_counts = {}
    for l in glabels:
        gt_counts[l] = gt_counts.get(l, 0) + 1
    gt_txt = ", ".join(f"{k} x{v}" for k, v in gt_counts.items()) or "none (background image)"
    if other:
        gt_txt += f" (not shown: {len(other)} box(es) of classes this model does not detect: {', '.join(sorted(set(other)))})"
    taus, tref, _ = bri_cfg(model_key)
    bx = bri.board_extent(img)
    g_ref = bri.board_report([(l, 1.0, b) for l, b in zip(glabels, gboxes)], img.shape, bx, taus=tref)
    g_pred = bri.board_report([(d["cls"], d["conf"], (d["x1"], d["y1"], d["x2"], d["y2"])) for d in res["dets"]],
                              img.shape, bx, taus=taus)
    md = (f"**{Path(path).name}** from board **{board}**, one of the 12 boards never used in training.  \n"
          f"Ground truth: {gt_txt}  \nPrediction: {summarize(res['dets']).replace('**', '')}  ({res['dt']*1000:.0f} ms on CPU)  \n"
          f"Grade from the annotations: {grade_badge(g_ref['grade'])} (damage {g_ref['DIS']:.4f})  "
          f"Grade from the model: {grade_badge(g_pred['grade'])} (damage {g_pred['DIS']:.4f})")
    return (cv2.cvtColor(gt_vis, cv2.COLOR_BGR2RGB),
            gr.update(value=cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), label=f"Prediction: {model_key}"),
            md)


# ---------------------------------------------------------------- results tab
def read(p):
    p = ROOT / p
    return p.read_text(encoding="utf-8") if p.exists() else f"_missing: {p.name}_"


RESULTS_MD = f"""
## Final test results (12 held-out boards, 469 images, 1,023 boxes; evaluated exactly once per model)

| Model | Test mAP50 | Test mAP50-95 | Precision | Recall | F1 | ms/img (T4) | Params |
|---|---:|---:|---:|---:|---:|---:|---:|
| YOLO11s, old 640 run, leaky tile split | 62.2 | -- | 73.1 | -- | -- | -- | 9.4 M |
| **YOLO11s, 1024 rect, clean board split** | **64.6** | 33.4 | 71.0 | 64.1 | 67.4 | 11.7 | 9.4 M |
| **YOLO11m, 1024 rect, clean board split** | 63.0 | **34.0** | 63.4 | 66.2 | 64.7 | 33.2 | 20.0 M |

The two clean-split models are tied within the noise of a 12-board test set. Crack improved from 42.2 (old)
to 53-58 (new). Quartzity is unlearned by both (125 training boxes). Capacity is not the bottleneck; data is.

## Mathematical model and final models (test, each evaluated once; all settings chosen on validation)

| Model | Classes | Test mAP50 | Test mAP50-95 |
|---|---:|---:|---:|
| **Fusion (WBF) YOLO11m + YOLO11s** | 8 | **65.7** | **36.1** |
| YOLO11s, 4 classes, no balancing | 4 | 71.7 | 33.4 |
| **YOLO11s, 4 classes, partial balance (final single model)** | 4 | 69.2 | 33.1 |
| YOLO11s, 4 classes, partial balance, 1280 px | 4 | 71.6 | 34.3 |
| Fusion (WBF) of four 4-class YOLO11s models (4,000-image subset) | 4 | 74.7 | 36.7 |
| YOLO11s 4-class, full dataset (20,276 images), 1024 px | 4 | 75.7 | 37.9 |
| YOLO11s 4-class, full dataset, 1280 px | 4 | 76.1 | 38.8 |
| **Final: fusion (WBF) of the two full-dataset models (deployed)** | 4 | **76.9** | **39.3** |

Fusion raises mAP50-95 by +2.4 over YOLO11s (95% board-bootstrap interval +1.6 to +3.2). On the same four classes the
8-class YOLO11s scores 69.6 mAP50. Training on the full dataset (407 boards; our 81 boards keep their split) lifts the
final system to 76.9 on the same 469 test images (+2.2 over the subset fusion, board-bootstrap interval +0.5 to +4.3) and
to **81.3 mAP50 / 44.1 mAP50-95 on the full test split** (2,488 images, 51 boards; AP50 Live_Knot 87.1, Dead_Knot 87.5,
Resin 83.3, Crack 67.4). Grading (Board Recoverability Index) with the final detector agrees with annotation-based
grades with weighted kappa 0.87 on the test images (exact 78.3%, within one grade 97.4%; 10 of 12 boards exact).

### YOLO11m per class (test)
{read('eval/yolo11m_final/test_metrics.md')}

### YOLO11s per class (test)
{read('eval/yolo11s_baseline/test_metrics.md')}

## Class mapping (the dataset's real names; the team's earlier names were wrong)

| id | Real name | What it looks like | Earlier wrong name |
|---|---|---|---|
""" + "\n".join(f"| {i} | {n} | {DESCR[n]} | {o} |" for i, (n, o) in enumerate(zip(NAMES, ["Crack", "Knot", "Hole", "Stain", "Split", "Warp", "Decay", "Scratch"]))) + """

## What changed versus the earlier YOLO11s run
1. Board-level split: the earlier split put every physical board in train, val and test (tile-level). Now 52 / 17 / 12 boards, zero overlap.
2. Correct class names (table above).
3. 1024 rectangular training instead of 640 square: no 63% black padding, 1.6x more pixels on thin defects.
4. Grain-safe augmentation: no rotation, no vertical flip, erasing 0.05.
5. Batch 32, lr0 0.001, patience 40 after run 1 showed an unstable curve.
"""

CM_M = str(ROOT / "eval" / "yolo11m_final" / "confusion_matrix_normalized.png")
CM_S = str(ROOT / "eval" / "yolo11s_baseline" / "confusion_matrix_normalized.png")
CURVE_M = str(ROOT / "runs_log" / "run2_yolo11m_1024rect_b32_lr001_v8" / "results.png")
CURVE_S = str(ROOT / "runs_log" / "run3_yolo11s_1024rect_b32_lr001_v9" / "results.png")

CSS = """
.hero {text-align:center; padding:26px 16px 18px; border-radius:14px; margin-bottom:8px;
       background: linear-gradient(120deg, #3b2a1a 0%, #7a5230 55%, #b8834a 100%); color:#fff;}
.hero h1 {margin:0 0 6px; font-size:2.1em; letter-spacing:.3px; color:#fff;}
.hero p {margin:2px 0; opacity:.92; color:#fff;}
.hero .chips span {display:inline-block; margin:8px 4px 0; padding:4px 10px; border-radius:999px;
                   background:rgba(255,255,255,.16); font-size:.85em;}
"""
HERO = """
<div class="hero">
  <h1>Wood Quality AI</h1>
  <p>Wood surface defect detection and localisation with YOLO11</p>
  <div class="chips"><span>defect detection + quality grade</span><span>board-level held-out test</span>
  <span>YOLO11m vs YOLO11s, identical training</span><span>runs on CPU</span></div>
</div>
"""

with gr.Blocks(title="Wood Quality AI - YOLO11 defect detection") as demo:
    gr.HTML(HERO)
    with gr.Tab("Detect on your image"):
        with gr.Row():
            with gr.Column(scale=1):
                inp = gr.Image(label="Board image (jpg/png; wide 2800x1024 strips work best)", type="numpy")
                model_dd = gr.Dropdown(MODEL_CHOICES, value=MODEL_CHOICES[0], label="Model")
                with gr.Row():
                    compare = gr.Checkbox(False, label="Run all models")
                    show_heat = gr.Checkbox(True, label="Show defect heatmap")
                conf = gr.Slider(0.05, 0.9, value=0.35, step=0.05, label="Confidence threshold")
                iou = gr.Slider(0.3, 0.9, value=0.6, step=0.05, label="NMS IoU")
                size_dd = gr.Dropdown(["Auto", "1024", "640", "416"], value="Auto",
                                      label="Input size (Auto = 1024 for full strips, near-native for small photos)")
                with gr.Accordion("Market value estimate (illustrative inputs; replace with the mill's price list)", open=False):
                    with gr.Row():
                        price = gr.Number(1500, label="Grade-A price (Rs per cubic foot)")
                        length = gr.Number(2400, label="Length (mm)")
                    with gr.Row():
                        width = gr.Number(150, label="Width (mm)")
                        thick = gr.Number(25, label="Thickness (mm)")
                    with gr.Row():
                        fA = gr.Number(1.0, label="Factor A")
                        fB = gr.Number(0.85, label="Factor B")
                    with gr.Row():
                        fC = gr.Number(0.65, label="Factor C")
                        fR = gr.Number(0.30, label="Factor Reject")
                btn = gr.Button("Analyse image", variant="primary")
            with gr.Column(scale=2):
                out_img1 = gr.Image(label="Detections", buttons=["fullscreen", "download"])
                out_img2 = gr.Image(label="Defect heatmap", buttons=["fullscreen", "download"], visible=False)
                out_img3 = gr.Image(label="Second model", buttons=["fullscreen", "download"], visible=False)
                out_img4 = gr.Image(label="Second model heatmap", buttons=["fullscreen", "download"], visible=False)
                out_img5 = gr.Image(label="Third model", buttons=["fullscreen", "download"], visible=False)
                out_img6 = gr.Image(label="Third model heatmap", buttons=["fullscreen", "download"], visible=False)
                out_md = gr.Markdown()
                out_grade = gr.Dataframe(headers=["model", "grade", "damage score", "recoverable %", "coverage %",
                                                  "defects", "est. value (Rs)", "value lost (Rs)"],
                                         label="Quality grade (Board Recoverability Index) and value", wrap=True)
                out_cls = gr.Dataframe(headers=["model", "class", "count", "area %", "mean conf"], label="Per-class breakdown", wrap=True)
                out_tbl = gr.Dataframe(headers=["model", "class", "conf", "x1", "y1", "x2", "y2", "w", "h"], label="Detections", wrap=True)
                out_json = gr.File(label="Download report (JSON)")
        btn.click(detect, [inp, model_dd, conf, iou, compare, size_dd, show_heat, price, length, width, thick, fA, fB, fC, fR],
                  [out_img1, out_img2, out_img3, out_img4, out_img5, out_img6, out_md, out_grade, out_cls, out_tbl, out_json])
    with gr.Tab("Test boards: ground truth vs prediction"):
        gr.Markdown("Images from the 12 held-out test boards. Left: annotator's boxes. Right: model output. "
                    "Colours are per class and identical on both sides.")
        with gr.Row():
            pick = gr.Dropdown(["random"] + TEST_IMG, value="random", label="Test image", allow_custom_value=False, scale=3)
            model_dd2 = gr.Dropdown(MODEL_CHOICES, value=MODEL_CHOICES[0], label="Model", scale=2)
            conf2 = gr.Slider(0.05, 0.9, value=0.35, step=0.05, label="Confidence", scale=1)
            iou2 = gr.Slider(0.3, 0.9, value=0.6, step=0.05, label="NMS IoU", scale=1)
        btn2 = gr.Button("Show", variant="primary")
        gt_img = gr.Image(label="Ground truth (annotator)", buttons=["fullscreen", "download"])
        pred_img = gr.Image(label="Prediction", buttons=["fullscreen", "download"])
        md2 = gr.Markdown()
        btn2.click(test_board, [pick, model_dd2, conf2, iou2], [gt_img, pred_img, md2])
    with gr.Tab("Results"):
        gr.Markdown(RESULTS_MD)
        with gr.Row():
            gr.Image(CM_M, label="Test confusion matrix, YOLO11m", interactive=False)
            gr.Image(CM_S, label="Test confusion matrix, YOLO11s", interactive=False)
        with gr.Row():
            gr.Image(CURVE_M, label="Training curves, YOLO11m run 2", interactive=False)
            gr.Image(CURVE_S, label="Training curves, YOLO11s", interactive=False)
    with gr.Tab("Legend"):
        gr.Markdown("## Classes and colours\n" + "\n".join(
            f"- <span style='display:inline-block;width:14px;height:14px;background:rgb({c[2]},{c[1]},{c[0]});border:1px solid #333;margin-right:6px'></span>**{n}**: {DESCR[n]}"
            for n, c in COLORS.items()) +
            "\n\n**Quality grade (Board Recoverability Index, guide's model).** Each defect's influence is "
            "severity weight x confidence x position penalty, where the penalty 1 - exp(-d / 250 px) grows with the "
            "distance d from the nearest side edge of the board (defects near an edge can be trimmed off). The impact "
            "map keeps the largest influence per pixel, so overlapping boxes are counted once; the damage score is its "
            "sum divided by the board area, recoverable area = 1 - damage score, and the A / B / C / Reject thresholds "
            "are fitted on the validation boards. Severity weights are the guide's placeholders pending expert calibration."
            "\n\n**Market value** = board volume x recoverable share x grade-A price x grade factor. All inputs are "
            "editable and illustrative.")


def _preload():
    for k, p in WEIGHTS.items():
        if p.exists():
            try:
                get_model(k)
            except Exception as e:  # noqa: BLE001
                print("preload failed for", k, e)


if __name__ == "__main__":
    _preload()
    demo.launch(server_name=os.environ.get("GRADIO_HOST", "127.0.0.1"), server_port=int(os.environ.get("PORT", 7860)), show_error=True, css=CSS)
