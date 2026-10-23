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
OUT = Path(r"C:\Users\ASUS\Desktop\Major_Project\docs\Major_Project_Phase-I_Report_Draft.docx")
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


def para(text="", lead=None, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, italic=False, space_after=6, ls=1.5, indent=None):
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
    if not first:
        page_break()
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
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
    page_break()
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
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
chapter(1, "Introduction")
section("1.1", "Overview")
para("Manual inspection of wood depends on human graders; fatigue and inter-inspector variation make results inconsistent, "
     "and throughput limits line speed. Defects differ in severity: a live knot is cosmetic, a dead or missing knot weakens the "
     "board, and a crack may make a section unusable. Grading therefore needs the defect type and its location, not a yes/no answer.")
para("One-stage detectors of the YOLO family find and classify small objects in real time, which suits a conveyor-mounted "
     "line-scan camera. Our system returns every visible defect with class, position, size and confidence, grades each board "
     "with the Board Recoverability Index (A / B / C / Reject), and estimates its recoverable area and value.")
section("1.2", "Problem Statement")
para("Manual wood quality inspection is time-consuming and subjective, and existing AI approaches mostly stop at detecting "
     "defects without a leakage-free evaluation or a path to usable-area estimation; this project therefore aims to develop an "
     "AI-based computer-vision system that detects, classifies and localises visible surface defects on wooden boards, evaluates "
     "the detector on boards it has never seen, and uses the detections to estimate the recoverable portion of each board.")
section("1.3", "Objectives")
for lead, txt in [
        ("Objective 1: ", "Annotated dataset of 4,000 line-scan images, 8 classes, 9,053 boxes, split by physical board with zero "
                          "overlap, expanded to 20,276 images from 407 boards. Higher-resolution input (1280 px), CLAHE / denoising "
                          "and copy-paste balancing of rare classes implemented and evaluated."),
        ("Objective 2: ", "Deep-learning framework for detection and localisation: reproducible preparation, balancing, training "
                          "and evaluation scripts; 8-class YOLO11m / YOLO11s and 4-class YOLO11s models, each tested once on held-out boards."),
        ("Objective 3: ", "Recoverable-area estimation: the guide's Board Recoverability Index gives a damage score, recoverable "
                          "area and grade per board, validated against annotation-based grades; market value estimated from grade."),
        ("Objective 4: ", "Comparison with P, R, F1, mAP50, mAP50-95 and inference time at identical settings, plus a mathematical "
                          "model: class-balancing rule, weighted box fusion, Wise-IoU loss, per-class thresholds and statistical validation.")]:
    bullet(txt, lead)
section("1.4", "Motivation")
para("Grading by eye is subjective, slow and hard to audit, and the value of a board depends on where its defects are, not only "
     "on whether it has any. An automatic system that finds every defect, measures how much of the board remains usable and "
     "assigns a consistent grade can raise throughput, reduce disagreement between graders and support pricing decisions. "
     "Published work mostly reports defect detection alone, often on splits where images of the same board appear in both "
     "training and test sets; our motivation is a system that is evaluated on boards it has never seen and that goes all the way "
     "from an image to a grade and a value estimate.")
section("1.5", "Outline of the thesis")
for lead, txt in [("Chapter 2 ", "reviews existing systems, their limitations, the gaps and our research methodology."),
                  ("Chapter 3 ", "gives the hardware and software requirements, the system architecture, the UML / DFD diagrams and the proposed algorithms."),
                  ("Chapter 4 ", "describes the data collection process, the technology stack and the pseudocode of the main algorithms."),
                  ("Chapter 5 ", "covers black-box and white-box testing and test coverage."),
                  ("Chapter 6 ", "presents the experimental results and the performance analysis."),
                  ("Chapter 7 ", "concludes with the objectives achieved, contributions, limitations and future enhancements.")]:
    bullet(txt, lead)

