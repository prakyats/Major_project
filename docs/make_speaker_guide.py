"""
make_speaker_guide.py - slide-by-slide explanation of the final deck (V4.2, 26 slides as saved on 22 Oct) for the
team: what is on each slide, what to say, the numbers to remember and the likely follow-up questions; plus the
story in one minute, a glossary and the live-demo script. Output: Major_Project/docs/Presentation_Explanation_Guide.docx
"""
from pathlib import Path
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(r"C:\Users\ASUS\Desktop\Major_Project\docs\Presentation_Explanation_Guide.docx")
GREEN = RGBColor(0x3E, 0x4A, 0x3F)

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.0); sec.top_margin = sec.bottom_margin = Cm(1.8)
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11); st.paragraph_format.space_after = Pt(4)
for lvl, size in ((1, 16), (2, 13), (3, 11.5)):
    h = doc.styles[f"Heading {lvl}"]; h.font.name = "Calibri"; h.font.size = Pt(size); h.font.color.rgb = GREEN; h.font.bold = True


def para(text, lead=None, italic=False, size=None, style=None, align=None):
    p = doc.add_paragraph(style=style)
    if lead:
        r = p.add_run(lead); r.bold = True
        if size: r.font.size = Pt(size)
    r = p.add_run(text); r.italic = italic
    if size: r.font.size = Pt(size)
    if align is not None: p.alignment = align
    return p


def bullets(items):
    for it in items:
        if isinstance(it, tuple):
            para(it[1], it[0], style="List Bullet")
        else:
            para(it, style="List Bullet")


def say(text):
    """the speaking script, in a shaded box"""
    t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0); c.width = Cm(17)
    tcPr = c._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), "EEF3EA"); tcPr.append(sh)
    p = c.paragraphs[0]; r = p.add_run("Say: "); r.bold = True; r.font.color.rgb = GREEN
    p.add_run(text)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def slide(n, title, on_slide, script, remember=None, asked=None):
    doc.add_heading(f"Slide {n}: {title}", 2)
    para(on_slide, "On the slide: ", size=10.5)
    say(script)
    if remember:
        para(remember, "Remember: ", size=10.5)
    if asked:
        para("", "If asked:", size=10.5)
        for q, a in asked:
            p = para(a, f"\u201c{q}\u201d  ", size=10.5, style="List Bullet")


# ======================================================================= cover
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("AI-Based Wood Quality Assessment"); r.bold = True; r.font.size = Pt(22); r.font.color.rgb = GREEN
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Slide-by-slide explanation for the final review (deck V4.2, 26 slides)").font.size = Pt(13)
para("Team 4 · Final review 23 October 2026, 9 AM · internal reference for the presenters, not for distribution",
     align=WD_ALIGN_PARAGRAPH.CENTER, size=10, italic=True)

doc.add_heading("How to use this document", 1)
bullets(["Each slide has: what is on it, a short script to say (shaded), the numbers to remember, and the questions it may trigger.",
         "The scripts are written to be spoken in about 45-90 seconds per content slide. Do not read the slide aloud; explain it.",
         "All numbers here match the slides exactly. If a number is not on a slide, it is marked as background.",
         "Sections at the end: the live-demo script, a glossary of every technical term, and suggested ways to split the slides."])

doc.add_heading("The story in one minute (everyone should be able to say this)", 1)
say("Manual wood grading is slow and subjective. We built an AI system that finds surface defects on wood boards, "
    "classifies them, and turns them into a quality grade and a recoverable-area estimate. At the 50% review our "
    "detectors were stuck at about 64 mAP50 because the data was scarce and imbalanced, and a bigger model did not help. "
    "Based on the feedback, we did three things: we expanded and engineered the data (20,276 images from 407 boards, "
    "plus our own synthetic examples of rare defects), we built a mathematical model that fuses several detectors and "
    "proves every gain statistically, and we implemented our guide's Board Recoverability Index for grading. The final "
    "system scores 76.9 mAP50 on the same unseen test boards and 81.3 on 51 more, its grades agree with the "
    "annotation-based grades with weighted kappa 0.87, and it runs as a web application on a normal laptop.")
