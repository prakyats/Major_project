"""
make_phase1_report.py - fills the department's "Project Phase-I Report Template.docx" with the project's content
(wording from the approved final deck V6.2; numbers from docs/final_results.json and eval/). Front matter keeps the
template's layout; the chapters follow the template's outline exactly. Page numbers for the contents and the lists are
filled in afterwards by fill_pages() through Word.
python docs/make_phase1_report.py
"""
import copy, json, re
from pathlib import Path
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(r"C:\Users\ASUS\Desktop\Project   Phase-I Report Template.docx")
OUT = Path(r"C:\Users\ASUS\Desktop\Major_Project\docs\Major_Project_Phase-I_Report_Draft_v2.docx")
R = json.loads((ROOT / "docs" / "final_results.json").read_text(encoding="utf-8"))
FIGS = ROOT / "docs" / "final_figs"; RFIGS = ROOT / "docs" / "report_figs"
TITLE = "AI-Based Wood Quality Assessment"
STUDENTS = [("GURUGUBELLI GAYATRI", "1DS23CB014"), ("PRAKYAT PRAMOD SHETTY", "1DS23CB033"),
            ("SAIPRASAD RAO", "1DS23CB041"), ("YASTI ANIL KOTAK", "1DS23CB063")]
GUIDE, GUIDE_DES = "Prof. Aparna H D", "Assistant Professor"
DATE = "23 October 2026"
FONT = "Times New Roman"

FU = R["full"]; FT = FU["test"]; ffo, fff = FT["full_fusion"]["orig"], FT["full_fusion"]["full"]
f4 = R["fusion4"]; F4 = f4["test"]["fused"]; st4 = f4["stats_fused_minus_best_single"]; stfu = FU["stats_new_minus_deployed_test_orig"]
T8 = R["test8"]; bri = R["bri"]; enh = R["enh"]; wi = R["wiou"]

doc = Document(str(TEMPLATE))
_body = list(doc.element.body.iterchildren())
for _i in (47, 49, 50, 51, 53, 69, 72, 73, 74):                 # empty spacers (template body order) before the signature / names tables
    assert not "".join(t.text or "" for t in _body[_i].iter(qn("w:t"))).strip()
    _body[_i].getparent().remove(_body[_i])
P = doc.paragraphs
FIG_LIST, TAB_LIST = [], []          # (number, caption)
TOC = []                              # (level, text, key)


# ---------------------------------------------------------------- helpers: front matter
def set_runs(p, texts):
    """replace run texts in place (keeps each run's formatting); extra runs are emptied"""
    for r, t in zip(p.runs, texts):
        r.text = t
    for r in p.runs[len(texts):]:
        r.text = ""


def fill_candidates(t):
    for row, (n, u) in zip(t.rows, STUDENTS):
        row.cells[0].paragraphs[0].runs[0].text = n
        row.cells[1].paragraphs[0].runs[0].text = u


names_usn = ", ".join(f"{n.title()} ({u})" for n, u in STUDENTS[:-1]) + f" and {STUDENTS[-1][0].title()} ({STUDENTS[-1][1]})"
for p in P:
    if p.text.strip() == "TITLE":
        p.runs[0].text = TITLE
    elif p.text.strip() == "<<Name of the Guide>>":
        set_runs(p, ["", GUIDE, ""])
    elif p.text.strip() == "<<Designation>>":
        set_runs(p, ["", GUIDE_DES, ""])
    elif p.text.startswith("Certified that the project report entitled"):
        rs = p.runs
        rs[1].text = f"\u201c{TITLE}"; rs[3].text = names_usn; rs[4].text = ""
    elif "hereby declare" in p.text:
        rs = p.runs
        rs[2].text = names_usn + ","
        rs[4].text = rs[4].text.replace("\u201c  Title of the Project \u201d", f"\u201c{TITLE}\u201d")
        rs[5].text = f"{GUIDE}, {GUIDE_DES}, "
        rs[6].text = "Department of Computer Science and Business Systems,"
    elif p.text.strip() == "PLACE:":
        p.add_run(" Bengaluru").bold = True
    elif p.text.strip() == "DATE:":
        p.add_run(f" {DATE}").bold = True
    elif p.text.startswith("We would like to express"):
        p.runs[1].text = (f"our profound gratitude to our guide, {GUIDE}, {GUIDE_DES}, Department of Computer Science and "
                          "Business Systems, Dayananda Sagar College of Engineering, Bengaluru,")
        for r in p.runs:
            if r.text == "His/Her":
                r.text = "Her"
    elif p.text.startswith("We express our sincere thanks to Project"):
        rs = p.runs
        rs[4].text = ""; rs[6].text = "Prof. Anil D, Assistant Professor,"; rs[7].text = ""; rs[8].text = ""; rs[9].text = ""
        rs[17].text = "for the continuous support and guidance. We thank all teaching and non-teaching staff of "
for i, t in enumerate(doc.tables):
    if t.rows[0].cells[0].text.strip() == "NAME OF THE CANDIDATE":
        fill_candidates(t)
    if t.rows[0].cells[0].text.startswith("Signature of the Guide"):
        c = t.rows[0].cells[0].paragraphs
        c[1].runs[0].text = GUIDE; c[2].runs[0].text = GUIDE_DES
