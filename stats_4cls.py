"""
stats_4cls.py - paired significance tests for the 4-class models on val and test (no model is chosen here).

Compares, on the same images and from the validator's own predictions (eval_capture.py):
  sqrt-balanced vs plain 4-class, sqrt-balanced vs the 8-class baseline scored on the 4 kept classes,
  plain 4-class vs that baseline.
Board-level bootstrap interval of the mAP50 difference + exact Wilcoxon signed-rank test on per-board AP50.
Writes eval/stats_4cls.json and .md.
"""
import json
from pathlib import Path
from eval_capture import capture, score
from math_model import paired_tests, rematch

KEEP = ["Live_Knot", "Dead_Knot", "Resin", "Crack"]


def to4(cap):
    """Map an 8-class capture onto the 4 kept classes (other predictions and ground truth dropped)."""
    m = {i: KEEP.index(n) for i, n in enumerate(cap["names"]) if n in KEEP}
    out = {}
    for s, im in cap["images"].items():
        keep_p = [k for k, c in enumerate(im["pred_cls"]) if c in m]
        keep_g = [k for k, c in enumerate(im["gt_cls"]) if c in m]
        out[s] = dict(stem=s, pred_boxes=[im["pred_boxes"][k] for k in keep_p], pred_conf=[im["pred_conf"][k] for k in keep_p],
                      pred_cls=[m[im["pred_cls"][k]] for k in keep_p], gt_boxes=[im["gt_boxes"][k] for k in keep_g],
                      gt_cls=[m[im["gt_cls"][k]] for k in keep_g])
    return out


def main(B=1000):
    res = {}
    for sp in ["val", "test"]:
        base = rematch(to4(capture("weights/yolo11s_baseline.pt", "dataset_clean/data.yaml", sp, 1024)))
        plain = rematch(capture("weights/yolo11s_4cls_plain.pt", "dataset_4cls/data_plain.yaml", sp, 1024)["images"])
        sqrt = rematch(capture("weights/yolo11s_4cls_balanced.pt", "dataset_4cls/data_sqrt.yaml", sp, 1024)["images"])
        pt = {k: score(v) for k, v in dict(base=base, plain=plain, sqrt=sqrt).items()}
        res[sp] = dict(map50={k: round(100 * v["map50"], 1) for k, v in pt.items()},
                       map={k: round(100 * v["map"], 1) for k, v in pt.items()},
                       tests={"sqrt - plain": paired_tests(sqrt, plain, B), "sqrt - base": paired_tests(sqrt, base, B),
                              "plain - base": paired_tests(plain, base, B)})
        print(sp, json.dumps(res[sp], indent=1), flush=True)
    Path("eval").mkdir(exist_ok=True)
    Path("eval/stats_4cls.json").write_text(json.dumps(res, indent=2))
    lines = ["| split | comparison | mAP50 diff (point) | 95% CI | boards better / worse | Wilcoxon p |", "|---|---|---:|---|---|---:|"]
    for sp, r in res.items():
        for k, t in r["tests"].items():
            a, b = k.split(" - ")
            lines.append(f"| {sp} | {k} | {r['map50'][a] - r['map50'][b]:+.1f} | [{t['map50_diff_ci'][0]:+.1f}, {t['map50_diff_ci'][1]:+.1f}] | "
                         f"{t['boards_better']} / {t['boards_worse']} | {t['wilcoxon_p']:.3f} |")
    Path("eval/stats_4cls.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