para("Three things the panel must remember: (1) every number is on boards the model never saw; (2) the mathematical "
     "model gives a statistically significant gain; (3) the system goes all the way from image to grade and value.",
     size=10.5, italic=True)

doc.add_heading("Numbers to know by heart", 1)
t = doc.add_table(rows=1, cols=2); t.style = "Table Grid"
for i, (a, b) in enumerate([("Item", "Value"),
                            ("50% review, 8 classes", "YOLO11m 63.0, YOLO11s 64.6 mAP50"),
                            ("Same model on the 4 main classes", "69.6 mAP50"),
                            ("Mathematical model (fusion of four models)", "74.7 mAP50; gain +2.7 to +7.1 (95% CI), Wilcoxon p = 0.042"),
                            ("Final detector, original 12 test boards", "76.9 mAP50 / 39.3 mAP50-95"),
                            ("Final detector, 51 further unseen boards", "81.3 mAP50 / 44.1 mAP50-95"),
                            ("Data", "4,000 images / 81 boards  ->  20,276 images / 407 boards"),
                            ("Crack (hardest class)", "53.0 at 50%  ->  62.2 (12 boards), 67.4 (51 boards)"),
                            ("BRI grading agreement", "weighted kappa 0.87; exact grade 78.3% of images, 10 of 12 boards"),
                            ("Speed", "about 0.5 s per image on a laptop CPU, no GPU needed")]):
    if i:
        t.add_row()
    for j, v in enumerate((a, b)):
        c = t.rows[i].cells[j]; c.text = v
        c.paragraphs[0].runs[0].font.size = Pt(10)
        if i == 0: c.paragraphs[0].runs[0].bold = True
doc.add_paragraph()

# ======================================================================= slides
doc.add_heading("Part A: recap, up to the 50% review (slides 1-11)", 1)
para("Aim: about a quarter of the time. Remind the panel what existed at mid-term, quickly.", italic=True, size=10.5)

slide(1, "Title", "Project title, team, guide, date 23 October 2026.",
      "Good morning. We are Team 4, and our project is AI-Based Wood Quality Assessment, under the guidance of Mrs. Aparna H D. "
      "Today we present the completed project: what we had at the 50% review, what we changed based on the feedback, and the final results with a live demonstration.")

slide(2, "Organisation of the presentation", "The 17 sections of the talk.",
      "We will first briefly recap the problem and our mid-term status, then cover the work since the 50% review: feedback and actions, "
      "data engineering, the mathematical model, how we chose the final model, results and their validation, and finally conclusions and future work.",
      remember="Do not read the list. Ten seconds is enough.")

slide(3, "Abstract", "Problem, system, mid-term result, what changed after feedback, final result, grading.",
      "Defects such as knots, cracks and resin pockets reduce the usable part of a wood board, and manual grading is slow and inconsistent. "
      "Our target application is high-value wood such as sandalwood. We built a system that detects, classifies and localises these defects "
      "and converts them into a quality grade, a recoverable area and a value estimate. At the 50% review we were at 63 to 65 mAP50, limited by data. "
      "Based on the feedback we expanded and engineered the data and built a mathematical model of class balancing and weighted box fusion. "
      "The final system reaches 76.9 mAP50 on the same unseen test boards and 81.3 on 51 further boards, and its grades match annotation-based grades with weighted kappa 0.87.",
      remember="76.9 / 81.3 / kappa 0.87 / 95% CI +2.7 to +7.1.",
      asked=[("Why sandalwood if you trained on other wood?",
              "Sandalwood is the target application, but there is no public labelled sandalwood defect dataset. We built and validated the method on a large public industrial wood-board dataset; the pipeline does not depend on the species, so moving to sandalwood means collecting and labelling sandalwood images and retraining. That is our first future-work item.")])