for s in doc.sections:
    for p in s.header.paragraphs:
        if "Project Title" in p.text:
            for r in p.runs:
                r.text = r.text.replace("Project Title", TITLE)
            if "Project Title" in p.text:
                set_runs(p, ["  " + TITLE])

# ---------------------------------------------------------------- abstract
ABSTRACT = [
    "Surface defects such as knots, cracks and resin pockets reduce the usable part of a wood board, and manual grading is "
    "slow, subjective and inconsistent. This project develops an AI-based computer-vision system that detects, classifies "
    "and localises visible surface defects on board images and turns them into a quality grade, a recoverable-area estimate "
    "and a value estimate.",
    "The detector is built on Ultralytics YOLO11. Images are split into training, validation and test sets by physical board, "
    "so every test board is unseen. At the 50% review, YOLO11m and YOLO11s reached 63.0 and 64.6 mAP50 over 8 classes on "
    "unseen boards, limited by scarce and imbalanced data. Revised based on the feedback received, we expanded and "
    "engineered the data (20,276 images from 407 boards, synthetic class balancing) and built a mathematical model of class "
    "balancing and weighted box fusion with board-level statistical validation. The Board Recoverability Index (BRI) "
    "converts the detections into a damage score, a recoverable area and a grade A / B / C / Reject.",
    f"The final detector, a weighted box fusion of two YOLO11s models, reaches {ffo['map50']:.1f} mAP50 on the same unseen "
    f"test boards and {fff['map50']:.1f} on 51 further unseen boards (from 64.6 at mid-term); the fusion gain is significant "
    f"(95% CI +{st4['map50_diff_ci'][0]:.1f} to +{st4['map50_diff_ci'][1]:.1f}). The Board Recoverability Index, adapted to "
    f"our images, matches annotation-based grades with weighted kappa {bri['test_per_image']['qwk']:.2f}. A web application "
    "shows defects, grade, recoverable area and value, and runs on a laptop CPU in about 0.5 s per image. Future work "
    "includes expert calibration of the grading, more data for the rare defect classes and segmentation of defect areas."]
for i, p in enumerate(P):
    if p.text.startswith("ABSTRACT") and "(250-300 Words)" in p.text:
        set_runs(p, ["ABSTRACT"])
        body = [q for q in P[i + 1:i + 6]]
        targets = [q for q in body if q.text.strip()]          # instruction paragraph, points paragraph, applications line
        for q, txt in zip(targets, ABSTRACT):
            set_runs(q, [txt])
            for r in q.runs:
                r.bold = False; r.italic = False; r.font.name = FONT; r.font.size = Pt(12)
            q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            q.paragraph_format.line_spacing = 1.5
        break


# ---------------------------------------------------------------- helpers: chapters
def fmt(run, size=12, bold=False, italic=False, mono=False):
    run.font.name = "Courier New" if mono else FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), run.font.name)
    run.font.size = Pt(size); run.bold = bold; run.italic = italic
    return run


def para(text="", lead=None, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, italic=False, space_after=6, ls=1.15, indent=None):
    p = doc.add_paragraph()
    if lead:
        fmt(p.add_run(lead), size, bold=True)
    if text:
        fmt(p.add_run(text), size, italic=italic)
    p.alignment = align
    pf = p.paragraph_format; pf.space_after = Pt(space_after); pf.space_before = Pt(0); pf.line_spacing = ls
    if indent is not None:
        pf.left_indent = Cm(indent)
    return p


def bullet(text, lead=None):
    p = para(text, lead, indent=0.9)
    p.paragraph_format.first_line_indent = Cm(-0.5)
    p.runs[0].text = "\u2022  " + p.runs[0].text
    return p


def page_break():
    p = doc.add_paragraph(); p.add_run().add_break(WD_BREAK.PAGE)


def chapter(n, title, first=False):
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    p.paragraph_format.page_break_before = not first
    fmt(p.add_run(f"CHAPTER {n}"), 16, bold=True)
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    fmt(p.add_run(title.upper()), 16, bold=True)
    p.style = doc.styles["Heading 1"]
    for r in p.runs:
        fmt(r, 16, bold=True); r.font.color.rgb = RGBColor(0, 0, 0)
    TOC.append((1, f"{n}. {title.upper()}", title.upper()))


def section(num, title, level=2):
    p = para("", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)
    p.paragraph_format.space_before = Pt(10)
    fmt(p.add_run(f"{num} {title}"), 14 if level == 2 else 12, bold=True)
    p.style = doc.styles["Heading 2"]
    for r in p.runs:
        fmt(r, 14 if level == 2 else 12, bold=True); r.font.color.rgb = RGBColor(0, 0, 0)
    TOC.append((level, f"{num} {title}", f"{num} {title}"))


def unnumbered(title):
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    p.paragraph_format.page_break_before = True
    fmt(p.add_run(title), 16, bold=True)
    TOC.append((1, title, title))


