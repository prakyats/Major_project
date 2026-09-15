"""
test_photos.py -- run both final detectors over a folder of your own wood photos.

Usage:
  python test_photos.py --src "C:/path/to/photos" --out photo_tests/college_2026-09-15 [--conf 0.30]

Writes, per image: <stem>_11m.jpg, <stem>_11s.jpg (boxes), <stem>_11m_heat.jpg (heatmap);
plus contact_sheet.jpg (input | YOLO11m | YOLO11s per row, for a slide) and results.csv / results.md.
Input size is chosen automatically per image (same rule as the app): full strips at 1024, small photos near native.
"""
import argparse, csv, glob, os, time
from pathlib import Path
import cv2
import numpy as np

import app  # reuse the demo's model loading, drawing, heatmap and size rule


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--conf", type=float, default=0.30)
    ap.add_argument("--iou", type=float, default=0.6)
    ap.add_argument("--max-side", type=int, default=2000, help="downscale very large phone photos to this longest side before inference")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in glob.glob(str(Path(a.src) / "*")) if p.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")))
    if not files:
        raise SystemExit(f"no images in {a.src}")
    models = {k: app.get_model(k) for k in app.WEIGHTS}
    rows, sheet_rows = [], []
    for f in files:
        img = cv2.imread(f)
        if img is None:
            print("skip unreadable", f); continue
        # phone photos may carry EXIF rotation; cv2 ignores it, so honour it via PIL
        try:
            from PIL import Image, ImageOps
            pim = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
            img = cv2.cvtColor(np.array(pim), cv2.COLOR_RGB2BGR)
        except Exception:
            pass
        h, w = img.shape[:2]
        if max(h, w) > a.max_side:
            s = a.max_side / max(h, w); img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        imgsz = app.pick_imgsz(img, "Auto")
        stem = Path(f).stem
        vis = {}
        for k, m in models.items():
            short = "11m" if "11m" in k else "11s"
            res = app.run_one(m, img, a.conf, a.iou, imgsz)
            labels = [f"{d['cls']} {d['conf']:.2f}" for d in res["dets"]]
            vis[short] = app.draw_boxes(img, res["boxes"], labels)
            cv2.imwrite(str(out / f"{stem}_{short}.jpg"), vis[short], [cv2.IMWRITE_JPEG_QUALITY, 90])
            if short == "11m":
                cv2.imwrite(str(out / f"{stem}_11m_heat.jpg"), app.heatmap(img, res["boxes"], res["confs"]), [cv2.IMWRITE_JPEG_QUALITY, 90])
            pc, cov = app.per_class(res["dets"], img.shape)
            counts = ", ".join(f"{r[0]} x{r[1]}" for r in pc) or "none"
            top = f"{res['dets'][0]['cls']} {res['dets'][0]['conf']:.2f}" if res["dets"] else ""
            rows.append([Path(f).name, f"{img.shape[1]}x{img.shape[0]}", imgsz, short, len(res["dets"]), counts, cov, top, round(res["dt"] * 1000)])
            print(f"{Path(f).name:40} {short}  {len(res['dets']):2} dets  {counts}")
        # contact sheet row: input | 11m | 11s
        th = 300; tw = int(w * th / h) if h else 400
        tiles = [cv2.resize(x, (min(tw, 700), th)) for x in (img, vis["11m"], vis["11s"])]
        sheet_rows.append(np.hstack(tiles))
    # write tables
    hdr = ["image", "input px", "imgsz", "model", "n_dets", "classes (count)", "coverage %", "top detection", "ms (CPU)"]
    with open(out / "results.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([hdr] + rows)
    md = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    (out / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    # contact sheet (pad rows to equal width)
    W = max(r.shape[1] for r in sheet_rows)
    padded = [np.pad(r, ((0, 6), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in sheet_rows]
    sheet = np.vstack(padded)
    cv2.putText(sheet, "input | YOLO11m | YOLO11s", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.imwrite(str(out / "contact_sheet.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"\nwrote {len(files)} images x 2 models to {out}  (results.md, contact_sheet.jpg)")


if __name__ == "__main__":
    main()
