"""
bri_validate.py - validate the BRI grading pipeline (detector + bri.py) against a reference grading.

No expert grades exist yet, so the reference is BRI applied to the annotators' boxes (confidence 1.0):
  1. Reference thresholds: quantiles of the ground-truth damage score on the VALIDATION boards
     (default 40 / 70 / 90 % -> about 40 % A, 30 % B, 20 % C, 10 % Reject).
  2. Automatic grader: BRI on the detector's boxes. Its thresholds are fitted on the VALIDATION boards with
     the guide's calibrate_thresholds (grid search maximising quadratic weighted kappa against the reference),
     because confidence weighting makes predicted damage scores systematically smaller than annotated ones.
  3. TEST boards (never used for any fitting): agreement per image and per physical board -
     exact agreement, within-one-grade agreement, quadratic weighted kappa, Spearman rho of the damage
     scores, mean absolute error of the recoverable percentage, grade confusion matrix.

python bri_validate.py --weights weights/yolo11s_4cls_balanced.pt --imgsz 1024
"""
import argparse, glob, json
from collections import defaultdict
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO
import bri
from eval_capture import spearman

GR = bri.GRADES


def gt_dets(lbl, names, w, h):
    out = []
    if lbl.exists():
        for ln in lbl.read_text().splitlines():
            v = ln.split()
            if len(v) == 5:
                c, xc, yc, bw, bh = int(v[0]), *map(float, v[1:])
                out.append((names[c], 1.0, ((xc - bw / 2) * w, (yc - bh / 2) * h, (xc + bw / 2) * w, (yc + bh / 2) * h)))
    return out


def predict_cached(model, weights, imgsz, conf, imgs, cache):
    if cache.exists():
        return json.loads(cache.read_text())
    out = {}
    for p in imgs:
        r = model.predict(p, imgsz=imgsz, conf=conf, iou=0.6, verbose=False, device="cpu")[0]
        out[Path(p).stem] = [(model.names[int(c)], float(f), [float(x) for x in b])
                             for b, c, f in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out))
    return out


def scores(split, data, names, preds, severity):
    rows = []
    for p in sorted(glob.glob(f"{data}/{split}/images/*.jpg")):
        stem = Path(p).stem
        img = cv2.imread(p); h, w = img.shape[:2]
        board = bri.board_extent(img)
        g = bri.board_report(gt_dets(Path(data) / split / "labels" / f"{stem}.txt", names, w, h), (h, w), board, severity)
        q = bri.board_report([(n, c, tuple(b)) for n, c, b in preds[stem]], (h, w), board, severity)
        rows.append(dict(stem=stem, board=stem.split("_", 1)[1][:4], dis_gt=g["DIS"], dis_pred=q["DIS"],
                         n_gt=g["n_defects"], n_pred=q["n_defects"]))
    return rows


def to_grade(d, taus):
    return GR.index(bri.grade(d, taus))


def calibrate(dis, ref, n=40):
    """Guide's calibrate_thresholds: grid search t1 < t2 < t3 maximising weighted kappa."""
    cand = np.unique(np.quantile(dis, np.linspace(0.02, 0.98, n)))
    best, bk = None, -2
    for i, a in enumerate(cand):
        for j in range(i + 1, len(cand)):
            for m in range(j + 1, len(cand)):
                pred = [to_grade(d, (a, cand[j], cand[m])) for d in dis]
                k = bri.quadratic_weighted_kappa(ref, pred)
                if k > bk:
                    best, bk = (float(a), float(cand[j]), float(cand[m])), k
    return best, bk


