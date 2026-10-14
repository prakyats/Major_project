"""
enhance_study.py - image-enhancement study on the VALIDATION boards (synopsis hypothesis H1; 50 % review item).

H0: enhancement (CLAHE, denoising, sharpening) does not change detection accuracy compared with raw images.
For each imaging condition the validation images are degraded synthetically, then fed to the detector either raw
or enhanced. Accuracy is the official validator mAP (eval_capture.py); the effect of each enhancement is the paired
difference to "raw" under the same condition, with a board-level bootstrap interval and an exact Wilcoxon test on
the per-board AP50 differences (17 boards).

Conditions : normal, low_light (gamma 2.0, x0.55), overexposed (x1.35 + 25), blur (Gaussian sigma 2.0),
             noise (Gaussian sigma 12), low_contrast (x0.55 around the mean)
Enhancement: raw, clahe (LAB L channel, clip 2.0, 8x8 tiles), denoise (bilateral 7 / 35 / 7),
             sharpen (unsharp mask, sigma 2, amount 1.0)
The model is trained on raw line-scan images; nothing is retrained here.

python enhance_study.py --weights weights/yolo11s_4cls_balanced.pt --imgsz 1024
"""
import argparse, json, os, shutil
from pathlib import Path
import cv2
import numpy as np
from eval_capture import capture, score
from math_model import paired_tests

CONDITIONS = {
    "normal": lambda im, r: im,
    "low_light": lambda im, r: 255 * 0.55 * (im / 255.0) ** 2.0,
    "overexposed": lambda im, r: np.clip(im * 1.35 + 25, 0, 255),
    "blur": lambda im, r: cv2.GaussianBlur(im, (0, 0), 2.0),
    "noise": lambda im, r: np.clip(im + r.normal(0, 12, im.shape), 0, 255),
    "low_contrast": lambda im, r: np.clip((im - im.mean()) * 0.55 + im.mean(), 0, 255),
}


def clahe(im):
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
    lab[..., 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


ENHANCE = {
    "raw": lambda im: im,
    "clahe": clahe,
    "denoise": lambda im: cv2.bilateralFilter(im, 7, 35, 7),
    "sharpen": lambda im: cv2.addWeighted(im, 2.0, cv2.GaussianBlur(im, (0, 0), 2.0), -1.0, 0),
}


def build(src, dst, cond, enh, seed=42):
    """Write degraded (+ enhanced) copies of src/val into dst/val; labels hard-linked."""
    rng = np.random.default_rng(seed)
    (dst / "val" / "images").mkdir(parents=True, exist_ok=True); (dst / "val" / "labels").mkdir(parents=True, exist_ok=True)
    for p in sorted((src / "val" / "images").glob("*.jpg")):
        im = cv2.imread(str(p)).astype(np.float32)
        im = np.clip(CONDITIONS[cond](im, rng), 0, 255).astype(np.uint8)
        im = ENHANCE[enh](im)
        cv2.imwrite(str(dst / "val" / "images" / p.name), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        lb = src / "val" / "labels" / (p.stem + ".txt")
        if lb.exists():
            try:
                os.link(lb, dst / "val" / "labels" / lb.name)
            except OSError:
                shutil.copy2(lb, dst / "val" / "labels" / lb.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--imgsz", type=int, default=1024)
    ap.add_argument("--data", default="dataset_4cls", help="dataset root with val/images and val/labels")
    ap.add_argument("--names", nargs="+", default=["Live_Knot", "Dead_Knot", "Resin", "Crack"])
    ap.add_argument("--work", default="weights_local/enh")
    ap.add_argument("--B", type=int, default=1000)
    a = ap.parse_args()
    src, tag = Path(a.data), Path(a.weights).stem
    results = {}
    for cond in CONDITIONS:
        for enh in ENHANCE:
            key = f"{cond}__{enh}"
            cache = Path(f"eval/capture_enh/{tag}_{a.imgsz}/{key}")
            if not (cache / f"{tag}_{a.imgsz}_val.json").exists():
                d = Path(a.work) / key
                if d.exists():
                    shutil.rmtree(d)
                build(src, d, cond, enh)
                y = d / "data.yaml"
                y.write_text(f"path: {d.resolve().as_posix()}\ntrain: val/images\nval: val/images\n\nnc: {len(a.names)}\n"
                             f"names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(a.names)))
                capture(a.weights, str(y), "val", a.imgsz, cache_dir=str(cache))
                shutil.rmtree(d)                               # free disk; the predictions are cached
            results[key] = capture(a.weights, "", "val", a.imgsz, cache_dir=str(cache))
            print(key, round(100 * results[key]["map50"], 1), round(100 * results[key]["map"], 1), flush=True)
    table, tests = {}, {}
    for cond in CONDITIONS:
        raw = results[f"{cond}__raw"]
        table[cond] = {enh: dict(map50=results[f"{cond}__{enh}"]["map50"], map=results[f"{cond}__{enh}"]["map"])
                       for enh in ENHANCE}
        for enh in ENHANCE:
            if enh != "raw":
                tests[f"{cond}: {enh} - raw"] = paired_tests(results[f"{cond}__{enh}"]["images"], raw["images"], B=a.B)
    out = dict(weights=a.weights, imgsz=a.imgsz, split="val", table=table, tests=tests)
    Path("eval/enhancement").mkdir(parents=True, exist_ok=True)
    Path(f"eval/enhancement/{tag}_{a.imgsz}.json").write_text(json.dumps(out, indent=2))
    hdr = "| condition | " + " | ".join(ENHANCE) + " |"
    lines = [hdr, "|---" * (len(ENHANCE) + 1) + "|"]
    for cond, row in table.items():
        lines.append(f"| {cond} | " + " | ".join(f"{100 * row[e]['map50']:.1f}" for e in ENHANCE) + " |")
    lines += ["", "| comparison | mAP50 diff 95% CI | boards better / worse | Wilcoxon p |", "|---|---|---|---:|"]
    for k, t in tests.items():
        lines.append(f"| {k} | [{t['map50_diff_ci'][0]:+.1f}, {t['map50_diff_ci'][1]:+.1f}] | "
                     f"{t['boards_better']} / {t['boards_worse']} | {t['wilcoxon_p']:.3f} |")
    md = "\n".join(lines) + "\n"
    Path(f"eval/enhancement/{tag}_{a.imgsz}.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
