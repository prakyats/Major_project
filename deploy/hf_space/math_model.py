"""
math_model.py - the accuracy part of the mathematical model promised at the 50 % review:

 (1) Weighted Boxes Fusion (WBF, Solovyev et al., Image and Vision Computing 2021) of several detectors.
     For every image and class, boxes of all models are clustered (IoU > t_iou with the running fused box);
     each cluster becomes one box whose coordinates are the confidence-weighted mean
         b_f = sum_i (w_m(i) c_i b_i) / sum_i (w_m(i) c_i)
     and whose confidence is the weighted mean confidence scaled by model agreement
         c_f = (sum_i w_m(i) c_i / sum_i w_m(i)) * min(sum_i w_m(i), W) / W,     W = sum of model weights,
     so a defect seen by every model keeps its confidence and one seen by a single model is down-weighted.
 (2) Per-class confidence thresholds: t_c = argmax_t F1_c(t) on the validation boards, versus one global
     threshold argmax_t macro-F1(t). Thresholds change the operating point (P, R, F1), not mAP.
 (3) Statistical validation on the test boards: paired board-level bootstrap (B resamples of the physical
     boards) for the mAP difference, and a Wilcoxon signed-rank test on per-board AP50 differences.

Every free parameter (fusion IoU, model weights, thresholds) is chosen on VALIDATION only; test is scored once.
Inputs are the validator's own predictions (eval_capture.py), so single-model numbers equal evaluate.py.

python math_model.py --models weights/yolo11m_final.pt weights/yolo11s_baseline.pt --data dataset_clean/data.yaml --tag 8cls_m_s
"""
import argparse, itertools, json
from collections import defaultdict
from pathlib import Path
import numpy as np
from eval_capture import capture, score, iou_matrix, match, wilcoxon_exact

# ------------------------------------------------------------------ (1) weighted boxes fusion
def wbf_image(per_model, weights, t_iou, skip=0.001):
    """per_model: list of dicts with pred_boxes / pred_conf / pred_cls (pixels). Returns fused lists."""
    W = float(sum(weights))
    out_b, out_c, out_k = [], [], []
    classes = set(itertools.chain.from_iterable(p["pred_cls"] for p in per_model))
    for k in classes:
        items = []
        for m, p in enumerate(per_model):
            for b, c, cl in zip(p["pred_boxes"], p["pred_conf"], p["pred_cls"]):
                if cl == k and c >= skip:
                    items.append((c * weights[m], weights[m], c, np.asarray(b, float)))
        items.sort(key=lambda x: -x[0])
        clusters, fused = [], []            # fused: (box, weighted conf sum)
        for wc, wm, c, b in items:
            j = -1
            if fused:
                ious = iou_matrix(np.array([f[0] for f in fused]), b[None])[:, 0]
                best = int(np.argmax(ious))
                if ious[best] > t_iou:
                    j = best
            if j < 0:
                clusters.append([(wc, wm, c, b)]); fused.append((b.copy(), wc))
            else:
                clusters[j].append((wc, wm, c, b))
                ws = np.array([x[0] for x in clusters[j]])
                bs = np.array([x[3] for x in clusters[j]])
                fused[j] = ((ws[:, None] * bs).sum(0) / ws.sum(), ws.sum())
        for cl, (fb, _) in zip(clusters, fused):
            wsum = sum(x[1] for x in cl)
            conf = sum(x[0] for x in cl) / wsum * min(wsum, W) / W
            out_b.append(fb.tolist()); out_c.append(float(conf)); out_k.append(int(k))
    return out_b, out_c, out_k


def fuse(caps, weights, t_iou, max_det=300):
    imgs = {}
    for s in caps[0]["images"]:
        per = [c["images"][s] for c in caps]
        b, c, k = wbf_image(per, weights, t_iou)
        o = np.argsort(-np.asarray(c))[:max_det] if c else []
        g = per[0]
        imgs[s] = dict(stem=s, pred_boxes=[b[i] for i in o], pred_conf=[c[i] for i in o], pred_cls=[k[i] for i in o],
                       gt_boxes=g["gt_boxes"], gt_cls=g["gt_cls"])
    return rematch(imgs)


