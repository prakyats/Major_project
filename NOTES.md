# NOTES.md — YOLO11m wood-defect sprint

Running log of facts the report needs and every deviation from CLAUDE.md / CFG.

## 1. Real class mapping (resolved 2026-09-07)

The Kaggle 4,000-image subset (nomihsa965) already ships **8 classes**, not the original 10.
Blue stain and Overgrown from Kodytek et al. (2022) are absent. The Kaggle data card lists the
classes in this order, and the per-id box shapes in the label files match it exactly
(e.g. id 2 boxes are long streaks along the grain = marrow/pith, not "holes"):

| id | real name (use this) | team's old name | mean box w x h (norm.) | share of boxes |
|----|----------------------|-----------------|------------------------|----------------|
| 0 | Quartzity        | Crack   | 0.034 x 0.475 | 1.9 % |
| 1 | Live_Knot        | Knot    | 0.062 x 0.079 | 44.2 % |
| 2 | Marrow           | Hole    | 0.046 x 0.515 | 2.2 % |
| 3 | Resin            | Stain   | 0.032 x 0.176 | 7.1 % |
| 4 | Dead_Knot        | Split   | 0.051 x 0.068 | 31.9 % |
| 5 | Knot_with_crack  | Warp    | 0.097 x 0.113 | 5.9 % |
| 6 | Knot_missing     | Decay   | 0.045 x 0.075 | 1.3 % |
| 7 | Crack            | Scratch | 0.030 x 0.422 | 5.6 % |

Cross-check: the paper's Table 1 frequency ranking (live knot > dead knot > resin > knot with
crack > crack) is the same ranking as ids 1 > 4 > 3 > 5 > 7 here.

Consequences for the write-up:
- The old YOLO11s per-class numbers were reported under wrong names. "Split 88.1" was really
  Dead_Knot, "Hole 87.7" was Marrow, "Warp 47.5" was Knot_with_crack, "Crack 19.2" was Quartzity,
  "Scratch 42.2" was the actual Crack class.
- CLAUDE.md's advice "Warp is diffuse shadow, don't chase it" was based on the wrong name.
  Knot_with_crack is a normal compact object; its low score is more likely confusion with
  Live_Knot / Dead_Knot. Check the confusion matrix for that.
- `dataset_clean/data.yaml` uses the real names. Ids are unchanged, so no label moved.

Sources: Kaggle data card (accessed 2026-09-07); Kodytek, Bodzas & Bilik (2022) F1000Research
10:581, doi:10.12688/f1000research.52903.2 (PMC9277195); Zenodo record 4694695.

## 2. Raw data as received

- `MP_dataset.zip` (3.32 GB) = raw Kaggle layout: `Images - 1/Images - 1/*.jpg` (4,000) and
  `Bounding Boxes - YOLO Format - 1/.../*.txt` (4,000). No data.yaml or classes file inside.
  Not the `data/{train,valid,test}` tree CLAUDE.md describes. Extracted flat to `data/images`
  and `data/labels` so prepare_dataset.py's flat-layout path finds the labels.
- 9,211 boxes, 388 empty label files (background), all lines 5 columns, class ids 0-7 only.
- Stems: 3,824 are 9-digit, 176 are 8-digit (`991xxxxx`, `999xxxxx`). Board id = first 4 chars
  in both cases; 81 boards total, as CLAUDE.md states.

## 3. Label cleaning

- Degenerate filter (w or h <= 0.0005 after clipping) dropped **158** boxes in 120 files
  (CLAUDE.md said 77; 158 is what the data actually contains).
  Per class: Live_Knot 52, Dead_Knot 38, Knot_with_crack 37, Quartzity 16, Crack 5, Resin 4,
  Knot_missing 4, Marrow 2. Every dropped line inspected had a side of 0-1 px (e.g.
  `w=0.000357 h=0.0`). No legitimate box was removed. Before/after samples: 100000044.txt
  8 -> 5 lines, 100000039.txt 7 -> 6, 100000008.txt 3 -> 2.
- **Not changed, flagged**: 99 boxes (1.1 %) that survived are still under 5 x 5 px in the
  source image (Live_Knot 41, Knot_with_crack 27, Dead_Knot 17, Quartzity 7, Knot_missing 4,
  Crack 2, Resin 1). These are annotation artefacts, unlearnable at 1024 rect (under 2 px), and
  will count as misses in recall. Left in to respect "verify, don't redo". If a rerun ever
  happens, raising MIN_WH to about 0.002 (5 px) is the one-line change; record it here if so.
- Crack geometry, measured: width min 2 px, p5 37 px, median 71 px, mean 85 px at 2800 wide.
  At 1024 rect that is a median of about 26 px; at 640 square about 16 px. CLAUDE.md's
  "hairline below 1 px at 640" is therefore overstated. The resolution fix still helps (1.6x
  more pixels per crack, no padding), but do not claim cracks were invisible at 640.

## 4. Board-level split (seed 42, ratios 0.70/0.18/0.12) - FINAL

