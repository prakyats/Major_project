"""
build_balanced.py - 4-class subset of dataset_clean, balanced by grain-aware copy-paste.

Keeps the 4 defect classes with the most boxes in the cleaned dataset
(Live_Knot 4018, Dead_Knot 2896, Resin 646, Crack 512; Knot_with_crack is 5th with 505),
remaps them to ids 0-3, and writes three training sets that share one val and one test set:

  train_plain : real train images, 4-class labels                       (control, no balancing)
  train_full  : + synthetic images until every class reaches n_max       (full balance)
  train_sqrt  : + synthetic images until class c reaches sqrt(n_c*n_max) (repeat-factor rule,
                Gupta et al., LVIS, CVPR 2019)

A synthetic image is a defect-free train image (the canvas) that receives 2-5 defect crops cut
from other train images. In these line-scan images the board runs top to bottom (grain and cracks
are vertical); the left/right ~150-190 px, and the end of the board on some tiles, are black
conveyor background, so a board mask is computed per image and crops are taken
only from inside the board and pasted only inside the canvas board. Crops keep their orientation
(no rotation, no vertical flip); only horizontal flip and +-10 % scale are applied. A crop never
lands on any existing box of the original 8 classes, so nothing is covered and no unlabelled
defect is created. Blending alternates between Poisson cloning and a feathered alpha blend that
is fully opaque on the defect box and fades out over the context margin, so the detector cannot
learn one seam artefact (Dwibedi et al., ICCV 2017). Only train images are used as sources and
canvases, so the board-level split is untouched. Val and test are the real images with 4-class
labels. Deterministic for a given --seed.

python build_balanced.py --src dataset_clean --out dataset_4cls --seed 42
"""
import argparse, collections, hashlib, json, math, os, random, shutil
from pathlib import Path
import cv2
import numpy as np

SRC_NAMES = ["Quartzity", "Live_Knot", "Marrow", "Resin", "Dead_Knot",
             "Knot_with_crack", "Knot_missing", "Crack"]
KEEP = ["Live_Knot", "Dead_Knot", "Resin", "Crack"]          # new ids 0..3
OLD2NEW = {SRC_NAMES.index(n): i for i, n in enumerate(KEEP)}
MIN_SRC_PX = 8      # crop sources smaller than this (either side) are annotation artefacts
GAP = 6             # px kept free around every box when placing a crop
PAD = 24            # reflect-padding of the canvas so blending works at the image border
EDGE = 12           # px kept clear inside the board edge


