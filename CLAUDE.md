# CLAUDE.md — AI-Based Wood Quality Assessment (YOLO11m sprint)

Read this fully before touching anything. It is the handover from a prior planning session.

## Goal (next 7 days, deadline hard)
Train **YOLO11m** on the wood-surface-defect dataset and produce a defensible per-class
metrics table on a held-out test set of physically separate boards. Nothing else is in scope
until that exists. No YOLOv8 baseline, no CWB-YOLOv8, no recoverability estimation yet.

## Project background
- VTU major project (DSCE, CSBS dept, AY 2026-27), 4-student team, guide Mrs. Aparna H D.
- Synopsis (Major-Project_Synopsis_V2_0.pdf) promises YOLOv8 baseline vs CWB-YOLOv8 on
  *plywood*. Implementation has diverged: YOLO11 on a sawn-timber dataset. The synopsis will be
  reworded later — do not spend time on it now, but keep results in a form that fits a
  "baseline vs proposed" narrative (per-class P/R/F1/mAP50/mAP50-95, inference ms/FPS).
- Prior run already exists: **YOLO11s @ 640 square, CPU, 83 epochs**, best.pt @ epoch 75:
  val mAP50 66.26 / mAP50-95 36.45 / P 71.81 / R 64.75; test mAP50 62.2.
  Per-class test mAP50: Split 88.1, Hole 87.7, Knot 81.2, Stain 72.5, Decay 59.2,
  Warp 47.5, Scratch 42.2, Crack 19.2 (Crack recall 10.5%).
  **These numbers are inflated by board leakage (see below) and must not be compared
  directly with the new run.**

## Dataset
- Source: https://www.kaggle.com/datasets/nomihsa965/large-scale-image-dataset-of-wood-surface-defects
  — a 4,000-image subset of Kodytek, Bodzas & Bilik (2022), "A large-scale image dataset of
  wood surface defects for automated vision-based quality control processes",
  *F1000Research* 10:581, doi:10.12688/f1000research.52903.2. Cite this.
- Sawn timber line-scan strips, **2800×1024** (98.9%; 44 images slightly narrower),
  aspect ≈ 2.73:1. Grain runs along the scan axis.
- Original dataset has 10 classes: live knot, dead knot, missing knot, knot with crack, crack,
  quartzity, resin, marrow, blue stain, overgrown.
- Team's current `data.yaml` uses **8 renamed classes**:
  `0 Crack, 1 Knot, 2 Hole, 3 Stain, 4 Split, 5 Warp, 6 Decay, 7 Scratch`.
  These are NOT the dataset's names. **Open task: find the real mapping** (check the label
  files / class list shipped on Kaggle) and record it in NOTES.md. The report must state it.
- Current local layout: `data/{train,valid,test}/{images,labels}` YOLO txt, 4,000 images,
  9,211 boxes, 388 background images (9.7%). Class share: Knot 44.2%, Split 31.9%,
  Stain 7.1%, Warp 5.9%, Scratch 5.6%, Hole 2.2%, Crack 1.9%, Decay 1.3%.
- Filenames: 9-digit stem, **first 4 digits = physical board id** (81 boards), rest = tile index.

## Known data problems (all handled by prepare_dataset.py — verify, don't redo)
1. **Board leakage**: previous split was tile-level; 100% of boards appear in train, val AND
   test. Fix = group-stratified split by board id. Script asserts zero overlap.
2. **77 degenerate boxes** (w or h = 0 or sub-pixel). Script drops boxes with w or h ≤ 0.0005
   after clipping to [0,1].
3. **Letterbox collapse**: 640 square wastes 63% of the tensor on padding and squashes
   hairline cracks below 1 px. Fix = `imgsz=1024 rect=True` (active 1024×384).
4. 42–48% of boxes are COCO-"small". Crack boxes avg w 0.031 × h 0.457 (hairline).
   Warp boxes are diffuse shadow regions — expect it to stay weak; don't chase it.

## Ultralytics gotchas already accounted for (do not "fix" them back)
- `rect=True` **disables mosaic and DataLoader shuffle**. Batches = consecutive sorted
  filenames. prepare_dataset.py prefixes every filename with a seeded 6-char hash so sorted
  order is random and batches mix boards. Keep the prefix; board id is still after the `_`.
- `copy_paste` is a no-op on box-only labels (needs polygons). Not used.
- `mosaic`/`close_mosaic` irrelevant under rect. Set mosaic=0.0 explicitly.
- Old augmentation had `degrees=10, flipud=0.1, erasing=0.4, hsv_s=0.7` — all bad for
  oriented grain / hairline defects. New config: degrees 0, flipud 0, erasing 0.05,
  hsv_h/s/v 0.01/0.3/0.2, fliplr 0.5, translate 0.08, scale 0.3.