# ======================================================================= CHAPTER 2
chapter(2, "Literature Survey")
section("2.1", "Review of Existing Systems")
para("Recent work shows that deep learning works for wood defects but has gaps. Table 2.1 summarises the reviewed papers.")
table("2.1", "Summary of the literature survey", [
    ["Author(s), year", "Title", "Technology", "Result", "Drawbacks / issues"],
    ["Y. Fang, Y. Ma, S. Gao, J. Chen, 2026 [1]", "Recent Advances in Wood Surface Defect Inspection using Deep Learning", "Review of deep-learning inspection", "Comprehensive review; supports automated wood-defect inspection", "Small datasets, poor generalisation and real-time deployment challenges"],
    ["J. Zheng, 2026 [2]", "IEL-YOLO: A Low-Light Robust Wood Defect Detection Method Based on YOLOv11", "Image enhancement + YOLOv11", "Improves defect visibility in low light; handles complex wood textures", "Generalisation challenges; no multimodal integration"],
    ["J. Qu, Y. Pang, Z. Wang, 2026 [3]", "WD-SEG: A Deep Learning Framework for Delicate and Accurate Wood Defect Segmentation", "AFN + TFN + ICO + deep learning", "Accurate segmentation; handles low contrast, reduces background interference", "Noise sensitivity, feature ambiguity, real-time deployment challenges"],
    ["J. Wang, S. Tang, 2026 [4]", "A Novel IWPT-VMD Denoising Method for Enhancing Air-Coupled Ultrasonic Detection of Wood Defects", "IWPT + VMD + ultrasonic signal processing", "Reduces noise; improves signal quality and defect detection", "Requires ultrasonic signals; limited AI integration; no multimodal fusion"],
    ["C. S. Erasmus, D. Drew, M. J. Booysen, 2026 [5]", "A Low-Cost Wireless Dendrometer and Digital Twin for Precision Forestry Applications", "IoT + LoRaWAN + digital twin", "Low-cost, scalable continuous monitoring", "No wood-quality assessment; no harvest optimisation; limited data fusion"],
    ["N. Perry et al., 2026 [6]", "Towards Precision Forestry: A Systematic Review of Optimisation Methods for Individual-Tree Decisions in Forest Management", "Heuristics, mathematical programming, machine learning", "Supports optimal forest-management decisions", "Limited real-world implementation; disturbance risks not fully integrated"],
    ["E. Z. Ba\u015fkent, A. Bon\u010dina, J. G. Borges, 2026 [7]", "A Review and Conceptual Framework for a New Era of Forest Management Planning", "Digital twin, monitoring, simulation, forecasting", "Adaptive forest planning integrating monitoring with forecasting", "Limited ML implementation; no wood-quality assessment"],
    ["J. Tan et al., 2025 [8]", "ForestryBERT: Continual Learning Adapted to Forestry Text", "BERT + NLP + continual learning", "Domain-specific forestry knowledge management", "Catastrophic forgetting; no defect-detection component"]],
    [3.0, 3.6, 2.6, 3.4, 3.4], size=8.5)
para("The fusion of detector outputs follows weighted box fusion [17]; the closest detection architecture to our synopsis is "
     "CWB-YOLOv8 [10], whose Wise-IoU loss [18] we also evaluate, and AI-based wood surface inspection is reviewed in [11].")
section("2.2", "Limitations of Existing Systems")
for t in ["Small datasets and poor generalisation to new boards, often measured on image-level splits in which the same board appears in training and test data.",
          "Real-time deployment challenges for heavy segmentation models; sensitivity to noise and low contrast.",
          "Ultrasonic methods need special sensors and offer limited AI integration.",
          "Forestry digital-twin, optimisation and language-model systems do not assess wood quality from images.",
          "Detection is rarely connected to a usable-area estimate, a grade or a value."]:
    bullet(t)
section("2.3", "Gap Identification and Analysis")
para("The common gaps are small datasets, weak generalisation to new boards, and no step from detection to a usable-area "
     "estimate. None of the forestry-pipeline papers assesses wood quality from images or connects defects to recoverable value; "
     "that is the gap at the end of the chain that our system targets. We address it with (i) a leakage-free, board-level "
     "evaluation, (ii) a mathematical model of class balancing and weighted box fusion whose gains are tested statistically, and "
     "(iii) the Board Recoverability Index, which converts detections into a damage score, a recoverable area and a grade.")
section("2.4", "Research Methodology for the Proposed System")
para("Figure 2.1 shows the methodology as completed. Images are cleaned and split by board; input is handled at high resolution "
     "with grain-safe augmentation and class balancing; YOLO11 models detect defects; the mathematical model fuses detectors and "
     "validates every gain statistically. The detections then go two ways: defect analysis and evaluation on one side, and "
     "recoverability grading and value estimation on the other, ending in the application and the final assessment.")
figure("2.1", FIGS / "methodology_final.png", "Methodology of the proposed system", 13)
para("Every choice is made on validation boards; each test model is evaluated exactly once; an enhancement study (CLAHE, "
     "denoise, sharpen) is run on validation.")

# ======================================================================= CHAPTER 3
chapter(3, "Requirement Analysis & Design")
section("3.1", "Hardware Requirements")
table("3.1", "Hardware requirements", [
    ["Purpose", "Hardware used"],
    ["Model training", "Kaggle cloud notebook with one NVIDIA Tesla T4 GPU (16 GB); about 1.4-2.4 GPU-hours per YOLO11s run on 4,000 images, 3.2 h (1024 px) and 4.3 h (1280 px) on the expanded data"],
    ["Data preparation", "Kaggle CPU sessions"],
    ["Development and demonstration", "ASUS Vivobook laptop: Intel Core i5-12500H, 16 GB RAM, Intel Iris Xe graphics, Windows 11"],
    ["Deployment (inference)", "Laptop CPU only; no GPU required (about 0.5 s per image)"]], [4.5, 11.5])
section("3.2", "Software Requirements")
table("3.2", "Software requirements", [
    ["Software", "Version / use"],
    ["Python", "3.12"],
    ["PyTorch", "2.x (CUDA on Kaggle, CPU build on the laptop)"],
    ["Ultralytics YOLO11 [13]", "8.4.142: training, validation, inference"],
    ["OpenCV, NumPy", "image processing, board mask, copy-paste synthesis, enhancement study"],
    ["Gradio", "web application"],
    ["Matplotlib", "figures and charts"],
    ["pytest, pytest-cov", "unit tests and coverage"],
    ["Kaggle API, Git / GitHub", "remote training runs, version control"]], [5.0, 11.0])
