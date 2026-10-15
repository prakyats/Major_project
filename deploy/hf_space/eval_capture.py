"""
eval_capture.py - run the official Ultralytics validation and keep every image's predictions and ground truth.

The numbers of evaluate.py come from DetectionValidator (rect batches, conf 0.001, NMS IoU 0.6). Re-predicting
image by image with model.predict pads differently and shifts mAP by 2-3 points, so every post-hoc analysis
(bootstrap intervals, box fusion, per-class thresholds) must start from the validator's own predictions.
CaptureValidator stores, per image: boxes / conf / class in ORIGINAL pixel coordinates, ground truth in original
pixel coordinates, and the validator's own true-positive matrix (10 IoU thresholds).

    from eval_capture import capture
    d = capture("weights/yolo11s_4cls_plain.pt", "dataset_4cls/data_plain.yaml", "test", imgsz=1024)
    d["map50"], d["images"]["<stem>"]["pred_boxes"] ...

Results are cached in eval/capture/<weights>_<imgsz>_<split>.npz-like JSON so CPU inference runs once.
"""
import json
from pathlib import Path
import numpy as np
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionValidator
from ultralytics.utils import ops
from ultralytics.utils.metrics import ap_per_class

_STORE = []
IOUV = np.linspace(0.5, 0.95, 10)


class CaptureValidator(DetectionValidator):
    def update_metrics(self, preds, batch):
        for si, pred in enumerate(preds):
            pb = self._prepare_batch(si, batch)
            pn = self._prepare_pred(pred)
            tp = self._process_batch(pn, pb)["tp"]
            sc = self.scale_preds(pn, pb)
            gt = ops.scale_boxes(pb["imgsz"], pb["bboxes"].clone(), pb["ori_shape"], pb["ratio_pad"]) \
                if pb["cls"].shape[0] else pb["bboxes"]
            _STORE.append(dict(stem=Path(pb["im_file"]).stem, shape=list(pb["ori_shape"]),
                               pred_boxes=sc["bboxes"].cpu().numpy().round(2).tolist(),
                               pred_conf=pn["conf"].cpu().numpy().round(5).tolist(),
                               pred_cls=pn["cls"].cpu().numpy().astype(int).tolist(),
                               tp=np.asarray(tp).astype(int).tolist(),
                               gt_boxes=gt.cpu().numpy().round(2).tolist(),
                               gt_cls=pb["cls"].cpu().numpy().astype(int).tolist()))
        super().update_metrics(preds, batch)


def capture(weights, data, split, imgsz=1024, cache_dir="eval/capture", device="cpu"):
    cache = Path(cache_dir) / f"{Path(weights).stem}_{imgsz}_{split}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    _STORE.clear()
    m = YOLO(weights)
    r = m.val(data=data, split=split, imgsz=imgsz, rect=True, batch=16, conf=0.001, iou=0.6, device=device,
              plots=False, verbose=False, validator=CaptureValidator, project="weights_local/val_tmp", name="cap", exist_ok=True)
    out = dict(weights=str(weights), data=data, split=split, imgsz=imgsz, names=[m.names[i] for i in range(len(m.names))],
               map50=float(r.box.map50), map=float(r.box.map), mp=float(r.box.mp), mr=float(r.box.mr),
               speed_ms=float(r.speed["inference"]), images={d["stem"]: d for d in _STORE})
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out))
    return out


# ------------------------------------------------------------------ scoring from captured / fused predictions
def iou_matrix(a, b):
    a, b = np.asarray(a, float).reshape(-1, 4), np.asarray(b, float).reshape(-1, 4)
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    tl = np.maximum(a[:, None, :2], b[None, :, :2]); br = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.clip(br - tl, 0, None).prod(2)
    ar = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])
    return inter / (ar(a)[:, None] + ar(b)[None, :] - inter + 1e-9)


def match(pred_cls, true_cls, iou):
    """Ultralytics BaseValidator.match_predictions (non-scipy path)."""
    pred_cls, true_cls = np.asarray(pred_cls), np.asarray(true_cls)
    correct = np.zeros((len(pred_cls), len(IOUV)), bool)
    if not len(pred_cls) or not len(true_cls):
        return correct
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


def stats_from_boxes(img):
    """(tp, conf, pred_cls, target_cls) for one image whose predictions are given in original pixels."""
    tp = match(img["pred_cls"], img["gt_cls"], iou_matrix(img["gt_boxes"], img["pred_boxes"]))
    return tp, np.asarray(img["pred_conf"], float), np.asarray(img["pred_cls"], int), np.asarray(img["gt_cls"], int)


def score(images, stems=None, use_captured_tp=True, nc=None):
    """mAP50, mAP50-95 and per-class AP50 over the given images (default all)."""
    stems = stems if stems is not None else list(images)
    T, C, P, G = [], [], [], []
    for s in stems:
        im = images[s]
        if use_captured_tp and "tp" in im:
            tp = np.asarray(im["tp"], bool).reshape(-1, len(IOUV))
            c, p, g = np.asarray(im["pred_conf"], float), np.asarray(im["pred_cls"], int), np.asarray(im["gt_cls"], int)
        else:
            tp, c, p, g = stats_from_boxes(im)
        T.append(tp); C.append(c); P.append(p); G.append(g)
    tp, conf, pc, tc = np.concatenate(T), np.concatenate(C), np.concatenate(P), np.concatenate(G)
    res = ap_per_class(tp, conf, pc, tc)
    ap, cls = res[5], res[6]
    per = {int(c): float(ap[k, 0]) for k, c in enumerate(cls)}
    per95 = {int(c): float(ap[k].mean()) for k, c in enumerate(cls)}
    return dict(map50=float(np.mean(list(per.values()))) if per else 0.0,
                map=float(np.mean(list(per95.values()))) if per95 else 0.0, ap50=per, ap=per95)


# ------------------------------------------------------------------ small exact statistics (no scipy needed)
def rankdata(x):
    """Average ranks (1-based), ties share the mean rank."""
    x = np.asarray(x, float); o = np.argsort(x, kind="mergesort"); r = np.empty(len(x))
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[o[j + 1]] == x[o[i]]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def wilcoxon_exact(d):
    """Two-sided exact Wilcoxon signed-rank test (zeros dropped); enumerates all 2^n sign patterns, n <= 20."""
    d = np.asarray(d, float); d = d[d != 0]
    n = len(d)
    if n == 0:
        return dict(n=0, W=0.0, p=1.0)
    r = rankdata(np.abs(d)); w = float(r[d > 0].sum())
    signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1).astype(bool)
    dist = (signs * r).sum(1)
    mu = r.sum() / 2
    p = float(np.mean(np.abs(dist - mu) >= abs(w - mu) - 1e-9))
    return dict(n=n, W=w, p=p)


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    return float(np.corrcoef(ra, rb)[0, 1]) if np.std(ra) and np.std(rb) else 0.0
