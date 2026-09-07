"""
prepare_dataset.py — build a clean, board-level-split YOLO dataset.

Input : any folder tree containing YOLO images + labels (same stem).
        e.g. data/train/images, data/train/labels, data/valid/..., data/test/...
Output: <out>/{train,val,test}/{images,labels} + <out>/data.yaml

What it does
  1. Pairs every image with its label file (missing label = background image).
  2. Drops degenerate boxes (zero/near-zero w or h), clips coords to [0,1].
  3. Groups images by physical board (first 4 digits of the filename stem).
  4. Greedy group-stratified split — every board lands in exactly one split,
     minority classes balanced across splits. Prints a verification table.
  5. Renames files with a seeded hash prefix so Ultralytics' rect mode
     (which sorts files and disables shuffle) still sees mixed boards per batch.

Usage
  python prepare_dataset.py --src data --out dataset_clean \
      --names Crack Knot Hole Stain Split Warp Decay Scratch \
      --ratios 0.70 0.18 0.12 --seed 42
"""
import argparse, hashlib, json, random, re, shutil
from collections import Counter, defaultdict
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
MIN_WH = 0.0005          # boxes thinner than this (normalised) are dropped


def board_id(stem: str) -> str:
    m = re.match(r"^(\d{4})", stem)
    if not m:
        raise ValueError(f"cannot derive board id from '{stem}' — adjust board_id()")
    return m.group(1)


def read_label(p: Path):
    good, dropped = [], 0
    if not p.exists():
        return good, dropped
    for line in p.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        c = int(float(parts[0]))
        x, y, w, h = (float(v) for v in parts[1:5])
        # clip to image
        x1, y1 = max(0.0, x - w / 2), max(0.0, y - h / 2)
        x2, y2 = min(1.0, x + w / 2), min(1.0, y + h / 2)
        w, h = x2 - x1, y2 - y1
        if w <= MIN_WH or h <= MIN_WH:
            dropped += 1
            continue
        good.append((c, (x1 + x2) / 2, (y1 + y2) / 2, w, h))
    return good, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--names", nargs="+", required=True, help="class names in id order")
    ap.add_argument("--ratios", nargs=3, type=float, default=[0.70, 0.18, 0.12])
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    src, out = Path(a.src), Path(a.out)
    nc = len(a.names)
    rng = random.Random(a.seed)

    # ---- 1. collect pairs -------------------------------------------------
    images = [p for p in src.rglob("*") if p.suffix.lower() in IMG_EXT]
    if not images:
        raise SystemExit(f"no images found under {src}")
    records, total_dropped, total_boxes = [], 0, 0
    for img in images:
        lbl = img.parent.parent / "labels" / (img.stem + ".txt")
        if not lbl.exists():                       # flat layout fallback
            lbl = img.with_suffix(".txt")
        boxes, dropped = read_label(lbl)
        total_dropped += dropped
        total_boxes += len(boxes)
        records.append(dict(img=img, boxes=boxes, board=board_id(img.stem)))
    print(f"images: {len(records)}  boxes kept: {total_boxes}  degenerate dropped: {total_dropped}")

    # ---- 2. per-board class counts ----------------------------------------
    boards = defaultdict(list)
    for r in records:
        boards[r["board"]].append(r)
    board_cls = {b: Counter(c for r in rs for c, *_ in r["boxes"]) for b, rs in boards.items()}
    global_cls = Counter()
    for c in board_cls.values():
        global_cls.update(c)
    print(f"boards: {len(boards)}")

    # ---- 3. greedy group-stratified assignment ----------------------------
    splits = ["train", "val", "test"]
    target = {s: {c: global_cls[c] * r for c in range(nc)} for s, r in zip(splits, a.ratios)}
    have = {s: Counter() for s in splits}
    n_img = {s: 0 for s in splits}
    assign = {}

    # rarest classes first so they get spread before the big boards consume quota
    rarity = {c: 1.0 / max(global_cls[c], 1) for c in range(nc)}
    order = sorted(boards, key=lambda b: -sum(board_cls[b][c] * rarity[c] for c in range(nc)))
    # break ties randomly but deterministically
    order = sorted(order, key=lambda b: (round(-sum(board_cls[b][c] * rarity[c] for c in range(nc)), 6), rng.random()))

    for b in order:
        best, best_score = None, None
        for s in splits:
            # relative fill after adding this board, weighted by class rarity
            score = 0.0
            for c in range(nc):
                if target[s][c] <= 0:
                    continue
                score += rarity[c] * (have[s][c] + board_cls[b][c]) / target[s][c]
            # also keep image counts near ratio
            score += (n_img[s] + len(boards[b])) / (len(records) * a.ratios[splits.index(s)])
            if best_score is None or score < best_score:
                best, best_score = s, score
        assign[b] = best
        have[best].update(board_cls[b])
        n_img[best] += len(boards[b])

    # ---- 4. write out -----------------------------------------------------
    if out.exists():
        shutil.rmtree(out)
    for s in splits:
        (out / s / "images").mkdir(parents=True)
        (out / s / "labels").mkdir(parents=True)
    for r in records:
        s = assign[r["board"]]
        h = hashlib.sha1(f"{a.seed}:{r['img'].stem}".encode()).hexdigest()[:6]
        new_stem = f"{h}_{r['img'].stem}"
        shutil.copy2(r["img"], out / s / "images" / (new_stem + r["img"].suffix.lower()))
        with open(out / s / "labels" / (new_stem + ".txt"), "w") as f:
            for c, x, y, w, h_ in r["boxes"]:
                f.write(f"{c} {x:.6f} {y:.6f} {w:.6f} {h_:.6f}\n")

    yaml = [f"path: {out.resolve()}", "train: train/images", "val: val/images", "test: test/images", "", f"nc: {nc}", "names:"]
    yaml += [f"  {i}: {n}" for i, n in enumerate(a.names)]
    (out / "data.yaml").write_text("\n".join(yaml) + "\n")

    # ---- 5. verify + report -----------------------------------------------
    bset = {s: {b for b, ss in assign.items() if ss == s} for s in splits}
    assert not (bset["train"] & bset["val"]) and not (bset["train"] & bset["test"]) and not (bset["val"] & bset["test"]), "board overlap!"
    print("\nboard overlap across splits: NONE (asserted)")
    print(f"{'split':6} {'boards':>7} {'images':>7} " + " ".join(f"{n[:7]:>8}" for n in a.names))
    for s in splits:
        print(f"{s:6} {len(bset[s]):>7} {n_img[s]:>7} " + " ".join(f"{have[s][c]:>8}" for c in range(nc)))
    json.dump({s: sorted(bset[s]) for s in splits}, open(out / "board_split.json", "w"), indent=1)
    print(f"\nwrote {out/'data.yaml'} and board_split.json")


if __name__ == "__main__":
    main()