Command: see README section 1. Board overlap train/val/test = 0 (asserted by the script).
Board lists in `dataset_clean/board_split.json`. Console log in `prepare_run_seed42.log`.

| split | boards | images | background | Quartzity | Live_Knot | Marrow | Resin | Dead_Knot | Knot_with_crack | Knot_missing | Crack |
|-------|-------:|-------:|-----------:|----------:|----------:|-------:|------:|----------:|----------------:|-------------:|------:|
| train | 52 | 2817 | 272 | 125 | 2899 | 94 | 489 | 2071 | 377 | 78 | 306 |
| val   | 17 |  714 |  71 |  20 |  713 | 64 |  88 |  482 |  98 | 15 | 111 |
| test  | 12 |  469 |  45 |  10 |  406 | 46 |  69 |  343 |  30 | 24 |  95 |

Checks from CLAUDE.md task 1: every class present in all splits: yes. Val and test >= 10
boards: yes. No class below 10 boxes in val: yes (rarest is Knot_missing with 15). Test has
only 10 Quartzity boxes, so its Quartzity mAP will be noisy; say so in the report. Seed not
changed.

Hash-prefix check (rect mode iterates sorted filenames without shuffle): distinct boards per
sorted batch of 16 in train = min 11, mean 13.5; per batch of 32 = min 20, mean 23.5.
Batches mix boards as intended.

## 5. Deviations from CLAUDE.md / CFG so far

| what | why |
|------|-----|
| `--names` changed to the real class names | wrong names would go into every plot and table; ids untouched |
| prepare_dataset.py: replaced a check-mark character in one print with ASCII | crashed with UnicodeEncodeError on the Windows cp1252 console before writing board_split.json |
| Source layout is flat `data/{images,labels}`, not `data/{train,valid,test}` | that is what the zip contains |
| **Single T4, batch 16, instead of 2xT4 batch 32** | Ultralytics 8.4 prints `'rect=True' is incompatible with Multi-GPU training, setting 'rect=False'` and falls back to 1024 square, which then OOMs at batch 32 on T4 15 GB (kernel v6 log). rect is the point of the whole setup, so keep it on one GPU. Cost: roughly 2x wall-clock, more sessions. |
| Kaggle accelerator set via `machine_shape: NvidiaTeslaT4` | default API GPU is a P100 (sm_60) which the image's torch 2.10+cu128 no longer supports (v5 log: `no kernel image is available`) |
| Dataset copied to `/kaggle/tmp` before training | mounted input reads at ~36 MB/s and is read-only, so no label cache; local copy takes ~2 min |
| Notebook, not the README cells, drives the run | pushed via `kaggle kernels push` from `kaggle_upload/notebook/`; it finds the scripts by glob because Kaggle mounts secondary datasets under `/kaggle/input/datasets/<user>/<slug>` |

## 6. Still to fill in

- [x] Kaggle datasets (private, 2026-09-07): `prakyats/wood-defects-clean` (dataset_clean.zip, 3.33 GB), `prakyats/wood-defects-scripts` (3 .py files). Notebook: `prakyats/yolo11m-wood-train` (pushed from kaggle_upload/notebook/).
- [x] Training run 1: 2026-09-07 11:35-14:14 IST, kernel v7, one session, 2.54 h GPU.
- [x] Run 1: 89 epochs (early stop), best epoch 64, val mAP50 62.6 / mAP50-95 33.7.
- [x] Log confirms rect=True (shuffle disabled warning present), imgsz 1024, no rect=False warning on single GPU.
- [x] OOM: v6 (2xT4, rect silently off, batch 32) OOM on GPU 1 at first step. Fixed by single-GPU rect batch 16 (v7).
- [x] Test evaluated exactly once per model on 2026-09-07 (notebook v9): YOLO11m run 2 best.pt and YOLO11s baseline best.pt.
- [ ] best.pt (run 1) stored at: Kaggle notebook v7 output, persist/yolo11m_1024rect/best.pt (40.5 MB); local copy weights_local/ (gitignored).

## 7. Run 1: YOLO11m, 1024 rect, single T4 (Kaggle notebook v7, 2026-09-07)

Config = CFG exactly (see `runs_log/run1_yolo11m_1024rect_v7/args.yaml`). Started ~11:35 IST, finished 14:14 IST.

- **89 epochs in 2.54 h** (about 103 s/epoch on one T4, batch 16, 7.35 GB GPU memory). The
  5-8 min/epoch estimate in CLAUDE.md was off by 3-4x; a 100-epoch run costs about 3 GPU-hours.
- Early stopping fired at epoch 89 (patience 25). **best.pt = epoch 64** (Ultralytics fitness =
  0.1 mAP50 + 0.9 mAP50-95). Log confirms `rect=True` active and shuffle disabled as expected.
- Test split NOT evaluated. Held back until the config is final (see section 8).

Validation (714 images, 1591 boxes, 17 boards), best.pt:

