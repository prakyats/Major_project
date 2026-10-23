"""
make_report_figs.py - figures for the Phase-I report: DFD level 0, DFD level 1, activity diagram, and a per-class
comparison chart (50 % review vs final detector, test mAP50 from docs/final_results.json). Output: docs/report_figs/
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "report_figs"; OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams["font.family"] = "Times New Roman"
GREEN, BLUE, GREY, ORANGE = "#9AD39A", "#BBD7F2", "#E6E6E6", "#F7C873"


def box(ax, x, y, w, h, text, fc, fs=11, round_=True, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.015" if round_ else "square,pad=0.004",
                                fc=fc, ec="#333", lw=1.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")


def store(ax, x, y, w, h, text, fs=10.5):
    ax.plot([x, x + w], [y + h, y + h], color="#333", lw=1.5); ax.plot([x, x + w], [y, y], color="#333", lw=1.5)
    ax.plot([x, x], [y, y + h], color="#333", lw=1.5)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x1, y1, x2, y2, label=None, off=(0, 0.012), fs=9.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.3))
    if label:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], label, ha="center", va="bottom", fontsize=fs, style="italic")


def canvas(w, h):
    fig = plt.figure(figsize=(w, h), dpi=150); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def dfd0():
    fig, ax = canvas(10, 5.2)
    box(ax, 0.02, 0.42, 0.18, 0.16, "User /\nQuality inspector", GREY, round_=False)
    box(ax, 0.80, 0.42, 0.18, 0.16, "Dataset\n(board images\n+ annotations)", GREY, round_=False)
    ax.add_patch(Ellipse((0.5, 0.5), 0.34, 0.46, fc=BLUE, ec="#333", lw=1.8))
    ax.text(0.5, 0.5, "0\nAI-Based Wood\nQuality Assessment\nSystem", ha="center", va="center", fontsize=13, fontweight="bold")
    arrow(ax, 0.20, 0.55, 0.335, 0.55, "board image, settings")
    arrow(ax, 0.335, 0.45, 0.20, 0.45, "defects, grade, recoverable\narea, value, report", off=(0, -0.085))
    arrow(ax, 0.80, 0.50, 0.665, 0.50, "training / test images")
    fig.savefig(OUT / "dfd_level0.png", bbox_inches="tight", pad_inches=0.1); plt.close(fig)


def dfd1():
    fig, ax = canvas(12, 7.2)
    box(ax, 0.01, 0.80, 0.14, 0.11, "Dataset", GREY, round_=False)
    box(ax, 0.01, 0.10, 0.14, 0.11, "User", GREY, round_=False)
    P = {1: (0.22, 0.78, "1.0 Prepare data\nclean labels, split by board,\nbalance classes"),
         2: (0.47, 0.78, "2.0 Train detectors\nYOLO11s at 1024 / 1280 px"),
         3: (0.72, 0.78, "3.0 Evaluate and select\nvalidation rule, single test,\nbootstrap / Wilcoxon"),
         4: (0.22, 0.12, "4.0 Detect defects\nfusion of two models (WBF)"),
         5: (0.47, 0.12, "5.0 Grade board\nBoard Recoverability Index"),
         6: (0.72, 0.12, "6.0 Estimate value\nand build report")}
    for k, (x, y, t) in P.items():
        ax.add_patch(Ellipse((x + 0.09, y + 0.06), 0.2, 0.15, fc=BLUE, ec="#333", lw=1.5))
        ax.text(x + 0.09, y + 0.06, t, ha="center", va="center", fontsize=9.5)
    store(ax, 0.235, 0.47, 0.17, 0.07, "D1  Prepared dataset")
    store(ax, 0.485, 0.47, 0.17, 0.07, "D2  Model weights")
    store(ax, 0.735, 0.47, 0.17, 0.07, "D3  Results, thresholds")
    arrow(ax, 0.15, 0.855, 0.21, 0.855, "images, labels", fs=8.5)
    arrow(ax, 0.31, 0.765, 0.31, 0.545, "split + balanced sets", off=(0.07, -0.02), fs=8.5)
    arrow(ax, 0.405, 0.51, 0.50, 0.77, "", fs=8.5)
    arrow(ax, 0.56, 0.765, 0.56, 0.545, "best.pt", off=(0.03, -0.02), fs=8.5)
    arrow(ax, 0.655, 0.51, 0.75, 0.77, "", fs=8.5)
    arrow(ax, 0.81, 0.765, 0.81, 0.545, "fusion settings,\ngrade thresholds", off=(0.065, -0.03), fs=8.5)
    arrow(ax, 0.15, 0.155, 0.21, 0.155, "board image", fs=8.5)
    arrow(ax, 0.50, 0.465, 0.36, 0.215, "weights", off=(-0.03, 0), fs=8.5)
    arrow(ax, 0.40, 0.18, 0.46, 0.18, "boxes", fs=8.5)
    arrow(ax, 0.65, 0.18, 0.71, 0.18, "grade, DIS", fs=8.5)
    arrow(ax, 0.78, 0.465, 0.62, 0.225, "thresholds", off=(0.04, 0), fs=8.5)
    ax.annotate("", xy=(0.09, 0.10), xytext=(0.81, 0.055), arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.3, connectionstyle="arc3,rad=-0.18"))
    ax.text(0.46, 0.005, "annotated image, heatmap, grade, recoverable area, value, JSON report", ha="center", fontsize=8.5, style="italic")
    fig.savefig(OUT / "dfd_level1.png", bbox_inches="tight", pad_inches=0.1); plt.close(fig)


def activity():
    fig, ax = canvas(7.5, 11)
    ax.add_patch(plt.Circle((0.5, 0.965), 0.015, color="#222"))
    steps = [("Upload board image", 0.89), ("Read image; choose model and thresholds", 0.815),
             ("Run YOLO11s at 1024 px and at 1280 px", 0.74), ("Fuse boxes with weighted box fusion", 0.665)]
    for t, y in steps:
        box(ax, 0.2, y - 0.025, 0.6, 0.05, t, GREEN, fs=10.5)
    ys = [0.95] + [y for _, y in steps]
    for a, b in zip(ys[:-1], ys[1:]):
        arrow(ax, 0.5, a - (0.0 if a == 0.95 else 0.025), 0.5, b + 0.025)
    ax.add_patch(plt.Polygon([[0.5, 0.615], [0.62, 0.575], [0.5, 0.535], [0.38, 0.575]], fc=ORANGE, ec="#333", lw=1.5))
    ax.text(0.5, 0.575, "defects\nfound?", ha="center", va="center", fontsize=10)
    arrow(ax, 0.5, 0.64, 0.5, 0.615)
    box(ax, 0.66, 0.555, 0.3, 0.04, "Damage score 0, Grade A", GREEN, fs=10)
    arrow(ax, 0.62, 0.575, 0.66, 0.575, "no", off=(0, 0.004))
    steps2 = [("Board mask; per-defect influence\nseverity x confidence x position", 0.49), ("Damage score (DIS), recoverable area", 0.41),
              ("Compare DIS with A / B / C / Reject cut-offs", 0.335), ("Estimate value from grade", 0.26),
              ("Show boxes, heatmap, grade, tables;\noffer JSON report", 0.18)]
    arrow(ax, 0.5, 0.535, 0.5, 0.49 + 0.03, "yes", off=(0.03, -0.01))
    for t, y in steps2:
        box(ax, 0.2, y - 0.03, 0.6, 0.06, t, GREEN, fs=10.5)
    for a, b in zip([s[1] for s in steps2][:-1], [s[1] for s in steps2][1:]):
        arrow(ax, 0.5, a - 0.03, 0.5, b + 0.03)
    ax.annotate("", xy=(0.80, 0.18), xytext=(0.81, 0.555), arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.3, connectionstyle="arc3,rad=-0.25"))
    ax.add_patch(plt.Circle((0.5, 0.09), 0.018, fc="white", ec="#222", lw=2)); ax.add_patch(plt.Circle((0.5, 0.09), 0.01, color="#222"))
    arrow(ax, 0.5, 0.15, 0.5, 0.108)
    fig.savefig(OUT / "activity_diagram.png", bbox_inches="tight", pad_inches=0.1); plt.close(fig)


def per_class_chart():
    R = json.loads((ROOT / "docs" / "final_results.json").read_text(encoding="utf-8"))
    fin = R["full"]["test"]["full_fusion"]["orig"]["ap50"]
    mid = R["test8"]["YOLO11s"]
    cls = ["Live_Knot", "Dead_Knot", "Resin", "Crack"]
    a = [mid[c][3] for c in cls]; b = [fin[c] for c in cls]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    x = range(len(cls))
    ax.bar([i - 0.2 for i in x], a, 0.38, label="50% review (YOLO11s)", color="#9DB4C0")
    ax.bar([i + 0.2 for i in x], b, 0.38, label="Final detector", color="#3E7C59")
    for i in x:
        ax.text(i - 0.2, a[i] + 1, f"{a[i]:.1f}", ha="center", fontsize=10); ax.text(i + 0.2, b[i] + 1, f"{b[i]:.1f}", ha="center", fontsize=10)
    ax.set_xticks(list(x)); ax.set_xticklabels(cls); ax.set_ylabel("Test mAP50 (12 unseen boards)"); ax.set_ylim(0, 100)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(OUT / "per_class_comparison.png"); plt.close(fig)


dfd0(); dfd1(); activity(); per_class_chart()
print("written", sorted(p.name for p in OUT.glob("*.png")))
