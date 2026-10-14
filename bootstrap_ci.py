"""
bootstrap_ci.py - board-level bootstrap confidence intervals for the 4-class models.

The val (17 boards) and test (12 boards) splits are small, so a 2-point mAP difference can be chance.
This script predicts every image once per model (conf 0.001, iou 0.6, imgsz 1024, same as evaluate.py),
matches predictions to ground truth exactly like Ultralytics (10 IoU thresholds 0.50-0.95), then
resamples whole BOARDS with replacement B times and recomputes mAP for every model on the same resample
(paired). Reported: point estimate, 95 % percentile interval, and for each model pair the interval of
the difference and the share of resamples in which the first model is not better.
No model is selected or tuned here; it only measures the uncertainty of numbers already reported.

python bootstrap_ci.py --split test --B 2000
"""
import argparse, glob, json
from collections import defaultdict
from pathlib import Path
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.metrics import ap_per_class

KEEP = ["Live_Knot", "Dead_Knot", "Resin", "Crack"]
MODELS = {
    "8-class YOLO11s baseline (4 classes scored)": "weights/yolo11s_baseline.pt",
    "4-class plain": "weights/yolo11s_4cls_plain.pt",
    "4-class sqrt-balanced": "weights/yolo11s_4cls_balanced.pt",
}
IOUV = np.linspace(0.5, 0.95, 10)


def iou_matrix(a, b):
    """a: (n,4) gt, b: (m,4) pred, xyxy -> (n,m)"""
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    tl = np.maximum(a[:, None, :2], b[None, :, :2]); br = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.clip(br - tl, 0, None).prod(2)
    area = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])
    return inter / (area(a)[:, None] + area(b)[None, :] - inter + 1e-9)


def match(pred_cls, true_cls, iou):
    """Ultralytics BaseValidator.match_predictions (non-scipy path)."""
    correct = np.zeros((len(pred_cls), len(IOUV)), bool)
    iou = iou * (true_cls[:, None] == pred_cls[None, :])
    for i, t in enumerate(IOUV):
        m = np.array(np.nonzero(iou >= t)).T
        if m.shape[0]:
            if m.shape[0] > 1:
                m = m[iou[m[:, 0], m[:, 1]].argsort()[::-1]]
                m = m[np.unique(m[:, 1], return_index=True)[1]]
                m = m[np.unique(m[:, 0], return_index=True)[1]]
            correct[m[:, 1].astype(int), i] = True
    return correct


def read_gt(lbl, W, H):
    boxes, cls = [], []
    if lbl.exists():
        for ln in lbl.read_text().splitlines():
            v = ln.split()
            if len(v) == 5:
                c, xc, yc, w, h = int(v[0]), *map(float, v[1:])
                boxes.append([(xc - w / 2) * W, (yc - h / 2) * H, (xc + w / 2) * W, (yc + h / 2) * H]); cls.append(c)
    return np.array(boxes).reshape(-1, 4), np.array(cls, int)


def per_image_stats(model, img_paths, lbl_dir):
    out = {}
    name2new = {n: i for i, n in enumerate(KEEP)}
    for p in img_paths:
        r = model.predict(p, imgsz=1024, conf=0.001, iou=0.6, max_det=300, verbose=False, device="cpu")[0]
        H, W = r.orig_shape
        gb, gc = read_gt(lbl_dir / (Path(p).stem + ".txt"), W, H)
        pb = r.boxes.xyxy.numpy(); pc = r.boxes.cls.numpy().astype(int); pf = r.boxes.conf.numpy()
        newc = np.array([name2new.get(model.names[c], -1) for c in pc], int)
        keep = newc >= 0                                    # an 8-class model is scored on the 4 classes only
        pb, pc, pf = pb[keep], newc[keep], pf[keep]
        tp = match(pc, gc, iou_matrix(gb, pb)) if len(pc) else np.zeros((0, len(IOUV)), bool)
        out[Path(p).stem] = (tp, pf, pc, gc)
    return out


