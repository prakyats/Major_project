"""
eval_full.py - full-dataset extension (NOTES.md section 23): fuse the two full-data YOLO11s 4-class models, choose the
fusion settings on the full validation split, apply the pre-registered rule on the ORIGINAL 714 validation images
(replace the deployed fusion only if > 78.1 mAP50), then score test once: original 469 images (paired against the
deployed fusion, same images and labels) and the full test split.
Inputs: captured predictions downloaded from Kaggle (weights_local/full_v2/<sz>/capture/<tag>/) and eval/capture/.
"""
import json
from pathlib import Path
import numpy as np
from eval_capture import score
from math_model import fuse, rematch, paired_tests

NEW = {1024: "weights_local/full_v2/1024/capture/{t}/best_1024_{sp}.json",
       1280: "weights_local/full_v2/1280/capture/{t}/best_1280_{sp}.json"}
DEPLOYED = (["yolo11s_4cls_balanced_1024", "yolo11s_4cls_plain_1024", "yolo11s_4cls_sqrt_1280_1280",
             "yolo11s_4cls_plain_1280_1280"], [2, 1, 1, 1], 0.55)


def rekey(cap):
    """Key images by '<prefix>_<9-digit stem>' with a common prefix so both datasets line up (board id stays after '_')."""
    cap = dict(cap)
    cap["images"] = {"x_" + s.split("_", 1)[1]: dict(im, stem="x_" + s.split("_", 1)[1]) for s, im in cap["images"].items()}
    return cap


def new(tag):
    sp = tag.split("_")[0]
    return [rekey(json.load(open(NEW[sz].format(t=tag, sp=sp)))) for sz in (1024, 1280)]


def r1(x):
    return round(100 * x, 1)


def main():
    out = {}
    # 1. fusion settings chosen on the full validation split (3,746 images, 76 boards)
    vf = new("val_full")
    grid = []
    for t_iou in [0.45, 0.55, 0.65]:
        for w in ([1, 1], [2, 1], [1, 2]):
            r = score(fuse(vf, w, t_iou))
            grid.append(dict(t_iou=t_iou, weights=w, val_full_map50=r["map50"], val_full_map=r["map"]))
            print("val_full", t_iou, w, r1(r["map50"]), r1(r["map"]))
    best = max(grid, key=lambda g: (round(g["val_full_map50"], 4), g["val_full_map"]))
    out["fusion_grid_val_full"], out["chosen"] = grid, best
    F = lambda caps: fuse(caps, best["weights"], best["t_iou"])
    # 2. decision rule on the original 714 validation images
    vo = new("val_orig")
    dep_caps = {sp: [rekey(json.load(open(f"eval/capture/{m}_{sp}.json"))) for m in DEPLOYED[0]] for sp in ("val", "test")}
    dep = {sp: fuse(c, DEPLOYED[1], DEPLOYED[2]) for sp, c in dep_caps.items()}
    rows = {}
    for name, imgs in (("deployed_fusion", dep["val"]), ("full_1024", rematch(vo[0]["images"])),
                       ("full_1280", rematch(vo[1]["images"])), ("full_fusion", F(vo))):
        r = score(imgs); rows[name] = (r1(r["map50"]), r1(r["map"]))
    out["val_orig"] = rows
    print("val_orig (714 images):", rows)
    candidates = {k: v for k, v in rows.items() if k != "deployed_fusion"}
    new_best = max(candidates, key=lambda k: candidates[k])
    replace = rows[new_best][0] > 78.1
    out["decision"] = dict(best_new_on_val_orig=new_best, val_orig_map50=rows[new_best][0], threshold=78.1, replace=replace)
    print("decision:", out["decision"])
    # 3. test, scored once with everything fixed above
    to, tf = new("test_orig"), new("test_full")
    sys_test = {"full_1024": (rematch(to[0]["images"]), rematch(tf[0]["images"])),
                "full_1280": (rematch(to[1]["images"]), rematch(tf[1]["images"])),
                "full_fusion": (F(to), F(tf))}
    gt_dep = sum(len(im["gt_cls"]) for im in dep["test"].values())
    gt_new = sum(len(im["gt_cls"]) for im in sys_test["full_fusion"][0].values())
    assert set(dep["test"]) == set(sys_test["full_fusion"][0]) and gt_dep == gt_new, (gt_dep, gt_new)
    test = {"deployed_fusion": dict(orig=score(dep["test"]))}
    for k, (o, f) in sys_test.items():
        test[k] = dict(orig=score(o), full=score(f))
    names = to[0]["names"]
    out["test"] = {k: {s: dict(map50=r1(r["map50"]), map=r1(r["map"]), ap50={names[c]: r1(v) for c, v in r["ap50"].items()})
                       for s, r in v.items()} for k, v in test.items()}
    for k, v in out["test"].items():
        print("test", k, {s: (x["map50"], x["map"], x["ap50"]) for s, x in v.items()})
    # 4. paired board-level statistics on the original 469 test images: new system minus deployed fusion
    out["stats_new_minus_deployed_test_orig"] = paired_tests(sys_test[new_best][0], dep["test"], B=1000)
    print("paired", new_best, "- deployed:", out["stats_new_minus_deployed_test_orig"])
    Path("eval/math_model").mkdir(parents=True, exist_ok=True)
    Path("eval/math_model/full_dataset.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