section("3.3", "System Architecture Diagram")
para("The data and detection pipeline (right) covers board images, preparation and balancing scripts, training on a GPU, "
     "evaluation with statistics, and detection output with box fusion. The defect analysis and application side (left) is what "
     "the user gets: the web application, defect analysis, recoverability with the BRI, the value estimate and a JSON report. "
     "Both meet in the final wood-quality assessment per board.")
figure("3.1", FIGS / "system_design_final.png", "System architecture", 14)
section("3.4", "UML Diagrams Relevant for the Proposed System")
para("Figure 3.2 is the context-level data-flow diagram, Figure 3.3 decomposes the system into its six processes and three data "
     "stores, and Figure 3.4 is the activity diagram of grading one board in the application.")
figure("3.2", RFIGS / "dfd_level0.png", "Data-flow diagram, level 0", 14)
figure("3.3", RFIGS / "dfd_level1.png", "Data-flow diagram, level 1", 15.5)
figure("3.4", RFIGS / "activity_diagram.png", "Activity diagram: grading a board in the application", 9)
section("3.5", "Proposed Algorithm and Techniques")
para("", "1. Class balancing. ")
doc.paragraphs[-1].add_run("")
para("Target boxes per class n_c* = n_max (full balance) or n_c* = \u221a(n_c \u00d7 n_max) (partial balance, the repeat-factor rule "
     "of LVIS [15], same idea as the effective number of samples [14]). Real defect crops are cut from training boards and pasted "
     "onto defect-free training boards (2-5 per image), only inside the board mask, with no rotation and with Poisson or feathered "
     "blending [16]; training split only.")
para("", "2. Weighted box fusion [17]. ")
para("Boxes of the same class from several detectors that overlap are merged: b_f = \u03a3(w\u00b7c\u00b7b) / \u03a3(w\u00b7c) and "
     "c_f = (\u03a3 w\u00b7c / \u03a3 w) \u00d7 min(\u03a3 w, W) / W, where b is a box, c its confidence, w the weight of its model and W "
     "the sum of model weights. Fusion averages the boxes weighted by confidence and lowers the confidence of boxes only one model finds.")
para("", "3. Wise-IoU v3 [18] and per-class thresholds. ")
para("L = r \u00d7 exp(d\u00b2 / (W_g\u00b2 + H_g\u00b2)) \u00d7 (1 \u2212 IoU), r = \u03b2 / (\u03b4 \u00b7 \u03b1^(\u03b2\u2212\u03b4)); per-class "
     "thresholds t_c = argmax_t F1_c(t) on validation. Both were evaluated and not adopted.")
para("", "4. Board Recoverability Index (BRI). ")
for t in ["Union of defects: A_def = |R_1 \u222a ... \u222a R_n| (overlaps counted once).",
          "Severity: w_c: Crack 1.00, Dead_Knot 0.60, Live_Knot 0.40, Resin 0.30 (guide's placeholders).",
          "Position: p_i = 1 \u2212 exp(\u2212d_i / 250 px), d_i = distance to the board's side edge (our change).",
          "Influence: s_i = w_c \u00d7 conf_i \u00d7 p_i.",
          "Damage: I(x, y) = max_i s_i; DIS = \u03a3 I / A_board (board pixels, our change); A_rec = A_board (1 \u2212 DIS).",
          "Grade: A / B / C / Reject from thresholds fitted on validation boards with the guide's weighted-kappa calibration.",
          "Check: the guide's worked example is reproduced exactly (DIS 0.020860, grade B)."]:
    bullet(t)
figure("3.5", FIGS / "bri_geometry.png", "Damage is measured from the board edge, not the image border", 13)
para("", "5. Statistical validation. ")
para("Board-level bootstrap: the test boards are resampled 1,000 times with replacement, so the interval reflects board-to-board "
     "variation [20]; exact Wilcoxon signed-rank test on per-board AP50 differences [21]; agreement of grades by quadratic "
     "weighted kappa [19].")

# ======================================================================= CHAPTER 4
chapter(4, "Implementation / Methodology / Proposed Approach")
section("4.1", "Description of Data Collection Process")
para("The images come from the industrial line-scan dataset of Kodytek et al. [12]: 2800 \u00d7 1024 board images with bounding-box "
     "annotations. Up to the 50% review we used 4,000 images from 81 physical boards with 8 classes (Quartzity, Live_Knot, "
     "Marrow, Resin, Dead_Knot, Knot_with_crack, Knot_missing, Crack) and 9,053 boxes, split by physical board into 52 / 17 / 12 "
     "boards for training, validation and test with zero overlap. The final detector uses the four classes with the most data: "
     "Live_Knot, Dead_Knot, Resin and Crack.")
para("Rare classes limited accuracy at mid-term, so the data was expanded to the complete industrial release of 20,276 images "
     "from 407 boards, keeping the original test boards fixed (280 / 76 / 51 boards). Our data work: we verified the copy we "
     "trained on against the original archive (43,974 boxes identical), fixed label-format errors, removed zero-size boxes, "
     "generated grain-aware synthetic defects inside the board mask, and photographed wood surfaces on campus for real-world testing.")
