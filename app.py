"""
app.py -- local demo / presentation UI for the wood-defect detectors.

Run:  python app.py        then open http://127.0.0.1:7860
Needs: weights/yolo11m_final.pt and weights/yolo11s_baseline.pt (see README), CPU is enough.
Optional: dataset_clean/test/ for the "Test boards" tab (ground truth vs prediction).
"""
import glob
import os
import random
import time
from pathlib import Path

import cv2
import gradio as gr
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).parent
WEIGHTS = {
    "YOLO11m (final, run 2)": ROOT / "weights" / "yolo11m_final.pt",
    "YOLO11s (baseline, same config)": ROOT / "weights" / "yolo11s_baseline.pt",
}
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
# one fixed colour per class (BGR for cv2), consistent between GT and prediction drawings
COLORS = {
    "Quartzity": (200, 120, 0), "Live_Knot": (0, 200, 0), "Marrow": (255, 0, 200), "Resin": (0, 165, 255),
    "Dead_Knot": (0, 0, 230), "Knot_with_crack": (230, 200, 0), "Knot_missing": (128, 0, 128), "Crack": (0, 230, 230),
}
IMGSZ = 1024
_models = {}


def get_model(key):
    if key not in _models:
        p = WEIGHTS[key]
        if not p.exists():
            raise gr.Error(f"Missing weights file {p}. Download best.pt from Kaggle into weights/ (see README).")
        _models[key] = YOLO(str(p))
    return _models[key]


def draw_boxes(img_bgr, boxes, labels, thickness=3):
    out = img_bgr.copy()
    h, w = out.shape[:2]
    fs = max(0.6, w / 2000)
    for (x1, y1, x2, y2), lab in zip(boxes, labels):
        cls = lab.split(" ")[0]
        c = COLORS.get(cls, (255, 255, 255))
        cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), c, thickness)
        (tw, th), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, fs, 2)
        y0 = int(y1) - 6 if y1 > th + 8 else int(y2) + th + 6
        cv2.rectangle(out, (int(x1), y0 - th - 4), (int(x1) + tw + 6, y0 + 4), c, -1)
        cv2.putText(out, lab, (int(x1) + 3, y0), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def run_one(model, img_bgr, conf, iou):
    t = time.time()
    r = model.predict(img_bgr, imgsz=IMGSZ, conf=conf, iou=iou, verbose=False, device="cpu")[0]
    dt = time.time() - t
    boxes = r.boxes.xyxy.cpu().numpy() if len(r.boxes) else np.zeros((0, 4))
    cls = r.boxes.cls.cpu().numpy().astype(int) if len(r.boxes) else np.zeros(0, int)
    confs = r.boxes.conf.cpu().numpy() if len(r.boxes) else np.zeros(0)
    labels = [f"{NAMES[c]} {p:.2f}" for c, p in zip(cls, confs)]
    rows = [[NAMES[c], round(float(p), 3), int(b[0]), int(b[1]), int(b[2]), int(b[3]), int(b[2] - b[0]), int(b[3] - b[1])]
            for c, p, b in zip(cls, confs, boxes)]
    rows.sort(key=lambda x: -x[1])
    return draw_boxes(img_bgr, boxes, labels), rows, dt, r.speed


def summarize(rows):
    if not rows:
        return "**No defects detected at this confidence.** The board section looks clean, or lower the threshold."
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    parts = [f"**{k}** x{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    return f"**{len(rows)} defect(s):** " + ", ".join(parts)


def detect(image, model_key, conf, iou, compare):
    if image is None:
        raise gr.Error("Upload a board image first.")
    img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    keys = list(WEIGHTS) if compare else [model_key]
    gallery, tables, notes = [], [], []
    for k in keys:
        m = get_model(k)
        vis, rows, dt, sp = run_one(m, img_bgr, conf, iou)
        gallery.append((cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), k))
        tables.extend([[k.split(" ")[0]] + r for r in rows])
        notes.append(f"{k}: {summarize(rows)}  \n_{dt*1000:.0f} ms on CPU (inference {sp['inference']:.0f} ms), input {image.shape[1]}x{image.shape[0]} at imgsz {IMGSZ}_")
    return gallery, tables, "\n\n".join(notes)


# ---------------- test-board tab (ground truth vs prediction) ----------------
TEST_IMG = sorted(glob.glob(str(ROOT / "dataset_clean" / "test" / "images" / "*.jpg")))


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
        raise gr.Error("dataset_clean/test not found next to app.py; this tab needs the local dataset.")
    path = random.choice(TEST_IMG) if pick == "random" else pick
    img, gboxes, glabels = load_gt(path)
    gt_vis = draw_boxes(img, gboxes, glabels)
    vis, rows, dt, _ = run_one(get_model(model_key), img, conf, iou)
    board = Path(path).stem.split("_")[1][:4]
    gt_counts = {}
    for l in glabels:
        gt_counts[l] = gt_counts.get(l, 0) + 1
    gt_txt = ", ".join(f"{k} x{v}" for k, v in gt_counts.items()) or "none (background image)"
    md = (f"**{Path(path).name}** from board **{board}** (this board was never seen in training).  \n"
          f"Ground truth: {gt_txt}  \nPrediction: {summarize(rows).replace('**', '')}  ({dt*1000:.0f} ms on CPU)")
    return [(cv2.cvtColor(gt_vis, cv2.COLOR_BGR2RGB), "Ground truth"), (cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), f"Prediction: {model_key}")], md


