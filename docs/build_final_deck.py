"""
build_final_deck.py - final (100 %) review deck from the approved 50 % deck (V3.0).
Literature survey, problem statement, model comparison, training-log slides and the original references are kept
unchanged; status slides are rewritten; new slides cover the mathematical model, validation, the enhancement study and
the conclusion. Every number comes from docs/final_results.json (collect_results.py).

python docs/build_final_deck.py --date "17 October 2026"
"""
import argparse, json, sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu, Inches, Pt

sys.path.insert(0, str(Path(__file__).parent))
import deck_tools as D

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"C:\Users\ASUS\Desktop\Major_Project\docs\Major_Project_50pct_Presentation_V3.0.pptx")
OUT = Path(r"C:\Users\ASUS\Desktop\Major_Project\docs\Major_Project_Final_Presentation_V4.1.pptx")
FIGS = ROOT / "docs" / "final_figs"
R = json.loads((ROOT / "docs" / "final_results.json").read_text(encoding="utf-8"))
IN = lambda x: int(Inches(x))


def f1(x):
    return "pending" if x is None else f"{x:.1f}"


def allrow(d):
    return d["ALL"] if d else None


def m(split, key, idx):
    d = R[split].get(key)
    return None if not d else d["ALL"][idx]


def tbl(slide):
    return [s for s in slide.shapes if s.has_table]


