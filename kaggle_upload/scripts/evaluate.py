"""
evaluate.py — run best.pt on the held-out test boards once, write the
per-class table (Precision / Recall / F1 / mAP50 / mAP50-95) as CSV + Markdown.

python evaluate.py --weights outputs/yolo11m_1024rect/weights/best.pt \
                   --data dataset_clean/data.yaml --split test
"""
import argparse, csv
from pathlib import Path
from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", default="test", choices=["val", "test"])
    ap.add_argument("--imgsz", type=int, default=1024)
    ap.add_argument("--device", default="0")
    ap.add_argument("--out", default="eval")
    a = ap.parse_args()

    model = YOLO(a.weights)
    m = model.val(data=a.data, split=a.split, imgsz=a.imgsz, rect=True, batch=16,
                  conf=0.001, iou=0.6, device=a.device, plots=True,
                  project=a.out, name=f"{a.split}_{Path(a.weights).parent.parent.name}", exist_ok=True)

    names = model.names
    idx = m.box.ap_class_index
    rows = []
    for k, ci in enumerate(idx):
        p, r = m.box.p[k], m.box.r[k]
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        rows.append([names[int(ci)], f"{p*100:.1f}", f"{r*100:.1f}", f"{f1*100:.1f}",
                     f"{m.box.ap50[k]*100:.1f}", f"{m.box.ap[k]*100:.1f}"])
    rows.sort(key=lambda x: -float(x[4]))
    mp, mr = m.box.mp, m.box.mr
    mf1 = 2 * mp * mr / (mp + mr) if (mp + mr) else 0.0
    rows.append(["ALL", f"{mp*100:.1f}", f"{mr*100:.1f}", f"{mf1*100:.1f}",
                 f"{m.box.map50*100:.1f}", f"{m.box.map*100:.1f}"])

    hdr = ["Class", "Precision", "Recall", "F1", "mAP@50", "mAP@50-95"]
    outdir = Path(a.out); outdir.mkdir(exist_ok=True)
    with open(outdir / f"{a.split}_metrics.csv", "w", newline="") as f:
        csv.writer(f).writerows([hdr] + rows)
    md = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)] + ["| " + " | ".join(r) + " |" for r in rows]
    (outdir / f"{a.split}_metrics.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"\ninference: {m.speed['inference']:.1f} ms/img  ->  {1000/m.speed['inference']:.1f} FPS")


if __name__ == "__main__":
    main()