- Fine-tune from COCO `yolo11m.pt`. Never random init on 4k images.
- Evaluate **best.pt** (val mAP50), never last.pt. Test split is run exactly once at the end;
  no hyperparameter, threshold, or patience decision may use it.

## Compute
- Team machine is **CPU only** (PyTorch 2.6). YOLO11m ≈ 100–120 min/epoch there → not viable.
- Plan: **Kaggle**, GPU T4 ×2, 30 GPU-h/week, 12 h/session. Expect roughly 5–8 min/epoch on
  a single T4 at 1024 rect batch 16; use `--device 0,1 --batch 32` on 2×T4. Budget ~10–14 h.
- Training must be resumable across sessions: train_yolo11m.py auto-resumes if
  `<project>/<name>/weights/last.pt` exists. Save Kaggle output between sessions.
- If OOM: halve batch. Do not drop imgsz below 1024 rect without noting why.

## Repo files
- `prepare_dataset.py` — pairs images/labels, drops degenerate boxes, board-level
  group-stratified split (70/18/12), hash-prefix rename, writes `dataset_clean/data.yaml`
  and `board_split.json`, prints per-split class table + overlap assertion.
  Run: `python prepare_dataset.py --src data --out dataset_clean --names Crack Knot Hole Stain Split Warp Decay Scratch --ratios 0.70 0.18 0.12 --seed 42`
- `train_yolo11m.py` — CFG dict holds the full training config (AdamW lr0 0.002, cos_lr,
  100 epochs, patience 25, cls 1.0 / box 7.5 / dfl 1.5, amp, seed 42, deterministic).
  Flags: `--data --project --name --device --epochs --batch --persist`.
- `evaluate.py` — `model.val(split=test, imgsz=1024, rect=True, conf=0.001, iou=0.6)`,
  writes `eval/test_metrics.{csv,md}` (per-class P/R/F1/mAP50/mAP50-95 + ALL row) and
  prints inference ms/img and FPS.
- `README.md` — Kaggle cell-by-cell instructions and the 7-day plan.

## Immediate task list (in order)
1. Run prepare_dataset.py on `data/`. Inspect the printed table: 0 overlap, every class
   present in train/val/test, val+test each ≥ 10 boards. If a rare class (Decay/Crack/Hole)
   has < ~10 boxes in val, adjust `--seed` or ratios and rerun; note what you changed.
2. Look at 5–10 label files before/after to confirm the degenerate filter did not remove
   legitimate thin Crack boxes (real cracks are ~0.03 wide, well above 0.0005).
3. Zip `dataset_clean/` → upload as a private Kaggle Dataset. Upload the 3 scripts too.
4. Start training per README. Confirm first-epoch log shows `rect` active, image shape
   ~(3,384,1024) or (3,1024,384), and no "shuffle" warning surprises.
5. After training: run evaluate.py on test once. Commit `eval/`, `results.csv`,
   `confusion_matrix.png`, `PR_curve.png`, `F1_curve.png`, `args.yaml`. Do not commit weights;
   store best.pt in Kaggle/Drive and link it.
6. Write NOTES.md: real class mapping, final split table, epochs run, best epoch,
   wall-clock time, any deviations from CFG.

## Realistic expectations (don't over-promise in the report)
Clean-split numbers will likely be *lower* than the leaky 66% val figure at first glance and
that is correct. Realistic overall test mAP50 after these fixes: ~70–80%. Crack and Scratch
should improve substantially from the resolution fix; Warp probably won't.

## Rules
- Never tune anything on the test split.
- Every result reports P, R, mAP50, mAP50-95 separately — never "accuracy".
- Keep seed=42 everywhere. Log every deviation from CFG in NOTES.md with a reason.
- Don't rewrite the synopsis in this sprint; collect what the rewrite will need.

## Status update 2026-09-07 (read NOTES.md before continuing)
- Real class mapping found and adopted: ids 0-7 = Quartzity, Live_Knot, Marrow, Resin, Dead_Knot,
  Knot_with_crack, Knot_missing, Crack. The 8 names listed above (Crack/Knot/Hole/...) were wrong.
  The prepare_dataset command under "Repo files" must use the real names (README section 1 has it).
- Tasks 1 and 2 done: dataset_clean/ built with seed 42, 0 board overlap, table in NOTES.md section 4.
- Raw zip is the flat Kaggle layout; extract to data/images + data/labels, not data/train/....