def borders(t):
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{e}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:color"), "000000"); b.append(el)
    tblPr.append(b)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), fill); tcPr.append(sh)


def table(num, caption, rows, widths, size=10, bold_last=False):
    TAB_LIST.append((num, caption))
    c = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4, ls=1.0)
    fmt(c.add_run(f"Table {num}: "), 11, bold=True); fmt(c.add_run(caption), 11)
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); borders(t); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = t.cell(i, j); cell.width = Cm(widths[j])
            q = cell.paragraphs[0]; q.paragraph_format.space_after = Pt(0); q.paragraph_format.line_spacing = 1.0
            fmt(q.add_run(str(v)), size, bold=(i == 0 or (bold_last and i == len(rows) - 1)))
            if i == 0:
                shade(cell, "D9D9D9")
            if j > 0 and i > 0:
                q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para("", space_after=4, ls=1.0)


def figure(num, path, caption, width=15):
    if not Path(path).exists():
        raise FileNotFoundError(path)
    FIG_LIST.append((num, caption))
    doc.add_picture(str(path), width=Cm(width)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10, ls=1.0)
    fmt(c.add_run(f"Fig. {num}: "), 11, bold=True); fmt(c.add_run(caption), 11)


def code(lines, size=9.5):
    for ln in lines:
        p = para("", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=0, ls=1.0, indent=0.6)
        fmt(p.add_run(ln if ln else " "), size, mono=True)
    para("", space_after=4, ls=1.0)


def source(path, name):
    s = (ROOT / path).read_text(encoding="utf-8").splitlines()
    i = next(k for k, l in enumerate(s) if l.startswith(f"def {name}("))
    j = next((k for k in range(i + 1, len(s)) if s[k].startswith("def ") or s[k].startswith("if __name__")), len(s))
    while not s[j - 1].strip():
        j -= 1
    return s[i:j]


def p1(x):
    return f"{x * 100:.1f}"


# ======================================================================= CHAPTER 1
chapter(1, "Introduction", first=True)
section("1.1", "Overview")
para("Manual inspection of wood depends on human graders, so results are inconsistent and throughput limits line speed. "
     "Our system uses YOLO11, a one-stage real-time detector, to return every "
     "visible defect with class, position, size and confidence, grades each board with the Board Recoverability Index "
     "(A / B / C / Reject), and estimates its recoverable area and value.")
section("1.2", "Problem Statement")
para("Manual wood quality inspection is time-consuming and subjective, and existing AI approaches mostly stop at detecting "
     "defects without a leakage-free evaluation or a path to usable-area estimation; this project therefore aims to develop an "
     "AI-based computer-vision system that detects, classifies and localises visible surface defects on wooden boards, evaluates "
     "the detector on boards it has never seen, and uses the detections to estimate the recoverable portion of each board.")
section("1.3", "Objectives")
for t in ["Build an annotated dataset split by physical board with zero overlap, and evaluate higher-resolution input, image enhancement and class balancing.",
          "Develop a deep-learning framework for defect detection and localisation, each model tested once on held-out boards.",
          "Estimate the recoverable area and grade of each board with the Board Recoverability Index, and a value from the grade.",
          "Compare models with P, R, F1, mAP50, mAP50-95 and inference time, and improve accuracy with a mathematical model validated statistically."]:
    bullet(t)
section("1.4", "Motivation")
para("Grading by eye is slow and hard to audit; a system that finds every defect, measures the usable part of the board and "
     "assigns a consistent grade can raise throughput and reduce disagreement between graders.")
section("1.5", "Outline of the thesis")
para("Chapters 2 to 7 cover the literature survey, requirements and design, implementation, testing, results and conclusion.")

# ======================================================================= CHAPTER 2
chapter(2, "Literature Survey")
section("2.1", "Review of Existing Systems")
table("2.1", "Summary of the literature survey", [
    ["Author(s), year", "Technology", "Result", "Drawbacks / issues"],
    ["Fang et al., 2026 [1]", "Review of deep-learning wood defect inspection", "Supports automated wood-defect inspection", "Small datasets, poor generalisation, real-time deployment challenges"],
    ["Zheng, 2026 [2]", "Image enhancement + YOLOv11 (IEL-YOLO)", "Better defect visibility in low light", "Generalisation challenges"],
    ["Qu et al., 2026 [3]", "WD-SEG segmentation (AFN + TFN + ICO)", "Accurate segmentation at low contrast", "Noise sensitivity, real-time deployment challenges"],
    ["Wang and Tang, 2026 [4]", "Ultrasonic signal processing (IWPT-VMD)", "Less noise, better defect detection", "Requires ultrasonic sensors; limited AI integration"],
    ["Erasmus et al., 2026 [5]", "IoT + LoRaWAN + digital twin", "Low-cost continuous monitoring", "No wood-quality assessment"],
    ["Perry et al., 2026 [6]", "Optimisation and ML for tree-level decisions", "Optimal forest-management decisions", "Limited real-world implementation"],
    ["Başkent et al., 2026 [7]", "Digital twin, monitoring, forecasting", "Adaptive forest planning", "No wood-quality assessment"],
    ["Tan et al., 2025 [8]", "ForestryBERT (NLP, continual learning)", "Forestry knowledge management", "No defect-detection component"]],
    [3.4, 4.4, 4.0, 4.6], size=8.5)