bs, bf = R["balance"]["train_sqrt"], R["balance_full"]["train_sqrt"]
table("4.1", "Data at the 50% review and in the final system", [
    ["", "50% review", "Final"],
    ["Images / physical boards", "4,000 / 81", "20,276 / 407 (complete industrial release [12])"],
    ["Boards train / val / test", "52 / 17 / 12", "280 / 76 / 51 (original test boards kept fixed)"],
    ["4-class training boxes incl. synthetic copy-paste data", f"{sum(bs.values()):,}", f"{sum(bf.values()):,}"],
    ["Crack training boxes (rarest, most severe)", f"{bs['Crack']:,}", f"{bf['Crack']:,}"]], [6.5, 3.5, 6.0])
bal = R["balance"]
table("4.2", "Class balancing of the 4-class training set (4,000-image stage)", [
    ["Class", "Training boxes", "Full balance (1:1)", "Partial balance \u221a(n_c n_max)"]] +
    [[c, str(bal["train_plain"][c]), str(bal["train_full"][c]), str(bal["train_sqrt"][c])] for c in ["Live_Knot", "Dead_Knot", "Resin", "Crack"]] +
    [["Imbalance max : min", "9.5 : 1", "1.06 : 1", "3.1 : 1"]], [4, 3.5, 3.5, 4.5])
prev = sorted((ROOT / "runs_log" / "run4_4cls_kaggle_v1" / "previews").glob("train_sqrt_*.jpg"))
if prev:
    figure("4.1", prev[0], "Synthetic training image: real defect crops pasted inside the board", 14)
section("4.2", "Tech Stack")
table("4.3", "Technology stack", [
    ["Layer", "Tools"],
    ["Language", "Python 3.12"],
    ["Deep learning", "PyTorch, Ultralytics YOLO11 (YOLO11s, YOLO11m), fine-tuned from COCO weights"],
    ["Image processing", "OpenCV, NumPy (board mask, copy-paste synthesis, CLAHE / denoise / sharpen)"],
    ["Mathematical model", "weighted box fusion, BRI, bootstrap and exact Wilcoxon test implemented in Python"],
    ["Training infrastructure", "Kaggle notebooks with a Tesla T4 GPU, Kaggle API"],
    ["Application", "Gradio web interface, JSON reports"],
    ["Testing", "pytest, pytest-cov, Gradio client for scripted black-box tests"],
    ["Version control", "Git, GitHub"]], [4.5, 11.5])
para("Training configuration: COCO-pretrained weights, rectangular input at 1024 px (1024 \u00d7 384) and 1280 px, AdamW with "
     "lr0 0.001, cosine schedule, batch 32, seed 42, grain-safe augmentation (no rotation, no vertical flip); best.pt chosen on "
     "validation; each test model evaluated once (confidence 0.001, NMS IoU 0.6).")
section("4.3", "Pseudocode")
para("", "Algorithm 1: board-level split and partial class balancing")
code(["INPUT: images with boxes, board id = first 4 digits of the file name",
      "group images by board; assign boards to train / val / test (70 / 18 / 12), seed 42",
      "ASSERT no board appears in two splits",
      "FOR each class c: n_c = number of training boxes; n_max = max_c n_c",
      "    target_c = round(sqrt(n_c * n_max))",
      "cut isolated defect crops from training boards",
      "WHILE some class c has fewer than target_c boxes:",
      "    pick a defect-free training board and 2-5 crops of under-filled classes",
      "    paste each crop inside the board mask, along the grain (Poisson or feathered blend)",
      "    write the new image and its boxes to the training set only"])
para("", "Algorithm 2: weighted box fusion of K detectors (one image)")
code(["FOR each class k:",
      "    items = all boxes of class k from all models, with weight w_m and confidence c",
      "    sort items by w_m * c, descending",
      "    FOR each item: if IoU(item, a cluster's fused box) > t_iou add it to that cluster, else start a new cluster",
      "    FOR each cluster: b_f = sum(w*c*b) / sum(w*c)",
      "                      c_f = (sum(w*c) / sum(w)) * min(sum(w), W) / W",
      "RETURN fused boxes, confidences, classes"])
para("", "Algorithm 3: Board Recoverability Index of one board")
code(["board = wood region of the image (board mask, left and right edges)",
      "FOR each detected defect i: d_i = distance from box centre to the nearest board side edge",
      "    p_i = 1 - exp(-d_i / 250);  s_i = w_class * conf_i * p_i",
      "I(x, y) = max of s_i over the boxes covering pixel (x, y)",
      "DIS = sum(I) / board area;  recoverable % = 100 * (1 - DIS)",
      "grade = A if DIS < t1, B if DIS < t2, C if DIS < t3, else Reject"])
para("", "Algorithm 4: grading an uploaded image in the application")
code(["load the 1024-px and 1280-px YOLO11s models once",
      "FOR an uploaded image: run both models (conf 0.25, NMS IoU 0.6)",
      "fuse their boxes (Algorithm 2, IoU 0.65, equal weights)",
      "compute BRI grade (Algorithm 3) with the thresholds fitted on validation",
      "value = volume * recoverable share * grade-A price * grade factor",
      "show boxes, heatmap, grade, per-class table; write JSON report"])