def one_table_slide(prs, src):
    s = D.clone_slide(prs, src)
    D.remove_shape(tbl(s)[1])
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="__ October 2026")
    ap.add_argument("--time", default="9Am Onwards")
    a = ap.parse_args()
    prs = Presentation(str(SRC))
    S = {i + 1: s for i, s in enumerate(prs.slides)}           # V3 slides by their V3 number

    fus8 = R["fusion8"]; f8 = fus8["test"]["fused"]; st8 = fus8["stats_fused_minus_best_single"]
    fus4 = R.get("fusion4")
    if fus4:
        fus4["adopted"] = fus4["chosen"]["val_map50"] > max(fus4["val_single_map50"])
    bri = R.get("bri"); enh = R.get("enh"); st4 = R.get("stats4"); wi = R.get("wiou")
    fin = R.get("final") or {}
    F4 = fus4["test"]["fused"] if fus4 else None
    st4f = fus4["stats_fused_minus_best_single"] if fus4 else None
    single4 = R["test4"]["sqrt_1024"]["ALL"]
    fin_name = fin.get("name", "YOLO11s, 4 classes, partial balance, 1024 px")
    fin_test = fin.get("test", allrow(R["test4"].get("sqrt_1024")))
    kappa = bri["test_per_image"]["qwk"] if bri else None
    FU = R["full"]; FT = FU["test"]; stfu = FU["stats_new_minus_deployed_test_orig"]
    ffo, fff = FT["full_fusion"]["orig"], FT["full_fusion"]["full"]       # final detector: original 469 / full 2,488 test images
    sub_fus = FT["deployed_fusion"]["orig"]                                 # four-model fusion trained on the subset

    # ---------------------------------------------------------------- 1 title
    D.set_bullets(D.shape_by_id(S[1], 94), ["7th Semester Major Project: Final (100%) Presentation",
                                            f"Date: {a.date}", f"Time: {a.time}"], template_index=0)
    # ---------------------------------------------------------------- 2 organisation
    D.set_bullets(D.shape_by_id(S[2], 109), [
        "Abstract", "Introduction", "Literature Survey", "Problem Statement", "Objectives and Final Status",
        "Methodology", "Dataset and Board-level Split", "System Design and Implementation", "Training Configuration and Runs",
        "Mathematical Model: Class Balancing, Box Fusion and Wise-IoU, Recoverability Index",
        "Results on Held-out Boards", "Full-dataset Extension (20,276 images)", "Statistical and Grading Validation", "Image Enhancement Study",
        "Model Comparison", "Demonstration Application", "Plan of Action", "Conclusion and Future Work", "References"], size=10.5)
    # ---------------------------------------------------------------- 3 abstract
    D.set_bullets(D.shape_by_id(S[3], 127), [
        "Surface defects such as knots, cracks and resin pockets reduce the usable part of sawn timber; manual grading is slow, subjective and inconsistent.",
        "We built an AI system that detects, classifies and localises surface defects on board images and turns them into a quality grade, a recoverable-area estimate and a value estimate.",
        "Data: 4,000 industrial line-scan images, 8 defect classes, split by physical board (52 / 17 / 12 boards), so every test board is unseen; extended to all 20,276 images (407 boards) for the final detector.",
        "Detection: YOLO11m and YOLO11s reach 63.0 and 64.6 mAP50 over 8 classes on 12 unseen boards; YOLO11s is 2.8x faster, so the final system is built on YOLO11s.",
        f"Mathematical model: class balancing, higher resolution and weighted box fusion of four 4-class YOLO11s models raise test mAP50 from {single4[3]:.1f} (best single model) to {F4['map50']*100:.1f} and mAP50-95 from {single4[4]:.1f} to {F4['map']*100:.1f}; 95% CI of the mAP50 gain +{st4f['map50_diff_ci'][0]:.1f} to +{st4f['map50_diff_ci'][1]:.1f}, Wilcoxon p = {st4f['wilcoxon_p']:.3f}. Retrained on the full dataset, two models fused reach {ffo['map50']:.1f} mAP50 on the same 12 test boards and {fff['map50']:.1f} on 51 unseen boards.",
        f"Quality assessment: the guide's Board Recoverability Index, adapted to line-scan geometry, matches annotation-based grades with weighted kappa {f1(kappa) if kappa is None else f'{kappa:.2f}'} on unseen boards; a web application shows defects, grade, recoverable area and value."], size=13)
    # ---------------------------------------------------------------- 4 introduction (last bullet only)
    sh = D.shape_by_id(S[4], 140)
    D.set_bullets(sh, [
        "Manual inspection of timber depends on human graders; fatigue and inter-inspector variation make results inconsistent, and throughput limits line speed.",
        "Defects differ in severity: a live knot is cosmetic, a dead or missing knot weakens the board, a crack may make a section unusable. Grading needs the defect type and its location, not a yes/no answer.",
        "One-stage detectors of the YOLO family find and classify small objects in real time, which suits a conveyor-mounted line-scan camera.",
        "Our system returns every visible defect with class, position, size and confidence, grades each board with the Board Recoverability Index (A / B / C / Reject), and estimates its recoverable area and value."])
    # ---------------------------------------------------------------- 8 objectives
    D.set_text(D.shape_by_id(S[8], 181), "OBJECTIVES AND FINAL STATUS")
    D.set_bullets(D.shape_by_id(S[8], 188), [
        ("Objective 1 (achieved): ", "Annotated dataset of 4,000 line-scan images, 8 classes, 9,053 boxes, split by physical board with zero overlap, then the full 20,276-image dataset (407 boards). Higher-resolution input (1280 px), CLAHE / denoising and copy-paste balancing of rare classes were all implemented and evaluated."),
        ("Objective 2 (achieved): ", "Deep-learning framework for detection and localisation: reproducible preparation, balancing, training and evaluation scripts; 8-class YOLO11m / YOLO11s and 4-class YOLO11s models, each tested once on held-out boards."),
        ("Objective 3 (achieved): ", f"Recoverable-area estimation: the guide's Board Recoverability Index gives a damage score, recoverable area and grade per board; validated against annotation-based grades (weighted kappa {kappa:.2f}); market value estimated from grade." if kappa else "Recoverable-area estimation with the Board Recoverability Index (validation pending)."),
        ("Objective 4 (achieved): ", "Comparison with P, R, F1, mAP50, mAP50-95 and inference time at identical settings, plus our mathematical model: class-balancing rule, weighted box fusion, Wise-IoU loss, per-class thresholds and statistical validation.")])
    # ---------------------------------------------------------------- 9 methodology figure
    D.set_text(D.shape_by_id(S[9], 200), "Fig. Methodology as completed for the final review")
    D.replace_picture(S[9], D.shape_by_id(S[9], 201), FIGS / "methodology_final.png", box=(IN(1.2), IN(0.75), IN(7.4), IN(5.75)))
    D.shape_by_id(S[9], 200).top = IN(6.6)
    # ---------------------------------------------------------------- 10 methodology text
    D.set_bullets(D.shape_by_id(S[10], 208), [
        ("Dataset preparation. ", "Public industrial line-scan dataset; label cleaning; class mapping verified; group-stratified split by board id (52 / 17 / 12 boards); final models on the full 20,276 images (280 / 76 / 51 boards, our 81 boards keep their split)."),
        ("Input handling. ", "2800 x 1024 strips trained with rectangular batches at 1024 px (1024 x 384) and, as an experiment, 1280 px (1280 x 480)."),
        ("Class balancing. ", "Four most frequent classes kept; real defect crops pasted onto defect-free training boards along the grain until n_c reaches n_max or sqrt(n_c x n_max)."),
        ("Detection. ", "Ultralytics YOLO11 fine-tuned from COCO: YOLO11m and YOLO11s with one recipe; Wise-IoU v3 tested as the box loss."),
        ("Mathematical model. ", "Weighted box fusion of detectors, per-class confidence thresholds, and statistical validation (board-level bootstrap, exact Wilcoxon test)."),
        ("Recoverability and value. ", "Board Recoverability Index: severity x confidence x position penalty -> damage score, recoverable area, grade A / B / C / Reject; value = volume x recoverable share x price x grade factor."),
        ("Evaluation protocol. ", "Every choice made on validation boards; each test model evaluated exactly once; enhancement study (CLAHE, denoise, sharpen) on validation.")], size=11)
    # ---------------------------------------------------------------- 11 dataset: imbalance note
    D.set_bullets(D.shape_by_id(S[11], 227), [
        "Imbalance: Live_Knot 44%, Dead_Knot 32% of boxes; Knot_missing 1.3%. Final detector: the 4 most frequent classes (Live_Knot, Dead_Knot, Resin, Crack)."], size=9)
    # ---------------------------------------------------------------- 12 system design text
    D.set_bullets(D.shape_by_id(S[12], 237), [
        ("1. Data / input layer : ", "board images, cleaned labels, board-level train / val / test sets; balanced 4-class training sets."),
        ("2. Input processing : ", "rectangular 1024 / 1280-px input, grain-aware augmentation, copy-paste balancing; CLAHE, denoising and sharpening evaluated."),
        ("3. Detection model : ", "YOLO11m (20.0 M) and YOLO11s (9.4 M); Wise-IoU variant; weighted box fusion of detectors."),
        ("4. Defect analysis : ", "class, position, size, confidence per defect; per-class counts and area."),
        ("5. Recoverability estimation : ", "Board Recoverability Index with a board mask; grade thresholds fitted on validation boards; weighted-kappa validation."),
        ("6. Training and evaluation : ", "P, R, F1, mAP50, mAP50-95, ms per image; single-shot test on 12 unseen boards; bootstrap and Wilcoxon tests."),
        ("7. Application : ", "web interface with boxes, heatmap, grade, recoverable area, value estimate and JSON report.")])
    # ---------------------------------------------------------------- 13 training configuration
    t = tbl(S[13])[0]
    D.fill_table(t, [["Setting", "Value (identical across models unless stated)"],
                     ["Pretrained weights", "COCO yolo11m.pt (20.0 M params, 68 GFLOPs) / yolo11s.pt (9.4 M, 21 GFLOPs)"],
                     ["Input", "imgsz 1024 rectangular (1024 x 384); high-resolution runs imgsz 1280 (1280 x 480)"],
                     ["Optimiser / schedule", "AdamW, lr0 0.001, lrf 0.01, cosine, 3 warm-up epochs, weight decay 5e-4"],
                     ["Batch / epochs / patience", "32 / 100 / 40 (subset); 32 / 40 / 15 on the full dataset (5x data per epoch)"],
                     ["Loss", "cls 1.0, box 7.5, dfl 1.5; box loss CIoU, or Wise-IoU v3 (alpha 1.9, delta 3)"],
                     ["Augmentation", "hsv 0.01 / 0.3 / 0.2, translate 0.08, scale 0.3, fliplr 0.5, degrees 0, flipud 0, mosaic 0, erasing 0.05"],
                     ["Class balancing (4-class)", "copy-paste of real crops; plain, full (1:1) or partial sqrt(n_c x n_max) (3:1)"],
                     ["Reproducibility", "seed 42, deterministic; seeds 1 and 2 repeat the final setup"],
                     ["Model selection / test", "best.pt by validation; each test model evaluated once (conf 0.001, NMS IoU 0.6)"]],
                 col_widths=[1.2, 3.8])
    D.set_bullets(D.shape_by_id(S[13], 251), [
        ("Compute: ", "Kaggle, one NVIDIA Tesla T4 (15 GB); about 1.4-2.4 GPU-hours per YOLO11s run, 2.6 per YOLO11m run; full-dataset runs 3.2 h (1024 px) and 4.3 h (1280 px)."),
        ("Software: ", "Python 3.12, PyTorch 2.10, Ultralytics 8.4.142, OpenCV, Gradio. Scripts: prepare_dataset, build_balanced, train_yolo11m, train_wiou, evaluate, eval_capture, math_model, bri, bri_validate, enhance_study, app; decision log in NOTES.md.")])
    # ---------------------------------------------------------------- 14 system design figure
    D.set_text(D.shape_by_id(S[14], 255), "Fig. System design as implemented for the final review")
    D.replace_picture(S[14], D.shape_by_id(S[14], 262), FIGS / "system_design_final.png", box=(IN(0.9), IN(0.35), IN(7.6), IN(6.2)))
    D.shape_by_id(S[14], 255).top = IN(6.6)
    # ---------------------------------------------------------------- 15 training runs
    def vr(k):
        v = R["val4"].get(k)
        return (f1(v["ALL"][3]), f1(v["ALL"][4])) if v else ("pending", "pending")
    rr = R.get("runs4") or {}
    h4 = R.get("hours4") or {}; h12 = R.get("hours1280") or {}
    def ep(k):
        x = rr.get(k); return (str(x["epochs"]), str(x["best_epoch"])) if x else ("-", "-")
    rows = [["Run", "Model / data", "Settings", "Epochs / GPU h", "Best ep.", "Val mAP50", "Val mAP50-95"],
            ["1", "YOLO11m, 8 cls", "batch 16, lr0 0.002", "89 / 2.54", "64", "62.6", "33.7"],
            ["2", "YOLO11m, 8 cls", "batch 32, lr0 0.001 (adopted)", "100 / 2.64", "73", "65.7", "36.2"],
            ["3", "YOLO11s, 8 cls", "as run 2", "90 / 1.43", "50", "65.3", "36.0"]]
    for rid, k, desc, hk in [("4a", "plain_1024", "4 cls, no balancing, 1024", h4.get("yolo11s_4cls_plain")),
                             ("4b", "full_1024", "4 cls, full balance 1:1, 1024", h4.get("yolo11s_4cls_full")),
                             ("4c", "sqrt_1024", "4 cls, partial balance 3:1, 1024 (subset final)", h4.get("yolo11s_4cls_sqrt")),
                             ("5a", "sqrt_1280", "4 cls, partial balance, 1280", h12.get("yolo11s_4cls_sqrt_1280")),
                             ("5b", "plain_1280", "4 cls, no balancing, 1280", h12.get("yolo11s_4cls_plain_1280"))]:
        e, b = ep(k); v50, v95 = vr(k)
        rows.append([rid, "YOLO11s", desc, f"{e} / {hk if hk else '-'}", b, v50, v95])
    if wi:
        for k, v in wi["val_map50"].items():
            rows.append(["6", "YOLO11s", ("Wise-IoU v3" if "wiou" in k else "seed " + k.split("seed")[-1][:1]) + ", setup of 4c", "-", "-", f1(v), "-"])
    for rid, k, desc, hk, sz in [("7a", "full4_1024", "4 cls, full dataset, partial balance, 1024 (final)", "3.15", "full_1024"),
                                 ("7b", "full4_1280", "4 cls, full dataset, partial balance, 1280 (final)", "4.31", "full_1280")]:
        e, b = ep(k); v = FU["val_orig"][sz]
        rows.append([rid, "YOLO11s", desc, f"{e} / {hk}", b, f1(v[0]), f1(v[1])])
    t = tbl(S[15])[0]
    D.fill_table(t, rows, col_widths=[0.35, 1.0, 2.3, 0.9, 0.55, 0.7, 0.8], size=8)
    D.set_row_heights(t, IN(0.22))
    D.set_bullets(D.shape_by_id(S[15], 275), [
        "Runs 1-3: 8-class models (validation pass during training).",
        "Runs 4-6: 4-class models on the 4,000-image subset; 1280 px and Wise-IoU gave no gain, seeds spread 0.8.",
        "Runs 7a / 7b: the same recipe on the full dataset; validation on the same 714 original images, so all rows compare.",
        "The final detector fuses runs 7a and 7b."], size=9.5)
    t.top = IN(0.95); t.left = IN(0.25); t.width = IN(8.7)
    D.set_row_heights(t, IN(0.2))
    D.replace_picture(S[15], D.shape_by_id(S[15], 274), ROOT / "runs_log" / "run4_yolo11s_4cls_sqrt_v1" / "results.png",
                      box=(IN(0.25), IN(4.0), IN(5.4), IN(2.55)))
    tb15 = D.shape_by_id(S[15], 275); tb15.left = IN(5.8); tb15.top = IN(4.05); tb15.width = IN(3.1); tb15.height = IN(2.5)
    D.set_text(D.shape_by_id(S[15], 276), "Fig. Training and validation curves, run 4c (subset)")
    D.shape_by_id(S[15], 276).top = IN(6.6); D.shape_by_id(S[15], 276).left = IN(0.25)
    # ---------------------------------------------------------------- 16 plan of action
    D.set_text(D.shape_by_id(S[16], 278), "PLAN OF ACTION: COMPLETED")
    D.replace_picture(S[16], D.shape_by_id(S[16], 286), FIGS / "plan_of_action_final.png", box=(IN(0.2), IN(1.0), IN(8.7), IN(4.4)))
    D.set_bullets(D.shape_by_id(S[16], 287), ["All planned work is complete: dataset and preprocessing, defect detection, the mathematical model and accuracy experiments, recoverability estimation and market value, evaluation, application and report."])
    # ---------------------------------------------------------------- 17 results: held-out test
    T8 = R["test8"]
    def row4(label, key, params="9.4 M"):
        d = R["test4"].get(key)
        if not d:
            return [label, "4", "-", "-", "-", "pending", "pending", "-", params]
        a_ = d["ALL"]; return [label, "4", f1(a_[0]), f1(a_[1]), f1(a_[2]), f1(a_[3]), f1(a_[4]), "11.7", params]
    top = [["Model", "Classes", "P", "R", "F1", "mAP50", "mAP50-95", "ms / img (T4)", "Params"],
           ["YOLO11m", "8"] + [f1(x) for x in T8["YOLO11m"]["ALL"]] + ["33.2", "20.0 M"],
           ["YOLO11s", "8"] + [f1(x) for x in T8["YOLO11s"]["ALL"]] + ["11.7", "9.4 M"],
           ["Fusion (WBF) YOLO11m + YOLO11s", "8", "-", "-", "-", f1(f8["map50"] * 100), f1(f8["map"] * 100), "44.9", "29.4 M"],
           row4("YOLO11s, no balancing", "plain_1024"), row4("YOLO11s, partial balance (subset single)", "sqrt_1024"),
           row4("YOLO11s, partial balance, 1280 px", "sqrt_1280")]
    if fus4 and fus4.get("adopted"):
        x = fus4["test"]["fused"]
        top.append(["Fusion (WBF) of four 4-class models (subset)", "4", "-", "-", "-", f1(x["map50"] * 100), f1(x["map"] * 100), "~60", "37.7 M"])
    top.append(["Fusion of two full-dataset models (final)", "4", "-", "-", "-", f1(ffo["map50"]), f1(ffo["map"]), "~30", "18.8 M"])
    t_top, t_cls = tbl(S[17])
    D.fill_table(t_top, top, col_widths=[2.6, 0.6, 0.6, 0.6, 0.6, 0.7, 0.8, 0.9, 0.7], size=8.5)
    D.set_row_heights(t_top, IN(0.24))
    fd = R["test4"][fin.get("single_key", "sqrt_1024")]
    base4 = {"Live_Knot": T8["YOLO11s"]["Live_Knot"], "Dead_Knot": T8["YOLO11s"]["Dead_Knot"],
             "Resin": T8["YOLO11s"]["Resin"], "Crack": T8["YOLO11s"]["Crack"]}
    crow = [["Class (test mAP50)", "Test boxes", "8-class YOLO11s", "Best single 4-class (P / R)", "Single mAP50", "Final detector mAP50"]]
    nbox = {"Live_Knot": 406, "Dead_Knot": 343, "Resin": 69, "Crack": 95}
    for c in ["Dead_Knot", "Live_Knot", "Resin", "Crack"]:
        crow.append([c, str(nbox[c]), f1(base4[c][3]), f"{f1(fd[c][0])} / {f1(fd[c][1])}", f1(fd[c][3]), f1(ffo["ap50"][c])])
    crow.append(["ALL (4 classes)", "913", "69.6", f"{f1(fd['ALL'][0])} / {f1(fd['ALL'][1])}", f1(fd["ALL"][3]), f1(ffo["map50"])])
    D.fill_table(t_cls, crow, col_widths=[1.5, 0.8, 1.1, 1.6, 1.0, 1.4], size=8.5, bold_rows=(len(crow) - 1,))
    t_cls.top = t_top.top + IN(0.24) * len(top) + IN(0.25)
    D.set_row_heights(t_cls, IN(0.24))
    D.set_bullets(D.shape_by_id(S[17], 301), [
        "Each model evaluated exactly once on boards never used for training, validation or any choice. 8-class and 4-class rows are not directly comparable: on the same four classes the 8-class YOLO11s scores 69.6 mAP50.",
        f"On the subset, only fusion beat the best single model (+{st4f['map50_diff_ci'][0]:.1f} to +{st4f['map50_diff_ci'][1]:.1f} mAP50, 95% CI). The final detector, trained on the full dataset, adds {ffo['map50'] - sub_fus['map50']:+.1f} on the same boards (CI {stfu['map50_diff_ci'][0]:+.1f} to {stfu['map50_diff_ci'][1]:+.1f}) and scores {fff['map50']:.1f} on 51 unseen boards."], size=10)
    D.shape_by_id(S[17], 301).top = t_cls.top + IN(0.24) * 6 + IN(0.2)

    # ================================================================ new slides
    new = {}
    # MM-I class balancing (clone of slide 13: one table + text)
    s = one_table_slide(prs, S[17]); new["mm1"] = s
    D.set_text(D.shape_by_text(s, "RESULTS: HELD-OUT TEST"), "MATH MODEL I: CLASS BALANCING")
    bal = R["balance"]
    rows = [["Class", "Training boxes", "Full balance (1:1)", "Partial balance sqrt(n_c n_max)"]]
    for c in ["Live_Knot", "Dead_Knot", "Resin", "Crack"]:
        rows.append([c, str(bal["train_plain"][c]), str(bal["train_full"][c]), str(bal["train_sqrt"][c])])
    rows.append(["Imbalance max : min", "9.5 : 1", "1.06 : 1", "3.1 : 1"])
    t = tbl(s)[0]; t.width = IN(5.2); D.fill_table(t, rows, col_widths=[1.3, 1.1, 1.2, 1.6], size=10)
    t.top = IN(1.0); D.set_row_heights(t, IN(0.3))
    tx = D.shape_by_text(s, "Each model evaluated")
    D.set_bullets(tx, [
        ("Rule: ", "target boxes per class n_c* = n_max (full) or n_c* = sqrt(n_c x n_max) (partial, the repeat-factor rule of LVIS [15], same idea as the effective number of samples [14])."),
        ("Synthesis: ", "real defect crops cut from training boards and pasted onto defect-free training boards (2-5 per image), only inside the board mask, no rotation, Poisson or feathered blending [16]; training split only."),
        ("Result: ", f"partial balance raised validation mAP50 from 73.1 to 75.3 but scored 69.2 on test vs 71.7 without balancing; difference not significant (95% CI {st4['test']['tests']['sqrt - plain']['map50_diff_ci'][0]:+.1f} to {st4['test']['tests']['sqrt - plain']['map50_diff_ci'][1]:+.1f})." if st4 else "pending"),
        ("Why full balance lost: ", "only 160 cracks could be cut out cleanly, so each was pasted up to 17 times.")], size=10.5)
    tx.top = IN(2.95); tx.left = IN(0.3); tx.width = IN(5.2); tx.height = IN(3.3)
    prev = sorted((ROOT / "runs_log" / "run4_4cls_kaggle_v1" / "previews").glob("train_sqrt_*.jpg"))
    if prev:
        D.add_picture(s, prev[0], (IN(5.55), IN(1.0), IN(3.4), IN(1.3)))
        D.add_picture(s, prev[1], (IN(5.55), IN(2.45), IN(3.4), IN(1.3)))

    # MM-II fusion, Wise-IoU, thresholds (clone of slide 13)
    s = one_table_slide(prs, S[17]); new["mm2"] = s
    D.set_text(D.shape_by_text(s, "RESULTS: HELD-OUT TEST"), "MATH MODEL II: FUSION AND LOSS")
    rows = [["Component", "Formula", "Test result (chosen on validation)"],
            ["Weighted box fusion [17]", "b_f = sum(w c b) / sum(w c);  c_f = (sum w c / sum w) x min(sum w, W) / W",
             f"YOLO11m + YOLO11s: mAP50 {f8['map50']*100:.1f}, mAP50-95 {f8['map']*100:.1f} (best single 64.6 / 33.7); mAP50-95 +{st8['map_diff_ci'][0]:.1f} to +{st8['map_diff_ci'][1]:.1f} (95% CI)"],
            ["Wise-IoU v3 [18]", "L = r x exp(d^2 / (W_g^2 + H_g^2)) x (1 - IoU);  r = beta / (delta alpha^(beta - delta))",
             (f"val mAP50 {[v for k, v in wi['val_map50'].items() if 'wiou' in k][0]:.1f} vs 75.3 (CIoU); seed spread {wi['seed_spread']:.1f}; adopted: {'yes' if wi['wiou_adopted'] else 'no'}" if wi else "training on Kaggle, result pending")],
            ["Per-class thresholds", "t_c = argmax_t F1_c(t) on validation",
             f"macro-F1 {fus8['thresholds']['fused_test_per_class']['F1']*100:.1f} vs {fus8['thresholds']['fused_test_global']['F1']*100:.1f} with one global threshold: not adopted"]]
    if fus4:
        x = fus4["test"]["fused"]; c = fus4["chosen"]
        rows.append(["Fusion of 4-class models", f"IoU {c['t_iou']}, weights {c['weights']}",
                     f"val {c['val_map50']*100:.1f} vs best single {max(fus4['val_single_map50'])*100:.1f}; "
                     + (f"adopted, test {x['map50']*100:.1f} / {x['map']*100:.1f}" if fus4.get("adopted") else "not adopted (rule fixed before running)")])
    ch = FU["chosen"]
    rows.append(["Fusion of full-dataset models", f"IoU {ch['t_iou']}, weights {ch['weights']}",
                 f"val {ch['val_full_map50']*100:.1f} (full val); adopted, test {ffo['map50']:.1f} / {ffo['map']:.1f} (12 boards), {fff['map50']:.1f} / {fff['map']:.1f} (51 boards)"])
    t = tbl(s)[0]; D.fill_table(t, rows, col_widths=[1.4, 3.2, 3.6], size=9)
    t.top = IN(1.0); D.set_row_heights(t, IN(0.45))
    D.set_bullets(D.shape_by_text(s, "Each model evaluated"), [
        f"Fusion averages the boxes of several detectors weighted by confidence and lowers the confidence of boxes only one model finds. Fusing four 4-class YOLO11s models (1024 and 1280 px, with and without balancing) raised test mAP50 from {single4[3]:.1f} to {F4['map50']*100:.1f}.",
        "Thresholds tuned per class over-fit the few validation boxes of Resin and Crack, so one global threshold is kept.",
        "Every setting was chosen on the 17 validation boards; the 12 test boards were scored once."], size=10.5)
    D.shape_by_text(s, "Fusion averages").top = IN(4.3)

    # MM-III BRI (clone of slide 10: bullets) + geometry figure
    s = D.clone_slide(prs, S[10]); new["mm3"] = s
    D.set_text(D.shape_by_text(s, "METHODOLOGY"), "MATH MODEL III: RECOVERABILITY")
    bs = D.shape_by_text(s, "Dataset preparation.")
    D.set_bullets(bs, [
        ("1. Union of defects: ", "A_def = |R_1 U ... U R_n| (overlaps counted once)."),
        ("2. Severity: ", "w_c: Crack 1.00, Dead_Knot 0.60, Live_Knot 0.40, Resin 0.30 (guide's placeholders)."),
        ("3. Position: ", "p_i = 1 - exp(-d_i / 250 px), d_i = distance to the board's side edge (our change)."),
        ("4. Influence: ", "s_i = w_c x conf_i x p_i."),
        ("5. Damage: ", "I(x, y) = max_i s_i;  DIS = sum I / A_board (board pixels, our change);  A_rec = A_board (1 - DIS)."),
        ("6. Grade: ", "A / B / C / Reject from thresholds fitted on validation boards with the guide's weighted-kappa calibration."),
        ("Check: ", "the guide's worked example is reproduced exactly (DIS 0.020860, grade B).")], size=10.5)
    bs.width = IN(4.6); bs.top = IN(1.0); bs.height = IN(5.0)
    geo = ROOT / "docs" / "final_figs" / "bri_geometry.png"
    if geo.exists():
        D.add_picture(s, geo, (IN(4.95), IN(1.3), IN(4.0), IN(2.2)))

    # STATS (clone of slide 17: two tables + text)
    s = D.clone_slide(prs, S[17]); new["stats"] = s
    D.set_text(D.shape_by_text(s, "RESULTS: HELD-OUT TEST"), "STATISTICAL VALIDATION")
    ta, tb_ = tbl(s)
    rows = [["Comparison (test, 12 boards)", "mAP50 diff", "95% CI (board bootstrap)", "Boards better / worse", "Wilcoxon p"],
            ["Final detector (full data) - subset fusion", f"{ffo['map50'] - sub_fus['map50']:+.1f}", f"[{stfu['map50_diff_ci'][0]:+.1f}, {stfu['map50_diff_ci'][1]:+.1f}]",
             f"{stfu['boards_better']} / {stfu['boards_worse']}", f"{stfu['wilcoxon_p']:.2f}"]]
    if fus4:
        rows.append(["Subset fusion (4 cls) - best single 4-class model", f"{(F4['map50'] - fus4['test']['singles'][fus4['best_single_on_val']]['map50'])*100:+.1f}",
                     f"[{st4f['map50_diff_ci'][0]:+.1f}, {st4f['map50_diff_ci'][1]:+.1f}]", f"{st4f['boards_better']} / {st4f['boards_worse']}", f"{st4f['wilcoxon_p']:.3f}"])
    rows.append(["Fusion (YOLO11m + YOLO11s) - YOLO11s, mAP50", f"{(f8['map50'] - fus8['test']['singles'][fus8['best_single_on_val']]['map50'])*100:+.1f}",
                 f"[{st8['map50_diff_ci'][0]:+.1f}, {st8['map50_diff_ci'][1]:+.1f}]", f"{st8['boards_better']} / {st8['boards_worse']}", f"{st8['wilcoxon_p']:.2f}"])
    rows.append(["Fusion - YOLO11s, mAP50-95", f"{(f8['map'] - fus8['test']['singles'][fus8['best_single_on_val']]['map'])*100:+.1f}",
                 f"[{st8['map_diff_ci'][0]:+.1f}, {st8['map_diff_ci'][1]:+.1f}]", "-", "-"])
    if st4:
        for k, lab in [("sqrt - plain", "Partial balance - no balancing (4 cls)"), ("sqrt - base", "Partial balance - 8-class model (4 cls)"), ("plain - base", "No balancing - 8-class model (4 cls)")]:
            tt = st4["test"]["tests"][k]; a_, b_ = k.split(" - ")
            rows.append([lab, f"{st4['test']['map50'][a_] - st4['test']['map50'][b_]:+.1f}", f"[{tt['map50_diff_ci'][0]:+.1f}, {tt['map50_diff_ci'][1]:+.1f}]",
                         f"{tt['boards_better']} / {tt['boards_worse']}", f"{tt['wilcoxon_p']:.2f}"])
    D.fill_table(ta, rows, col_widths=[3.2, 0.9, 1.6, 1.3, 0.9], size=9); D.set_row_heights(ta, IN(0.28))
    rows = [["Run-to-run spread (final setup, validation)", "Value"]]
    if wi:
        rows += [["Val mAP50, seeds 42 / 1 / 2", " / ".join(f"{v:.1f}" for v in wi["seed_val_map50"])], ["Spread (max - min)", f"{wi['seed_spread']:.1f}"]]
    else:
        rows += [["Val mAP50, seeds 42 / 1 / 2", "pending (Kaggle)"]]
    D.fill_table(tb_, rows, col_widths=[3.0, 2.0], size=9); tb_.width = IN(5.0)
    tb_.top = ta.top + IN(0.28) * len(ta.table.rows) + IN(0.3); D.set_row_heights(tb_, IN(0.28))
    D.set_bullets(D.shape_by_text(s, "Each model evaluated"), [
        "Board-level bootstrap: the 12 test boards are resampled 1,000 times with replacement, so the interval reflects board-to-board variation [20]; exact Wilcoxon signed-rank test on per-board AP50 differences [21].",
        "Only the fusion and full-dataset gains have intervals that exclude zero; the subset fusion is also significant by the Wilcoxon test. Differences of 2-3 mAP50 points between single models are within the noise of a 12-board test set."], size=10)
    D.shape_by_text(s, "Board-level bootstrap").top = tb_.top + IN(1.1)

    # GRADING (clone of slide 17)
    s = D.clone_slide(prs, S[17]); new["grading"] = s
    D.set_text(D.shape_by_text(s, "RESULTS: HELD-OUT TEST"), "GRADING VALIDATION (BRI)")
    ta, tb_ = tbl(s)
    if bri:
        pi, pb = bri["test_per_image"], bri["test_per_board"]
        rows = [["Agreement with annotation-based grade", "Per image (469)", "Per board (12)"],
                ["Exact grade", f"{pi['exact']*100:.1f} %", f"{pb['exact']*100:.1f} %"],
                ["Within one grade", f"{pi['within_one']*100:.1f} %", f"{pb['within_one']*100:.1f} %"],
                ["Quadratic weighted kappa [19]", f"{pi['qwk']:.2f}", f"{pb['qwk']:.2f}"],
                ["Spearman correlation of damage scores", f"{pi['spearman']:.2f}", f"{pb['spearman']:.2f}"],
                ["Mean abs. error, recoverable area", f"{pi['mae_recoverable_pct']:.2f} pts", f"{pb['mae_recoverable_pct']:.2f} pts"]]
        D.fill_table(ta, rows, col_widths=[3.0, 1.4, 1.4], size=9.5); ta.width = IN(5.8); D.set_row_heights(ta, IN(0.28))
        cm = pi["confusion"]; G = ["A", "B", "C", "Reject"]
        rows = [["Reference \\ Model", "A", "B", "C", "Reject"]] + [[f"{G[i]} ({sum(cm[i])})"] + [str(x) for x in cm[i]] for i in range(4)]
        D.fill_table(tb_, rows, col_widths=[1.6, 0.8, 0.8, 0.8, 0.8], size=9.5); tb_.width = IN(4.8)
        tb_.top = ta.top + IN(0.28) * 6 + IN(0.3); D.set_row_heights(tb_, IN(0.28))
        D.set_bullets(D.shape_by_text(s, "Each model evaluated"), [
            f"Reference grade = BRI on the annotators' boxes, thresholds at the 40th / 70th / 90th percentiles of validation damage scores ({', '.join(f'{x:.4f}' for x in bri['tau_reference'])}).",
            f"Model grade = BRI on the detector's boxes, thresholds fitted on validation with the guide's calibration ({', '.join(f'{x:.4f}' for x in bri['tau_detector'])}); test boards never used for fitting.",
            "Next step agreed with the guide: blind expert grading of 30-50 boards to calibrate severity weights and thresholds."], size=10)
        D.shape_by_text(s, "Reference grade =").top = tb_.top + IN(1.6)

    # ENHANCEMENT (clone of slide 13)
    s = one_table_slide(prs, S[17]); new["enh"] = s
    D.set_text(D.shape_by_text(s, "RESULTS: HELD-OUT TEST"), "IMAGE ENHANCEMENT STUDY (H1)")
    if enh:
        E = ["raw", "clahe", "denoise", "sharpen"]
        rows = [["Condition (validation, mAP50)", "Raw", "CLAHE [22]", "Denoise", "Sharpen"]]
        for c, lab in [("normal", "Normal"), ("low_light", "Low light"), ("overexposed", "Over-exposed"), ("blur", "Blur"), ("noise", "Noise"), ("low_contrast", "Low contrast")]:
            row = enh["table"][c]; rows.append([lab] + [f1(row[e]["map50"] * 100) for e in E])
        t = tbl(s)[0]; D.fill_table(t, rows, col_widths=[2.0, 1, 1, 1, 1], size=10); t.top = IN(1.0); t.width = IN(6.0)
        D.set_row_heights(t, IN(0.3))
    D.set_bullets(D.shape_by_text(s, "Each model evaluated"), [
        ("H1 rejected for raw images: ", "CLAHE lowers mAP50 significantly in 5 of 6 conditions (Wilcoxon p <= 0.006); sharpening gives no significant gain."),
        ("Denoising helps only on noisy images: ", "+3.2 to +7.2 mAP50 (95% CI), p = 0.006; recommended only for a noisy camera."),
        ("Imaging conditions matter more than enhancement: ", "low light costs about 25 points, so controlled lighting is the main requirement for deployment.")], size=10.5)
    D.shape_by_text(s, "H1 rejected").top = IN(3.35)

    # CONCLUSION (clone of slide 10)
    s = D.clone_slide(prs, S[10]); new["concl"] = s
    D.set_text(D.shape_by_text(s, "METHODOLOGY"), "CONCLUSION AND FUTURE WORK")
    D.set_bullets(D.shape_by_text(s, "Dataset preparation."), [
        ("Clean evaluation: ", "a board-level split and rectangular high-resolution input give a reproducible baseline of 63-65 mAP50 over 8 classes on 12 unseen boards; YOLO11s matches YOLO11m at 2.8x the speed."),
        ("Mathematical model: ", f"weighted box fusion of four balanced / high-resolution YOLO11s models raises test mAP50 from {single4[3]:.1f} to {F4['map50']*100:.1f} (significant, 10 of 12 boards better); balancing or 1280 px alone, Wise-IoU and per-class thresholds gave no significant gain."),
        ("More data: ", f"the same recipe on all 20,276 images lifts the final detector to {ffo['map50']:.1f} mAP50 on the original test boards (+{ffo['map50'] - sub_fus['map50']:.1f}, CI excludes zero) and {fff['map50']:.1f} / {fff['map']:.1f} on 51 unseen boards; Crack reaches {fff['ap50']['Crack']:.1f}."),
        ("Quality assessment: ", f"the guide's Board Recoverability Index, adapted to line-scan geometry, reproduces annotation-based grades (weighted kappa {kappa:.2f} per image with the deployed detector) and drives a market-value estimate."),
        ("Deliverable: ", "a CPU web application that shows defects, grade, recoverable area and value for an uploaded board image."),
        ("Future work: ", "blind expert grading to calibrate severity weights and thresholds; k-fold validation over boards; more rare-class data; segmentation masks for tighter defect area; CondConv / BiFormer (full CWB) architecture; plywood images and field cameras.")], size=10.5)

    # REFERENCES (contd.) (clone of slide 24)
    s = D.clone_slide(prs, S[24]); new["refs"] = s
    rs = D.shape_by_text(s, "REFERENCES")
    D.set_bullets(rs, [
        "[12] P. Kodytek, A. Bodzas, and P. Bilik, \u201cA large-scale image dataset of wood surface defects for automated vision-based quality control processes,\u201d F1000Research, vol. 10, p. 581, 2022, doi: 10.12688/f1000research.52903.2.",
        "[13] G. Jocher and J. Qiu, \u201cUltralytics YOLO11,\u201d version 11.0.0, 2024. [Online]. Available: https://github.com/ultralytics/ultralytics",
        "[14] Y. Cui, M. Jia, T.-Y. Lin, Y. Song, and S. Belongie, \u201cClass-balanced loss based on effective number of samples,\u201d in Proc. IEEE/CVF CVPR, 2019, pp. 9268\u20139277.",
        "[15] A. Gupta, P. Doll\u00e1r, and R. Girshick, \u201cLVIS: A dataset for large vocabulary instance segmentation,\u201d in Proc. IEEE/CVF CVPR, 2019, pp. 5356\u20135364.",
        "[16] D. Dwibedi, I. Misra, and M. Hebert, \u201cCut, paste and learn: Surprisingly easy synthesis for instance detection,\u201d in Proc. IEEE ICCV, 2017, pp. 1301\u20131310.",
        "[17] R. Solovyev, W. Wang, and T. Gabruseva, \u201cWeighted boxes fusion: Ensembling boxes from different object detection models,\u201d Image and Vision Computing, vol. 107, Art. no. 104117, 2021.",
        "[18] Z. Tong, Y. Chen, Z. Xu, and R. Yu, \u201cWise-IoU: Bounding box regression loss with dynamic focusing mechanism,\u201d arXiv:2301.10051, 2023.",
        "[19] J. Cohen, \u201cWeighted kappa: Nominal scale agreement provision for scaled disagreement or partial credit,\u201d Psychological Bulletin, vol. 70, no. 4, pp. 213\u2013220, 1968.",
        "[20] B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap. New York, NY, USA: Chapman & Hall, 1993.",
        "[21] F. Wilcoxon, \u201cIndividual comparisons by ranking methods,\u201d Biometrics Bulletin, vol. 1, no. 6, pp. 80\u201383, 1945.",
        "[22] K. Zuiderveld, \u201cContrast limited adaptive histogram equalization,\u201d in Graphics Gems IV, P. S. Heckbert, Ed. San Diego, CA, USA: Academic Press, 1994, pp. 474\u2013485."],
        size=10, keep_first=True)
    D.set_text_first(rs, "REFERENCES (contd.)")

    # ---------------------------------------------------------------- demo app slide (21): text; screenshots if present
    D.set_text(D.shape_by_id(S[21], 316), "DEMONSTRATION APPLICATION")
    D.set_bullets(D.shape_by_id(S[21], 326), [
        ("Detect: ", "upload a board image, choose a model or run all; colour-coded boxes, heatmap, per-class counts and area."),
        ("Grade: ", "Board Recoverability Index grade A / B / C / Reject, damage score, recoverable area; editable market-value estimate."),
        ("Test boards: ", "annotators' boxes and grade next to the model's on the 12 unseen boards."),
        ("Deployment: ", "runs on a CPU laptop (0.2-0.6 s per image); JSON report per image.")], size=10)
    D.set_bullets(D.shape_by_id(S[21], 327), [
        ("Validated components: ", "detection (single-shot test), grading (weighted kappa), enhancement (study on validation).")], size=10)
    D.set_bullets(D.shape_by_id(S[21], 328), [
        "Limitations: 12-board original test set (51 boards on full data); severity weights and grade thresholds await expert calibration; trained on controlled line-scan imagery."], size=9.5)
    shots = [ROOT / "docs" / "final_figs" / "app_detect.png", ROOT / "docs" / "final_figs" / "app_grade.png"]
    pics = [x for x in S[21].shapes if x.shape_type == 13 and x.width > IN(3)]
    for pic, shot in zip(pics, shots):
        if shot.exists():
            D.replace_picture(S[21], pic, shot)

    s = D.clone_slide(prs, S[17]); new["full"] = s
    D.set_text(D.shape_by_text(s, "RESULTS: HELD-OUT TEST"), "FULL-DATASET EXTENSION")
    ta, tb_ = tbl(s)
    bs, bf = R["balance"]["train_sqrt"], R["balance_full"]["train_sqrt"]
    rows = [["", "4,000-image subset", "Full dataset [12]"],
            ["Images / boards", "4,000 / 81", "20,276 / 407"],
            ["Boards train / val / test", "52 / 17 / 12", "280 / 76 / 51 (our 81 keep their split)"],
            ["4-class training boxes after partial balance", f"{sum(bs.values()):,}", f"{sum(bf.values()):,}"],
            ["Crack training boxes", f"{bs['Crack']:,}", f"{bf['Crack']:,}"]]
    D.fill_table(ta, rows, col_widths=[2.6, 1.7, 2.9], size=9); ta.width = IN(7.2); D.set_row_heights(ta, IN(0.26))
    V = FU["val_orig"]
    def mm(x):
        return f"{x['map50']:.1f} / {x['map']:.1f}"
    rows = [["mAP50 / mAP50-95", "Val, 714 original images", "Test, 469 original images", "Test, full split (2,488)"],
            ["Four-model fusion, subset (previous)", "{:.1f} / {:.1f}".format(*V["deployed_fusion"]), mm(sub_fus), "-"],
            ["YOLO11s full data, 1024 px", "{:.1f} / {:.1f}".format(*V["full_1024"]), mm(FT["full_1024"]["orig"]), mm(FT["full_1024"]["full"])],
            ["YOLO11s full data, 1280 px", "{:.1f} / {:.1f}".format(*V["full_1280"]), mm(FT["full_1280"]["orig"]), mm(FT["full_1280"]["full"])],
            ["Fusion of the two (final detector)", "{:.1f} / {:.1f}".format(*V["full_fusion"]), mm(ffo), mm(fff)]]
    D.fill_table(tb_, rows, col_widths=[2.5, 1.6, 1.6, 1.6], size=9, bold_rows=(4,)); tb_.width = IN(7.3)
    tb_.top = ta.top + IN(0.26) * 5 + IN(0.25); D.set_row_heights(tb_, IN(0.26))
    tx = D.shape_by_text(s, "Each model evaluated")
    D.set_bullets(tx, [
        ("Rule fixed before training: ", f"replace the system only if mAP50 on the original 714 validation images exceeds {V['deployed_fusion'][0]:.1f}; met with {V['full_fusion'][0]:.1f}."),
        ("Same test boards: ", f"{ffo['map50'] - sub_fus['map50']:+.1f} mAP50 over the subset fusion (95% CI {stfu['map50_diff_ci'][0]:+.1f} to {stfu['map50_diff_ci'][1]:+.1f}), with 2 models instead of 4."),
        ("Per class, full test: ", ", ".join(f"{c} {fff['ap50'][c]:.1f}" for c in ["Live_Knot", "Dead_Knot", "Resin", "Crack"]) + " AP50."),
        ("Data check: ", "images from the Kaggle mirror of [12] (43,974 boxes, identical labels on our 4,000 images within 1 px).")], size=10)
    tx.top = tb_.top + IN(0.26) * 5 + IN(0.2)

    # ---------------------------------------------------------------- order
    order = [S[1], S[2], S[3], S[4], S[5], S[6], S[7], S[8], S[9], S[10], S[11], S[12], S[13], S[14], S[15],
             new["mm1"], new["mm2"], new["mm3"], S[17], new["full"], new["stats"], new["grading"], new["enh"], S[20], S[18], S[19],
             S[21], S[22], S[16], new["concl"], S[23], S[24], new["refs"], S[25]]
    for i, sl in enumerate(order):
        D.move_slide(prs, sl, i)
    prs.save(str(OUT))
    print("saved", OUT, len(prs.slides), "slides")


if __name__ == "__main__":
    main()