section("2.2", "Limitations of Existing Systems")
para("Existing work reports small datasets and weak generalisation to new boards, has real-time deployment issues, needs special "
     "sensors in the ultrasonic case, and rarely connects detection to a usable-area estimate, a grade or a value.")
section("2.3", "Gap Identification and Analysis")
para("None of the reviewed systems assesses wood quality from images all the way to recoverable value. We address this gap with "
     "a leakage-free, board-level evaluation, a mathematical model of class balancing and weighted box fusion [17] whose gains "
     "are tested statistically, and the Board Recoverability Index for grading.")
section("2.4", "Research Methodology for the Proposed System")
para("Images are cleaned and split by board; input is handled at high resolution with grain-safe augmentation and class "
     "balancing; YOLO11 models detect defects; the mathematical model fuses detectors and validates every gain statistically; "
     "the detections are then graded and valued (Fig. 2.1). Every choice is made on validation boards and each test model is "
     "evaluated exactly once.")
figure("2.1", FIGS / "methodology_final.png", "Methodology of the proposed system", 7.0)

# ======================================================================= CHAPTER 3
chapter(3, "Requirement Analysis & Design")
section("3.1", "Hardware Requirements")
para("Training: Kaggle cloud notebook with one NVIDIA Tesla T4 GPU (16 GB). Development and demonstration: laptop with an Intel "
     "Core i5-12500H processor and 16 GB RAM. Deployment needs only a CPU (about 0.5 s per image).")
section("3.2", "Software Requirements")
para("Python 3.12, PyTorch, Ultralytics YOLO11 8.4.142 [13], OpenCV, NumPy, Gradio, Matplotlib, pytest; Git / GitHub; Windows 11.")
section("3.3", "System Architecture Diagram")
para("The data and detection pipeline (board images, preparation and balancing, training, evaluation, detection with box "
     "fusion) feeds the application side (defect analysis, BRI grading, value estimate, JSON report); both meet in the final "
     "wood-quality assessment per board (Fig. 3.1).")
figure("3.1", FIGS / "system_design_final.png", "System architecture", 10.5)
section("3.4", "UML Diagrams Relevant for the Proposed System")
figure("3.2", RFIGS / "dfd_level0.png", "Data-flow diagram, level 0", 9.0)
figure("3.3", RFIGS / "activity_diagram.png", "Activity diagram: grading a board in the application", 5.2)
section("3.5", "Proposed Algorithm and Techniques")
for lead, t in [
        ("Class balancing: ", "target boxes per class n_c* = √(n_c × n_max) (partial balance, the repeat-factor rule of LVIS [15]); real defect crops are pasted onto defect-free training boards inside the board mask [16]."),
        ("Weighted box fusion [17]: ", "overlapping boxes of several detectors are merged, b_f = Σ(w·c·b) / Σ(w·c); a box found by only one model gets lower confidence."),
        ("Board Recoverability Index: ", "s_i = w_c × conf_i × p_i with p_i = 1 − exp(−d_i / 250 px), d_i the distance to the board's side edge; DIS = Σ I / A_board; A_rec = A_board (1 − DIS); grade A / B / C / Reject from thresholds fitted on validation boards."),
        ("Statistical validation: ", "board-level bootstrap confidence intervals [20] and the exact Wilcoxon signed-rank test [21]; grade agreement by weighted kappa [19].")]:
    bullet(t, lead)

# ======================================================================= CHAPTER 4
chapter(4, "Implementation / Methodology / Proposed Approach")
section("4.1", "Description of Data Collection Process")
para("The images come from the industrial line-scan dataset of Kodytek et al. [12] (2800 × 1024 board images with bounding "
     "boxes). We split the images by physical board and used the four classes with the most data: Live_Knot, Dead_Knot, Resin "
     "and Crack. To address scarce rare-class data, the data was expanded to the complete release with the original test boards "
     "kept fixed. We verified the copy we trained on against the original archive (43,974 boxes identical), fixed label-format "
     "errors, removed zero-size boxes, generated grain-aware synthetic defects, and photographed wood surfaces on campus for "
     "real-world testing.")
bs, bf = R["balance"]["train_sqrt"], R["balance_full"]["train_sqrt"]
table("4.1", "Data at the 50% review and in the final system", [
    ["", "50% review", "Final"],
    ["Images / physical boards", "4,000 / 81", "20,276 / 407"],
    ["Boards train / val / test", "52 / 17 / 12", "280 / 76 / 51"],
    ["4-class training boxes (incl. synthetic)", f"{sum(bs.values()):,}", f"{sum(bf.values()):,}"],
    ["Crack training boxes", f"{bs['Crack']:,}", f"{bf['Crack']:,}"]], [7, 4, 4])