# ======================================================================= CHAPTER 5
chapter(5, "Testing")
section("5.1", "Black Box Testing")
section("5.1.1", "Tools and Techniques used", 3)
para("The application was tested from the outside, through its web interface and through scripted calls to the same interface "
     "with the Gradio client: upload an image, choose the model and settings, and compare the returned defects, grade and report "
     "with the expected result. Inputs cover clean boards, each defect class, each grade, non-wood images and a fresh installation.")
section("5.1.2", "Test Suite and Report", 3)
table("5.1", "Black-box test cases (final detector, confidence 0.25)", [
    ["ID", "Input", "Expected result", "Observed result", "Status"],
    ["BB1", "Unseen test board with no defects", "No boxes, Grade A", "No boxes, Grade A", "Pass"],
    ["BB2", "Unseen board with 3 cracks and 1 dead knot", "All 4 defects, grade as annotation (C)", "4 correct boxes, Grade C", "Pass"],
    ["BB3", "Unseen board with 6 defects of 3 types", "All 6 defects, Grade C", "6 correct boxes, Grade C", "Pass"],
    ["BB4", "Unseen board with crack, resin and dead knots", "All defects, Grade Reject", "4 correct boxes, Grade Reject, cut-offs shown", "Pass"],
    ["BB5", "Test-boards tab: annotated board", "Annotator's and model's boxes and grades side by side", "Both shown", "Pass"],
    ["BB6", "Eight non-wood photographs", "No wood defects", "No boxes on 7 of 8; Grade A shown (no wood check)", "Partial"],
    ["BB7", "Fresh installation without model files", "Clear error naming the missing file", "Error message with the missing file path", "Pass"],
    ["BB8", "Same image through the public link", "Same result as locally", "Identical grade and damage score", "Pass"],
    ["BB9", "Report download", "JSON report with detections and grade", "JSON file produced", "Pass"],
    ["BB10", "Speed on the laptop CPU", "Under 1 s per image", "About 0.46 s per image (mean of 11 images)", "Pass"]],
    [1.2, 3.8, 3.8, 4.6, 1.4], size=9)
section("5.2", "White Box Testing")
section("5.2.1", "Tools and Techniques used", 3)
para("Internal functions were tested with unit tests written in pytest against known values: the guide's worked example for "
     "the BRI, hand-computed IoU and fusion cases, grade thresholds and the statistical test. In addition, the data and training "
     "pipelines contain assertions that stop a run when a check fails (board overlap, image and box counts), and a CPU smoke test "
     "runs the complete training pipeline on a small slice before any GPU run.")
section("5.2.2", "Test Suite and Report", 3)
table("5.2", "White-box tests", [
    ["ID", "Unit / check", "Condition tested", "Status"],
    ["WB1", "bri.board_report", "Guide's worked example: DIS 0.020860, grade B, union 102,800 px", "Pass"],
    ["WB2", "bri.board_report", "Board without defects: DIS 0, Grade A, 100% recoverable", "Pass"],
    ["WB3", "bri.grade", "Damage scores map to A / B / C / Reject at the fitted cut-offs", "Pass"],
    ["WB4", "bri.position_penalty", "Penalty grows with distance from the board edge, within [0, 1]", "Pass"],
    ["WB5", "bri.quadratic_weighted_kappa", "Identical gradings give 1; reversed gradings give a low value", "Pass"],
    ["WB6", "eval_capture.iou_matrix", "Identical boxes IoU 1, disjoint boxes IoU 0", "Pass"],
    ["WB7", "math_model.wbf_image", "Agreeing boxes merge; a box from one model only gets lower confidence", "Pass"],
    ["WB8", "eval_capture.match", "A ground-truth box is matched by at most one prediction", "Pass"],
    ["WB9", "eval_capture.wilcoxon_exact", "Twelve positive differences give p < 0.01", "Pass"],
    ["WB10", "Split assertion (pipeline)", "Zero boards shared between train, val and test", "Pass"],
    ["WB11", "Data assertions (pipeline)", "20,276 images; original val / test: 714 / 469 images with unchanged box counts", "Pass"]],
    [1.2, 4.0, 8.4, 1.4], size=9)
section("5.3", "Test Coverage using Tool")
para("Statement coverage of the unit tests was measured with pytest-cov (coverage.py). All 9 unit tests pass. Coverage is "
     "highest for the grading module; the remaining statements are mostly command-line and file-handling code exercised by the "
     "pipeline runs rather than by unit tests.")
table("5.3", "Statement coverage of the unit tests (pytest-cov)", [
    ["Module", "Statements", "Missed", "Coverage"],
    ["bri.py (Board Recoverability Index)", "74", "22", "70%"],
    ["eval_capture.py (matching, scoring, statistics)", "96", "41", "57%"],
    ["math_model.py (fusion, thresholds, tests)", "134", "88", "34%"],
    ["Total", "304", "151", "50%"]], [7, 2.5, 2.5, 2.5], bold_last=True)