def maps(stats, stems):
    tp = np.concatenate([stats[s][0] for s in stems]); cf = np.concatenate([stats[s][1] for s in stems])
    pc = np.concatenate([stats[s][2] for s in stems]); tc = np.concatenate([stats[s][3] for s in stems])
    res = ap_per_class(tp, cf, pc, tc)
    ap, cls = res[5], res[6]
    per = {KEEP[c]: (100 * ap[k, 0], 100 * ap[k].mean()) for k, c in enumerate(cls)}
    m50 = float(np.mean([per[c][0] for c in KEEP if c in per])) if per else 0.0
    m95 = float(np.mean([per[c][1] for c in KEEP if c in per])) if per else 0.0
    return m50, m95, per


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--data", default="dataset_4cls")
    ap_.add_argument("--split", default="test", choices=["val", "test"])
    ap_.add_argument("--B", type=int, default=2000)
    ap_.add_argument("--seed", type=int, default=42)
    a = ap_.parse_args()
    imgs = sorted(glob.glob(f"{a.data}/{a.split}/images/*.jpg"))
    lbl_dir = Path(a.data) / a.split / "labels"
    boards = defaultdict(list)
    for p in imgs:
        boards[Path(p).stem.split("_", 1)[1][:4]].append(Path(p).stem)
    bids = sorted(boards)
    print(f"{a.split}: {len(imgs)} images, {len(bids)} boards")
    stats = {k: per_image_stats(YOLO(w), imgs, lbl_dir) for k, w in MODELS.items()}
    allstems = [s for b in bids for s in boards[b]]
    point = {k: maps(v, allstems) for k, v in stats.items()}
    rng = np.random.default_rng(a.seed)
    draws = defaultdict(list)
    for _ in range(a.B):
        pick = rng.choice(len(bids), len(bids), replace=True)
        stems = [s for i in pick for s in boards[bids[i]]]
        for k, v in stats.items():
            m50, m95, per = maps(v, stems)
            draws[(k, "mAP50")].append(m50); draws[(k, "mAP50-95")].append(m95)
            for c in KEEP:
                draws[(k, c)].append(per.get(c, (np.nan,))[0])
    ci = lambda x: (float(np.nanpercentile(x, 2.5)), float(np.nanpercentile(x, 97.5)))
    keys = list(MODELS)
    lines = [f"## Board-level bootstrap, {a.split} split ({len(bids)} boards, {len(imgs)} images, B={a.B}, seed {a.seed})", "",
             "| Model | mAP50 | 95% CI | mAP50-95 | 95% CI | " + " | ".join(f"{c} AP50 [95% CI]" for c in KEEP) + " |",
             "|---|---:|---|---:|---|" + "---|" * len(KEEP)]
    out = {"split": a.split, "boards": len(bids), "images": len(imgs), "B": a.B, "models": {}, "pairs": {}}
    for k in keys:
        m50, m95, per = point[k]
        c50, c95 = ci(draws[(k, "mAP50")]), ci(draws[(k, "mAP50-95")])
        pcs = []
        for c in KEEP:
            lo, hi = ci(draws[(k, c)]); pcs.append(f"{per.get(c, (float('nan'),))[0]:.1f} [{lo:.1f}, {hi:.1f}]")
        lines.append(f"| {k} | {m50:.1f} | [{c50[0]:.1f}, {c50[1]:.1f}] | {m95:.1f} | [{c95[0]:.1f}, {c95[1]:.1f}] | " + " | ".join(pcs) + " |")
        out["models"][k] = dict(mAP50=m50, mAP50_ci=c50, mAP50_95=m95, mAP50_95_ci=c95,
                                per_class={c: per.get(c, (None, None))[0] for c in KEEP})
    lines += ["", "| Difference (paired) | mAP50 diff | 95% CI | share of resamples with diff <= 0 | Crack AP50 diff | 95% CI |",
              "|---|---:|---|---:|---:|---|"]
    for i in range(len(keys)):
        for j in range(len(keys)):
            if i >= j:
                continue
            A, Bm = keys[j], keys[i]
            d = np.array(draws[(A, "mAP50")]) - np.array(draws[(Bm, "mAP50")])
            dc = np.array(draws[(A, "Crack")]) - np.array(draws[(Bm, "Crack")])
            pd = point[A][0] - point[Bm][0]
            pc_ = point[A][2].get("Crack", (np.nan,))[0] - point[Bm][2].get("Crack", (np.nan,))[0]
            lines.append(f"| {A} minus {Bm} | {pd:+.1f} | [{ci(d)[0]:+.1f}, {ci(d)[1]:+.1f}] | {np.mean(d <= 0):.2f} | "
                         f"{pc_:+.1f} | [{ci(dc)[0]:+.1f}, {ci(dc)[1]:+.1f}] |")
            out["pairs"][f"{A} - {Bm}"] = dict(diff=pd, ci=ci(d), p_not_better=float(np.mean(d <= 0)),
                                                crack_diff=pc_, crack_ci=ci(dc))
    md = "\n".join(lines) + "\n"
    Path("eval").mkdir(exist_ok=True)
    Path(f"eval/bootstrap_4cls_{a.split}.md").write_text(md, encoding="utf-8")
    Path(f"eval/bootstrap_4cls_{a.split}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
