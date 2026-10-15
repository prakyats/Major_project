"""
prepare_full.py - board-level dataset from the full Kodytek et al. set (20,276 images, 407 boards).

Our 81 boards keep their split from dataset_clean/board_split.json (52 / 17 / 12); the 326 new boards are split
70 / 18 / 12 by board with seed 42. Labels come from the converted full set (8 classes, our id order) for every image,
with the same clean-up as prepare_dataset.py (clip to [0, 1], drop boxes with w or h <= 0.0005). Images are symlinked
(subset images from wood-defects-clean, new images from wood-full-convert), names hash-prefixed so rect batches mix
boards. Also writes val_orig.txt / test_orig.txt: the original 714 validation and 469 test images, so new models can
be compared with the old ones on exactly the same images.

python prepare_full.py --subset <dataset_clean dir> --full <dir with images/ labels/> --out <dir>
"""
import argparse, hashlib, json, os, random
from collections import Counter, defaultdict
from pathlib import Path

NAMES = ["Quartzity", "Live_Knot", "Marrow", "Resin", "Dead_Knot", "Knot_with_crack", "Knot_missing", "Crack"]
MIN_WH = 0.0005


def clean(lines):
    out = []
    for ln in lines:
        v = ln.split()
        if len(v) != 5:
            continue
        c, xc, yc, w, h = int(v[0]), *map(float, v[1:])
        x1, y1, x2, y2 = max(0, xc - w / 2), max(0, yc - h / 2), min(1, xc + w / 2), min(1, yc + h / 2)
        if x2 - x1 <= MIN_WH or y2 - y1 <= MIN_WH:
            continue
        out.append(f"{c} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", required=True)
    ap.add_argument("--full", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    sub, full, out = Path(a.subset), Path(a.full), Path(a.out)
    split = json.loads((sub / "board_split.json").read_text())
    board_of = {}
    for sp in ("train", "val", "test"):
        for b in split[sp]:
            board_of[str(b)] = sp
    src = {}                                   # stem -> image path
    orig = defaultdict(list)                   # original split membership of subset images
    for sp in ("train", "val", "test"):
        for p in (sub / sp / "images").glob("*.jpg"):
            stem = p.stem.split("_", 1)[1]
            src[stem] = p; orig[sp].append(stem)
    for p in (full / "images").glob("*.jpg"):
        src.setdefault(p.stem, p)
    labels = {p.stem: p for p in (full / "labels").glob("*.txt")}
    stems = sorted(s for s in labels if s in src)
    new_boards = sorted({s[:4] for s in stems} - set(board_of))
    rng = random.Random(a.seed); rng.shuffle(new_boards)
    n = len(new_boards); ntr, nva = round(0.70 * n), round(0.18 * n)
    for i, b in enumerate(new_boards):
        board_of[b] = "train" if i < ntr else ("val" if i < ntr + nva else "test")
    counts = {sp: Counter() for sp in ("train", "val", "test")}
    nimg, nb = Counter(), {sp: set() for sp in ("train", "val", "test")}
    names = {}
    for s in stems:
        sp = board_of[s[:4]]
        name = hashlib.sha1(f"{a.seed}-{s}".encode()).hexdigest()[:6] + "_" + s
        names[s] = (sp, name)
        (out / sp / "images").mkdir(parents=True, exist_ok=True); (out / sp / "labels").mkdir(parents=True, exist_ok=True)
        dst = out / sp / "images" / f"{name}.jpg"
        if not dst.exists():
            os.symlink(os.path.abspath(src[s]), dst)
        rows = clean(labels[s].read_text().splitlines())
        (out / sp / "labels" / f"{name}.txt").write_text("".join(r + "\n" for r in rows))
        counts[sp].update(int(r.split()[0]) for r in rows); nimg[sp] += 1; nb[sp].add(s[:4])
    for sp in ("train", "val", "test"):
        assert not (nb[sp] & set().union(*[nb[o] for o in nb if o != sp])), "board overlap"
    for sp, key in (("val", "val_orig"), ("test", "test_orig")):
        paths = [str((out / sp / "images" / f"{names[s][1]}.jpg").absolute()) for s in sorted(orig[sp]) if s in names]
        (out / f"{key}.txt").write_text("\n".join(paths) + "\n")
        print(key, len(paths), "images")
    (out / "data.yaml").write_text(f"path: {out.absolute().as_posix()}\ntrain: train/images\nval: val/images\ntest: test/images\n\n"
                                   f"nc: {len(NAMES)}\nnames:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)))
    (out / "board_split.json").write_text(json.dumps({sp: sorted(nb[sp]) for sp in nb}, indent=1))
    print(f"{'split':6s} boards images " + " ".join(f"{n[:9]:>9s}" for n in NAMES))
    for sp in ("train", "val", "test"):
        print(f"{sp:6s} {len(nb[sp]):6d} {nimg[sp]:6d} " + " ".join(f"{counts[sp][i]:9d}" for i in range(len(NAMES))))
    print("board overlap: 0 (asserted)")


if __name__ == "__main__":
    main()