| Class | Instances | P | R | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|
| **all** | 1591 | 61.0 | 62.5 | **62.6** | **33.7** |
| Quartzity | 20 | 6.6 | 5.0 | 4.3 | 2.5 |
| Live_Knot | 713 | 77.2 | 75.5 | 76.7 | 33.3 |
| Marrow | 64 | 75.4 | 70.3 | 72.8 | 41.3 |
| Resin | 88 | 69.9 | 73.9 | 71.2 | 34.7 |
| Dead_Knot | 482 | 78.5 | 74.9 | 81.8 | 42.6 |
| Knot_with_crack | 98 | 61.7 | 64.3 | 61.7 | 40.0 |
| Knot_missing | 15 | 69.1 | 74.6 | 81.4 | 47.3 |
| Crack | 111 | 49.4 | 61.3 | 51.1 | 27.7 |

Speed on T4 at 1024 rect: 19.5 ms inference + 1.6 ms pre/post per image, about 47 FPS end to end.

Reading of the result:
- Overall val mAP50 62.6 on clean boards vs 66.3 on the leaky split for YOLO11s. As predicted,
  not a regression. Mean over the 7 classes excluding Quartzity is 70.9.
- **Quartzity collapsed (4.3 mAP50).** 125 train boxes, 20 val boxes, long thin streaks along the
  grain. It alone costs about 8 points of overall mAP50. Under its old wrong name "Crack" it scored
  19.2 on the leaky test set.
- **Crack improved: 51.1 vs 42.2** (old leaky test, under the wrong name "Scratch") even though the
  new split is harder. The rect/resolution fix did what it was supposed to.
- Training was noisy: val cls loss spiked to 14.8 (ep 1) and 21.5 (ep 6), and val mAP50 dropped
  10-15 points at epochs 16, 26, 29, 39, 42 before recovering. Suggests lr0 0.002 with AdamW and
  batch 16 is on the aggressive side.

## 8. Plan for run 2+ (decided on val only; test stays untouched)

Because a run costs 3 GPU-h, not 10-14, there is budget for 3-4 iterations this week. Candidate
changes, one or two per run, every one mirrored by the YOLO11s run before the final test:

1. Stability: batch 32 (fits, 7.35 GB used of 15 at batch 16) and lr0 0.001. Expected: fewer
   collapses, slightly higher plateau.
2. Drop the 99 sub-5-px boxes (MIN_WH 0.002) and rebuild the dataset once (same seed, same boards).
3. Quartzity / Crack resolution: imgsz 1280 rect (1280 x 480). About 1.6x compute, still under 5 h.
4. Patience 40 given the noisy curve (cheap now).

Rules unchanged: seed 42, best.pt, one test evaluation per final model, every change logged here.

## 9. Run 2: stability experiment (Kaggle notebook v8, started 2026-09-07 ~15:05 IST)

Deviations from CFG, all logged here: **batch 32** (7.35 GB used of 15 at batch 16, so it should fit),
**lr0 0.001**, **patience 40**. Everything else identical to run 1, same dataset, seed 42.
Reason: run 1's val curve had repeated 10-15 point collapses and two val-cls-loss spikes; larger
batch plus half the LR is the standard remedy and costs nothing extra. Notebook falls back to batch 24
under a different run name if 32 OOMs. Scripts dataset version 2 adds `--lr0 --patience --imgsz`
flags to train_yolo11m.py (CFG defaults unchanged).
The YOLO11s run must use the same three flags before the final comparison.

## 10. Run 2 result (notebook v8, finished 2026-09-07 17:43 IST) -- ADOPTED AS FINAL YOLO11m CONFIG

Batch 32 fitted in 13.9 GB. 100 epochs in 2.64 h (no early stop). best.pt = epoch 73 by fitness;
max val mAP50 66.0 at epoch 69. No mAP collapses (largest epoch-to-epoch drop under 8 points vs
five drops of 10-15 in run 1); val cls loss peaked at 4.45 vs 21.5. Artefacts:
`runs_log/run2_yolo11m_1024rect_b32_lr001_v8/`.

Validation, best.pt (run 1 mAP50 in the last column for comparison):

| Class | Boxes | P | R | mAP50 | mAP50-95 | run 1 mAP50 |
|---|---:|---:|---:|---:|---:|---:|
| **all** | 1591 | 67.9 | 62.7 | **65.7** | **36.2** | 62.6 |
| Quartzity | 20 | 11.8 | 5.0 | 5.4 | 3.2 | 4.3 |
| Live_Knot | 713 | 83.1 | 71.4 | 77.6 | 34.7 | 76.7 |
| Marrow | 64 | 70.8 | 75.0 | 76.0 | 48.7 | 72.8 |
| Resin | 88 | 74.1 | 71.6 | 71.9 | 34.9 | 71.2 |
| Dead_Knot | 482 | 77.7 | 77.8 | 83.4 | 42.7 | 81.8 |
| Knot_with_crack | 98 | 70.7 | 59.2 | 64.3 | 43.1 | 61.7 |
| Knot_missing | 15 | 87.9 | 80.0 | 88.8 | 52.9 | 81.4 |
| Crack | 111 | 66.8 | 61.3 | 58.0 | 29.4 | 51.1 |