def agreement(ref, pred, dg, dp):
    ref, pred = np.array(ref), np.array(pred)
    cm = np.zeros((4, 4), int)
    for a, b in zip(ref, pred):
        cm[a, b] += 1
    return dict(n=len(ref), exact=float(np.mean(ref == pred)), within_one=float(np.mean(abs(ref - pred) <= 1)),
                qwk=float(bri.quadratic_weighted_kappa(ref, pred)), spearman=spearman(dg, dp),
                mae_recoverable_pct=float(np.mean(np.abs(100 * (np.array(dg) - np.array(dp))))), confusion=cm.tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights/yolo11s_4cls_balanced.pt")
    ap.add_argument("--imgsz", type=int, default=1024)
    ap.add_argument("--data", default="dataset_4cls")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--quantiles", type=float, nargs=3, default=[0.40, 0.70, 0.90])
    ap.add_argument("--out", default="eval/bri")
    a = ap.parse_args()
    if Path(a.weights).stem.startswith("fusion"):      # fused detector: predictions come from the cache only
        model, names = None, ["Live_Knot", "Dead_Knot", "Resin", "Crack"]
    else:
        model = YOLO(a.weights)
        names = [model.names[i] for i in range(len(model.names))]
    severity = {n: bri.SEVERITY[n] for n in names}
    tag = Path(a.weights).stem
    res = {}
    for split in ["val", "test"]:
        imgs = sorted(glob.glob(f"{a.data}/{split}/images/*.jpg"))
        preds = predict_cached(model, a.weights, a.imgsz, a.conf, imgs, Path(a.out) / f"pred_{tag}_{a.imgsz}_{split}.json")
        res[split] = scores(split, a.data, names, preds, severity)
    vg = np.array([r["dis_gt"] for r in res["val"]]); vp = np.array([r["dis_pred"] for r in res["val"]])
    tau_ref = tuple(float(x) for x in np.quantile(vg, a.quantiles))
    ref_val = [to_grade(d, tau_ref) for d in vg]
    tau_pred, k_val = calibrate(vp, ref_val)
    out = dict(weights=a.weights, imgsz=a.imgsz, conf=a.conf, severity=severity, lam=bri.LAMBDA,
               tau_reference=tau_ref, tau_detector=tau_pred, val_qwk_after_fit=k_val,
               val_reference_grade_share={g: float(np.mean(np.array(ref_val) == i)) for i, g in enumerate(GR)})
    # test: per image
    t = res["test"]
    tg = [r["dis_gt"] for r in t]; tp = [r["dis_pred"] for r in t]
    out["test_per_image"] = agreement([to_grade(d, tau_ref) for d in tg], [to_grade(d, tau_pred) for d in tp], tg, tp)
    # test: per physical board (mean damage over its images)
    by = defaultdict(list)
    for r in t:
        by[r["board"]].append(r)
    bg = [float(np.mean([r["dis_gt"] for r in v])) for v in by.values()]
    bp = [float(np.mean([r["dis_pred"] for r in v])) for v in by.values()]
    out["test_per_board"] = agreement([to_grade(d, tau_ref) for d in bg], [to_grade(d, tau_pred) for d in bp], bg, bp)
    out["test_boards"] = {b: dict(images=len(v), dis_gt=float(np.mean([r["dis_gt"] for r in v])),
                                  dis_pred=float(np.mean([r["dis_pred"] for r in v]))) for b, v in sorted(by.items())}
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / f"bri_validation_{tag}_{a.imgsz}.json").write_text(json.dumps(out, indent=2))
    pi, pb = out["test_per_image"], out["test_per_board"]
    print(json.dumps({k: out[k] for k in ("tau_reference", "tau_detector", "val_qwk_after_fit", "val_reference_grade_share")}, indent=1))
    for nm, d in [("per image", pi), ("per board", pb)]:
        print(f"TEST {nm}: n={d['n']} exact {100*d['exact']:.1f}%  within-one {100*d['within_one']:.1f}%  "
              f"QWK {d['qwk']:.3f}  Spearman {d['spearman']:.3f}  MAE recoverable {d['mae_recoverable_pct']:.2f} pts")
        print("  confusion (rows reference A,B,C,R; cols detector):", d["confusion"])


if __name__ == "__main__":
    main()