section("4.2", "Tech Stack")
para("Python 3.12; PyTorch and Ultralytics YOLO11 (fine-tuned from COCO weights); OpenCV and NumPy for image processing; Gradio "
     "for the web application; Kaggle notebooks with a Tesla T4 GPU for training; pytest for testing; Git / GitHub for version "
     "control.")
section("4.3", "Pseudocode")
para("", "Algorithm 1: weighted box fusion (one image)")
code(["FOR each class k:",
      "    sort the boxes of class k from all models by w_m * c",
      "    add each box to a cluster if IoU with its fused box > t_iou, else start a new cluster",
      "    FOR each cluster: b_f = sum(w*c*b) / sum(w*c)",
      "                      c_f = (sum(w*c) / sum(w)) * min(sum(w), W) / W",
      "RETURN fused boxes, confidences, classes"])
para("", "Algorithm 2: Board Recoverability Index (one board)")
code(["FOR each defect i: d_i = distance to the nearest board side edge",
      "    s_i = w_class * conf_i * (1 - exp(-d_i / 250))",
      "DIS = sum over board pixels of max s_i  /  board area",
      "recoverable % = 100 * (1 - DIS)",
      "grade = A if DIS < t1, B if DIS < t2, C if DIS < t3, else Reject"])

# ======================================================================= CHAPTER 5
chapter(5, "Testing")
section("5.1", "Black Box Testing")
section("5.1.1", "Tools and Techniques used", 3)
para("The application was tested through its web interface and through scripted calls with the Gradio client: upload an image "
     "and compare the returned defects and grade with the expected result.")
section("5.1.2", "Test Suite and Report", 3)
table("5.1", "Black-box test cases", [
    ["ID", "Input", "Expected", "Observed", "Status"],
    ["BB1", "Unseen board, no defects", "No boxes, Grade A", "No boxes, Grade A", "Pass"],
    ["BB2", "Unseen board, 3 cracks + 1 dead knot", "All defects, Grade C", "4 correct boxes, Grade C", "Pass"],
    ["BB3", "Unseen board, crack, resin, dead knots", "All defects, Grade Reject", "4 correct boxes, Grade Reject", "Pass"],
    ["BB4", "Non-wood photographs (8)", "No wood defects", "No boxes on 7 of 8", "Partial"],
    ["BB5", "Installation without model files", "Clear error message", "Error names the missing file", "Pass"],
    ["BB6", "Speed on laptop CPU", "Under 1 s per image", "About 0.46 s per image", "Pass"]], [1.2, 4.6, 3.6, 4.2, 1.4], size=9)
section("5.2", "White Box Testing")
section("5.2.1", "Tools and Techniques used", 3)
para("Unit tests in pytest check internal functions against known values, and the data pipeline contains assertions that stop a "
     "run when a check fails.")
section("5.2.2", "Test Suite and Report", 3)
table("5.2", "White-box tests", [
    ["ID", "Unit / check", "Condition", "Status"],
    ["WB1", "bri.board_report", "Guide's worked example: DIS 0.020860, grade B", "Pass"],
    ["WB2", "bri.grade", "Damage scores map to A / B / C / Reject", "Pass"],
    ["WB3", "math_model.wbf_image", "Agreeing boxes merge; single-model box gets lower confidence", "Pass"],
    ["WB4", "eval_capture.iou_matrix / match", "IoU values; one prediction per ground-truth box", "Pass"],
    ["WB5", "Split assertion", "Zero boards shared between train, val and test", "Pass"]], [1.2, 4.8, 7.6, 1.4], size=9)
section("5.3", "Test Coverage using Tool")
para("Statement coverage measured with pytest-cov: 9 unit tests pass, with 70% coverage of the grading module (bri.py), 57% of "
     "eval_capture.py and 34% of math_model.py, 50% overall.")

# ======================================================================= CHAPTER 6
chapter(6, "Results and Discussions")
para("All results are on boards never used for training or for any choice of settings. At the 50% review the detectors were "
     "tied at 63-65 mAP50 over 8 classes, limited by scarce and imbalanced data. The mathematical model raised test mAP50 on the "
     f"four main classes from 69.2 to 74.7, and the same recipe on the expanded data lifted the final detector to {ffo['map50']:.1f} "
     f"on the same boards and {fff['map50']:.1f} on 51 further boards.")
section("6.1", "Experimental Results")
table("6.1", "Results: 50% review vs final (test mAP50 / mAP50-95)", [
    ["Model", "Classes", "mAP50", "mAP50-95"],
    ["50% review: YOLO11m", "8", "63.0", "34.0"],
    ["50% review: YOLO11s", "8", "64.6", "33.4"],
    ["50% review YOLO11s, on the 4 classes", "4", "69.6", "32.9"],
    ["Mathematical model: fusion of four models", "4", "74.7", "36.7"],
    ["Final: fusion of two models, expanded data", "4", f"{ffo['map50']:.1f}", f"{ffo['map']:.1f}"],
    ["Final, on 51 further unseen boards", "4", f"{fff['map50']:.1f}", f"{fff['map']:.1f}"]], [7.5, 2, 2.5, 2.5], bold_last=False)