Every class improved or held. Crack +6.9, Knot_missing +7.4, Marrow +3.2, Knot_with_crack +2.6.
Quartzity is still not learned (5.4). Inference 19.1 ms/img on T4.

Decision: final YOLO11m configuration = CFG with batch 32, lr0 0.001, patience 40. No further
YOLO11m iterations before the test evaluation; remaining quota goes to the YOLO11s baseline with
the identical configuration, then one test evaluation per model in the same session.

## 11. Final session plan (notebook v9)

1. Train YOLO11s: `--model yolo11s.pt --batch 32 --lr0 0.001 --patience 40`, name
   `yolo11s_1024rect_b32_lr001`. Scripts dataset v3 adds the `--model` flag.
2. Evaluate test split ONCE for each model with evaluate.py (conf 0.001, iou 0.6, rect, 1024):
   YOLO11m best.pt from run 2 (uploaded as Kaggle dataset `prakyats/wood-yolo11m-weights`),
   YOLO11s best.pt from step 1.
3. Commit eval/ tables, both runs' artefacts, and the final table in docs/PROGRESS.md.

## 12. FINAL: test evaluation, run once per model (notebook v9, 2026-09-07 evening)

YOLO11s baseline: `--model yolo11s.pt`, otherwise identical to the adopted config (batch 32, lr0
0.001, patience 40, 1024 rect, seed 42). 90 epochs in 1.43 h, early stop, best epoch 50, val mAP50
65.3 / mAP50-95 36.0. Artefacts: `runs_log/run3_yolo11s_1024rect_b32_lr001_v9/`.

Test split (12 boards, 469 images, 1,023 boxes) evaluated exactly once per model with evaluate.py
(best.pt, imgsz 1024, rect, conf 0.001, iou 0.6). Tables: `eval/yolo11m_final/` and
`eval/yolo11s_baseline/` (csv, md, PR/F1 curves, confusion matrices).

| Model | Split used for training | Test P | Test R | Test F1 | Test mAP50 | Test mAP50-95 | Inference ms/img (T4, 1024 rect) | Params |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| YOLO11s, 640 square (old run) | leaky, tile-level | 73.1 | -- | -- | 62.2 | -- | -- | 9.4 M |
| **YOLO11s, 1024 rect (clean baseline)** | board-level, seed 42 | 71.0 | 64.1 | 67.4 | **64.6** | 33.4 | 11.7 | 9.4 M |
| **YOLO11m, 1024 rect (proposed)** | board-level, seed 42 | 63.4 | 66.2 | 64.7 | **63.0** | **34.0** | 33.2 | 20.0 M |

Per class:

| Class | Test boxes | 11s P | 11s R | 11s F1 | 11s mAP50 | 11s mAP50-95 | 11m P | 11m R | 11m F1 | 11m mAP50 | 11m mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dead_Knot | 343 | 83.0 | 84.3 | 83.6 | 89.1 | 43.3 | 77.2 | 88.0 | 82.3 | 86.8 | 41.8 |
| Marrow | 46 | 89.3 | 72.7 | 80.2 | 87.7 | 55.2 | 79.6 | 84.9 | 82.2 | 85.8 | 57.4 |
| Live_Knot | 406 | 75.2 | 75.1 | 75.2 | 75.8 | 32.6 | 73.5 | 79.2 | 76.3 | 74.8 | 32.0 |
| Knot_missing | 24 | 80.8 | 70.8 | 75.5 | 69.6 | 34.1 | 57.9 | 62.5 | 60.1 | 62.7 | 35.7 |
| Knot_with_crack | 30 | 80.9 | 63.3 | 71.1 | 67.5 | 42.8 | 63.2 | 63.3 | 63.3 | 61.7 | 38.4 |
| Resin | 69 | 81.9 | 53.6 | 64.8 | 60.4 | 29.5 | 68.0 | 56.5 | 61.7 | 59.5 | 29.9 |
| Crack | 95 | 60.5 | 63.2 | 61.8 | 53.0 | 26.3 | 56.8 | 72.6 | 63.7 | 57.7 | 31.0 |
| Quartzity | 10 | 16.7 | 30.0 | 21.5 | 13.4 | 3.0 | 30.7 | 22.3 | 25.8 | 15.4 | 5.7 |
| **ALL** | 1023 | 71.0 | 64.1 | 67.4 | 64.6 | 33.4 | 63.4 | 66.2 | 64.7 | 63.0 | 34.0 |

Reading of the result (be this honest in the report):

- **The two models are statistically tied on the test boards.** YOLO11s leads mAP50 by 1.6 points
  and precision by 7.6; YOLO11m leads mAP50-95 by 0.6, recall by 2.1, and Crack mAP50 by 4.7.
  The test set is 12 boards and 1,023 boxes; the four rarest classes have 10 to 46 boxes each,
  so per-class differences of a few points are noise. Do not claim that YOLO11m is better.
