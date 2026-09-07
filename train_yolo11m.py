"""
train_yolo11m.py — YOLO11m on the board-split wood dataset. Resumable.

Fresh run :  python train_yolo11m.py --data dataset_clean/data.yaml
Resume    :  python train_yolo11m.py --data dataset_clean/data.yaml   (auto-detects last.pt)
Kaggle    :  set --project /kaggle/working/outputs and re-run the same cell after a restart.

Notes on the config
  imgsz=1024 + rect=True : 2800x1024 strips train at 1024x384 (no black padding,
                           ~same compute as 640-square, 1.6x resolution vs 768 rect).
  rect mode disables mosaic and shuffling in Ultralytics — prepare_dataset.py
  hash-prefixes filenames so the sorted order is already random.
  copy_paste is omitted: it needs polygon labels and is a no-op on boxes.
  degrees/flipud = 0 : grain runs along the scan axis; vertical flips are unphysical.
"""
import argparse, shutil
from pathlib import Path
from ultralytics import YOLO

CFG = dict(
    epochs=100, imgsz=1024, rect=True, batch=16, patience=25,
    optimizer="AdamW", lr0=0.002, lrf=0.01, cos_lr=True,
    weight_decay=0.0005, warmup_epochs=3,
    cls=1.0, box=7.5, dfl=1.5,
    hsv_h=0.01, hsv_s=0.3, hsv_v=0.2,
    degrees=0.0, translate=0.08, scale=0.3,
    fliplr=0.5, flipud=0.0, mosaic=0.0, mixup=0.0, erasing=0.05,
    amp=True, cache=False, workers=4, seed=42, deterministic=True, plots=True,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--project", default="outputs")
    ap.add_argument("--name", default="yolo11m_1024rect")
    ap.add_argument("--device", default="0", help="'0', '0,1' or 'cpu'")
    ap.add_argument("--epochs", type=int, default=CFG["epochs"])
    ap.add_argument("--batch", type=int, default=CFG["batch"])
    ap.add_argument("--lr0", type=float, default=CFG["lr0"], help="override CFG lr0 (log the reason in NOTES.md)")
    ap.add_argument("--patience", type=int, default=CFG["patience"], help="override CFG patience")
    ap.add_argument("--imgsz", type=int, default=CFG["imgsz"], help="override CFG imgsz (rect stays on)")
    ap.add_argument("--persist", default=None, help="optional dir to copy weights+results into after training")
    a = ap.parse_args()

    run_dir = Path(a.project) / a.name
    last = run_dir / "weights" / "last.pt"
    cfg = dict(CFG, epochs=a.epochs, batch=a.batch, lr0=a.lr0, patience=a.patience, imgsz=a.imgsz,
               device=a.device, project=a.project, name=a.name, exist_ok=True)

    if last.exists():
        print(f"resuming from {last}")
        model = YOLO(str(last))
        model.train(resume=True)
    else:
        print("fresh run from COCO-pretrained yolo11m.pt")
        model = YOLO("yolo11m.pt")
        model.train(data=a.data, **cfg)

    if a.persist:
        dst = Path(a.persist) / a.name
        dst.mkdir(parents=True, exist_ok=True)
        for f in ["weights/best.pt", "weights/last.pt", "results.csv", "args.yaml",
                  "confusion_matrix.png", "PR_curve.png", "F1_curve.png", "results.png"]:
            src = run_dir / f
            if src.exists():
                shutil.copy2(src, dst / src.name)
        print(f"persisted to {dst}")


if __name__ == "__main__":
    main()