def rematch(images):
    """Recompute the true-positive matrix in original pixels, so single and fused predictions are scored
    identically; the result is cached in 'tp' so bootstrap resampling does not re-match."""
    out = {}
    for s, im in images.items():
        d = {k: v for k, v in im.items() if k != "tp"}
        d["tp"] = match(d["pred_cls"], d["gt_cls"], iou_matrix(d["gt_boxes"], d["pred_boxes"])).astype(int).tolist()
        out[s] = d
    return out


# ------------------------------------------------------------------ (2) per-class thresholds
def tp_table(images):
    rows = defaultdict(list); ngt = defaultdict(int)
    for im in images.values():
        tp = match(im["pred_cls"], im["gt_cls"], iou_matrix(im["gt_boxes"], im["pred_boxes"]))[:, 0] \
            if im["pred_cls"] else np.zeros(0, bool)
        for c, cf, t in zip(im["pred_cls"], im["pred_conf"], tp):
            rows[c].append((cf, bool(t)))
        for g in im["gt_cls"]:
            ngt[g] += 1
    return rows, ngt


def prf(rows, ngt, c, t):
    sel = [x for x in rows.get(c, []) if x[0] >= t]
    tp = sum(x[1] for x in sel); fp = len(sel) - tp; fn = ngt.get(c, 0) - tp
    p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


GRID = np.round(np.arange(0.05, 0.91, 0.01), 2)


def fit_thresholds(val_images, classes):
    rows, ngt = tp_table(val_images)
    per = {c: float(GRID[int(np.argmax([prf(rows, ngt, c, t)[2] for t in GRID]))]) for c in classes}
    glob_t = float(GRID[int(np.argmax([np.mean([prf(rows, ngt, c, t)[2] for c in classes]) for t in GRID]))])
    return per, glob_t


def operating_point(images, classes, thr):
    rows, ngt = tp_table(images)
    res = {c: prf(rows, ngt, c, thr[c] if isinstance(thr, dict) else thr) for c in classes}
    P = np.mean([v[0] for v in res.values()]); R = np.mean([v[1] for v in res.values()])
    return dict(P=float(P), R=float(R), F1=float(np.mean([v[2] for v in res.values()])),
                per_class={int(c): [round(100 * x, 1) for x in v] for c, v in res.items()})


# ------------------------------------------------------------------ (3) statistics
def boards_of(images):
    b = defaultdict(list)
    for s in images:
        b[s.split("_", 1)[1][:4]].append(s)
    return b