- **What is defensible to claim:** (1) the data pipeline fixes (board-level split, correct class
  names, rectangular 1024 training, grain-safe augmentation) produce a clean-split test mAP50 of
  63 to 65 for both model sizes, which is at least as good as the old leaky 62.2 measured on a
  far easier split; (2) Crack, the class the resolution fix targeted, went from 42.2 (leaky) to
  53.0 / 57.7 (clean); (3) at equal training cost YOLO11s is 2.8x faster at inference
  (11.7 vs 33.2 ms/img on a T4, batch 16) with no loss in mAP50, so it is the better deployment
  choice on this dataset; (4) capacity is not the bottleneck, which is what the pre-training
  audit predicted. The bottleneck is data: Quartzity has 125 training boxes and is unlearned by
  both models (13 to 15 mAP50), and knot subtypes are confused with each other.
- Validation vs test: both models scored about 65 on val and 63 to 65 on test, so there is no
  sign of overfitting to the validation boards.
- Inference speed: evaluate.py runs batch 16 on the test split (33.2 / 11.7 ms). The training-time
  validation pass reported 19.1 / 13.7 ms at its own batch size; quote one setting consistently.

Weights (not in git): Kaggle dataset `prakyats/wood-yolo11m-weights` holds run 1 and run 2 YOLO11m
best.pt; YOLO11s best.pt is in notebook v9 output `persist/yolo11s_1024rect_b32_lr001/`. Local
copies in `weights_local/`.

GPU used this week: 6.8 h of 30 (all runs plus failed attempts). Remaining: about 23 h.

## 13. If there is appetite for one more round (all optional, none changes the table above)

The test split has now been used once for each model. Any further model would need its own single
test evaluation, and the write-up must say how many test evaluations were performed in total.
Options ranked by expected value:
1. **Nothing more on models; spend the time on the report.** The tie is a legitimate finding.
2. Multi-seed estimate of the noise floor: retrain YOLO11s with seeds 1 and 2 (1.4 h each) and
   report val mean and spread. This tells the examiner what a 1.6-point gap means. Val only.
3. Data-side: drop the 99 sub-5-px boxes (MIN_WH 0.002), rebuild, retrain both. Small, honest.
4. Quartzity: it will not be fixed by model size. Either report it as a data limitation (10 test
   boxes) or merge it into a "grain anomaly" class in a clearly labelled secondary experiment.

## 14. Final phase (2026-10-07): 4-class balanced dataset, YOLO11s (team decision)

Team decision for the final review: deploy YOLO11s (tied with 11m on test, 2.8x faster), restrict to
the 4 most frequent defect classes, balance them with augmentation, and retrain.

**Classes kept** (box counts in dataset_clean, all splits): Live_Knot 4018, Dead_Knot 2896, Resin 646,
Crack 512. Knot_with_crack is 5th with 505 (it was 4th before the degenerate-box filter removed 37 of
its boxes). Dropped: Knot_with_crack, Marrow, Quartzity, Knot_missing. New ids 0-3 in that order.

**Fair baseline.** Per-class AP is computed class by class, so the 8-class YOLO11s baseline's AP on
these 4 classes is unchanged by dropping the others. The 4-class bar to beat is therefore the mean of
those 4 rows, NOT the 8-class 64.6:

| YOLO11s 8-class baseline, 4 kept classes | Live_Knot | Dead_Knot | Resin | Crack | **4-class mean** |
|---|---:|---:|---:|---:|---:|
| val mAP50 / mAP50-95 | 78.1 / 34.6 | 83.7 / 42.8 | 74.9 / 37.8 | 53.3 / 26.9 | **72.5 / 35.5** |
| test mAP50 / mAP50-95 | 75.8 / 32.6 | 89.1 / 43.3 | 60.4 / 29.5 | 53.0 / 26.3 | **69.6 / 32.9** |

**Balancing** (`build_balanced.py`, seed 42): grain-aware copy-paste of real defect crops from the train
split onto defect-free train images (canvases). Line-scan geometry checked on the previews: the board
runs top to bottom (grain and cracks vertical), and the left/right ~150-190 px of every image is black
conveyor background, so crops come only from inside the board and are pasted only inside the canvas
board. No rotation, no vertical flip; horizontal flip and +-10 % scale only. Crops never overlap any box
of the original 8 classes. Blending alternates Poisson cloning / feathered alpha (defect box opaque,
context margin fading out). Val and test are untouched real images with 4-class labels.
Two balance levels, plus the control:

| train set | Live_Knot | Dead_Knot | Resin | Crack | images | max:min |
|---|---:|---:|---:|---:|---:|---:|
| plain (control) | 2899 | 2071 | 489 | 306 | 2817 | 9.47 |
| full: every class to n_max | 2899 | ~3067 | 2899 | 2899 | ~4315 | 1.06 |
| sqrt: n_c -> sqrt(n_c * n_max) | 2899 | ~2462 | 1191 | 942 | ~3241 | 3.08 |

