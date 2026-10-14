# AI-Based Wood Quality Assessment

VTU major project, Dept. of CSBS, Dayananda Sagar College of Engineering, AY 2026-27. Guide: Mrs. Aparna H D.
Team 4: Gurugubelli Gayatri, Prakyat Pramod Shetty, Saiprasad Rao, Yasti Anil Kotak.

The system finds surface defects on sawn-timber board images, grades each board (A / B / C / Reject) with the
Board Recoverability Index, and estimates its recoverable area and value. Final review: **24 October 2026**.

**Status (14 Oct 2026): complete.** Everything proposed at the 50 % review is implemented and measured on 12
physical boards never used for training or for any choice of settings. An extension on the full 20,275-image
dataset is in progress (see the end of this page).

## Results on the 12 held-out test boards

| Model | Classes | Test mAP50 | Test mAP50-95 |
|---|---:|---:|---:|
| YOLO11m (50 % review) | 8 | 63.0 | 34.0 |
| YOLO11s (50 % review) | 8 | 64.6 | 33.4 |
| YOLO11s, scored on the 4 main classes | 4 | 69.6 | 32.9 |
| Best single 4-class model (partial class balance, 1024 px) | 4 | 69.2 | 33.1 |
| **Deployed: weighted box fusion of four 4-class YOLO11s models** | 4 | **74.7** | **36.7** |

The fusion is the mathematical model's main result: mAP50 +5.5 over the best single model, 95 % board-bootstrap
interval +2.7 to +7.1, better on 10 of 12 boards (exact Wilcoxon p = 0.042). Grading (BRI) agrees with grades
computed from the annotations with weighted kappa 0.83. Every choice was made on the 17 validation boards; each
candidate final model was tested once (7 test evaluations in total).

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

## Documents (`docs/`)

| File | What it is |
|---|---|
| `Major_Project_Final_Presentation_V4.0.pptx` | Final (100 %) review deck, 33 slides |
| `Project_Status_and_Mathematical_Model_2026-10-14.docx` | Phase-by-phase status and the mathematical model (draft) |
| `BRI_Model_Update_2026-10-07.docx` | The guide's BRI model: our reading, changes and validation |
| `Presentation_Speaker_Notes.docx`, `Major_Project_50pct_Presentation_V3.0.pptx` | 50 % review material |
| [NOTES.md](NOTES.md) | Decision log: every run, result and deviation (sections 1-22) |
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
| `bri.py`, `bri_validate.py`, `bri_validate_fused.py` | Board Recoverability Index and its validation |
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

Weights go in `weights/` (not in git; from the Kaggle notebook outputs): `yolo11s_4cls_balanced.pt`,
`yolo11s_4cls_plain.pt`, `yolo11s_4cls_sqrt_1280.pt`, `yolo11s_4cls_plain_1280.pt` (deployed fusion),
`yolo11m_final.pt`, `yolo11s_baseline.pt` (8-class models). The default model is the deployed fusion; the app shows
boxes, a heatmap, the grade, damage score, recoverable area, an editable value estimate and a JSON report.
The deployed fusion takes about 2 s per 2800 x 1024 image on a laptop CPU.

## Reproduce

Data: Kodytek, Bodzas and Bilik (2022), F1000Research 10:581, doi:10.12688/f1000research.52903.2 (4,000-image
Kaggle subset). Prepare with
`python prepare_dataset.py --src data --out dataset_clean --names Quartzity Live_Knot Marrow Resin Dead_Knot Knot_with_crack Knot_missing Crack --ratios 0.70 0.18 0.12 --seed 42`,
then `python build_balanced.py --src dataset_clean --out dataset_4cls --seed 42`. Training ran on Kaggle (one
Tesla T4); the notebooks in `kaggle_upload/` show the exact commands. Seed 42 throughout.

## In progress: full dataset

The original dataset has 20,275 images from 407 boards (our subset: 4,000 images, 81 boards), with 4-7x more
examples of the rare classes. The two strongest fusion members (partial balance at 1024 and 1280 px, 4 classes)
are being retrained on it, keeping the current 12 test boards so results compare directly with 74.7.
The current deployed system remains the version for the final review if this is not ready or not better.