pi = bri["test_per_image"]
table("6.2", "Statistical and grading validation", [
    ["Measure", "Value"],
    ["Fusion vs best single model (mAP50, 95% CI)", f"+5.5 [{st4['map50_diff_ci'][0]:+.1f}, {st4['map50_diff_ci'][1]:+.1f}], Wilcoxon p = {st4['wilcoxon_p']:.3f}"],
    ["Final vs four-model fusion (mAP50, 95% CI)", f"{ffo['map50'] - FT['deployed_fusion']['orig']['map50']:+.1f} [{stfu['map50_diff_ci'][0]:+.1f}, {stfu['map50_diff_ci'][1]:+.1f}]"],
    ["BRI grade vs annotation-based grade", f"exact {pi['exact']*100:.1f}%, within one grade {pi['within_one']*100:.1f}%, weighted kappa {pi['qwk']:.2f}"]], [7, 8])
section("6.2", "Performance Analysis (Graphs / Metrics)")
figure("6.1", RFIGS / "per_class_comparison.png", "Per-class test mAP50: 50% review vs final detector", 9.0)
para("The largest gains are on the hardest defects: Resin from 60.4 to 76.6 and Crack from 53.0 to 62.2. CLAHE enhancement "
     "lowered accuracy in 5 of 6 imaging conditions; the final detector runs at about 0.5 s per image on a laptop CPU.")

# ======================================================================= CHAPTER 7
chapter(7, "Conclusion and Future Work")
section("7.1", "Objectives Achieved")
para("All four objectives were achieved: a board-level dataset expanded to 20,276 images, a reproducible detection framework, "
     f"recoverable-area grading validated with weighted kappa {pi['qwk']:.2f}, and a full comparison with a statistically "
     "validated mathematical model.")
section("7.2", "Contributions")
for t in ["A leakage-free, board-level evaluation of YOLO11 on industrial line-scan images.",
          "A mathematical model of class balancing and weighted box fusion with a significant gain (69.2 to 74.7 mAP50).",
          f"An expanded, engineered dataset lifting the final detector to {ffo['map50']:.1f} / {fff['map50']:.1f} mAP50.",
          "The Board Recoverability Index adapted to line-scan geometry, and a CPU web application."]:
    bullet(t)
section("7.3", "Limitations / Challenges / Drawbacks")
para("The original test set has 12 boards; severity weights and grade thresholds await expert calibration; only the four most "
     "frequent defect classes are detected; accuracy drops under poor lighting and on painted surfaces.")
section("7.4", "Future Enhancements")
para("Expert grading to calibrate the BRI, k-fold validation over boards, more rare-class data, segmentation masks for tighter "
     "defect areas, and the full CWB architecture.")