Only 199 of the 306 train cracks are isolated enough to crop cleanly, so full balance reuses each crack
crop up to ~13 times (with flip/scale/blend variation); sqrt reuses at most 4 times. That is the reason
for running both. Exact counts of the Kaggle build are in its `balance_report.json`.

**Pre-registered protocol (fixed before training):** three YOLO11s runs with the baseline config
(1024 rect, batch 32, lr0 0.001, patience 40, seed 42): full, plain, sqrt. Between full and sqrt, the one
with the higher 4-class val mAP50 is the balanced model. Test is evaluated once for the plain control and
once for the chosen balanced model. Test evaluations in total after this: 4 (11s 8-class, 11m 8-class,
11s 4-class plain, 11s 4-class balanced). Kaggle notebook `prakyats/yolo11s-wood-4cls-balanced`.

Correction to the BRI discussion: the position penalty must measure distance to the board's side edges
(where the board meets the black background), not to the image top/bottom, which are tile cuts along
the board length. Ma'am's code with edges="ends" uses the image left/right, which in these images is the
black background, not a board end.

## 15. Result of the 4-class balanced experiment (Kaggle `yolo11s-wood-4cls-balanced` v1, 2026-10-07)

Ran 11:41-17:14 IST on one T4. Runs (all early-stopped, no errors): full 97 epochs / 2.39 h (best ep 46),
plain 91 epochs / 1.43 h (best ep 51), sqrt 90 epochs / 1.58 h (best ep 50). The Kaggle build produced the
same class counts as the local build (balance_report.json) but different canvases (OpenCV version on Kaggle
changes the board mask by a few px, so the seeded random stream diverges); the Kaggle build is the one trained on.

Validation (4-class mAP50 / mAP50-95), pre-registered choice = sqrt (75.3 > full 71.9):

| model | Live_Knot | Dead_Knot | Resin | Crack | **mAP50** | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| 8-class YOLO11s baseline, 4 classes scored | 78.1 | 83.7 | 74.9 | 53.3 | 72.5 | 35.5 |
| 4-class plain | 80.3 | 82.0 | 75.6 | 54.4 | 73.1 | 35.4 |
| 4-class full balance (1.06:1) | 78.8 | 83.1 | 70.4 | 55.4 | 71.9 | 36.0 |
| **4-class sqrt balance (3.1:1)** | 79.9 | 81.4 | 79.5 | 60.5 | **75.3** | 36.0 |

Test, evaluated once per model (plain control + chosen sqrt):

| model | Live_Knot | Dead_Knot | Resin | Crack | **mAP50** | mAP50-95 | P | R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 8-class YOLO11s baseline, 4 classes scored | 75.8 | 89.1 | 60.4 | 53.0 | 69.6 | 32.9 | -- | -- |
| 4-class plain | 74.5 | 89.4 | 63.7 | 59.2 | **71.7** | 33.4 | 76.7 | 70.0 |
| 4-class sqrt balance | 76.4 | 87.5 | 64.2 | 48.7 | 69.2 | 33.1 | 74.8 | 69.4 |

Reading:
- The val gain of sqrt balancing (+2.2 over plain, +2.8 over the 8-class baseline; Crack +6.1, Resin +3.9)
  did NOT carry over to test (-2.5 vs plain, -0.4 vs baseline). Almost the whole swing is Crack:
  val +6.1, test -10.5. Resin is +3.9 val / +0.5 test; Live_Knot +1.9 test.
- mAP50-95 is flat everywhere (val 35.4-36.0, test 32.9-33.4): no model is reliably better at strict IoU.
- Full balance (each of 160 clean crack crops reused up to 17x) was the worst on val, as expected from
  duplicate memorisation; the milder sqrt level was better. More copies of the same few cracks add no new
  information.
- Restricting to 4 classes (plain) is +0.6 val / +2.1 test over the 8-class model on the same classes.
- Do not report the test-best model (plain) as "chosen": the choice was fixed on val before testing.
  Test evaluations in total now: 4.
- Bootstrap CIs over boards: see eval/bootstrap_4cls_{test,val}.md (bootstrap_ci.py).

## 16. Resolution step: imgsz 1280 rect (Kaggle `yolo11s-wood-4cls-1280` v1, started 2026-10-07 17:28 IST)

Team choice after section 15: raise the input resolution. The source strips are 2800 x 1024; imgsz 1024 rect trains
at 1024 x 384 (37 % of native width), imgsz 1280 rect at 1280 x 480 (46 %). Median crack width goes from ~26 px to
~33 px. GPU memory at 1024 / batch 32 was 7.25 GB of 14.9, so 1280 (~1.56x pixels, ~11 GB) keeps batch 32;
the notebook retries at batch 16 only if a run fails.
Same data (build_balanced.py unchanged, seed 42, rebuilt on Kaggle; preview names compared with v1 to confirm an
identical build), same config otherwise. Runs: sqrt @1280, plain @1280.

