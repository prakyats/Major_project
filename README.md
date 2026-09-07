# YOLO11m — wood surface defects (Kodytek et al. 2022 subset)

> **Progress and results so far:** see [docs/PROGRESS.md](docs/PROGRESS.md). Decision log: [NOTES.md](NOTES.md).


## 0. One-time
Kaggle account with phone verification (needed for GPU). Settings → Accelerator → **GPU T4 x2**.
Free quota: 30 GPU-hours/week, 12 h per session. Budget for this run: ~10–14 h total.

## 1. Prepare the dataset (CPU, run locally once, about 3 min, copies 3.3 GB)
`prepare_dataset.py` is standard library only; no pip install is needed for this step.

The raw Kaggle zip (`MP_dataset.zip`) ships as `Images - 1/Images - 1/*.jpg` and
`Bounding Boxes - YOLO Format - 1/Bounding Boxes - YOLO Format - 1/*.txt`. Put the jpgs in
`data/images/` and the txts in `data/labels/` first (flat layout). If you skip this the script finds
no labels and silently treats all 4,000 images as background.
```
python prepare_dataset.py --src data --out dataset_clean     --names Quartzity Live_Knot Marrow Resin Dead_Knot Knot_with_crack Knot_missing Crack     --ratios 0.70 0.18 0.12 --seed 42
```
These are the dataset's real class names in label-id order (Kaggle data card). The team's old names
`Crack Knot Hole Stain Split Warp Decay Scratch` were wrong; the mapping is in NOTES.md.

Check the printed table: 0 board overlap, every class present in all three splits. Then zip
`dataset_clean/` and upload it as a **Kaggle Dataset** (private). Also upload the three .py files as a
second small dataset, or paste them into notebook cells.

## 2. Kaggle notebook
Cell 1
```
!pip -q install -U ultralytics
!cp -r /kaggle/input/<your-dataset-name>/dataset_clean /kaggle/working/
!sed -i 's#^path:.*#path: /kaggle/working/dataset_clean#' /kaggle/working/dataset_clean/data.yaml
```
Cell 2 (train — re-run this exact cell after any restart; it resumes from last.pt)
```
!python /kaggle/input/<scripts-dataset>/train_yolo11m.py \
    --data /kaggle/working/dataset_clean/data.yaml \
    --project /kaggle/working/outputs --name yolo11m_1024rect \
    --device 0,1 --batch 32 --persist /kaggle/working/persist
```
With 2×T4 use `--device 0,1 --batch 32`; single T4 use `--device 0 --batch 16`. If OOM, halve batch.

**Before the 12 h limit hits**: File → Save Version (Quick Save) with "Save output" — this keeps
`/kaggle/working/outputs` so the next session can resume. Add the saved version's output as input
to the new session and copy `outputs/` back to `/kaggle/working/` before re-running Cell 2.

Cell 3 (once, at the very end — never tune on this)
```
!python /kaggle/input/<scripts-dataset>/evaluate.py \
    --weights /kaggle/working/outputs/yolo11m_1024rect/weights/best.pt \
    --data /kaggle/working/dataset_clean/data.yaml --split test --device 0
```
Download `eval/test_metrics.md`, `results.csv`, `confusion_matrix.png`, `PR_curve.png`, `F1_curve.png`, `best.pt`.

## 3. 7-day plan
- Day 1: prepare_dataset locally, upload, start training (first 12 h session).
- Day 2: resume + finish 100 epochs (or early-stop on patience=25).
- Day 3: evaluate on test boards; sanity-check per-class table; look at confusion matrix.
- Day 4–5: buffer for one rerun if something is off (e.g. batch OOM, class-name fix).
- Day 6–7: write-up. Remember: cite Kodytek, Bodzas & Bilik (2022) F1000Research 10:581,
  state the real class mapping, and replace "plywood" wording.