# ======================================================================= references
unnumbered("REFERENCES / BIBLIOGRAPHY")
REFS = [
    "Y. Fang, Y. Ma, S. Gao, and J. Chen, \u201cRecent advances in wood surface defect inspection using deep learning (2021\u20132025),\u201d BioResources, vol. 21, no. 3, 2026.",
    "J. Zheng, \u201cIEL-YOLO: A low-light robust wood defect detection method based on YOLOv11,\u201d in Proc. 2026 3rd Int. Conf. Electrical Technology and Automation Engineering (ETAE), 2026, pp. 818\u2013821, doi: 10.1109/ETAE69474.2026.11496073.",
    "J. Qu, Y. Pang, and Z. Wang, \u201cWD-SEG: A deep learning framework for delicate and accurate wood defect segmentation,\u201d BioResources, vol. 21, no. 2, pp. 2925\u20132947, 2026.",
    "J. Wang and S. Tang, \u201cA novel IWPT-VMD denoising method for enhancing air-coupled ultrasonic detection of wood defects,\u201d AIP Advances, vol. 16, no. 2, Art. no. 025217, 2026, doi: 10.1063/5.0313821.",
    "C. S. Erasmus, D. M. Drew, and M. J. Booysen, \u201cA low-cost wireless dendrometer and digital twin for precision forestry applications,\u201d Measurement, vol. 276, Art. no. 121442, 2026, doi: 10.1016/j.measurement.2026.121442.",
    "N. Perry, J. Schweier, L. G. Bont, S. K. Kushwaha, H. Peltola, K. Eyvindson, R. Astrup, M. Chapman, and C. Blattert, \u201cTowards precision forestry: A systematic review of optimisation methods for individual-tree decisions in forest management,\u201d Trees, Forests and People, vol. 24, Art. no. 101226, 2026, doi: 10.1016/j.tfp.2026.101226.",
    "E. Z. Ba\u015fkent, A. Bon\u010dina, and J. G. Borges, \u201cA review and conceptual framework for a new era of forest management planning: Integrating hybrid digital twin systems toward sustainable forest ecosystems,\u201d Ecosystem Services, vol. 79, Art. no. 101851, 2026, doi: 10.1016/j.ecoser.2026.101851.",
    "J. Tan, H. Zhang, J. Yang, Y. Liu, D. Zheng, and X. Liu, \u201cForestryBERT: A pre-trained language model with continual learning adapted to changing forestry text,\u201d Knowledge-Based Systems, vol. 320, Art. no. 113706, 2025, doi: 10.1016/j.knosys.2025.113706.",
    "T. I. Zohdi, \u201cA machine-learning enabled digital-twin framework for next generation precision agriculture and forestry,\u201d Computer Methods in Applied Mechanics and Engineering, vol. 431, Art. no. 117250, 2024, doi: 10.1016/j.cma.2024.117250.",
    "H. An, Z. Liang, M. Qin, Y. Huang, F. Xiong, and G. Zeng, \u201cWood defect detection based on the CWB-YOLOv8 algorithm,\u201d Journal of Wood Science, vol. 70, Art. no. 26, 2024, doi: 10.1186/s10086-024-02139-z.",
    "L. P. Yi, M. F. Akbar, M. N. A. Wahab, B. A. Rosdi, M. A. Fauthan, and N. H. M. M. Shrifan, \u201cThe prospect of artificial intelligence-based wood surface inspection: A review,\u201d IEEE Access, vol. 12, pp. 84706\u201384725, 2024, doi: 10.1109/ACCESS.2024.3412928.",
    "P. Kodytek, A. Bodzas, and P. Bilik, \u201cA large-scale image dataset of wood surface defects for automated vision-based quality control processes,\u201d F1000Research, vol. 10, p. 581, 2022, doi: 10.12688/f1000research.52903.2.",
    "G. Jocher and J. Qiu, \u201cUltralytics YOLO11,\u201d version 11.0.0, 2024. [Online]. Available: https://github.com/ultralytics/ultralytics",
    "Y. Cui, M. Jia, T.-Y. Lin, Y. Song, and S. Belongie, \u201cClass-balanced loss based on effective number of samples,\u201d in Proc. IEEE/CVF CVPR, 2019, pp. 9268\u20139277.",
    "A. Gupta, P. Doll\u00e1r, and R. Girshick, \u201cLVIS: A dataset for large vocabulary instance segmentation,\u201d in Proc. IEEE/CVF CVPR, 2019, pp. 5356\u20135364.",
    "D. Dwibedi, I. Misra, and M. Hebert, \u201cCut, paste and learn: Surprisingly easy synthesis for instance detection,\u201d in Proc. IEEE ICCV, 2017, pp. 1301\u20131310.",
    "R. Solovyev, W. Wang, and T. Gabruseva, \u201cWeighted boxes fusion: Ensembling boxes from different object detection models,\u201d Image and Vision Computing, vol. 107, Art. no. 104117, 2021.",
    "Z. Tong, Y. Chen, Z. Xu, and R. Yu, \u201cWise-IoU: Bounding box regression loss with dynamic focusing mechanism,\u201d arXiv:2301.10051, 2023.",
    "J. Cohen, \u201cWeighted kappa: Nominal scale agreement provision for scaled disagreement or partial credit,\u201d Psychological Bulletin, vol. 70, no. 4, pp. 213\u2013220, 1968.",
    "B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap. New York, NY, USA: Chapman & Hall, 1993.",
    "F. Wilcoxon, \u201cIndividual comparisons by ranking methods,\u201d Biometrics Bulletin, vol. 1, no. 6, pp. 80\u201383, 1945.",
    "K. Zuiderveld, \u201cContrast limited adaptive histogram equalization,\u201d in Graphics Gems IV, P. S. Heckbert, Ed. San Diego, CA, USA: Academic Press, 1994, pp. 474\u2013485."]
for i, r in enumerate(REFS, 1):
    p = para(r, f"[{i}] ", size=10.5, ls=1.0, indent=0.9)
    p.paragraph_format.first_line_indent = Cm(-0.9)


# ======================================================================= appendix
unnumbered("APPENDIX -1")
section("A.", "User Manual/Screenshots")
para("Run  python app.py  and open http://127.0.0.1:7860. Upload a board image and press 'Analyse image': the application shows "
     "the defects with confidence, a heatmap, the BRI grade, the recoverable area, a value estimate and a JSON report.")
figure("A.1", FIGS / "app_detect.png", "Application: detections on a board and confidence heatmap", 13)
section("B.", "Code Snippets")
para("", "Grade of the Board Recoverability Index (bri.py):", size=11)
code(source("bri.py", "grade"), size=9)
section("C.", "Tools used")
para("Python, PyTorch, Ultralytics YOLO11, OpenCV, NumPy, Gradio, Kaggle (Tesla T4), pytest, Git / GitHub.")

unnumbered("PUBLICATION DETAILS (Survey paper) / (Implementation paper)")
para("")
for t in ("PATENT (If Any)", "PROJECT PROPOSAL SUBMITTED (if Any)"):
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    p.paragraph_format.space_before = Pt(36)
    fmt(p.add_run(t), 16, bold=True)
    TOC.append((1, t, t))
unnumbered("PLAGIARISM REPORT (Plagiarism check using Turnitin)")
para("[Turnitin plagiarism report to be attached]", align=WD_ALIGN_PARAGRAPH.CENTER, italic=True)