def board_mask(im, erode_px=0):
    """Integral image of the board mask at 1/4 resolution (black conveyor and board ends excluded).
    Dark regions enclosed by wood (knots, resin) count as board: only dark regions connected to the
    left/right image sides are background. None if the board covers under half the image."""
    g = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (im.shape[1] // 4, im.shape[0] // 4),
                   interpolation=cv2.INTER_AREA)
    _, lab = cv2.connectedComponents((g <= 60).astype(np.uint8), connectivity=4)
    side = (set(np.unique(lab[:, 0])) | set(np.unique(lab[:, -1]))) - {0}
    board = (~np.isin(lab, list(side))).astype(np.uint8)
    n, lab2, st, _ = cv2.connectedComponentsWithStats(board, connectivity=4)
    if n < 2:
        return None
    board = (lab2 == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    if board.mean() < 0.5:
        return None
    if erode_px:
        k = max(1, erode_px // 4)
        board = cv2.erode(board, np.ones((2 * k + 1, 2 * k + 1), np.uint8))
    return cv2.integral(board)


def on_board(ii, x1, y1, x2, y2):
    """Fraction of the rectangle (full-res px) that lies on the board."""
    a, b = max(0, int(x1) // 4), max(0, int(y1) // 4)
    c, d = min(ii.shape[1] - 1, -(-int(x2) // 4)), min(ii.shape[0] - 1, -(-int(y2) // 4))
    if c <= a or d <= b:
        return 0.0
    return float(ii[d, c] - ii[b, c] - ii[d, a] + ii[b, a]) / ((c - a) * (d - b))


def read_labels(p):
    out = []
    if p.exists():
        for ln in p.read_text().splitlines():
            v = ln.split()
            if len(v) == 5:
                out.append((int(v[0]), *map(float, v[1:])))
    return out


def to_px(l, W, H):
    _, xc, yc, w, h = l
    return ((xc - w / 2) * W, (yc - h / 2) * H, (xc + w / 2) * W, (yc + h / 2) * H)


def to_yolo(c, x1, y1, x2, y2, W, H):
    x1, x2 = max(0.0, x1), min(float(W), x2)
    y1, y2 = max(0.0, y1), min(float(H), y2)
    return f"{c} {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}"


def overlaps(a, b, gap=0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def link(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        try:                                   # read-only or cross-device source (Kaggle inputs): symlink
            os.symlink(os.path.realpath(src), dst)
        except OSError:
            shutil.copy2(src, dst)


def write_split(src_root, dst_root, split):
    """Real images (hard-linked) + 4-class labels. Returns per-class box counts."""
    si, sl = src_root / split / "images", src_root / split / "labels"
    di, dl = dst_root / split / "images", dst_root / split / "labels"
    di.mkdir(parents=True, exist_ok=True); dl.mkdir(parents=True, exist_ok=True)
    cnt = collections.Counter()
    for ip in sorted(si.glob("*.jpg")):
        link(ip, di / ip.name)
        keep = [l for l in read_labels(sl / (ip.stem + ".txt")) if l[0] in OLD2NEW]
        cnt.update(OLD2NEW[l[0]] for l in keep)
        (dl / (ip.stem + ".txt")).write_text(
            "".join(f"{OLD2NEW[l[0]]} {l[1]:.6f} {l[2]:.6f} {l[3]:.6f} {l[4]:.6f}\n" for l in keep))
    return cnt


def collect_sources(src_root):
    """Crop every isolated 4-class box of the train split (with context padding) into memory."""
    si, sl = src_root / "train" / "images", src_root / "train" / "labels"
    pool = collections.defaultdict(list)
    for ip in sorted(si.glob("*.jpg")):
        labs = read_labels(sl / (ip.stem + ".txt"))
        if not any(l[0] in OLD2NEW for l in labs):
            continue
        im = cv2.imread(str(ip))
        H, W = im.shape[:2]
        ii = board_mask(im)
        if ii is None:
            continue
        for k, l in enumerate(labs):
            if l[0] not in OLD2NEW:
                continue
            x1, y1, x2, y2 = to_px(l, W, H)
            bw, bh = x2 - x1, y2 - y1
            if bw < MIN_SRC_PX or bh < MIN_SRC_PX:
                continue
            px, py = max(8, round(0.15 * bw)), max(8, round(0.15 * bh))
            cx1, cy1 = max(0, int(x1) - px), max(0, int(y1) - py)
            cx2, cy2 = min(W, int(math.ceil(x2)) + px), min(H, int(math.ceil(y2)) + py)
            if on_board(ii, cx1, cy1, cx2, cy2) < 0.995:
                continue                      # crop would carry board edge / black background
            crop_r = (cx1, cy1, cx2, cy2)
            if any(overlaps(crop_r, to_px(o, W, H)) for j, o in enumerate(labs) if j != k):
                continue                      # crop would carry part of another defect
            pool[OLD2NEW[l[0]]].append(dict(
                crop=im[cy1:cy2, cx1:cx2].copy(),
                box=(x1 - cx1, y1 - cy1, x2 - cx1, y2 - cy1),   # defect box inside the crop
                top=cy1 == 0, bottom=cy2 == H, src=ip.stem))
    return pool


def ramp(n, a, b):
    """1 on [a, b], falling linearly to 0 at both ends of [0, n)."""
    i = np.arange(n, dtype=np.float32) + 0.5
    up = np.clip(i / max(a, 1e-3), 0, 1)
    down = np.clip((n - i) / max(n - b, 1e-3), 0, 1)
    return np.minimum(up, down)


def blend(canvas, crop, x0, y0, mode, box=None):
    """Paste crop into the PAD-padded canvas so its top-left lands on image pixel (x0, y0).
    box = defect box inside the crop; it stays fully opaque, the context margin fades out."""
    h, w = crop.shape[:2]
    X, Y = x0 + PAD, y0 + PAD
    bx1, by1, bx2, by2 = box if box is not None else (0, 0, w, h)
    if mode == "poisson" and w > 8 and h > 8:
        # mask = defect box + 40 % of the context margin, at least 2 px inside the crop
        mx1 = int(max(2, bx1 - 0.4 * bx1)); my1 = int(max(2, by1 - 0.4 * by1))
        mx2 = int(min(w - 2, bx2 + 0.4 * (w - bx2))); my2 = int(min(h - 2, by2 + 0.4 * (h - by2)))
        mask = np.zeros((h, w), np.uint8); mask[my1:my2, mx1:mx2] = 255
        mw, mh = mx2 - mx1, my2 - my1
        centre = (X + mx1 + mw // 2, Y + my1 + mh // 2)   # OpenCV puts the rect at centre - size//2
        canvas[:] = cv2.seamlessClone(crop, canvas, mask, centre, cv2.NORMAL_CLONE)
        return
    roi = canvas[Y:Y + h, X:X + w].astype(np.float32)
    c = crop.astype(np.float32)
    ring = np.ones((h, w), bool); ring[4:-4, 4:-4] = False   # outer context ring
    c += np.clip(np.median(roi[ring], 0) - np.median(c[ring], 0), -40, 40) * 0.8  # match exposure (robust)
    a = np.minimum.outer(ramp(h, by1, by2), ramp(w, bx1, bx2))
    a = (a * a * (3 - 2 * a))[..., None]                       # smoothstep
    canvas[Y:Y + h, X:X + w] = np.clip(a * c + (1 - a) * roi, 0, 255).astype(np.uint8)


def synthesise(src_root, dst_root, name, targets, pool, counts, seed):
    """Add synthetic images to dst_root/<name> until every class reaches its target."""
    rng = random.Random(f"{seed}-{name}")
    si, sl = src_root / "train" / "images", src_root / "train" / "labels"
    di, dl = dst_root / name / "images", dst_root / name / "labels"
    # canvases: train images with no box at all, or one box of a class that is not the largest
    canv = []
    for ip in sorted(si.glob("*.jpg")):
        labs = read_labels(sl / (ip.stem + ".txt"))
        if not labs or (len(labs) == 1 and labs[0][0] in OLD2NEW and OLD2NEW[labs[0][0]] != 0):
            canv.append(ip)
    order = {c: rng.sample(range(len(pool[c])), len(pool[c])) for c in pool}
    ptr = collections.Counter(); uses = collections.Counter()
    deficit = {c: max(0, targets[c] - counts[c]) for c in targets}
    stats = dict(pasted=collections.Counter(), canvas_boxes=collections.Counter(),
                 modes=collections.Counter(), canvases=len(canv))
    queue, fails, n = [], 0, 0
    while sum(deficit.values()) > 0 and fails < 200:
        if not queue:
            queue = rng.sample(canv, len(canv))
        ip = queue.pop()
        im = cv2.imread(str(ip)); H, W = im.shape[:2]
        labs = read_labels(sl / (ip.stem + ".txt"))
        flip = rng.random() < 0.5
        if flip:
            im = im[:, ::-1].copy()
        ii = board_mask(im, erode_px=EDGE)            # pasted crops stay EDGE px inside the board
        if ii is None:
            fails += 1
            continue
        occ, out = [], []
        for l in labs:
            x1, y1, x2, y2 = to_px(l, W, H)
            if flip:
                x1, x2 = W - x2, W - x1
            occ.append((x1, y1, x2, y2))
            if l[0] in OLD2NEW:
                out.append(to_yolo(OLD2NEW[l[0]], x1, y1, x2, y2, W, H))
        canvas = cv2.copyMakeBorder(im, PAD, PAD, PAD, PAD, cv2.BORDER_REFLECT)
        added = collections.Counter()
        for _ in range(rng.randint(2, 5)):
            live = [c for c in deficit if deficit[c] - added[c] > 0]
            if not live:
                break
            c = rng.choices(live, weights=[deficit[k] - added[k] for k in live])[0]
            placed = False
            for _try in range(3):                       # three different sources at most
                s = pool[c][order[c][ptr[c] % len(order[c])]]; ptr[c] += 1
                crop, (bx1, by1, bx2, by2) = s["crop"], s["box"]
                border = s["top"] or s["bottom"]
                sc = 1.0 if border else rng.uniform(0.9, 1.1)
                if sc != 1.0:
                    nh, nw = max(9, round(crop.shape[0] * sc)), max(9, round(crop.shape[1] * sc))
                    fx, fy = nw / crop.shape[1], nh / crop.shape[0]
                    crop = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    bx1, bx2, by1, by2 = bx1 * fx, bx2 * fx, by1 * fy, by2 * fy
                ch, cw = crop.shape[:2]
                if rng.random() < 0.5:
                    crop = crop[:, ::-1].copy(); bx1, bx2 = cw - bx2, cw - bx1
                if cw > W or ch > H:
                    continue
                for _pos in range(80):
                    x0 = rng.randint(0, W - cw)
                    y0 = 0 if s["top"] else (H - ch if s["bottom"] else rng.randint(0, H - ch))
                    r = (x0, y0, x0 + cw, y0 + ch)
                    if on_board(ii, *r) >= 0.999 and not any(overlaps(r, o, GAP) for o in occ):
                        break
                else:
                    continue
                mode = "poisson" if rng.random() < 0.5 else "alpha"
                blend(canvas, crop, x0, y0, mode, (bx1, by1, bx2, by2))
                occ.append(r)
                out.append(to_yolo(c, x0 + bx1, y0 + by1, x0 + bx2, y0 + by2, W, H))
                added[c] += 1; stats["modes"][mode] += 1; uses[(c, s["src"], s["box"])] += 1
                placed = True
                break
            if not placed:
                break
        if not added:
            fails += 1
            continue
        fails = 0
        for l in labs:
            if l[0] in OLD2NEW:
                stats["canvas_boxes"][OLD2NEW[l[0]]] += 1
                deficit[OLD2NEW[l[0]]] -= 1
        for c, k in added.items():
            deficit[c] -= k; stats["pasted"][c] += k
        deficit = {c: max(0, v) for c, v in deficit.items()}
        n += 1
        h6 = hashlib.sha1(f"{seed}-{name}-{n}".encode()).hexdigest()[:6]
        stem = f"{h6}_{ip.stem.split('_', 1)[1]}s{n:04d}"
        cv2.imwrite(str(di / f"{stem}.jpg"), canvas[PAD:PAD + H, PAD:PAD + W], [cv2.IMWRITE_JPEG_QUALITY, 95])
        (dl / f"{stem}.txt").write_text("\n".join(out) + "\n")
    stats["images"] = n
    stats["max_reuse_per_source"] = max(uses.values()) if uses else 0
    return stats


def preview(dst_root, name, k=6, seed=42):
    """Draw boxes on a few synthetic images for a visual check."""
    di, dl = dst_root / name / "images", dst_root / name / "labels"
    syn = sorted(p for p in di.glob("*.jpg") if "s" in p.stem.split("_", 1)[1])
    out = dst_root / "previews"; out.mkdir(exist_ok=True)
    col = [(60, 200, 60), (0, 165, 255), (255, 80, 200), (40, 40, 255)]
    for p in random.Random(seed).sample(syn, min(k, len(syn))):
        im = cv2.imread(str(p)); H, W = im.shape[:2]
        for l in read_labels(dl / (p.stem + ".txt")):
            x1, y1, x2, y2 = map(int, to_px(l, W, H))
            cv2.rectangle(im, (x1, y1), (x2, y2), col[l[0]], 4)
            cv2.putText(im, KEEP[l[0]], (x1, max(30, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 1.1, col[l[0]], 3)
        cv2.imwrite(str(out / f"{name}_{p.stem}.jpg"), cv2.resize(im, (W // 2, H // 2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="dataset_clean")
    ap.add_argument("--out", default="dataset_4cls")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--variants", nargs="+", default=["full", "sqrt"], choices=["full", "sqrt"])
    a = ap.parse_args()
    src, dst = Path(a.src), Path(a.out)
    if dst.exists():
        shutil.rmtree(dst)
    report = {}
    for sp in ["val", "test"]:
        report[sp] = write_split(src, dst, sp)
    plain = write_split(src, dst, "train")
    (dst / "train").rename(dst / "train_plain")
    report["train_plain"] = plain
    pool = collect_sources(src)
    print("isolated crop sources per class:", {KEEP[c]: len(v) for c, v in sorted(pool.items())})
    n_max = max(plain.values())
    for v in a.variants:
        tgt = {c: n_max if v == "full" else round(math.sqrt(plain[c] * n_max)) for c in range(len(KEEP))}
        d = dst / f"train_{v}"
        (d / "images").mkdir(parents=True); (d / "labels").mkdir(parents=True)
        for f in (dst / "train_plain" / "images").iterdir():
            link(f, d / "images" / f.name)
        for f in (dst / "train_plain" / "labels").iterdir():
            shutil.copy2(f, d / "labels" / f.name)
        st = synthesise(src, dst, f"train_{v}", tgt, pool, collections.Counter(plain), a.seed)
        final = collections.Counter()
        for f in (d / "labels").glob("*.txt"):
            final.update(int(l.split()[0]) for l in f.read_text().splitlines() if l.strip())
        report[f"train_{v}"] = final
        report[f"synth_{v}"] = dict(target={KEEP[c]: t for c, t in tgt.items()},
                                    synthetic_images=st["images"], canvases_available=st["canvases"],
                                    pasted={KEEP[c]: k for c, k in sorted(st["pasted"].items())},
                                    canvas_boxes={KEEP[c]: k for c, k in sorted(st["canvas_boxes"].items())},
                                    blend_modes=dict(st["modes"]),
                                    max_reuse_per_source=st["max_reuse_per_source"])
        preview(dst, f"train_{v}")
    for v in ["plain"] + a.variants:
        (dst / f"data_{v}.yaml").write_text(
            f"path: {dst.resolve().as_posix()}\ntrain: train_{v}/images\nval: val/images\ntest: test/images\n\n"
            f"nc: {len(KEEP)}\nnames:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(KEEP)))
    rep = {k: ({KEEP[c]: n for c, n in sorted(v.items())} if isinstance(v, collections.Counter) else v)
           for k, v in report.items()}
    (dst / "balance_report.json").write_text(json.dumps(rep, indent=2))
    print(f"\n{'split':12s}" + "".join(f"{n:>11s}" for n in KEEP) + "   images   max:min")
    for k in ["train_plain"] + [f"train_{v}" for v in a.variants] + ["val", "test"]:
        c = report[k]; ni = len(list((dst / k / "images").glob("*.jpg")))
        vals = [c[i] for i in range(len(KEEP))]
        print(f"{k:12s}" + "".join(f"{x:11d}" for x in vals) + f"{ni:9d}   {max(vals) / max(1, min(vals)):5.2f}")
    for v in a.variants:
        print(f"\n{v}:", json.dumps(rep[f'synth_{v}']))


if __name__ == "__main__":
    main()