# ======================================================================= CHAPTER 6
chapter(6, "Results and Discussions")
para("Every result in this chapter is measured on boards never used for training, validation or any choice of settings. At the "
     "50% review the detectors were tied at 63-65 mAP50 over 8 classes, so model size was not the bottleneck; scarce and "
     "imbalanced data was. After the review, the mathematical model raised test mAP50 on the four main classes from 69.2 to "
     f"74.7, a statistically significant gain, and the same recipe on the expanded data lifted the final detector to "
     f"{ffo['map50']:.1f} on the same boards and {fff['map50']:.1f} on 51 further boards. Single changes such as balancing alone, "
     "1280-px input, Wise-IoU or per-class thresholds were within the noise of a 12-board test set; their value came from the "
     "diversity they gave to the fused models.")
section("6.1", "Experimental Results")
table("6.1", "Results at the 50% review (8 classes, 12 unseen test boards)", [
    ["Aspect", "YOLO11m", "YOLO11s", "m - s"],
    ["mAP50", "63.0", "64.6", "-1.6"], ["mAP50-95", "34.0", "33.4", "+0.6"], ["Precision", "63.4", "71.0", "-7.6"],
    ["Recall", "66.2", "64.1", "+2.1"], ["F1", "64.7", "67.4", "-2.7"], ["Crack mAP50 / recall", "57.7 / 72.6", "53.0 / 63.2", "+4.7 / +9.4"],
    ["Inference, T4", "33.2 ms (30 FPS)", "11.7 ms (86 FPS)", "2.8x slower"], ["Training cost", "2.64 h", "1.43 h", "1.8x"],
    ["Parameters", "20.0 M", "9.4 M", "2.1x"]], [5, 3.5, 3.5, 3.5])
table("6.2", "Results: 50% review vs final (test, 12 unseen boards)", [
    ["Model", "Classes", "P", "R", "F1", "mAP50", "mAP50-95"],
    ["50% review: YOLO11m", "8", "63.4", "66.2", "64.7", "63.0", "34.0"],
    ["50% review: YOLO11s", "8", "71.0", "64.1", "67.4", "64.6", "33.4"],
    ["50% review YOLO11s, scored on the 4 classes", "4", "-", "-", "-", "69.6", "32.9"],
    ["YOLO11s 4 classes, partial balance", "4", "74.8", "69.4", "72.0", "69.2", "33.1"],
    ["Mathematical model: fusion of four 4-class models", "4", "-", "-", "-", "74.7", "36.7"],
    ["Final: fusion of two models, expanded data", "4", "-", "-", "-", f"{ffo['map50']:.1f}", f"{ffo['map']:.1f}"],
    ["Final, on 51 further unseen boards", "4", "-", "-", "-", f"{fff['map50']:.1f}", f"{fff['map']:.1f}"]],
    [6.6, 1.5, 1.4, 1.4, 1.4, 1.6, 2.0], size=9.5)
sd = R["test4"]["sqrt_1024"]
table("6.3", "Per-class test mAP50 (12 unseen boards)", [
    ["Class", "Test boxes", "50% review (YOLO11s)", "Best single 4-class", "Final detector"]] +
    [[c, str(n), f"{T8['YOLO11s'][c][3]:.1f}", f"{sd[c][3]:.1f}", f"{ffo['ap50'][c]:.1f}"]
     for c, n in (("Dead_Knot", 343), ("Live_Knot", 406), ("Resin", 69), ("Crack", 95))] +
    [["ALL (4 classes)", "913", "69.6", f"{sd['ALL'][3]:.1f}", f"{ffo['map50']:.1f}"]], [3.5, 2.5, 3.5, 3.5, 3.0], bold_last=True)
V = FU["val_orig"]
def mm(x):
    return f"{x['map50']:.1f} / {x['map']:.1f}"
table("6.4", "Effect of the data expansion (mAP50 / mAP50-95)", [
    ["System", "Val, 714 original images", "Test, 469 original images", "Test, 51 further boards (2,488)"],
    ["Four-model fusion (before expansion)", "{:.1f} / {:.1f}".format(*V["deployed_fusion"]), mm(FT["deployed_fusion"]["orig"]), "-"],
    ["YOLO11s expanded data, 1024 px", "{:.1f} / {:.1f}".format(*V["full_1024"]), mm(FT["full_1024"]["orig"]), mm(FT["full_1024"]["full"])],
    ["YOLO11s expanded data, 1280 px", "{:.1f} / {:.1f}".format(*V["full_1280"]), mm(FT["full_1280"]["orig"]), mm(FT["full_1280"]["full"])],
    ["Fusion of the two (final detector)", "{:.1f} / {:.1f}".format(*V["full_fusion"]), mm(ffo), mm(fff)]],
    [5.5, 3.4, 3.4, 3.7], size=9.5, bold_last=True)
