# Wood Defect Detection: YOLO11m vs YOLO11s, what we are doing and why

Team brief, 7 September 2026. Prepared for the teammate training YOLO11s so that both runs are directly comparable.


## 1. The goal in one paragraph

We are training YOLO11m on the Kaggle 4,000-image subset of the Kodytek, Bodzas and Bilik (2022) sawn-timber defect dataset, and reporting per-class Precision, Recall, F1, mAP50 and mAP50-95 on a held-out test set made of physically separate boards. A YOLO11s run trained with exactly the same data and settings gives us a fair baseline, so the report can say 'baseline vs proposed' honestly. Everything else (the synopsis rewrite, CWB-style architecture changes, recoverability estimation) waits until those two numbers exist.


## 2. Why the old YOLO11s numbers cannot be reused

The previous YOLO11s run (640 square, 83 epochs, test mAP50 62.2%) has three problems that an examiner would catch. None of them is anyone's fault; they are in the data as downloaded.

- Board leakage. The filename's first four digits identify the physical board (81 boards). The old split was done per tile, so every test board also appears in train. The model partly memorised grain and lighting, and the 62.2% is inflated by an unknown amount. Fix: split by board id, zero overlap, asserted by script.
- Wrong class names. The team's data.yaml called the classes Crack, Knot, Hole, Stain, Split, Warp, Decay, Scratch. The Kaggle data card, the box shapes per id, and the paper's class frequency ranking all agree these are not the real names (table below). Every per-class statement in the old reports is about a different defect than it says. For example 'Warp is a diffuse 3D deformation' is not true: that class is Knot_with_crack.
- Letterboxing. Images are 2800 x 1024 (aspect 2.73:1). At 640 square, 63% of the tensor is black padding and the active image is 640 x 234. Fix: imgsz 1024 with rect=True, which trains at 1024 x 384 with almost no padding.
- Also fixed: 158 degenerate boxes with a 0 to 1 pixel side were dropped; the old augmentation (rotation 10 degrees, vertical flips, erasing 0.4, strong HSV) was replaced with grain-safe settings.


## 3. Real class mapping (use these names everywhere)

| id | Real name | Old wrong name | Share of boxes | Typical box shape |
|---|---|---|---|---|
| 0 | Quartzity | Crack | 1.9% | long thin streak along grain |
| 1 | Live_Knot | Knot | 44.2% | compact |
| 2 | Marrow | Hole | 2.2% | long streak (pith) |
| 3 | Resin | Stain | 7.1% | elongated |
| 4 | Dead_Knot | Split | 31.9% | compact |
| 5 | Knot_with_crack | Warp | 5.9% | compact, slightly larger |
| 6 | Knot_missing | Decay | 1.3% | compact |
| 7 | Crack | Scratch | 5.6% | long thin streak |

Label ids did not change, only the names, so no box moved. Source: Kaggle data card for nomihsa965/large-scale-image-dataset-of-wood-surface-defects; Kodytek et al. 2022, F1000Research 10:581, doi 10.12688/f1000research.52903.2.


## 4. The clean dataset (already built, use it as-is)

Private Kaggle dataset prakyats/wood-defects-clean (3.33 GB). Built with prepare_dataset.py, seed 42, ratios 0.70/0.18/0.12 by board. Board overlap across splits is zero.

| Split | Boards | Images | Background | Quartzity | Live_Knot | Marrow | Resin | Dead_Knot | Knot_with_crack | Knot_missing | Crack |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 52 | 2817 | 272 | 125 | 2899 | 94 | 489 | 2071 | 377 | 78 | 306 |
| val | 17 | 714 | 71 | 20 | 713 | 64 | 88 | 482 | 98 | 15 | 111 |
| test | 12 | 469 | 45 | 10 | 406 | 46 | 69 | 343 | 30 | 24 | 95 |

Filenames carry a 6-character hash prefix (for example 00291f_110900073.jpg). Keep it: rect mode disables shuffling, and the prefix is what makes each batch contain a mix of boards. The board id is still the four digits after the underscore.


## 5. Training configuration (identical for both models)

| Setting | Value | Why |
|---|---|---|
| Pretrained weights | yolo11m.pt (you: yolo11s.pt), COCO | never random init on 4k images |
| imgsz / rect | 1024 / True | 2.73:1 strips train at 1024 x 384, no padding waste |
| Device / batch | single T4, batch 16 | Ultralytics turns rect off under multi-GPU; two T4s also OOM at batch 32 |
| Epochs / patience | 100 / 25 | early stop on val mAP50 plateau |
| Optimizer | AdamW, lr0 0.002, lrf 0.01, cos_lr, warmup 3, wd 5e-4 |  |
| Loss gains | cls 1.0, box 7.5, dfl 1.5 | cls raised from 0.5 for rare classes |
| Augmentation | hsv 0.01/0.3/0.2, degrees 0, translate 0.08, scale 0.3, fliplr 0.5, flipud 0, mosaic 0, mixup 0, erasing 0.05 | grain is oriented; no rotation or vertical flip |
| Seed / determinism | 42 / True |  |
| Evaluation | best.pt only, test split run once, conf 0.001, iou 0.6 |  |