slide(4, "Introduction", "Why manual grading fails; defects differ in severity; why YOLO; what our system outputs.",
      "Manual inspection depends on human graders, so fatigue and differences between inspectors make results inconsistent, and it limits line speed. "
      "Not all defects are equal: a live knot is mostly cosmetic, a dead or missing knot weakens the board, and a crack can make a section unusable. "
      "So grading needs the type and the location of each defect, not just a yes or no. We use YOLO, a one-stage detector that finds and classifies small objects in real time, "
      "which suits a camera above a conveyor. Our system returns every defect with class, position, size and confidence, grades the board A, B, C or Reject, and estimates the recoverable area and value.")

slide(5, "Literature survey (1)", "Four 2026 papers on wood defect detection: a review, IEL-YOLO (low light), WD-SEG (segmentation), ultrasonic denoising.",
      "Recent work shows deep learning works for wood defects but has gaps. The 2026 review by Fang et al. notes small datasets and poor generalisation. "
      "IEL-YOLO adds image enhancement to YOLOv11 for low light, which is why we tested enhancement ourselves. WD-SEG gives accurate segmentation but struggles with noise and real-time use. "
      "Ultrasonic methods need special sensors. The common gaps are small datasets, weak generalisation to new boards, and no step from detection to a usable-area estimate, which is what we address.",
      remember="Gap we fill: leakage-free evaluation on unseen boards + detection-to-recoverability.")

slide(6, "Literature survey (2)", "Forestry digital twin, precision-forestry optimisation, forest planning framework, ForestryBERT.",
      "These papers look at the wider forestry pipeline: IoT dendrometers and digital twins, optimisation for tree-level decisions, planning frameworks and language models for forestry text. "
      "None of them assesses wood quality from images or connects defects to recoverable value. That is the gap at the end of the chain that our system targets.",
      asked=[("Why include forestry papers?", "They show where wood-quality assessment fits in the larger forestry and timber-value chain, and that this step is missing from it.")])

slide(7, "Problem statement", "One paragraph: detect, classify and localise defects; evaluate on unseen boards; estimate the recoverable portion.",
      "Our problem statement has three parts. First, detect, classify and localise visible surface defects on wooden boards. "
      "Second, evaluate honestly, on boards the model has never seen, because images from the same board look alike and would inflate scores. "
      "Third, use the detections to estimate the recoverable portion of each board.")

slide(8, "Objectives and final status", "Four objectives, all achieved.",
      "All four objectives are achieved. One: an annotated dataset split by physical board, expanded from 4,000 to 20,276 images, with higher resolution, enhancement and class balancing evaluated. "
      "Two: a reproducible deep-learning framework with 8-class and 4-class models, each tested once on held-out boards. "
      "Three: recoverable-area estimation with the Board Recoverability Index, validated with weighted kappa 0.87, plus a value estimate. "
      "Four: a full comparison with precision, recall, F1, mAP and speed, and our mathematical model with statistical validation.")

slide(9, "Methodology", "Eight-stage flow: data preparation, input and balancing, detection, mathematical model, defect analysis, recoverability, evaluation, market-value analytics, output.",
      "This is the complete pipeline. Images are cleaned and split by board; input is handled at high resolution with grain-safe augmentation and class balancing; "
      "YOLO11 models detect defects; the mathematical model fuses detectors and validates every gain statistically. "
      "The detections then go two ways: defect analysis and evaluation on one side, and recoverability grading and value estimation on the other, ending in the application and the final assessment.",
      remember="Stage 4, the mathematical model, is the blue box: it is the core contribution after mid-term.")

