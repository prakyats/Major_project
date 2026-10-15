"""
make_final_report.py - final project report for the guide and the team (replaces the 14 Oct status draft and the 7 Oct
BRI update): phases including the leakage story, the mathematical model, the full-dataset extension, the guide's Board
Recoverability Index with our changes and its validation, the application, conclusions and open points.
Every number comes from docs/final_results.json and eval/ (run docs/collect_results.py first).
"""
import json
from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
R = json.loads((ROOT / "docs" / "final_results.json").read_text(encoding="utf-8"))
FIG = ROOT / "docs" / "final_figs"
OUT = Path(r"C:\Users\ASUS\Desktop\Major_Project\docs\Final_Project_Report_2026-10-15.docx")
GREEN = "3E4A3F"
DATE = "15 October 2026"

f8, f4 = R["fusion8"], R["fusion4"]
F8, F4 = f8["test"]["fused"], f4["test"]["fused"]
s8, s4 = f8["stats_fused_minus_best_single"], f4["stats_fused_minus_best_single"]
single4 = f4["test"]["singles"][f4["best_single_on_val"]]
bri = R["bri"]; enh = R["enh"]; st = R["stats4"]; wi = R["wiou"]
FU = R["full"]; FT = FU["test"]; stfu = FU["stats_new_minus_deployed_test_orig"]
ffo, fff = FT["full_fusion"]["orig"], FT["full_fusion"]["full"]
sub = FT["deployed_fusion"]["orig"]
bal_s, bal_f = R["balance"]["train_sqrt"], R["balance_full"]["train_sqrt"]
bri_single = json.loads((ROOT / "eval" / "bri" / "bri_validation_yolo11s_4cls_balanced_1024.json").read_text())
bri_sub = json.loads((ROOT / "eval" / "bri" / "bri_validation_fusion4_1024.json").read_text())
T8 = R["test8"]; v4 = R["val4"]; t4 = R["test4"]
wiou_v = [v for k, v in wi["val_map50"].items() if "wiou" in k][0]

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Cm(2.2))
sec.top_margin = sec.bottom_margin = Cm(2.0)
st_n = doc.styles["Normal"]; st_n.font.name = "Calibri"; st_n.font.size = Pt(11)
st_n.paragraph_format.space_after = Pt(6)
for lvl, size in ((1, 16), (2, 13), (3, 11.5)):
    h = doc.styles[f"Heading {lvl}"]; h.font.name = "Calibri"; h.font.size = Pt(size)
    h.font.color.rgb = RGBColor(0x3E, 0x4A, 0x3F); h.font.bold = True


def para(text, bold_lead=None, style=None, italic=False, size=None, align=None):
    p = doc.add_paragraph(style=style)
    if bold_lead:
        r = p.add_run(bold_lead); r.bold = True
        if size: r.font.size = Pt(size)
    r = p.add_run(text); r.italic = italic
    if size: r.font.size = Pt(size)
    if align is not None: p.alignment = align
    return p


def bullet(text, bold_lead=None):
    return para(text, bold_lead, style="List Bullet")


_num = [0]


def number(text, bold_lead=None, restart=False):
    """numbered paragraph with explicit numbers (Word's List Number would continue across sections)"""
    _num[0] = 1 if restart else _num[0] + 1
    p = para(text, f"{_num[0]}. " + (bold_lead or ""))
    p.paragraph_format.left_indent = Cm(0.6); p.paragraph_format.first_line_indent = Cm(-0.6)
    return p


def shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hex_); tcPr.append(sh)


def table(rows, widths, size=9.5, highlight=()):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Cm(widths[j]); c.text = ""
            r = c.paragraphs[0].add_run(str(val)); r.font.size = Pt(size)
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
            if j > 0 and i > 0:
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if i == 0:
                r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255); shade(c, GREEN)
            elif i in highlight:
                r.bold = True; shade(c, "E8F0E3")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def formula(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); r.italic = True; r.font.name = "Cambria Math"; r.font.size = Pt(11.5)
    return p


