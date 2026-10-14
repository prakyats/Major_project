"""
make_final_diagrams.py - methodology, system-design and plan-of-action figures for the final (100 %) review,
drawn in the style of the 50 % review figures (serif text, rounded boxes, status colours).

python docs/make_final_diagrams.py --final "YOLO11s, 4 classes, 1280 px" --out docs/final_figs
"""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["mathtext.fontset"] = "stix"
GREEN, BLUE, EDGE, PINK, HEAD = "#9bd59b", "#bcd8f5", "#333333", "#f3cccc", "#d4e8d4"


def box(ax, x, y, w, h, text, fc, lw=2.0, bold=False, fs=13.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012",
                                fc=fc, ec=EDGE, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", lw=2, color=EDGE, mutation_scale=16))


def line(ax, xs, ys):
    ax.plot(xs, ys, color=EDGE, lw=2)


def methodology(out, final):
    fig = plt.figure(figsize=(12.05, 11.6), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    cw, cx = 0.56, 0.22
    box(ax, cx, 0.895, cw, 0.08, "Stage 1: Dataset preparation\n4,000 line-scan board images, 8 defect classes,\n"
        "label cleaning, board-level train / val / test split (52 / 17 / 12 boards)", GREEN)
    arrow(ax, 0.5, 0.895, 0.5, 0.865)
    box(ax, cx, 0.785, cw, 0.08, "Stage 2: Input handling & class balancing\nrectangular high-resolution input, grain-safe "
        "augmentation,\ncopy-paste balancing of rare defect classes", GREEN)
    arrow(ax, 0.5, 0.785, 0.5, 0.755)
    box(ax, cx, 0.675, cw, 0.08, f"Stage 3: Defect detection\nYOLO11m and YOLO11s, identical recipe on Kaggle T4;\n"
        f"final detector: {final}", GREEN)
    arrow(ax, 0.5, 0.675, 0.5, 0.645)
    box(ax, 0.17, 0.53, 0.66, 0.115, "Stage 4: MATHEMATICAL MODEL\nClass-balancing rule  $n_c \\rightarrow \\sqrt{n_c\\, n_{max}}$;  "
        "weighted box fusion of detectors;\nWise-IoU v3 box loss;  per-class threshold test;\n"
        "statistical validation (board bootstrap, Wilcoxon signed-rank)", BLUE, lw=3.2, bold=True, fs=13.5)
    line(ax, [0.5, 0.5], [0.53, 0.5]); line(ax, [0.27, 0.73], [0.5, 0.5])
    arrow(ax, 0.27, 0.5, 0.27, 0.47); arrow(ax, 0.73, 0.5, 0.73, 0.47)
    box(ax, 0.06, 0.39, 0.42, 0.08, "Stage 5: Defect analysis\nclass, position, size, confidence,\n"
        "per-class counts and area", GREEN)
    box(ax, 0.52, 0.39, 0.42, 0.08, "Stage 6: Recoverability estimation\nBoard Recoverability Index: severity × confidence\n"
        "× position → damage score, grade A / B / C / Reject", GREEN)
    arrow(ax, 0.27, 0.39, 0.27, 0.355); arrow(ax, 0.73, 0.39, 0.73, 0.355)
    box(ax, 0.06, 0.275, 0.42, 0.08, "Stage 7: Evaluation & comparison\nP, R, F1, mAP50, mAP50-95, ms/img; single-shot\n"
        "test on 12 unseen boards; enhancement study", GREEN)
    box(ax, 0.52, 0.275, 0.42, 0.08, "Stage 8: Market price analytics\nquality grade to value: volume × recoverable\n"
        "share × price × grade factor", GREEN)
    line(ax, [0.27, 0.27], [0.275, 0.245]); line(ax, [0.73, 0.73], [0.275, 0.245]); line(ax, [0.27, 0.73], [0.245, 0.245])
    arrow(ax, 0.5, 0.245, 0.5, 0.215)
    box(ax, cx, 0.135, cw, 0.08, "Output: demonstration application and final assessment\nboxes, heatmap, per-class "
        "statistics, grade, recoverable area,\nestimated value and JSON report per board", "#f6c97b")
    for x, fc, t in [(0.06, GREEN, "Completed"), (0.36, BLUE, "Mathematical model (completed)"), (0.70, "#f6c97b", "Final output")]:
        ax.add_patch(FancyBboxPatch((x, 0.075), 0.035, 0.022, boxstyle="square,pad=0", fc=fc, ec=EDGE, lw=1.5))
        ax.text(x + 0.045, 0.086, t, va="center", fontsize=13)
    fig.savefig(out / "methodology_final.png", dpi=100, bbox_inches="tight", pad_inches=0.15); plt.close(fig)


def system_design(out, final, metrics):
    fig = plt.figure(figsize=(11.7, 10.3), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    lx, rx, w, h = 0.04, 0.52, 0.44, 0.072
    box(ax, lx, 0.895, w, 0.065, "DEFECT ANALYSIS & APPLICATION", HEAD, bold=True, fs=14)
    box(ax, rx, 0.895, w, 0.065, "DATA & DETECTION PIPELINE", HEAD, bold=True, fs=14)
    left = ["Web application (Gradio, CPU)\nupload, model choice, thresholds, live grading",
            "Defect analysis\nper-class counts, area share, defect coverage",
            "Recoverability (BRI)\ndamage score, recoverable area, grade A / B / C / Reject",
            "Market value estimate\nvolume × recoverable share × price × grade factor",
            "Reports\nJSON per image: defects, grade, value"]
    right = ["Board images (2800 × 1024)\nKodytek et al. dataset, 8 classes",
             "Preparation + balancing scripts\nboard split, label cleaning, copy-paste balancing",
             f"Training script (Kaggle T4)\nYOLO11m / YOLO11s, Wise-IoU option; final: {final}",
             "Evaluation + statistics\nsingle-shot test, bootstrap CI, Wilcoxon, kappa",
             "Detection output (+ box fusion)\nclass, box, confidence per defect"]
    ys = [0.78 - i * 0.115 for i in range(5)]
    for i, (a, b) in enumerate(zip(left, right)):
        box(ax, lx, ys[i], w, h, a, GREEN, fs=13); box(ax, rx, ys[i], w, h, b, GREEN, fs=13)
        if i < 4:
            arrow(ax, lx + w / 2, ys[i], lx + w / 2, ys[i + 1] + h); arrow(ax, rx + w / 2, ys[i], rx + w / 2, ys[i + 1] + h)
    ax.plot([0.5, 0.5], [ys[4] + h / 2, ys[1] + h / 2], color=EDGE, lw=1.5, ls="--")
    arrow(ax, 0.5, ys[4] + h / 2, lx + w + 0.005, ys[4] + h / 2); arrow(ax, 0.5, ys[1] + h / 2, lx + w + 0.005, ys[1] + h / 2)
    line(ax, [lx + w / 2, lx + w / 2], [ys[4], 0.24]); line(ax, [rx + w / 2, rx + w / 2], [ys[4], 0.24])
    line(ax, [lx + w / 2, rx + w / 2], [0.24, 0.24]); arrow(ax, 0.5, 0.24, 0.5, 0.21)
    box(ax, 0.13, 0.085, 0.74, 0.125, f"Wood quality assessment\nper board: detected defects, grade, recoverable area and value\n"
        f"held-out test: {metrics}", PINK, fs=13.5)
    ax.add_patch(FancyBboxPatch((0.33, 0.035), 0.03, 0.022, boxstyle="square,pad=0", fc=GREEN, ec=EDGE, lw=1.5))
    ax.text(0.37, 0.046, "Completed (all components)", va="center", fontsize=13)
    fig.savefig(out / "system_design_final.png", dpi=100, bbox_inches="tight", pad_inches=0.15); plt.close(fig)


def gantt(out, review_label):
    weeks = [f"W{i}" for i in range(1, 5)] * 4
    months = ["August", "September", "October", "November"]
    tasks = [("Planning & synopsis", 0, 3.5, "#4a6a8a"), ("Dataset & preprocessing", 3, 6, "#3e9a84"),
             ("Defect detection (YOLO11m, YOLO11s)", 5, 8.5, "#c8642a"), ("Demo application", 6, 8, "#7a5230"),
             ("Mathematical model & accuracy experiments", 8.0, 10.3, "#6b5b95"),
             ("Recoverability (BRI) & market value", 8.6, 10.3, "#5b7f95"), ("Evaluation & finalisation", 9.6, 11.1, "#a05060")]
    fig, ax = plt.subplots(figsize=(14.4, 6.4), dpi=100)
    ax.set_xlim(-0.2, 16); ax.set_ylim(len(tasks) + 1.4, -1.0); ax.axis("off")
    x0 = 0
    for m, name in enumerate(months):
        ax.add_patch(plt.Rectangle((m * 4, -0.95), 4, 0.95, fill=False, lw=1.5))
        ax.text(m * 4 + 2, -0.55, name, ha="center", va="center", fontsize=17, fontweight="bold")
        for k in range(4):
            ax.text(m * 4 + k + 0.5, -0.12, weeks[k], ha="center", va="center", fontsize=11)
            ax.plot([m * 4 + k, m * 4 + k], [-0.3, 0], color="k", lw=0.8)
    ax.plot([0, 16], [0, 0], color="k", lw=1.5)
    for i, (name, s, e, c) in enumerate(tasks):
        y = i + 0.7
        ax.add_patch(plt.Rectangle((s, y - 0.33), e - s, 0.66, fc=c, ec="k", lw=1.2))
        ax.text(-0.3, y, name, ha="right", va="center", fontsize=15)
        ax.text((s + e) / 2, y, "done", ha="center", va="center", fontsize=13, color="white", fontweight="bold")
    rv = 11.3
    ax.plot([rv, rv], [-0.1, len(tasks) + 0.4], color="#d32f2f", lw=2.5, ls="--")
    ax.text(rv, len(tasks) + 0.95, review_label, ha="center", va="center", fontsize=14, color="#d32f2f", fontweight="bold")
    fig.savefig(out / "plan_of_action_final.png", dpi=100, bbox_inches="tight", pad_inches=0.1); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", default="YOLO11s, 4 classes")
    ap.add_argument("--metrics", default="see results slides")
    ap.add_argument("--review", default="Final review")
    ap.add_argument("--out", default="docs/final_figs")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    methodology(out, a.final); system_design(out, a.final, a.metrics); gantt(out, a.review)
    print("written:", sorted(p.name for p in out.glob("*.png")))