slide(10, "Recap: results at the 50% review", "YOLO11m vs YOLO11s comparison table and confusion matrix; four recap bullets.",
      "At mid-term we first fixed the evaluation. The team's earliest model reported 62.2, but the data had been split image by image, so the same physical boards were in training and test: "
      "the model was partly remembering boards. We split by physical board, 52, 17 and 12 boards with zero overlap, and used rectangular 1024-pixel input instead of padded squares. "
      "On this honest setup YOLO11m scored 63.0 and YOLO11s 64.6 mAP50: a tie, while YOLO11s is 2.8 times faster. "
      "So model size was not the bottleneck; scarce and imbalanced data was. That conclusion drove the second half of the project.",
      remember="63.0 vs 64.6; 2.8x faster; 'data, not model size'.",
      asked=[("The earliest model reported 62.2. Isn't 63-65 about the same?", "The 62.2 was measured on a leaky split, so it overstated real performance; 63-65 is measured on unseen boards, so it is the first trustworthy baseline, and everything after it is compared on the same boards."),
             ("Why not a bigger model?", "We tested it: YOLO11m (2x parameters) did not beat YOLO11s.")])

slide(11, "System design", "Two columns: data and detection pipeline, defect analysis and application; final wood-quality assessment.",
      "On the right is the data and detection pipeline: board images, preparation and balancing scripts, training on a GPU, evaluation with statistics, and detection output with box fusion. "
      "On the left is what the user gets: the web application, defect analysis, recoverability with the BRI, the value estimate and a JSON report. "
      "Both meet in the final wood-quality assessment per board. Every component is implemented.")

doc.add_heading("Part B: work after the 50% review (slides 12-22)", 1)
para("Aim: about three quarters of the time. This is where the marks are.", italic=True, size=10.5)

slide(12, "Feedback received and actions taken", "Six rows: feedback, what we did, outcome.",
      "This slide maps the feedback to our work. We were asked to improve accuracy with a mathematical model: we built class balancing, box fusion and statistical tests, and fusion gave a significant gain. "
      "Rare classes had too little data: we expanded the data and generated synthetic examples, so crack training boxes went from 306 to 4,612. "
      "A grade, not only detection: we implemented the guide's Board Recoverability Index and validated it, kappa 0.87. "
      "Higher resolution, enhancement and a CWB-style loss: we tested all three and kept only what helped. Reliability: every claim has a confidence interval. "
      "And a usable product: the web application, about half a second per image on a laptop.",
      remember="Feedback came from the guide and the panel. Every row was measured on unseen boards.")

slide(13, "Data engineering and expansion", "Before/after data table; results table on the original and further test boards; three bullets.",
      "Data was the bottleneck, so this was our biggest effort. We expanded from 4,000 images of 81 boards to the complete industrial release of 20,276 images from 407 boards, "
      "keeping the original test boards fixed so that before and after are directly comparable. "
      "Our own data work: we verified the copy we trained on against the original archive, all 43,974 boxes identical; fixed label-format errors and removed zero-size boxes; "
      "generated grain-aware synthetic defects inside the board area, which raised the balanced training set from 7,502 to 36,165 boxes; and photographed wood surfaces on campus for real-world testing. "
      "Each new model beats the previous four-model fusion on validation, and fusing the two gives 80.2 on validation, 76.9 on the original test boards and 81.3 on 51 further boards. "
      "The decision rule, beat 78.1 on validation, was written down before training.",
      remember="20,276 / 407; synthetic 7,502 -> 36,165 boxes; crack 942 -> 4,612; +2.2 mAP50 (CI +0.5 to +4.3).",
      asked=[("Is this your own dataset?", "The images are from the published industrial dataset of Kodytek et al. [12], the standard public benchmark for this task; the cleaning, verification, board-level split, synthetic data and campus photos are our own work. Sandalwood has no public dataset, which is why the method is built to be species-independent."),
             ("Why not collect from a sawmill?", "We could not get access to a mill's line-scan camera within the project; collecting and labelling such data, especially sandalwood, is the next phase.")])