**Pre-registered rule (fixed before training):** final 4-class model = highest 4-class val mAP50 among
sqrt@1024 (75.3), plain@1024 (73.1), sqrt@1280, plain@1280. Both 1280 models evaluated on test once at imgsz 1280.
Test evaluations in total after this: 6.

## 17. Mathematical model, accuracy part (2026-10-07 evening)

All numbers below come from the validator's own predictions (`eval_capture.py`; a CPU re-run of the official
evaluation reproduces every reported test number exactly). Model choices on validation only; test scored once.

**Corrected 4-class validation baseline.** The 8-class YOLO11s scored on the 4 kept classes gives 73.8 val mAP50
through the official evaluator (batch 16); the 72.5 in section 14 came from the training log's own validation
(batch 64). Test is unchanged at 69.6. Use 73.8.

**Paired tests, 4-class models (`stats_4cls.py`, board bootstrap B=1000, exact Wilcoxon on per-board AP50):**
val sqrt-plain +2.5 [-0.1, +4.9] p 0.75; val sqrt-base +1.8 [-0.9, +4.5]; test sqrt-plain -2.6 [-4.6, +0.3] p 0.57;
test sqrt-base -0.4 [-2.8, +1.9]; test plain-base +2.2 [-1.4, +4.4]. No difference is significant.
(The earlier `bootstrap_ci.py` re-predicted image by image and was 2-3 points off the official numbers: superseded.)

**Weighted Boxes Fusion of YOLO11m + YOLO11s, 8 classes (`math_model.py --tag 8cls_m_s`).** Grid on val:
fusion IoU {0.45, 0.55, 0.65} x weights {1:1, 2:1, 1:2}; chosen IoU 0.65, weights 1:1 (val 69.4 / 39.0 vs singles
66.1 / 66.3 mAP50). Test: fused 65.7 mAP50 / 36.1 mAP50-95; YOLO11m 63.0 / 34.1; YOLO11s 64.6 / 33.7 (singles re-matched
in original pixels, within 0.3 of the official). Fused minus YOLO11s (best single on val): mAP50 +1.1 [-0.5, +2.7],
**mAP50-95 +2.4 [+1.6, +3.2]** (significant), 7 boards better / 5 worse, Wilcoxon p 0.52 on AP50.
Note: the chosen IoU is the top of the grid; the grid was fixed before running and is not widened after the test.

**Per-class thresholds (F1-optimal per class on val) vs one global threshold (0.26 on val):** test macro-F1 fused
66.2 vs 66.9 global; YOLO11s 64.9 vs 66.8. Per-class thresholds over-fit the rare classes' few val boxes:
NOT adopted; the application keeps one global threshold.

**Pre-registered for the 4-class final model (fixed before the 1280 results are read):** after section 16's rule
picks the best single model, run `math_model.py` on all four 4-class models (plain/sqrt x 1024/1280) with the same
grid (IoU {0.45, 0.55, 0.65}; equal weights or one model doubled). The deployed detector is the fused one if its val
mAP50 exceeds the best single model's val mAP50, otherwise the best single model. The deployed detector is tested once.

## 18. HANDOVER / resume point (paused 2026-10-07 ~21:45 IST at the user's request)

Running when paused (no action needed to keep them going):
- Kaggle `prakyats/yolo11s-wood-4cls-1280` (sqrt@1280 + plain@1280, val selection + test once), expected done ~22:45 IST.
- Local CPU: `enhance_study.py --weights weights/yolo11s_4cls_balanced.pt --imgsz 1024` (~85 min) -> eval/enhancement/.

Done today (all uncommitted): build_balanced.py, bootstrap_ci.py (superseded), eval_capture.py, stats_4cls.py,
math_model.py (WBF 8-class done: test 65.7/36.1, +2.4 mAP50-95 sig.), bri.py + bri_validate.py (kappa 0.86 test),
train_wiou.py + --seed flag (Kaggle scripts v5 uploaded), enhance_study.py, app.py (4-class model, BRI grade,
value estimate, per-model imgsz), docs/make_final_diagrams.py, docs/deck_tools.py (tested), docs/collect_results.py.
Guide doc: Major_Project/docs/BRI_Model_Update_for_Guide_2026-10-07.docx.

Next, in order:
1. Download 1280 outputs: `python -m kaggle kernels output prakyats/yolo11s-wood-4cls-1280 -p weights_local/kaggle_1280_v1`;
   copy into runs_log/run5_* , eval/yolo11s_4cls_{sqrt,plain}_1280/, runs_log/run5_4cls_1280_v1/selection.json.
2. Apply section 16 rule -> final single model; capture 1280 models (eval_capture), run section 17 4-class fusion rule.
3. Write docs/final_model.json; push WIoU+seeds notebook: `python <scratch>/make_nb_wiou.py <variant> <imgsz> <val_map50>`
   (generator in session scratchpad; recreate from section 17 description if lost), kaggle kernels push.