table("6.5", "How we arrived at the final model", [
    ["Step (YOLO11s unless stated)", "Val mAP50", "Test mAP50", "Decision and reason"],
    ["8 classes, YOLO11m vs YOLO11s (50% review)", "65.7 / 65.3", "63.0 / 64.6", "Tied: capacity is not the bottleneck"],
    ["Fusion of YOLO11m + YOLO11s, 8 classes", "-", "65.7", "mAP50-95 +2.4 (significant), still limited by rare classes"],
    ["4 main classes, no balancing", "73.1", "71.7", "Fair baseline for 4 classes: 69.6 (8-class model)"],
    ["+ full balance 1:1", "71.9", "not tested", "Worse on validation: cracks pasted up to 17 times"],
    ["+ partial balance \u221a(n_c n_max)", "75.3", "69.2", "Best single on validation; kept as fusion member"],
    ["+ 1280 px input", "74.6", "71.6", "Not better alone; adds diversity for fusion"],
    ["+ Wise-IoU v3 loss / 3 seeds", "74.6", "not tested", "Within seed spread 0.8: not adopted"],
    ["Fusion of four 4-class models", "78.1", "74.7", "Significant gain: adopted"],
    ["Same recipe on the expanded data, fused (final)", "80.2", f"{ffo['map50']:.1f}", "Rule 78.1 on val beaten: final, 2 models"]],
    [5.2, 2.0, 2.0, 6.8], size=9, bold_last=True)
section("6.2", "Performance Analysis (Graphs / Metrics)")
figure("6.1", RFIGS / "per_class_comparison.png", "Per-class test mAP50: 50% review vs final detector", 13)
para("The largest gains are on the hardest defects: Resin from 60.4 to 76.6 and Crack from 53.0 to 62.2; Dead_Knot was already "
     "strong and stays near 90. On the 51 further boards Crack reaches 67.4.")
figure("6.2", ROOT / "runs_log" / "run7_full4_1024_v2" / "results.png", "Training and validation curves of the final 1024-px model", 15.5)
table("6.6", "Statistical validation (test, 12 boards)", [
    ["Comparison", "mAP50 diff", "95% CI (board bootstrap)", "Boards better / worse", "Wilcoxon p"],
    ["Final detector (expanded data) - four-model fusion", f"{ffo['map50'] - FT['deployed_fusion']['orig']['map50']:+.1f}", f"[{stfu['map50_diff_ci'][0]:+.1f}, {stfu['map50_diff_ci'][1]:+.1f}]", f"{stfu['boards_better']} / {stfu['boards_worse']}", f"{stfu['wilcoxon_p']:.2f}"],
    ["Four-model fusion - best single 4-class model", "+5.5", f"[{st4['map50_diff_ci'][0]:+.1f}, {st4['map50_diff_ci'][1]:+.1f}]", f"{st4['boards_better']} / {st4['boards_worse']}", f"{st4['wilcoxon_p']:.3f}"],
    ["Fusion (YOLO11m + YOLO11s) - YOLO11s, mAP50", "+1.1", "[-0.5, +2.7]", "7 / 5", "0.52"],
    ["Fusion - YOLO11s, mAP50-95", "+2.4", "[+1.6, +3.2]", "-", "-"],
    ["Partial balance - no balancing (4 cls)", "-2.6", "[-4.6, +0.3]", "4 / 8", "0.57"]],
    [6.0, 2.0, 3.2, 2.6, 2.2], size=9)
para("Only the fusion and data-expansion gains have intervals that exclude zero; the four-model fusion is also significant by the "
     "Wilcoxon test. Repeating the final setup with seeds 42 / 1 / 2 gives validation mAP50 75.3 / 74.8 / 75.6 (spread 0.8).")
pi, pb = bri["test_per_image"], bri["test_per_board"]
table("6.7", "Grading validation (BRI) against annotation-based grades", [
    ["Agreement", "Per image (469)", "Per board (12)"],
    ["Exact grade", f"{pi['exact']*100:.1f} %", f"{pb['exact']*100:.1f} %"],
    ["Within one grade", f"{pi['within_one']*100:.1f} %", f"{pb['within_one']*100:.1f} %"],
    ["Quadratic weighted kappa [19]", f"{pi['qwk']:.2f}", f"{pb['qwk']:.2f}"],
    ["Spearman correlation of damage scores", f"{pi['spearman']:.2f}", f"{pb['spearman']:.2f}"],
    ["Mean abs. error, recoverable area", f"{pi['mae_recoverable_pct']:.2f} pts", f"{pb['mae_recoverable_pct']:.2f} pts"]], [6.5, 4, 4])
E = ["raw", "clahe", "denoise", "sharpen"]
table("6.8", "Image enhancement study (validation mAP50)", [["Condition", "Raw", "CLAHE [22]", "Denoise", "Sharpen"]] +
      [[lab] + [p1(enh["table"][c][e]["map50"]) for e in E] for c, lab in
       [("normal", "Normal"), ("low_light", "Low light"), ("overexposed", "Over-exposed"), ("blur", "Blur"), ("noise", "Noise"), ("low_contrast", "Low contrast")]],
      [4, 2.6, 2.6, 2.6, 2.6])
para("CLAHE lowers mAP50 significantly in 5 of 6 conditions (Wilcoxon p \u2264 0.006), so hypothesis H1 is rejected for raw images; "
     "denoising helps only on noisy images (+3.2 to +7.2 mAP50, 95% CI); low light costs about 25 points, so controlled lighting is "
     "the main requirement for deployment. The final detector runs at about 0.5 s per image on a laptop CPU.")