slide(14, "Mathematical model I: class balancing", "Class counts under full and partial balancing; the rule; synthesis; result.",
      "The first part of the model decides how many examples each class should have. Full balance gives every class as many as the largest one. "
      "Partial balance uses the square-root rule, n-c-star equals the square root of n-c times n-max, the repeat-factor rule from the LVIS paper. "
      "It reduces the imbalance from 9.5 to 1 to about 3 to 1 without over-copying. To create the extra examples we cut real defects from training boards and paste them onto clean training boards, "
      "only inside the wood, along the grain, with Poisson or feathered blending. Full balance lost because only 160 cracks could be cut out cleanly, so each was pasted up to 17 times. "
      "Partial balance helped on validation but alone was not significant on test; its value came inside the fusion.",
      remember="sqrt(n_c x n_max); 9.5:1 -> 3.1:1; training split only.",
      asked=[("Isn't synthetic data cheating?", "It is only added to the training split; validation and test images are untouched real images.")])

slide(15, "Mathematical model II: fusion and loss", "Weighted box fusion, Wise-IoU, per-class thresholds, the two adopted fusions.",
      "The core of the mathematical model is weighted box fusion. Several detectors look at the same board; boxes of the same class that overlap are merged, "
      "the position is the confidence-weighted average, and a box that only one model finds gets its confidence reduced. "
      "We also tested the Wise-IoU loss from the CWB-YOLOv8 paper and per-class thresholds; neither beat the simpler choice, so they were not adopted. "
      "Fusing four 4-class models raised test mAP50 from 69.2 to 74.7, and the final fusion of the two expanded-data models gives 76.9 on the same boards and 81.3 on 51 further boards. "
      "Every setting was chosen on validation boards; test boards were scored once.",
      remember="Fusion formula: b_f = sum(w c b) / sum(w c). 69.2 -> 74.7 -> 76.9.",
      asked=[("Why does fusion work?", "The members make different mistakes: different input sizes and class balance. Averaging cancels some errors and places boxes more precisely."),
             ("Why not adopt Wise-IoU?", "74.6 vs 75.3 on validation, within the 0.8 run-to-run spread: no evidence it helps.")])

slide(16, "How we arrived at the final model", "Nine iterations, from the 50% models to the final fusion, with validation and test mAP50 and the reason for each decision.",
      "This slide shows the research path. We started with the tied 8-class models; fusing them helped mAP50-95 but rare classes still limited us. "
      "We focused on the four main classes, then tried full balance, which was worse, partial balance, which was the best single model, 1280-pixel input, Wise-IoU and three seeds. "
      "None of the single changes was significant alone, but they produced diverse models, and fusing four of them gave a significant gain. "
      "Finally the same recipe on the expanded data, fused from just two models, beat the pre-set validation threshold and became the final detector. "
      "So: balancing and resolution give diversity, fusion combines it, and more data lifts every member.",
      remember="Every decision on validation, rule written before training, test once per candidate.",
      asked=[("Why not test every model on test?", "Choosing among models using the test set would make the test score optimistic; we only tested candidates chosen on validation.")])

slide(17, "Mathematical model III: recoverability (BRI)", "Six steps of the Board Recoverability Index, our two changes, check against the guide's worked example.",
      "The third part converts detections into a grade, using the Board Recoverability Index proposed by our guide. Each defect's influence is its severity weight times the model's confidence times a position penalty: "
      "defects near the board's side edge can be trimmed off, so they count less. The influence map is summed over the board and divided by the board area to give the damage score; "
      "recoverable area is one minus that. Thresholds then give A, B, C or Reject. We made two changes for our images: distance is measured to the board's side edge, because the images include conveyor, "
      "and the area counts only wood pixels. Our code reproduces the guide's worked example exactly: damage score 0.020860, grade B.",
      remember="s_i = w_c x conf x p_i; p_i = 1 - exp(-d/250 px); DIS = sum I / A_board.",
      asked=[("Why is a board with 98% recoverable graded Reject?", "The grade is relative: thresholds are fitted on validation boards (best ~40% A, next 30% B, next 20% C, worst 10% Reject). The damage score is severity- and confidence-weighted, so it is small by design; the recoverable % is an index, not physical yield. The app shows the cut-offs next to the grade."),
             ("Where do the severity weights come from?", "From the guide's BRI document; calibrating them with expert grading is planned.")])