# ---------------- results tab ----------------
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

with gr.Blocks(title="Wood Defect Detection - YOLO11") as demo:
    gr.Markdown("# Wood surface defect detection (YOLO11m vs YOLO11s)\n"
                "Sawn-timber line-scan images, 8 defect classes, trained on a board-level split of the Kodytek et al. (2022) dataset. "
                "Runs on CPU; about 0.3 s (11s) to 0.6 s (11m) per 2800x1024 image.")
    with gr.Tab("Detect on your image"):
        with gr.Row():
            with gr.Column(scale=1):
                inp = gr.Image(label="Board image (jpg/png; wide 2800x1024 strips work best)", type="numpy")
                model_dd = gr.Dropdown(list(WEIGHTS), value=list(WEIGHTS)[0], label="Model")
                compare = gr.Checkbox(False, label="Run both models side by side")
                conf = gr.Slider(0.05, 0.9, value=0.35, step=0.05, label="Confidence threshold")
                iou = gr.Slider(0.3, 0.9, value=0.6, step=0.05, label="NMS IoU")
                btn = gr.Button("Detect", variant="primary")
            with gr.Column(scale=2):
                out_gal = gr.Gallery(label="Detections", columns=1, height=520, object_fit="contain")
                out_md = gr.Markdown()
                out_tbl = gr.Dataframe(headers=["model", "class", "conf", "x1", "y1", "x2", "y2", "w", "h"], label="Detections", wrap=True)
        btn.click(detect, [inp, model_dd, conf, iou, compare], [out_gal, out_tbl, out_md])
    with gr.Tab("Test boards: ground truth vs prediction"):
        gr.Markdown("Images from the 12 held-out test boards. Left: annotator's boxes. Right: model output. "
                    "Colours are per class and identical on both sides.")
        with gr.Row():
            pick = gr.Dropdown(["random"] + TEST_IMG, value="random", label="Test image", allow_custom_value=False, scale=3)
            model_dd2 = gr.Dropdown(list(WEIGHTS), value=list(WEIGHTS)[0], label="Model", scale=2)
            conf2 = gr.Slider(0.05, 0.9, value=0.35, step=0.05, label="Confidence", scale=1)
            iou2 = gr.Slider(0.3, 0.9, value=0.6, step=0.05, label="NMS IoU", scale=1)
        btn2 = gr.Button("Show", variant="primary")
        gal2 = gr.Gallery(label="Ground truth (left) vs prediction (right)", columns=1, height=620, object_fit="contain")
        md2 = gr.Markdown()
        btn2.click(test_board, [pick, model_dd2, conf2, iou2], [gal2, md2])
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
            for n, c in COLORS.items()))

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, show_error=True)