def paired_tests(img_a, img_b, B=2000, seed=42):
    """A minus B: bootstrap CI over boards for mAP50 / mAP50-95, Wilcoxon on per-board AP50 means."""
    bd = boards_of(img_a); ids = sorted(bd)
    rng = np.random.default_rng(seed)
    d50, d95 = [], []
    for _ in range(B):
        st = [s for i in rng.choice(len(ids), len(ids)) for s in bd[ids[i]]]
        a, b = score(img_a, st), score(img_b, st)
        d50.append(a["map50"] - b["map50"]); d95.append(a["map"] - b["map"])
    pa = [score(img_a, bd[i])["map50"] for i in ids]
    pb = [score(img_b, bd[i])["map50"] for i in ids]
    diff = np.array(pa) - np.array(pb)
    w = wilcoxon_exact(diff)
    ci = lambda x: [round(100 * float(np.percentile(x, 2.5)), 1), round(100 * float(np.percentile(x, 97.5)), 1)]
    return dict(boards=len(ids), map50_diff_ci=ci(d50), map_diff_ci=ci(d95),
                share_not_better=float(np.mean(np.array(d50) <= 0)),
                boards_better=int((diff > 0).sum()), boards_worse=int((diff < 0).sum()),
                wilcoxon_p=w["p"], wilcoxon_n=w["n"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--imgsz", nargs="+", type=int, default=None, help="one per model (default 1024)")
    ap.add_argument("--data", nargs="+", required=True, help="data.yaml (one, or one per model)")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--B", type=int, default=1000)
    a = ap.parse_args()
    sz = a.imgsz or [1024] * len(a.models)
    dy = a.data * len(a.models) if len(a.data) == 1 else a.data
    cap = {sp: [capture(m, d, sp, s) for m, d, s in zip(a.models, dy, sz)] for sp in ["val", "test"]}
    names = cap["val"][0]["names"]; classes = list(range(len(names)))
    single_val = [score(rematch(c["images"])) for c in cap["val"]]
    # (1) choose fusion settings on val
    grid = []
    for t_iou in [0.45, 0.55, 0.65]:
        for wts in ([1] * len(a.models), *[[2 if i == j else 1 for i in range(len(a.models))] for j in range(len(a.models))]):
            r = score(fuse(cap["val"], wts, t_iou))
            grid.append(dict(t_iou=t_iou, weights=wts, val_map50=r["map50"], val_map=r["map"]))
            print("val", t_iou, wts, round(100 * r["map50"], 1), round(100 * r["map"], 1), flush=True)
    best = max(grid, key=lambda g: (round(g["val_map50"], 4), g["val_map"]))
    best_single = int(np.argmax([s["map50"] for s in single_val]))
    # test, once, with the settings fixed above
    fused_test = fuse(cap["test"], best["weights"], best["t_iou"])
    singles_test = [rematch(c["images"]) for c in cap["test"]]
    res_f = score(fused_test)
    res_s = [score(s) for s in singles_test]
    # (2) per-class thresholds for the fused model, fitted on val
    fused_val = fuse(cap["val"], best["weights"], best["t_iou"])
    per_t, glob_t = fit_thresholds(fused_val, classes)
    op_glob = operating_point(fused_test, classes, glob_t)
    op_per = operating_point(fused_test, classes, per_t)
    sp, sg = fit_thresholds(rematch(cap["val"][best_single]["images"]), classes)
    op_single_glob = operating_point(singles_test[best_single], classes, sg)
    op_single_per = operating_point(singles_test[best_single], classes, sp)
    # (3) statistics: fused vs the model that was best on val
    stats = paired_tests(fused_test, singles_test[best_single], B=a.B)
    out = dict(models=a.models, imgsz=sz, names=names, fusion_grid_val=grid, chosen=best,
               val_single_map50=[s["map50"] for s in single_val], best_single_on_val=a.models[best_single],
               test=dict(fused=dict(map50=res_f["map50"], map=res_f["map"], ap50={names[k]: v for k, v in res_f["ap50"].items()}),
                         singles={m: dict(map50=r["map50"], map=r["map"], ap50={names[k]: v for k, v in r["ap50"].items()})
                                  for m, r in zip(a.models, res_s)},
                         official_singles={m: dict(map50=c["map50"], map=c["map"]) for m, c in zip(a.models, cap["test"])}),
               thresholds=dict(per_class={names[c]: t for c, t in per_t.items()}, global_=glob_t,
                               fused_test_global=op_glob, fused_test_per_class=op_per,
                               single_thresholds={names[c]: t for c, t in sp.items()}, single_global=sg,
                               single_test_global=op_single_glob, single_test_per_class=op_single_per),
               stats_fused_minus_best_single=stats)
    Path("eval/math_model").mkdir(parents=True, exist_ok=True)
    Path(f"eval/math_model/{a.tag}.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(dict(chosen=best, test_fused=(round(100 * res_f["map50"], 1), round(100 * res_f["map"], 1)),
                          test_singles=[(round(100 * r["map50"], 1), round(100 * r["map"], 1)) for r in res_s],
                          per_class_thr=out["thresholds"]["per_class"], global_thr=glob_t,
                          F1_global=round(100 * op_glob["F1"], 1), F1_per_class=round(100 * op_per["F1"], 1),
                          single_F1_global=round(100 * op_single_glob["F1"], 1), single_F1_per_class=round(100 * op_single_per["F1"], 1),
                          stats=stats), indent=1))


if __name__ == "__main__":
    main()