slide(18, "Results: 50% review vs final", "Overall table from the 50% models to the final detector; per-class table; two bullets.",
      "This is the before-and-after on the same 12 unseen test boards. At the 50% review YOLO11s scored 64.6 over 8 classes, which is 69.6 on our four main classes. "
      "The mathematical model brought it to 74.7, and the final detector to 76.9, with mAP50-95 rising from 33 to 39. On 51 further unseen boards it reaches 81.3. "
      "Per class, the biggest gains are on the hardest defects: Resin from 60.4 to 76.6 and Crack from 53.0 to 62.2. Dead knot was already strong and stays near 90.",
      remember="64.6 -> 69.6 (4 cls) -> 74.7 -> 76.9; 81.3 on 51 boards; Resin +16, Crack +9.",
      asked=[("Why compare to 69.6 and not 64.6?", "64.6 is over 8 classes; the final model has 4. On the same 4 classes the mid-term model scores 69.6, so that is the fair baseline."),
             ("What is mAP50-95?", "The same accuracy averaged over stricter box-overlap requirements, from 50% to 95%; it rewards precise boxes.")])

slide(19, "Statistical validation", "Paired comparisons with 95% bootstrap intervals, boards better/worse and Wilcoxon p; seed spread.",
      "We do not claim a gain unless it survives a statistical test. We resample the 12 test boards a thousand times to get a 95% confidence interval for each difference, "
      "and use the Wilcoxon signed-rank test on per-board results. The four-model fusion beats the best single model by 5.5 points, interval 2.7 to 7.1, better on 10 of 12 boards, p equals 0.042. "
      "The final detector beats that fusion by 2.2, interval 0.5 to 4.3. Differences between single models, two or three points, are not significant, and repeating the final setup with three seeds varies by only 0.8.",
      remember="Fusion +5.5 [+2.7, +7.1], p 0.042; final +2.2 [+0.5, +4.3]; seed spread 0.8.",
      asked=[("Why resample boards and not images?", "Images of one board are not independent; resampling boards gives an honest interval."),
             ("The final gain has p = 0.30. Is it significant?", "The bootstrap interval excludes zero; the Wilcoxon test has little power with only 12 boards. That is why we also report 51 further boards, where the final detector reaches 81.3.")])

slide(20, "Grading validation (BRI)", "Agreement table per image and per board; confusion matrix of grades; how reference and model grades are made.",
      "We checked whether the grades from the model match grades computed from the human annotations on the same boards. "
      "Per image the exact grade matches 78.3% of the time and is within one grade 97.4% of the time, weighted kappa 0.87, which is strong agreement. Per board, 10 of 12 are exact. "
      "Most disagreements are between neighbouring grades. All thresholds were fitted on validation boards only. "
      "The next step, agreed with the guide, is blind grading by an expert to calibrate weights and thresholds against a human grader.",
      remember="78.3% exact, 97.4% within one, kappa 0.87, 10/12 boards.",
      asked=[("What is weighted kappa?", "Agreement between two graders corrected for chance, where disagreeing by two grades counts more than by one; above 0.8 is considered strong.")])

slide(21, "Image enhancement study (H1)", "Validation mAP50 under six imaging conditions for raw, CLAHE, denoise and sharpen; three findings.",
      "Our synopsis hypothesised that enhancement such as CLAHE improves detection. We tested it under six conditions: normal, low light, over-exposed, blur, noise and low contrast. "
      "CLAHE actually lowered accuracy significantly in five of six conditions, so the hypothesis is rejected for normal images. Denoising helps only on noisy images, by 3 to 7 points. "
      "The biggest effect is lighting itself: low light costs about 25 points. So for deployment, controlled lighting matters more than any enhancement.",
      remember="H1 rejected; denoise only for noisy cameras; lighting is key.",
      asked=[("Isn't a rejected hypothesis a failure?", "No: it is a measured finding with a significance test, and it tells a real deployment what to invest in, lighting rather than software enhancement.")])