## 6. Status right now

- YOLO11m training started 7 Sep 2026 at about 11:35 IST on Kaggle, notebook prakyats/yolo11m-wood-train, version 7, single T4.
- Expected 5 to 8 minutes per epoch, so 8 to 13 GPU hours total; that means 2 to 3 twelve-hour Kaggle sessions with automatic resume from last.pt.
- Six earlier notebook versions failed on setup issues (no internet before phone verification, P100 not supported by the image's PyTorch, rect disabled under 2 GPUs). All fixed; the notebook now pins the T4, finds the scripts itself, and copies the dataset to local disk for speed.
- Test evaluation has not been run and will be run exactly once per model at the end.


## 7. What the YOLO11s teammate should do

1. Ask for collaborator access to the two Kaggle datasets prakyats/wood-defects-clean and prakyats/wood-defects-scripts, or receive dataset_clean.zip and upload your own copy. Do not rebuild the split; two different splits would make the comparison meaningless.
2. Take train_yolo11m.py and change exactly one thing: the model file, yolo11m.pt to yolo11s.pt. Run it with --name yolo11s_1024rect. Keep every CFG value, seed 42 included.
3. Use the same notebook cells (kaggle_upload/notebook/yolo11m-wood-train.ipynb): pin machine_shape NvidiaTeslaT4, enable internet, single GPU, batch 16. Phone verification on the Kaggle account is required for internet and GPU.
4. Confirm in the first-epoch log that rect is active and the image shape is 3 x 384 x 1024 (or 3 x 1024 x 384), and that there is no 'rect=False' warning.
5. Save the Kaggle version with output before the 12-hour limit; on the next session attach the previous version's output as input and re-run, it resumes automatically.
6. When training stops, run evaluate.py once on split test with best.pt. Send results.csv, args.yaml, eval/test_metrics.md, confusion_matrix.png, PR_curve.png, F1_curve.png. Keep best.pt on Kaggle or Drive, do not put it in git.
7. If you already have a YOLO11s run on the old split, keep it: it becomes the 'leaky baseline' row of the table, but it is not the comparison row.


## 8. Rules we both follow

- Never tune anything (threshold, epochs, augmentation) on the test split; validation only.
- Report Precision, Recall, mAP50 and mAP50-95 separately; never the word 'accuracy'.
- Evaluate best.pt, never last.pt.
- Any deviation from the config goes into NOTES.md with a reason.


## 9. What to expect, so nobody panics

- The clean-split numbers may look lower than the old 62 to 66% at first glance. That is correct, not a regression: the old number was leaky.
- Realistic range for YOLO11m overall test mAP50 is about 70 to 80%. The real Crack class should improve most from the resolution fix.
- Quartzity (10 test boxes) and Knot_missing (24 test boxes) will be noisy per-class numbers; we say so in the report rather than chase them.
- The old audit said the model was not capacity-limited, so do not expect the m-vs-s gap alone to be large. The data fixes carry most of the gain; the m-vs-s comparison is what makes the 'proposed' claim honest.


## 10. How I suggest we proceed after these two runs

Ranked by expected value per GPU hour. Each is a one-line change and a re-push; each new run gets its own name and its own NOTES.md entry.

1. Build the three-row table first: leaky YOLO11s (old), clean YOLO11s, clean YOLO11m, per class plus inference ms/img and FPS on T4. This is the deliverable; everything below is optional.
2. Drop the 99 remaining boxes under 5 x 5 pixels (raise MIN_WH from 0.0005 to 0.002 in prepare_dataset.py) and rebuild once, for both models. They are annotation artefacts that count as guaranteed misses in recall. Cheap, honest, and it must be applied to both runs at the same time.
3. If Crack or Quartzity recall is still poor, try imgsz 1280 rect (1280 x 480) on the better model. Roughly 1.6x the compute; only worth it if the confusion matrix shows misses rather than confusions.
4. If Knot_with_crack is confused with Live_Knot and Dead_Knot (likely, they look alike), that is a labelling-ambiguity story for the report, not a training problem. Show the confusion matrix and say so.
5. Pick the operating confidence threshold from the validation F1 curve (the old report suggested 0.35 to 0.40) and report precision and recall at that threshold alongside mAP. Do this on val, then apply once to test.
6. Report speed properly: ms per image and FPS on T4 at 1024 rect, and once on the CPU machine, since the synopsis talks about deployment.
7. Only after the table exists: rewrite the synopsis (plywood to sawn timber, real class names, Kodytek citation, YOLO11 instead of YOLOv8) and decide with the guide whether a CWB-style architecture experiment fits the remaining time. Custom architecture work is the biggest time sink and should not start before the baseline table is final.


## 11. Where things live

- Repo: C:\Users\ASUS\Desktop\MP-Code (CLAUDE.md, README.md, NOTES.md, prepare_dataset.py, train_yolo11m.py, evaluate.py, kaggle_upload/).
- Kaggle: datasets prakyats/wood-defects-clean and prakyats/wood-defects-scripts; notebook prakyats/yolo11m-wood-train.
- NOTES.md is the running log: class mapping evidence, split table, cleaning audit, every deviation and why. Read it before changing anything.