# ---------------------------------------------------------------- contents and lists (page numbers filled by Word)
def rewrite_toc():
    body = doc.element.body
    paras = doc.paragraphs
    start = next(i for i, p in enumerate(paras) if p.text.strip() == "Table of Contents")
    end = next(i for i, p in enumerate(paras) if "PLAGIARISM REPORT" in p.text and i > start)
    template_p = paras[start + 2]          # " ABSTRACT ... iii" line
    anchor = paras[start + 1]
    front = [(" ABSTRACT", "iii"), (" ACKNOWLEDGMENT", "iv"), (" LIST OF TABLES", "vii"), (" LIST OF FIGURES", "viii"),
             (" LIST OF ABBREVIATIONS AND SYMBOLS", "ix")]
    for i in range(end, start + 1, -1):
        e = paras[i]._element; e.getparent().remove(e)
    entries = [(0, t, None, pg) for t, pg in front] + [(lvl, txt, key, None) for lvl, txt, key in TOC]
    prev = anchor._element
    from docx.text.paragraph import Paragraph
    for lvl, txt, key, pg in entries:
        p = OxmlElement("w:p")
        prev.addnext(p); prev = p
        q = Paragraph(p, anchor._parent)
        q.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        q.paragraph_format.left_indent = Cm({0: 0, 1: 0, 2: 0.8, 3: 1.6}[lvl]); q.paragraph_format.first_line_indent = Cm(0)
        q.paragraph_format.space_after = Pt(3); q.paragraph_format.line_spacing = 1.15
        fmt(q.add_run(txt), 12 if lvl <= 1 else 11, bold=lvl <= 1)
        fmt(q.add_run("\t" + (pg if pg else "{{PG:%s}}" % key)), 12 if lvl <= 1 else 11, bold=lvl <= 1)


def fill_list(header_text, items, prefix):
    t = next(t for t in doc.tables if t.rows[0].cells[0].text.strip().startswith(header_text))
    while len(t.rows) - 1 < len(items):
        t._tbl.append(copy.deepcopy(t.rows[-1]._tr))
    for row, (num, cap) in zip(t.rows[1:], items):
        for cell, val in zip(row.cells, (num, cap, "{{PG:%s %s:}}" % (prefix, num))):
            q = cell.paragraphs[0]
            for r in q.runs:
                r.text = ""
            fmt(q.add_run(val), 11)
    for row in t.rows[1 + len(items):]:
        t._tbl.remove(row._tr)


rewrite_toc()
for t in doc.tables:                           # drop empty spacer lines after the list tables (page breaks replace them)
    if t.rows[0].cells[0].text.strip().startswith(("Fig. No", "Table No", "Abbreviation")):
        nxt = t._tbl.getnext()
        while nxt is not None and nxt.tag == qn("w:p") and not "".join(x.text or "" for x in nxt.iter(qn("w:t"))).strip()                 and nxt.find(".//" + qn("w:sectPr")) is None:
            gone, nxt = nxt, nxt.getnext(); gone.getparent().remove(gone)
for p in doc.paragraphs:                       # each front-matter heading starts its own page, as in the template
    if p.text.strip() in ("ABSTRACT", "LIST OF FIGURES", "LIST OF TABLES", "LIST OF ABBREVIATIONS"):
        p.paragraph_format.page_break_before = True
fill_list("Fig. No", FIG_LIST, "Fig.")
fill_list("Table No", TAB_LIST, "Table")
ABBR = [("AI", "Artificial Intelligence"), ("BRI", "Board Recoverability Index"), ("CI", "Confidence Interval"),
        ("CLAHE", "Contrast Limited Adaptive Histogram Equalization"), ("COCO", "Common Objects in Context (pre-training dataset)"),
        ("CPU / GPU", "Central / Graphics Processing Unit"), ("DFD", "Data Flow Diagram"), ("DIS", "Damage Impact Score (BRI damage score)"),
        ("F1", "Harmonic mean of precision and recall"), ("IoU", "Intersection over Union"), ("JSON", "JavaScript Object Notation"),
        ("mAP50", "Mean Average Precision at IoU 0.5"), ("mAP50-95", "Mean Average Precision averaged over IoU 0.5 to 0.95"),
        ("NMS", "Non-Maximum Suppression"), ("P / R", "Precision / Recall"), ("QWK", "Quadratic Weighted Kappa"),
        ("UML", "Unified Modeling Language"), ("WBF", "Weighted Box Fusion"), ("YOLO", "You Only Look Once (object detector)")]
t = next(t for t in doc.tables if t.rows[0].cells[0].text.strip().startswith("Abbreviation"))
while len(t.rows) - 1 < len(ABBR):
    t._tbl.append(copy.deepcopy(t.rows[-1]._tr))
for row, (a, b) in zip(t.rows[1:], ABBR):
    for cell, val in zip(row.cells, (a, b)):
        q = cell.paragraphs[0]
        for r in q.runs:
            r.text = ""
        fmt(q.add_run(val), 11)

doc.save(str(OUT))
print("saved", OUT, len(FIG_LIST), "figures", len(TAB_LIST), "tables", len(TOC), "toc entries")
