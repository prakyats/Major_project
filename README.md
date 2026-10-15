# AI-Based Wood Quality Assessment

VTU major project, Dept. of CSBS, Dayananda Sagar College of Engineering, AY 2026-27. Guide: Mrs. Aparna H D.
Team 4: Gurugubelli Gayatri, Prakyat Pramod Shetty, Saiprasad Rao, Yasti Anil Kotak.

The system finds surface defects on sawn-timber board images, grades each board (A / B / C / Reject) with the
Board Recoverability Index, and estimates its recoverable area and value. Final review: **24 October 2026**.

**Status (15 Oct 2026): complete.** Everything proposed at the 50 % review is implemented and measured on
physical boards never used for training or for any choice of settings. The final detector is trained on the full
dataset (20,276 images, 407 boards).

## Results on the 12 held-out test boards

| Model | Classes | Test mAP50 | Test mAP50-95 |
|---|---:|---:|---:|
| YOLO11m (50 % review) | 8 | 63.0 | 34.0 |
| YOLO11s (50 % review) | 8 | 64.6 | 33.4 |
| YOLO11s, scored on the 4 main classes | 4 | 69.6 | 32.9 |
| Best single 4-class model (partial class balance, 1024 px) | 4 | 69.2 | 33.1 |
| Weighted box fusion of four 4-class YOLO11s models (4,000-image subset) | 4 | 74.7 | 36.7 |
| **Final: fusion of two 4-class YOLO11s models trained on the full dataset (1024 + 1280 px)** | 4 | **76.9** | **39.3** |

On the full dataset's own test split (2,488 images, 51 unseen boards) the final detector scores **81.3 mAP50 /
44.1 mAP50-95** (AP50: Live_Knot 87.1, Dead_Knot 87.5, Resin 83.3, Crack 67.4).

Fusion is the mathematical model's main result: on the subset, mAP50 +5.5 over the best single model (95 %
board-bootstrap interval +2.7 to +7.1, better on 10 of 12 boards, exact Wilcoxon p = 0.042). Training on the full
dataset adds +2.2 on the same 12 boards (interval +0.5 to +4.3) with two models instead of four; it replaced the
subset fusion under a rule fixed before training (original validation mAP50 80.2 > 78.1). Grading (BRI) with the
final detector agrees with grades computed from the annotations with weighted kappa 0.87 (exact 78.3 %, within one
grade 97.4 %). Every choice was made on validation boards; each candidate final model was tested once.

Tested and **not** adopted (reported with intervals): class balancing alone, 1280-px input, Wise-IoU v3 loss,
per-class confidence thresholds, CLAHE / denoising / sharpening (hypothesis H1 rejected for normal images).

## Project phases

1. **Starting point.** An early YOLO11s (640 px, CPU) scored 62.2 mAP50, but on a split that leaked boards into
   the test set, with wrong class names and square padding. Rebuilt from scratch.
2. **Up to the 50 % review (16 Sep).** Board-level split (52 / 17 / 12 boards, zero overlap), correct class names,
   rectangular 1024-px input, YOLO11m vs YOLO11s on Kaggle T4 (tied at 63-65 mAP50), demo application.
3. **To completion (8 Oct).** Four main classes, copy-paste class balancing, 1280-px and Wise-IoU runs, three
   seeds, weighted box fusion, statistical validation, image-enhancement study, the guide's Board Recoverability
   Index (adapted to line-scan geometry and validated), market-value estimate, final application and deck.
4. **Full dataset (15 Oct).** All 20,276 images (407 boards; our 81 boards keep their split, new boards 70 / 18 / 12).
   The two strongest settings retrained on Kaggle and fused: 76.9 on the original test boards, 81.3 on 51 new ones.

## Documents (`docs/`)

| File | What it is |
|---|---|
| `Major_Project_Final_Presentation_V4.1.pptx` | Final (100 %) review deck, 34 slides (V4.0: before the full dataset) |
| `Project_Status_and_Mathematical_Model_2026-10-14.docx` | Phase-by-phase status and the mathematical model (draft) |
| `BRI_Model_Update_2026-10-07.docx` | The guide's BRI model: our reading, changes and validation |
| `Presentation_Speaker_Notes.docx`, `Major_Project_50pct_Presentation_V3.0.pptx` | 50 % review material |
| [NOTES.md](NOTES.md) | Decision log: every run, result and deviation (sections 1-23) |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Progress log up to the 50 % review |

## Code

| Script | Purpose |
|---|---|
| `prepare_dataset.py` | Label cleaning, board-level split, hash-prefixed file names |
| `build_balanced.py` | 4-class subset and grain-aware copy-paste balancing (plain / full / partial) |
| `train_yolo11m.py`, `train_wiou.py` | Training (any YOLO11 size, resumable, `--seed`); Wise-IoU v3 variant |
| `evaluate.py` | Single-shot test evaluation: per-class P, R, F1, mAP50, mAP50-95 |
| `eval_capture.py` | Runs the official evaluator and keeps every prediction for later analysis |
| `math_model.py` | Weighted box fusion, per-class thresholds, board bootstrap and exact Wilcoxon tests |
| `stats_4cls.py` | Paired significance tests between the 4-class models |
| `prepare_full.py`, `eval_full.py` | Full-dataset split (keeps our 81 boards' split); fusion, decision rule and tests for the full-data models |
| `bri.py`, `bri_validate.py`, `bri_validate_fused.py`, `bri_validate_full.py` | Board Recoverability Index and its validation |
| `enhance_study.py` | CLAHE / denoise / sharpen under six imaging conditions (validation) |
| `app.py` | Gradio demo application |
| `docs/collect_results.py`, `docs/build_final_deck.py`, `docs/make_final_diagrams.py`, `docs/make_status_doc.py` | Rebuild the deck, figures and status document from the result files |

Results: `eval/` (test and validation tables, fusion, BRI, enhancement, statistics), `runs_log/` (training logs
per run), `kaggle_upload/` (the Kaggle notebooks that produced every run).

## Run the demo (CPU is enough)

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics gradio
python app.py        # http://127.0.0.1:7860
```

Weights go in `weights/` (not in git; from the Kaggle notebook outputs): `yolo11s_full4_1024.pt`,
`yolo11s_full4_1280.pt` (final fusion, the default model); `yolo11s_4cls_balanced.pt`, `yolo11s_4cls_plain.pt`,
`yolo11s_4cls_sqrt_1280.pt`, `yolo11s_4cls_plain_1280.pt` (subset fusion); `yolo11m_final.pt`,
`yolo11s_baseline.pt` (8-class models). The app shows boxes, a heatmap, the grade, damage score, recoverable area,
an editable value estimate and a JSON report.

## Reproduce

Data: Kodytek, Bodzas and Bilik (2022), F1000Research 10:581, doi:10.12688/f1000research.52903.2 (4,000-image
Kaggle subset). Prepare with
`python prepare_dataset.py --src data --out dataset_clean --names Quartzity Live_Knot Marrow Resin Dead_Knot Knot_with_crack Knot_missing Crack --ratios 0.70 0.18 0.12 --seed 42`,
then `python build_balanced.py --src dataset_clean --out dataset_4cls --seed 42`. Training ran on Kaggle (one
Tesla T4); the notebooks in `kaggle_upload/` show the exact commands. Seed 42 throughout.
Full dataset: Kaggle mirror `kirs0816/wood-surface-defects` of the same work (all 20,276 images, COCO boxes);
`kaggle_upload/notebook_full_train/make_nb.py` builds the CPU smoke test and the two GPU notebooks, and
`kaggle_upload/run_full_chain_v2.sh` runs them in order.