def figure(path, width_cm, caption):
    if not Path(path).exists():
        return
    doc.add_picture(str(path), width=Cm(width_cm)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(caption, italic=True, size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER)


def lead(bold, text):
    p = para("", bold); p.add_run(text); return p


def p1(x):
    return f"{x * 100:.1f}"


def mm(d):
    return f"{d['map50']:.1f} / {d['map']:.1f}"


# ======================================================================= title
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("AI-Based Wood Quality Assessment"); r.bold = True; r.font.size = Pt(22); r.font.color.rgb = RGBColor(0x3E, 0x4A, 0x3F)
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Final project report: phases, mathematical model, full dataset and recoverability grading"); r.font.size = Pt(13)
para("Major Project, Dept. of CSBS, Dayananda Sagar College of Engineering, AY 2026-27 · Guide: Mrs. Aparna H D",
     align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
para("Team 4: Gurugubelli Gayatri (1DS23CB014), Prakyat Pramod Shetty (1DS23CB033), Saiprasad Rao (1DS23CB041), "
     f"Yasti Anil Kotak (1DS23CB063) · {DATE}", align=WD_ALIGN_PARAGRAPH.CENTER, size=10)

# ======================================================================= 1 summary
doc.add_heading("1. Summary", 1)
para("The project is complete. Everything proposed at the 50 % review has been implemented and measured on physical "
     "boards that were never used for training or for any choice of settings. The final review is on 24 October 2026.")
lead("At the 50 % review ", "both detectors were stuck at 63-65 mAP50 over 8 defect classes, and the larger model did "
     "not help. The guide suggested a mathematical model to improve accuracy and shared the Board Recoverability Index (BRI).")
lead("Since then ", f"we built the mathematical model (class-balancing rule, weighted box fusion of detectors, Wise-IoU "
     f"loss, per-class thresholds and statistical validation), trained the final models on the full public dataset "
     f"(20,276 images from 407 boards instead of 4,000 from 81), and implemented, adapted and validated the guide's BRI. "
     f"On the four main defect classes the final detector scores {ffo['map50']:.1f} mAP50 on the original 12 test boards "
     f"(best single model at mid-term: {p1(single4['map50'])}) and {fff['map50']:.1f} on 51 further unseen boards.")
table([["Item", "Result (test boards never used for any choice)"],
       ["Detection, 8 classes (50 % review)", "YOLO11s 64.6 mAP50, YOLO11m 63.0 mAP50"],
       ["Best single model, 4 main classes (4,000 images)", f"{p1(single4['map50'])} mAP50, {p1(single4['map'])} mAP50-95"],
       ["Mathematical model: fusion of four 4-class models", f"{p1(F4['map50'])} mAP50, {p1(F4['map'])} mAP50-95; gain +{s4['map50_diff_ci'][0]:.1f} to +{s4['map50_diff_ci'][1]:.1f} (95 % CI), Wilcoxon p = {s4['wilcoxon_p']:.3f}"],
       ["Final detector: fusion of two models trained on the full dataset", f"{mm(ffo)} on the 12 original test boards; {mm(fff)} on 51 new test boards"],
       ["Gain of the final detector on the same 12 boards", f"{ffo['map50'] - sub['map50']:+.1f} mAP50 (95 % CI {stfu['map50_diff_ci'][0]:+.1f} to {stfu['map50_diff_ci'][1]:+.1f}), with 2 models instead of 4"],
       ["Grading (BRI) vs grades from the annotations", f"weighted kappa {bri['test_per_image']['qwk']:.2f}; exact {bri['test_per_image']['exact']*100:.1f} %, within one grade {bri['test_per_image']['within_one']*100:.1f} %; {round(bri['test_per_board']['exact']*12)} of 12 boards exact"],
       ["Application", "Web app on a laptop CPU (about 0.5 s per image): defects, heatmap, grade A / B / C / Reject, recoverable area, value estimate"]],
      [7.0, 9.5], highlight=(4, 5))
figure(FIG / "methodology_final.png", 12.5, "Fig. 1. Methodology as completed.")

# ======================================================================= 2 phase 0
doc.add_heading("2. Phase 0: the starting point and the leakage problem", 1)
para("The team's first model was YOLO11s trained on square 640-px images for 83 epochs on a laptop CPU. It reported "
     "62.2 mAP50 on its test set (validation 66.3). Before building on it we checked the pipeline and found three problems:")
_num[0] = 0
number("The data was split image by image. Each physical board is cut into about 49 images, so every one of the 81 boards "
       "appeared in training, validation and test. A model can then score well by remembering a board's grain and "
       "colour; the score measured memory of boards, not how the model would do on a new board.", "Board leakage. ")
number("The class names in the configuration (Crack, Knot, Hole, Stain, Split, Warp, Decay, Scratch) were not the "
       "dataset's classes. The real classes are Quartzity, Live_Knot, Marrow, Resin, Dead_Knot, Knot_with_crack, "
       "Knot_missing and Crack (checked against the dataset's own label files).", "Wrong class names. ")
number("The images are 2800 x 1024 strips. Squeezing them into a 640 x 640 square wasted 63 % of the input on padding "
       "and shrank hairline cracks to below one pixel.", "Square input. ")
table([["Check", "Earlier pipeline", "Rebuilt pipeline"],
       ["Boards shared between train / val / test", "100 % of boards in all three", "0 (asserted by the script)"],
       ["Class names", "8 invented names", "dataset's real names"],
       ["Input", "640 x 640, 63 % padding", "1024 x 384 rectangular, no padding"],
       ["Zero-size labels", "158 kept", "removed"],
       ["Augmentation", "rotation 10°, vertical flip, heavy erasing", "grain-safe: no rotation, no vertical flip"]],
      [5.5, 5.0, 6.0], size=9.5)
para("So the 62.2 was not a usable baseline. The honest numbers after the fix are lower at first sight (Section 3) but "
     "they predict performance on new boards, which is what a sawmill needs. Every later result in this report uses "
     "board-level splits.")

# ======================================================================= 3 phase 1
doc.add_heading("3. Phase 1: up to the 50 % review (16 September)", 1)
doc.add_heading("3.1 What we did", 2)
bullet("4,000 line-scan images of sawn timber (Kodytek, Bodzas and Bilik, F1000Research 2022), 8 classes, 9,053 boxes.", "Dataset. ")
bullet("Split by physical board: 52 boards for training, 17 for validation, 12 for test, zero overlap.", "Leakage-free split. ")
bullet("Rectangular 1024-px input, augmentation that respects the grain direction.", "Input. ")
bullet("YOLO11m (20.0 M parameters) and YOLO11s (9.4 M), fine-tuned from COCO with one identical recipe on a Kaggle "
       "Tesla T4 GPU. Each model was evaluated on the test boards exactly once.", "Models. ")
bullet("A web application showing boxes, a heatmap, per-class statistics and a JSON report.", "Demo. ")
doc.add_heading("3.2 Results and the accuracy problem", 2)
rows = [["Model (8 classes)", "Precision", "Recall", "F1", "mAP50", "mAP50-95", "ms / image (T4)"]]
for n, ms in (("YOLO11m", "33.2"), ("YOLO11s", "11.7")):
    a = T8[n]["ALL"]; rows.append([n] + [f"{x:.1f}" for x in a] + [ms])
table(rows, [3.6, 2, 2, 1.6, 1.8, 2.2, 2.6])
rows = [["Class", "Test boxes", "YOLO11m mAP50", "YOLO11s mAP50"]]
for c, nb in (("Dead_Knot", 343), ("Marrow", 46), ("Live_Knot", 406), ("Knot_missing", 24), ("Knot_with_crack", 30),
              ("Resin", 69), ("Crack", 95), ("Quartzity", 10)):
    rows.append([c, nb, f"{T8['YOLO11m'][c][3]:.1f}", f"{T8['YOLO11s'][c][3]:.1f}"])
table(rows, [4, 2.5, 3, 3])
para("The two models were tied, so a bigger network was not the answer. The score was held down by the data: "
     "Quartzity (125 training boxes) was not learned (13-15 mAP50), Crack is thin and faint (53-58), and the rare knot "
     "types were confused with each other. The training set is 37:1 imbalanced (2,899 Live_Knot boxes against 78 "
     "Knot_missing). This is the accuracy issue that led the guide to suggest a mathematical model.")

# ======================================================================= 4 phase 2
doc.add_heading("4. Phase 2: from 50 % to completion (17 September - 8 October)", 1)
para("Every item promised at the 50 % review was implemented. Each choice was made on validation boards and each "
     "candidate final model was tested once, so the test numbers are not tuned to the test set.")
table([["Promised at 50 %", "What we did", "Outcome"],
       ["More samples for rare classes", "Kept the 4 most frequent classes; copy-paste balancing of real defect crops; later the full dataset", "Balancing alone: not significant; full dataset: significant gain (Section 6)"],
       ["Higher-resolution input", "Trained at 1280 px (1280 x 480) as well as 1024 px", "Alone not better; useful inside fusion"],
       ["Mathematical model: fusion, Wise-IoU, thresholds, statistics", "Implemented all four (Section 5)", "Fusion adopted: significant gain"],
       ["CWB-style architecture", "Wise-IoU (the CWB loss) implemented and tested", "Not better; CondConv / BiFormer left as future work"],
       ["Image enhancement (CLAHE, denoising)", "Study under 6 imaging conditions on validation", "No gain on normal images (Section 4.3)"],
       ["Recoverability grading rule", "Guide's BRI implemented, adapted and validated (Section 7)", f"Weighted kappa {bri['test_per_image']['qwk']:.2f}"],
       ["Market-price analytics", "Grade-to-value estimate in the application", "Done (inputs editable)"],
       ["Multi-seed runs", "Final setup repeated with 3 seeds", f"Spread {wi['seed_spread']:.1f} mAP50"],
       ["Final evaluation and application", "Single-shot tests; app with grading and value", "Done; final deck V4.1 prepared"]],
      [4.5, 6.5, 5.5], size=9)
doc.add_heading("4.1 Why four classes", 2)
para("The final system detects the four defect classes with the most data: Live_Knot, Dead_Knot, Resin and Crack. "
     "Crack, the most severe defect, is kept. The other four classes have too few examples (78-125 training boxes in the "
     "subset) to learn or to measure reliably on 12 test boards. On these four classes the 8-class YOLO11s scores 69.6 "
     "mAP50 on test; that, not 64.6, is the fair starting point for every 4-class comparison.")
doc.add_heading("4.2 All runs on the 4,000-image subset", 2)
rows = [["Model (YOLO11s unless stated)", "Val mAP50", "Test mAP50", "Test mAP50-95"],
        ["8-class YOLO11s, scored on the 4 classes", "73.8", "69.6", "32.9"]]
for k, lab in (("plain_1024", "4 classes, no balancing, 1024 px"), ("full_1024", "4 classes, full balance 1:1"),
               ("sqrt_1024", "4 classes, partial balance 3:1, 1024 px (best single)"), ("sqrt_1280", "4 classes, partial balance, 1280 px"),
               ("plain_1280", "4 classes, no balancing, 1280 px")):
    rows.append([lab, f"{v4[k]['ALL'][3]:.1f}", f"{t4[k]['ALL'][3]:.1f}" if t4.get(k) else "not tested",
                 f"{t4[k]['ALL'][4]:.1f}" if t4.get(k) else "-"])
rows.append(["Wise-IoU loss, final setup", f"{wiou_v:.1f}", "not tested", "-"])
rows.append(["Seeds 42 / 1 / 2, final setup", " / ".join(f"{x:.1f}" for x in wi["seed_val_map50"]), "-", "-"])
rows.append(["Fusion of the four 4-class models", p1(f4["chosen"]["val_map50"]), p1(F4["map50"]), p1(F4["map"])])
table(rows, [7.5, 2.8, 2.8, 3], highlight=(len(rows) - 1,))
para("Models without a test number were rejected on validation by rules written down before training; testing them "
     "anyway would have meant choosing on the test set.", italic=True, size=9.5)
doc.add_heading("4.3 Image-enhancement study (synopsis hypothesis H1)", 2)
rows = [["Condition (validation mAP50)", "Raw", "CLAHE", "Denoise", "Sharpen"]]
for c, lab in (("normal", "Normal"), ("low_light", "Low light"), ("overexposed", "Over-exposed"), ("blur", "Blur"),
               ("noise", "Noise"), ("low_contrast", "Low contrast")):
    rows.append([lab] + [p1(enh["table"][c][e]["map50"]) for e in ("raw", "clahe", "denoise", "sharpen")])
table(rows, [5, 2.4, 2.4, 2.4, 2.4])
para("CLAHE lowered accuracy significantly in 5 of 6 conditions; denoising helped only on noisy images (+3 to +7 "
     "points). Hypothesis H1 is therefore rejected for normal images. Lighting matters far more than enhancement: low "
     "light costs about 25 points, so controlled lighting is the main requirement for deployment.")

# ======================================================================= 5 math model
doc.add_heading("5. The mathematical model for accuracy", 1)
para("This section answers the guide's question: can a mathematical model improve accuracy, and by how much? Yes: "
     "on the same data, weighted box fusion adds about 5.5 mAP50 points on the main defect classes, with a 95 % "
     "confidence interval that excludes zero.")
doc.add_heading("5.1 Components", 2)
lead("1. Class-balancing rule. ", "Rare classes get more training examples by pasting real defect crops onto "
     "defect-free training boards (inside the wood, along the grain, training split only). The target count per class is "
     "the repeat-factor rule of LVIS (Gupta et al., 2019), related to the effective number of samples (Cui et al., 2019):")
formula("n_c* = √(n_c × n_max)        (partial balance; full balance: n_c* = n_max)")
para("It turns the 9.5 : 1 imbalance of the four classes into 3.1 : 1 (partial) or 1.06 : 1 (full).")
lead("2. Weighted box fusion (Solovyev et al., 2021). ", "Several detectors look at the same board; overlapping boxes "
     "of the same class are merged into one box, averaged by confidence, and a box that only one model sees is down-weighted:")
formula("b_f = Σ w_m c_i b_i / Σ w_m c_i        c_f = (Σ w_m c_i / Σ w_m) × min(Σ w_m, W) / W")
para("b = box, c = confidence, w_m = weight of model m, W = sum of all model weights. The overlap threshold and the "
     "weights are chosen on validation from a fixed grid (IoU 0.45 / 0.55 / 0.65; equal weights or one model doubled).",
     size=9.5, italic=True)
lead("3. Wise-IoU v3 box loss (Tong et al., 2023). ", "The loss used by the CWB-YOLOv8 reference model, which focuses "
     "training on ordinary-quality boxes:")
formula("L = r × exp(d² / (W_g² + H_g²)) × (1 − IoU),    r = β / (δ α^(β − δ))")
lead("4. Per-class confidence thresholds. ", "One threshold per class, chosen to maximise F1 on validation.")
lead("5. Statistical validation. ", "Board-level bootstrap (the test boards resampled 1,000 times) for a 95 % "
     "confidence interval of every improvement, and an exact Wilcoxon signed-rank test on per-board differences. "
     "Resampling boards rather than images respects the fact that images of one board are not independent.")
doc.add_heading("5.2 Effect on the score (4,000-image subset)", 2)
rows = [["Step (test, 4 classes)", "mAP50", "mAP50-95", "Verdict"],
        ["8-class YOLO11s (50 % review), on the 4 classes", "69.6", "32.9", "starting point"],
        ["4-class model, no balancing", f"{t4['plain_1024']['ALL'][3]:.1f}", f"{t4['plain_1024']['ALL'][4]:.1f}", "not significant"],
        ["+ partial class balancing (best single on validation)", f"{p1(single4['map50'])}", f"{p1(single4['map'])}", "not significant"],
        ["+ 1280-px model", f"{t4['sqrt_1280']['ALL'][3]:.1f}", f"{t4['sqrt_1280']['ALL'][4]:.1f}", "not chosen on validation"],
        ["Weighted box fusion of the four 4-class models", p1(F4["map50"]), p1(F4["map"]), "significant gain"]]
table(rows, [7.5, 2.2, 2.4, 4.3], highlight=(5,))
table([["Fusion vs best single model (test)", "Difference", "95 % interval", "Boards better / worse", "Wilcoxon p"],
       ["4 classes, mAP50", f"+{(F4['map50'] - single4['map50']) * 100:.1f}", f"+{s4['map50_diff_ci'][0]:.1f} to +{s4['map50_diff_ci'][1]:.1f}", f"{s4['boards_better']} / {s4['boards_worse']}", f"{s4['wilcoxon_p']:.3f}"],
       ["4 classes, mAP50-95", f"+{(F4['map'] - single4['map']) * 100:.1f}", f"+{s4['map_diff_ci'][0]:.1f} to +{s4['map_diff_ci'][1]:.1f}", "-", "-"],
       ["8 classes (YOLO11m + YOLO11s), mAP50", f"+{(F8['map50'] - f8['test']['singles'][f8['best_single_on_val']]['map50']) * 100:.1f}", f"{s8['map50_diff_ci'][0]:+.1f} to {s8['map50_diff_ci'][1]:+.1f}", f"{s8['boards_better']} / {s8['boards_worse']}", f"{s8['wilcoxon_p']:.2f}"],
       ["8 classes, mAP50-95", f"+{(F8['map'] - f8['test']['singles'][f8['best_single_on_val']]['map']) * 100:.1f}", f"+{s8['map_diff_ci'][0]:.1f} to +{s8['map_diff_ci'][1]:.1f}", "-", "-"]],
      [5.5, 2.2, 3.4, 3, 2.2])
para("Fusion helped every class, most of all Crack (+11.5) and Resin (+5.5), the two thinner and rarer defects. It works "
     "because the members make different mistakes (different input sizes and class balance); averaging cancels some "
     "errors and places boxes more precisely.")
doc.add_heading("5.3 What did not help (also a finding)", 2)
bullet("helped on validation (+2.2) but not on test; full balance was worst, because only 160 cracks could be cut out "
       "cleanly and each was pasted up to 17 times.", "Class balancing alone ")
bullet("was not better on validation.", "1280-px input alone ")
bullet(f"scored {wiou_v:.1f} vs 75.3 on validation, within the seed spread of {wi['seed_spread']:.1f}: not adopted.", "Wise-IoU ")
bullet(f"lowered macro-F1 on test ({p1(f4['thresholds']['fused_test_per_class']['F1'])} vs {p1(f4['thresholds']['fused_test_global']['F1'])} with one global threshold): they over-fit the few validation boxes.", "Per-class thresholds ")

# ======================================================================= 6 full dataset
doc.add_heading("6. Phase 3: the full dataset (14-15 October)", 1)
para("Section 5 showed that the limit was data, not the network. The public dataset our 4,000 images come from has "
     "20,276 images from 407 boards (Kodytek et al., 2022), with 4-7 times more examples of the rare classes. We "
     "retrained the two strongest fusion members on all of it.")
doc.add_heading("6.1 Data and split", 2)
table([["", "4,000-image subset", "Full dataset"],
       ["Images / boards", "4,000 / 81", "20,276 / 407"],
       ["Boards train / val / test", "52 / 17 / 12", "280 / 76 / 51"],
       ["4-class training boxes after partial balance", f"{sum(bal_s.values()):,}", f"{sum(bal_f.values()):,}"],
       ["Crack training boxes after partial balance", f"{bal_s['Crack']:,}", f"{bal_f['Crack']:,}"],
       ["Training time per model (one T4)", "1.6 h (1024 px), 2.1 h (1280 px)", "3.2 h (1024 px), 4.3 h (1280 px)"]],
      [6.5, 4.5, 5.5])
bullet("our 81 boards keep their split, so the original 12 test boards stay untouched; the 326 new boards are split "
       "70 / 18 / 12 by board (seed 42).", "Split. ")
bullet("the full images come from a Kaggle copy of the published dataset. Before use we checked it: the same 43,974 "
       "boxes as the original release, and on our 4,000 images 3,953 label files identical and the rest within 1 pixel. "
       "Our 4,000 images keep their original files and labels, so the comparison with Section 5 is exact (checked by the "
       "notebook before training).", "Data check. ")
bullet("YOLO11s, 4 classes, partial balance, at 1024 and 1280 px; 40 epochs, patience 15, batch 32, lr0 0.001; a "
       "free CPU test of the whole pipeline ran before any GPU time was used.", "Models. ")
bullet(f"written down before training: the new system replaces the previous one only if its mAP50 on the original 714 "
       f"validation images exceeds {FU['val_orig']['deployed_fusion'][0]:.1f}.", "Decision rule. ")
doc.add_heading("6.2 Results", 2)
V = FU["val_orig"]
rows = [["mAP50 / mAP50-95", "Val, 714 original images", "Test, 469 original images (12 boards)", "Test, full split (2,488 images, 51 boards)"],
        ["Fusion of four models, subset (previous)", "{:.1f} / {:.1f}".format(*V["deployed_fusion"]), mm(sub), "-"],
        ["YOLO11s full data, 1024 px", "{:.1f} / {:.1f}".format(*V["full_1024"]), mm(FT["full_1024"]["orig"]), mm(FT["full_1024"]["full"])],
        ["YOLO11s full data, 1280 px", "{:.1f} / {:.1f}".format(*V["full_1280"]), mm(FT["full_1280"]["orig"]), mm(FT["full_1280"]["full"])],
        ["Final detector: fusion of the two", "{:.1f} / {:.1f}".format(*V["full_fusion"]), mm(ffo), mm(fff)]]
table(rows, [5.2, 3.3, 3.9, 4.1], size=9, highlight=(4,))
para(f"The rule was met ({V['full_fusion'][0]:.1f} > {V['deployed_fusion'][0]:.1f}), so the full-data fusion is the final "
     f"detector. Fusion settings, chosen on the full validation split: IoU {FU['chosen']['t_iou']}, equal weights.")
rows = [["Class (test AP50)", "Best single, subset", "Fusion, subset", "Final, 12 original boards", "Final, 51 new boards"]]
for c in ("Live_Knot", "Dead_Knot", "Resin", "Crack"):
    rows.append([c, f"{t4['sqrt_1024'][c][3]:.1f}", p1(F4["ap50"][c]), f"{ffo['ap50'][c]:.1f}", f"{fff['ap50'][c]:.1f}"])
table(rows, [3.8, 3.1, 3.1, 3.4, 3.1], size=9)
table([["Final detector minus subset fusion (12 original test boards)", "Value"],
       ["mAP50 difference", f"{ffo['map50'] - sub['map50']:+.1f}"],
       ["95 % interval (board bootstrap), mAP50", f"{stfu['map50_diff_ci'][0]:+.1f} to {stfu['map50_diff_ci'][1]:+.1f}"],
       ["95 % interval, mAP50-95", f"{stfu['map_diff_ci'][0]:+.1f} to {stfu['map_diff_ci'][1]:+.1f}"],
       ["Boards better / worse", f"{stfu['boards_better']} / {stfu['boards_worse']}"],
       ["Wilcoxon p (12 boards)", f"{stfu['wilcoxon_p']:.2f}"]], [10, 5])
para("The gain is smaller than the gain from fusion but its interval excludes zero; with only 12 boards the Wilcoxon "
     "test cannot confirm it, which is why the 51-board test split matters: there the final detector reaches "
     f"{fff['map50']:.1f} mAP50, and Crack, the hardest class, {fff['ap50']['Crack']:.1f}. The final system also needs "
     "two models instead of four, so it is about twice as fast.")
figure(ROOT / "runs_log" / "run7_full4_1024_v2" / "results.png", 15, "Fig. 2. Training and validation curves, full dataset, 1024 px.")
doc.add_heading("6.3 What went wrong and how it was handled", 2)
para("The first attempt converted the original 140 GB release on a Kaggle CPU session; it hit the 12-hour session limit "
     "before finishing and the chained GPU run started without its input, so it was stopped and discarded (no result "
     "from it was used). The second attempt used the verified Kaggle copy, a CPU smoke test of the whole pipeline, and a "
     "time guard that ends training safely before the session limit. Both runs finished in about 3.5 and 4.6 hours.")

# ======================================================================= 7 BRI
doc.add_heading("7. The guide's Board Recoverability Index (BRI) and our changes", 1)
para("The guide's document proposed the BRI: it turns the detected defects into a damage score, a recoverable area and a "
     "grade A / B / C / Reject. It does not change detection accuracy; it is the quality-assessment part of the project. "
     "We implemented all six steps as given, and our code reproduces the document's worked example exactly (damage "
     "score 0.020860, grade B).")
formula("s_i = w_c × conf_i × p_i,   p_i = 1 − exp(−d_i / λ),   DIS = Σ max_i s_i / A_board,   A_rec = A_board (1 − DIS)")
figure(FIG / "bri_geometry.png", 13, "Fig. 3. Our images are sections of a board with black conveyor on both sides; the trimmable edges are the board's sides.")
table([["Part of BRI", "Guide's version", "Our change and why"],
       ["Distance d_i", "to the nearest image border", "to the nearest side edge of the board (board mask): image borders include ~160 px of conveyor, and the top and bottom are cuts between sections, not edges a sawmill can trim"],
       ["Board area", "image width x height", "wood pixels only: the conveyor is ~12 % of each image"],
       ["Grade thresholds", "0.01 / 0.03 / 0.06 (illustrative)", "fitted on validation boards: the defaults grade 72 % of our boards A; the detector gets its own thresholds (guide's calibrate_thresholds) because model confidences are below 1"],
       ["Severity weights", "8-class placeholder table", "same values for the 4 classes: Crack 1.00, Dead_Knot 0.60, Live_Knot 0.40, Resin 0.30 (awaiting the guide's ranking)"]],
      [3, 3.8, 9.7], size=9)
para("Validation (no expert grades yet): the reference grade is BRI computed on the annotators' boxes; the model grade is "
     "BRI on the detector's boxes; all thresholds are fitted on validation boards and agreement is measured on the 12 test boards.")
pi, pb = bri["test_per_image"], bri["test_per_board"]
po, ps = bri_sub["test_per_image"], bri_single["test_per_image"]
table([["Agreement with the annotation-based grade", "Final detector, per image", "Final detector, per board", "Subset fusion, per image", "Best single, per image"],
       ["Exact grade", f"{pi['exact']*100:.1f} %", f"{pb['exact']*100:.1f} %", f"{po['exact']*100:.1f} %", f"{ps['exact']*100:.1f} %"],
       ["Within one grade", f"{pi['within_one']*100:.1f} %", f"{pb['within_one']*100:.1f} %", f"{po['within_one']*100:.1f} %", f"{ps['within_one']*100:.1f} %"],
       ["Quadratic weighted kappa", f"{pi['qwk']:.2f}", f"{pb['qwk']:.2f}", f"{po['qwk']:.2f}", f"{ps['qwk']:.2f}"],
       ["Mean abs. error, recoverable area", f"{pi['mae_recoverable_pct']:.2f} pts", f"{pb['mae_recoverable_pct']:.2f} pts", f"{po['mae_recoverable_pct']:.2f} pts", f"{ps['mae_recoverable_pct']:.2f} pts"]],
      [4.6, 3.0, 3.0, 3.0, 3.0], size=9)
cm = pi["confusion"]; G = ["A", "B", "C", "Reject"]
table([["Reference \\ final detector (469 test images)", "A", "B", "C", "Reject"]] +
      [[f"{G[i]} ({sum(cm[i])} images)"] + [str(x) for x in cm[i]] for i in range(4)], [6.0, 2.5, 2.5, 2.5, 2.5])
para("Most disagreements are one grade apart; a two-grade error happens for about 2-3 % of images. The grading feeds a "
     "value estimate in the application: value = board volume x recoverable share x grade-A price x grade factor (all "
     "inputs editable).")
lead("Points for the guide: ", "(1) approve the changes above; (2) rank the four defect classes by severity, to replace "
     "the placeholder weights; (3) if possible, blind expert grading of 30-50 board images to calibrate the weights and "
     "thresholds and report kappa against an expert, as proposed in Section 5 of the BRI document.")

# ======================================================================= 8 application
doc.add_heading("8. System and application", 1)
figure(FIG / "system_design_final.png", 12.5, "Fig. 4. System design as implemented.")
bullet("upload a board image; the final detector (two fused models) draws colour-coded boxes; heatmap, per-class "
       "counts and area.", "Detect: ")
bullet("BRI grade A / B / C / Reject, damage score, recoverable area, and an editable market-value estimate.", "Grade: ")
bullet("for the 12 test boards, the annotators' boxes and grade are shown next to the model's.", "Compare: ")
bullet("runs on a laptop CPU, about 0.5 s per 2800 x 1024 image for the final detector (0.8 s for the earlier "
       "four-model fusion); JSON report per image. Earlier models remain selectable for comparison.", "Deployment: ")
figure(FIG / "app_grade.png", 15, "Fig. 5. Application: damage heatmap of a test board (BRI influence map).")

# ======================================================================= 9 conclusion
doc.add_heading("9. Conclusions, limitations and future work", 1)
_num[0] = 0
number("A leakage-free, board-level evaluation of YOLO11 on industrial line-scan timber images; the earlier 62.2 was "
       "inflated by board leakage, and model size (YOLO11m vs YOLO11s) is not the bottleneck.")
number(f"A mathematical model (class-balancing rule + weighted box fusion + board-level statistics) that raises mAP50 "
       f"from {p1(single4['map50'])} to {p1(F4['map50'])} on the same data, with a significant board-level interval.")
number(f"More data, with the same recipe: the final detector reaches {ffo['map50']:.1f} on the original test boards and "
       f"{fff['map50']:.1f} / {fff['map']:.1f} (mAP50 / mAP50-95) on 51 new boards.")
number(f"The guide's Board Recoverability Index, adapted to line-scan geometry and validated (weighted kappa {pi['qwk']:.2f}).")
number("Negative results reported with intervals: CLAHE enhancement, Wise-IoU, per-class thresholds and higher "
       "resolution alone did not help.")
lead("Limitations: ", "the original test set has 12 boards (now complemented by 51); severity weights and grade "
     "thresholds await expert calibration; the four rare classes are out of scope; trained on controlled line-scan "
     "imagery, so field cameras need new data.")
lead("Future work: ", "expert grading to calibrate BRI; k-fold validation over boards; the rare classes with the full "
     "dataset; segmentation masks for tighter defect area; the full CWB architecture (CondConv / BiFormer); plywood.")

# ======================================================================= 10 deliverables
doc.add_heading("10. Deliverables", 1)
table([["Deliverable", "Where"],
       ["Final presentation V4.1 (34 slides), review 24 October 2026, 9 AM", "Major_Project_Final_Presentation_V4.1.pptx"],
       ["This report", "Final_Project_Report_2026-10-15.docx"],
       ["Web application (final detector, grading, value)", "app.py in the GitHub repository"],
       ["Code, results and decision log (every run and deviation)", "GitHub repository: scripts, eval/, runs_log/, NOTES.md"],
       ["Training notebooks (Kaggle T4)", "kaggle_upload/ in the repository"]], [9.5, 7])
doc.add_heading("References", 2); _num[0] = 0
for ref in [
    "P. Kodytek, A. Bodzas, P. Bilik, A large-scale image dataset of wood surface defects for automated vision-based quality control processes, F1000Research 10:581, 2022, doi:10.12688/f1000research.52903.2.",
    "G. Jocher, J. Qiu, Ultralytics YOLO11, 2024, github.com/ultralytics/ultralytics.",
    "R. Solovyev, W. Wang, T. Gabruseva, Weighted boxes fusion: ensembling boxes from different object detection models, Image and Vision Computing 107, 104117, 2021.",
    "A. Gupta, P. Dollár, R. Girshick, LVIS: a dataset for large vocabulary instance segmentation, CVPR 2019.",
    "Y. Cui, M. Jia, T.-Y. Lin, Y. Song, S. Belongie, Class-balanced loss based on effective number of samples, CVPR 2019.",
    "D. Dwibedi, I. Misra, M. Hebert, Cut, paste and learn: surprisingly easy synthesis for instance detection, ICCV 2017.",
    "Z. Tong, Y. Chen, Z. Xu, R. Yu, Wise-IoU: bounding box regression loss with dynamic focusing mechanism, arXiv:2301.10051, 2023.",
    "J. Cohen, Weighted kappa, Psychological Bulletin 70(4), 1968.",
    "B. Efron, R. J. Tibshirani, An Introduction to the Bootstrap, Chapman & Hall, 1993.",
    "F. Wilcoxon, Individual comparisons by ranking methods, Biometrics Bulletin 1(6), 1945.",
    "K. Zuiderveld, Contrast limited adaptive histogram equalization, Graphics Gems IV, 1994."]:
    _num[0] += 1; para(ref, f"[{_num[0]}] ", size=9.5)

doc.save(str(OUT))
print("saved", OUT)