slide(22, "Conclusion and future work", "Six conclusions including future work.",
      "To conclude: with a leakage-free, board-level evaluation we found that data, not model size, limited accuracy. Our mathematical model of balancing and weighted box fusion gave a significant gain, "
      "and expanding and engineering the data took the final detector to 76.9 on the original test boards and 81.3 on 51 more. The guide's Board Recoverability Index, adapted to our images, reproduces annotation-based grades with kappa 0.87, "
      "and everything runs in a web application on a laptop. Next, we want to collect and label sandalwood images and retrain, calibrate the grading with an expert, add the rare defect classes, and move to segmentation masks for tighter defect areas.",
      remember="End on: the pipeline is ready for sandalwood data.")

doc.add_heading("Part C: references and close (slides 23-26)", 1)
slide("23-25", "References", "22 references: the literature survey [1]-[11], the dataset [12], YOLO11 [13], and the methods we used [14]-[22].",
      "Our references cover the literature survey, the public dataset by Kodytek et al., Ultralytics YOLO11, and the papers behind each method we used: class balancing, copy-paste synthesis, weighted box fusion, Wise-IoU, weighted kappa, the bootstrap, the Wilcoxon test and CLAHE.",
      remember="Do not read them; one sentence, then move to the demo or questions.")
slide(26, "Thank you", "Thank you slide.", "Thank you. We would now like to show the live demonstration, and we are happy to take questions.")

# ======================================================================= demo
doc.add_heading("Live demonstration (after slide 22 or at the end)", 1)
para("The demo slides were removed from the deck, so the demo is shown live. Prepare before the panel arrives:", size=10.5)
bullets(["Run  python app.py  and open http://127.0.0.1:7860 on the demo laptop; analyse one image once so the models are loaded.",
         "Keep the folder 'October 23 test' open: test_boards (10 images from unseen test boards) and college_photos (2 photos).",
         "Laptop charged, sleep off, notifications off; do not depend on Wi-Fi."])
para("Suggested sequence (about 3 minutes):", "", size=10.5)
for i, (a, b) in enumerate([
        ("Clean board: ", "upload 115100055.jpg: no defects, Grade A. 'A clean board is graded A.'"),
        ("Hardest defect: ", "upload 111700062.jpg: three cracks and a dead knot, all found, Grade C. 'Cracks are thin and faint; this was our weakest class at mid-term.'"),
        ("Many defects: ", "upload 113400036.jpg: six defects of three types, all found, Grade C."),
        ("Reject: ", "upload 114500011.jpg: crack, resin and dead knots, Grade Reject; point at the line that shows the damage score against the cut-offs."),
        ("Ground truth vs model: ", "open the tab 'Test boards: ground truth vs prediction' and choose 7559bb_114500011.jpg: annotators' boxes on the left, model on the right, both grades shown. Offer the panel to pick any other image from the list."),
        ("Extras: ", "show the heatmap, the per-class table, the value estimate (an illustrative add-on) and the JSON report download.")], 1):
    para(b, f"{i}. {a}", size=10.5)
para("Say while uploading: ", "", size=10.5)
say("These images come from the test boards the model never saw during training. Each result shows the defects with confidence, the grade with the damage score and the cut-offs it is compared to, the recoverable area and a value estimate.")
para("If they ask for a live photo or another object:", "", size=10.5)
bullets([("Food, a phone, a person: ", "the model is not a general object recogniser; it only looks for four wood defects. A non-wood image usually shows no boxes, and the app then says Grade A, because it assumes a wood board as on a production line. A wood / not-wood check is listed as future work."),
         ("A photo of a desk or door: ", "trained on raw industrial wood boards under controlled lighting; painted or laminated furniture is a different surface, so some labels can be wrong. For a mill we retrain on that camera's images."),
         ("If you must take a photo: ", "unpainted wood, grain left to right, fill the frame, even light, phone parallel to the surface.")])
