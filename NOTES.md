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
- [ ] Test evaluated exactly once on (date):
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