# ======================================================================= CHAPTER 7
chapter(7, "Conclusion and Future Work")
section("7.1", "Objectives Achieved")
for t in ["Objective 1 (achieved): dataset split by physical board, expanded from 4,000 to 20,276 images from 407 boards; higher resolution, enhancement and class balancing evaluated.",
          "Objective 2 (achieved): reproducible detection framework with 8-class and 4-class models, each tested once on held-out boards.",
          f"Objective 3 (achieved): recoverable-area estimation with the Board Recoverability Index, validated with weighted kappa {pi['qwk']:.2f}, plus a value estimate.",
          "Objective 4 (achieved): full comparison with precision, recall, F1, mAP and speed, and the mathematical model with statistical validation."]:
    bullet(t)
section("7.2", "Contributions")
for lead, t in [("Clean evaluation: ", "a board-level split and rectangular high-resolution input give a reproducible baseline of 63-65 mAP50 over 8 classes on 12 unseen boards; YOLO11s matches YOLO11m at 2.8x the speed."),
                ("Mathematical model: ", "weighted box fusion of four balanced / high-resolution YOLO11s models raises test mAP50 from 69.2 to 74.7 (significant, 10 of 12 boards better)."),
                ("Data engineering: ", f"the same recipe on the expanded 20,276-image data lifts the final detector to {ffo['map50']:.1f} mAP50 on the original test boards (+2.2, CI excludes zero) and {fff['map50']:.1f} / {fff['map']:.1f} on 51 unseen boards."),
                ("Quality assessment: ", f"the guide's Board Recoverability Index, adapted to line-scan geometry, reproduces annotation-based grades (weighted kappa {pi['qwk']:.2f}) and drives a market-value estimate."),
                ("Deliverable: ", "a CPU web application that shows defects, grade, recoverable area and value for an uploaded board image.")]:
    bullet(t, lead)
section("7.3", "Limitations / Challenges / Drawbacks")
for t in ["The original test set has 12 boards (complemented by 51 boards on the expanded data); differences of 2-3 mAP50 points between single models are within its noise.",
          "Severity weights and grade thresholds await expert calibration; grades are relative to the validation boards.",
          "Only the four most frequent defect classes are detected; the other four had fewer than 130 training examples each.",
          "Trained on controlled line-scan imagery: low light, painted or laminated surfaces and phone photos reduce accuracy.",
          "The application assumes the input is a wood board; it does not reject non-wood images.",
          "Challenge: scarce and imbalanced data, and training time on the expanded data within cloud session limits."]:
    bullet(t)
section("7.4", "Future Enhancements")
for t in ["Blind expert grading of 30-50 boards to calibrate severity weights and thresholds.",
          "k-fold validation over boards; more rare-class data.",
          "Segmentation masks for tighter defect area.",
          "CondConv / BiFormer (full CWB) architecture.",
          "Plywood images and field cameras; a wood / not-wood check in the application."]:
    bullet(t)

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
    p = para(r, f"[{i}] ", size=11, ls=1.15, indent=0.9)
    p.paragraph_format.first_line_indent = Cm(-0.9)

# ======================================================================= appendix
unnumbered("APPENDIX -1")
section("A.", "User Manual/Screenshots")
for t in ["Start the application with  python app.py  and open http://127.0.0.1:7860 in a browser.",
          "Tab 'Detect on your image': upload a board image, keep the default model (fusion of two YOLO11s models), confidence 0.25 and NMS IoU 0.6, and press 'Analyse image'.",
          "The result shows the boxes with class and confidence, the defect heatmap, the BRI grade with the damage score and the cut-offs, the recoverable area, the per-class table, an editable value estimate and a downloadable JSON report.",
          "Tab 'Test boards: ground truth vs prediction': choose an image from the unseen test boards to compare the annotator's boxes and grade with the model's.",
          "Tabs 'Results' and 'Legend' list the evaluation results, the classes and the grading method."]:
    bullet(t)
figure("A.1", FIGS / "app_detect.png", "Application: detections on a board and confidence heatmap", 15)
figure("A.2", FIGS / "app_grade.png", "Application: grade, recoverable area and value", 15)
section("B.", "Code Snippets")
para("", "Grade and position penalty of the Board Recoverability Index (bri.py):", size=11)
code(source("bri.py", "position_penalty") + [""] + source("bri.py", "grade"), size=8.5)
para("", "Weighted box fusion of one image (math_model.py):", size=11)
code(source("math_model.py", "wbf_image"), size=8.5)
section("C.", "Tools used")
for t in ["Python 3.12, PyTorch, Ultralytics YOLO11 8.4.142, OpenCV, NumPy, Gradio, Matplotlib.",
          "Kaggle notebooks (NVIDIA Tesla T4) and the Kaggle API for training.",
          "pytest and pytest-cov for testing; Git and GitHub for version control."]:
    bullet(t)

unnumbered("PUBLICATION DETAILS (Survey paper) / (Implementation paper)")
para("")
unnumbered("PATENT (If Any)")
para("")
unnumbered("PROJECT PROPOSAL SUBMITTED (if Any)")
para("")
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