4. bri_validate.py with the final detector; enhancement study rerun if final model differs (optional).
5. collect_results.py -> write docs/build_final_deck.py (plan: 33 slides, V3.0 + new MM-I/II/III, stats, grading,
   enhancement, conclusion, refs [12]-[22]) -> Major_Project/docs/Major_Project_Final_Presentation_V4.0.pptx.
6. App screenshots with final model; update Results tab; commit (as prakyats, no co-author trailer).
Open questions for the user: final review date/time; ma'am's severity ranking.

## 19. Results 2026-10-08 (resumed)

**1280 rect (Kaggle `yolo11s-wood-4cls-1280` v1, finished 22:01 IST, identical build to v1 confirmed).**
sqrt@1280: 2.10 h, val 74.6 / 35.5, test 71.6 / 34.3 (Crack 54.5, Resin 67.6).
plain@1280: 2.17 h, val 71.5 / 33.9, test 67.5 / 30.7.
Section 16 rule (highest val mAP50): **final single model = sqrt@1024 (val 75.3)**. sqrt@1280 scored higher on test
(71.6 vs 69.2) but test is not used for selection; report it as an observation only. Test evaluations total: 6.

**Enhancement study, val, sqrt@1024 (`enhance_study.py`, eval/enhancement/).** mAP50, raw / CLAHE / denoise / sharpen:
normal 74.8 / 65.8 / 75.3 / 73.8; low light 50.0 / 27.7 / 48.0 / 49.3; overexposed 58.2 / 47.9 / 58.2 / 57.7;
blur 73.3 / 62.2 / 72.9 / 75.1; noise 67.8 / 56.5 / 73.0 / 57.0; low contrast 61.3 / 62.6 / 61.6 / 62.6.
CLAHE significantly worse in 5 of 6 conditions (CI excludes 0, Wilcoxon p <= 0.006). Denoise significantly better
only on noisy input (+3.2 to +7.2, p 0.006). Sharpen: blur +, n.s. => H1 (enhancement improves detection) rejected for
raw images; denoising recommended only for noisy cameras. Degradations cost up to 25 points (low light): imaging
conditions matter more than any enhancement.

**Launched:** Kaggle `prakyats/yolo11s-wood-final-wiou-seeds` (sqrt@1024: Wise-IoU seed 42, CIoU seeds 1 and 2;
rule in its first cell). Local: 4-class fusion per section 17 (`math_model.py --tag 4cls_fusion`).

## 20. 4-class fusion (section 17 rule) -> deployed detector (2026-10-08 morning)

`math_model.py --tag 4cls_fusion` on sqrt@1024, plain@1024, sqrt@1280, plain@1280. Val singles 75.6 / 73.1 / 74.7 / 71.7
(re-matched). Grid choice on val: fusion IoU 0.55, weights 2:1:1:1 (sqrt@1024 doubled), val 78.1 / 39.2.
78.1 > 75.6 => **fusion adopted as the deployed detector** (pre-registered rule). Tested once:
**test fused 74.7 mAP50 / 36.7 mAP50-95** vs best-on-val single (sqrt@1024) 69.2 / 33.3:
mAP50 diff 95% CI [+2.7, +7.1], mAP50-95 [+1.8, +4.7], 10 boards better / 2 worse, exact Wilcoxon p = 0.042.
Per-class thresholds again worse (macro-F1 71.2 vs 73.6 global 0.20): not adopted. Test evaluations in total: 7.

## 21. Status 2026-10-08 late morning
- Deployed detector = 4-class fusion (section 20). BRI with it: test per image exact 78.3 %, within-one 96.2 %,
  QWK 0.83, Spearman 0.86; per board 10/12 exact, QWK 0.73 (eval/bri/bri_validation_fusion4_1024.json).
- app.py: default model "Final: fusion of four 4-class YOLO11s models (deployed)" (+ 8-class m+s fusion), BRI
  thresholds per detector, Results tab updated. Backups of earlier app versions in weights_local/.
- Final deck built: Major_Project/docs/Major_Project_Final_Presentation_V4.0.pptx (33 slides) by
  `python docs/collect_results.py && python docs/build_final_deck.py --date "<date>"`.
- Pending: Kaggle wiou+seeds -> download to weights_local/kaggle_wiou_v1, copy selection.json to
  runs_log/run6_final_wiou_seeds_v1/, rerun collect + build. Review date for the title slide.

## 22. Wise-IoU and seeds (Kaggle `yolo11s-wood-final-wiou-seeds` v1, 2026-10-08)
Final single setup sqrt@1024: val mAP50 seed 42 / 1 / 2 = 75.3 / 74.8 / 75.6 -> run-to-run spread 0.8.
Wise-IoU v3 (seed 42): val 74.6 / 35.7 (Crack 59.4) -> not above CIoU by more than the spread -> not adopted, no test
evaluation (rule in the notebook's first cell). Test evaluations in total stay at 7.
Review date: 24 October 2026, 9 am (title slide, Gantt).