para("If asked 'did you choose images that work?': yes, they are prepared examples from the held-out test boards, as in any demo; offer the Test-boards tab so the panel can pick any image, and quote 76.9 mAP50 over all 469 test images.", size=10.5, italic=True)

# ======================================================================= glossary
doc.add_heading("Glossary (say it in one sentence)", 1)
for a, b in [
        ("YOLO / YOLO11s, YOLO11m", "a one-stage object detector that finds and classifies objects in one pass; s = small (9.4 M parameters), m = medium (20 M)."),
        ("Bounding box", "the rectangle the model draws around a defect."),
        ("IoU (intersection over union)", "overlap between the predicted and the true box, from 0 to 1."),
        ("Precision / Recall / F1", "precision: share of predicted defects that are real; recall: share of real defects found; F1: their harmonic mean."),
        ("mAP50", "mean average precision with a box counting as correct at IoU 0.5 or more, averaged over classes; the standard detection accuracy."),
        ("mAP50-95", "mAP averaged over IoU thresholds 0.5 to 0.95; rewards precise boxes."),
        ("Board-level split", "every image of a physical board goes to only one of train, validation or test, so test boards are truly unseen."),
        ("Data leakage", "test data that is too similar to training data (here, the same boards), which inflates scores."),
        ("Validation vs test", "validation boards are used to choose settings; test boards are used once at the end to report results."),
        ("Class imbalance / balancing", "some defects are far rarer than others; balancing adds training examples of rare classes."),
        ("Copy-paste synthesis", "cutting real defects from training boards and pasting them onto clean training boards to create more examples."),
        ("Weighted box fusion (WBF)", "merging the boxes of several detectors by confidence-weighted averaging."),
        ("Wise-IoU", "a box-regression loss used in the CWB-YOLOv8 paper; tested, not adopted."),
        ("Bootstrap confidence interval", "resampling the test boards many times to see how much a result could vary; 95% CI excluding zero means the gain is reliable."),
        ("Wilcoxon signed-rank test", "a non-parametric test of whether per-board differences are consistently positive; p < 0.05 is significant."),
        ("Weighted kappa", "agreement between two graders beyond chance, penalising larger disagreements more; 0.87 is strong agreement."),
        ("BRI, DIS", "Board Recoverability Index; DIS is its damage score (weighted defect impact per board area)."),
        ("CLAHE", "contrast-limited adaptive histogram equalisation, an image-enhancement method."),
        ("Epoch, fine-tuning, COCO", "one pass over the training data; starting from a model pre-trained on the COCO image dataset and adapting it to our data.")]:
    para(b, a + ": ", style="List Bullet", size=10.5)

# ======================================================================= split
doc.add_heading("Suggested ways to split the slides between four presenters", 1)
para("Not decided yet; two balanced options (time per person about equal):", size=10.5)
t = doc.add_table(rows=5, cols=3); t.style = "Table Grid"
rows = [("Presenter", "Option 1 (by story)", "Option 2 (by expertise)"),
        ("1", "Slides 1-9: introduction, survey, problem, objectives, methodology", "Slides 1-8 + 22 (opening and conclusion)"),
        ("2", "Slides 10-13: 50% recap, system design, feedback, data engineering", "Slides 9-13 (method, recap, system, feedback, data)"),
        ("3", "Slides 14-17: mathematical model I-III and model selection", "Slides 14-19 (mathematical model, results, statistics)"),
        ("4", "Slides 18-22 + live demo: results, validation, enhancement, conclusion", "Slides 20-21 + live demo (grading, enhancement, app)")]
for i, r in enumerate(rows):
    for j, v in enumerate(r):
        c = t.rows[i].cells[j]; c.text = v; c.paragraphs[0].runs[0].font.size = Pt(10)
        if i == 0: c.paragraphs[0].runs[0].bold = True
doc.add_paragraph()
para("Whoever presents slides 14-19 should also be ready for most technical questions; whoever runs the demo should rehearse it on the demo laptop.",
     size=10.5, italic=True)

doc.save(str(OUT))
print("saved", OUT)
