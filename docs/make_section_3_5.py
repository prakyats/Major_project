"""
make_section_3_5.py - section 3.5 (Proposed Algorithm and Techniques) of the Phase-I report rewritten with proper,
numbered Word equations (guide's suggestion: make the formulas clear and separate from the description).
Built through Word so the equations are native, editable Office Math. Output: Major_Project/docs/Section_3.5_Formulas.docx
"""
import win32com.client

OUT = r"C:\Users\ASUS\Desktop\Major_Project\docs\Section_3.5_Formulas.docx"
FONT = "Times New Roman"

w = win32com.client.DispatchEx("Word.Application"); w.Visible = False; w.DisplayAlerts = 0
doc = w.Documents.Add()


def put(text, bold=False, italic=False, sub=False, sup=False, size=12):
    """append a run of text at the end of the document"""
    e = doc.Content; e.Collapse(0); a = e.Start
    e.InsertAfter(text)
    r = doc.Range(a, a + len(text))
    r.Font.Name = FONT; r.Font.Size = size; r.Font.Bold = bold; r.Font.Italic = italic
    r.Font.Subscript = sub; r.Font.Superscript = sup


def end_para(align=3, space_after=6, indent=0):
    """align: 0 left, 1 centre, 3 justify"""
    p = doc.Paragraphs(doc.Paragraphs.Count)
    p.Alignment = align; p.SpaceAfter = space_after; p.SpaceBefore = 0; p.LeftIndent = indent
    doc.Content.InsertParagraphAfter()


def para(text, lead=None, align=3, size=12, bold=False, italic=False, space_after=6):
    if lead:
        put(lead, bold=True, size=size)
    put(text, bold=bold, italic=italic, size=size)
    end_para(align, space_after)


def eq(linear):
    """one displayed equation, centred, number on the right; 'linear' is Word UnicodeMath (# = equation number)"""
    e = doc.Content; e.Collapse(0); a = e.Start
    e.InsertAfter(linear)
    om = doc.OMaths.Add(doc.Range(a, a + len(linear)))
    om.OMaths(1).BuildUp()
    p = doc.Paragraphs(doc.Paragraphs.Count); p.SpaceAfter = 6; p.SpaceBefore = 3
    doc.Content.InsertParagraphAfter()


def symbol(base, sub=None, sup=None):
    put(base, italic=len(base) == 1)
    if sub:
        put(sub, italic=len(sub) <= 2, sub=True)
    if sup:
        put(sup, sup=True)


def where(rows):
    """rows: ([(base, sub, sup), ...], meaning) - symbols with real subscripts, then the meaning"""
    put("where", italic=True); end_para(0, 0)
    for syms, meaning in rows:
        for k, s in enumerate(syms):
            if k:
                put(", ")
            symbol(*s)
        put("  \u2013  " + meaning)
        end_para(0, 0, indent=36)
    doc.Paragraphs(doc.Paragraphs.Count - 1).SpaceAfter = 8


try:
    st = doc.Styles(-1)
    st.Font.Name = FONT; st.Font.Size = 12
    st.ParagraphFormat.SpaceAfter = 6; st.ParagraphFormat.SpaceBefore = 0

    para("3.5 Proposed Algorithm and Techniques", bold=True, size=14, align=0, space_after=8)
    para("The proposed system combines four techniques: a class-balancing rule for the training data, weighted box fusion of "
         "two detectors, the Board Recoverability Index (BRI) for grading, and statistical validation of every result. Each "
         "technique is described below, followed by its formula.")

    # (a) class balancing
    para("(a) Class balancing", bold=True, align=0, space_after=4)
    para("Rare defect classes receive extra training examples. The target number of boxes for each class follows the "
         "repeat-factor rule of LVIS [15], related to the effective number of samples [14]:")
    eq("n_c^\u2217=\u221a(n_c\u2009n_\"max\" )#(3.1)")
    where([([("n", "c", None)], "number of training boxes of class c"),
           ([("n", "max", None)], "number of training boxes of the most frequent class"),
           ([("n", "c", "*")], "target number of boxes for class c after balancing")])
    para("The extra boxes are created by pasting real defect crops onto defect-free training boards, only inside the board "
         "area, without rotation, with Poisson or feathered blending [16]. Only the training split is modified.")

    # (b) weighted box fusion
    para("(b) Weighted box fusion", bold=True, align=0, space_after=4)
    para("Boxes of the same class that overlap between the two detectors are grouped into a cluster and merged into one "
         "box [17]. The fused box and its confidence are:")
    eq("b_f=(\u2211_i \u3016w_i\u2009c_i\u2009b_i\u3017)/(\u2211_i \u3016w_i\u2009c_i\u3017)#(3.2)")
    eq("c_f=(\u2211_i \u3016w_i\u2009c_i\u3017)/(\u2211_i \u3016w_i\u3017)\u00b7\"min\"(\u2211_i \u3016w_i\u3017,W)/W#(3.3)")
    where([([("b", "i", None), ("c", "i", None)], "box coordinates and confidence of the i-th box in the cluster"),
           ([("w", "i", None)], "weight of the model that produced box i"),
           ([("W", None, None)], "sum of the weights of all models"),
           ([("b", "f", None), ("c", "f", None)], "fused box and fused confidence")])
    para("A defect found by only one model therefore receives a lower confidence than one confirmed by both models.")

    # (c) BRI
    para("(c) Board Recoverability Index (BRI)", bold=True, align=0, space_after=4)
    para("Each detected defect i receives an influence score that combines its severity, the model's confidence and its "
         "position on the board; defects near a side edge can be trimmed off and therefore count less:")
    eq("s_i=w_c\u2009\u00b7\u2009\"conf\"_i\u2009\u00b7\u2009p_i#(3.4)")
    eq("p_i=1\u2212e^(\u2212d_i/\u03bb),\u2003\u03bb=250\u2009\"px\"#(3.5)")
    where([([("w", "c", None)], "severity weight of the defect class: Crack 1.00, Dead_Knot 0.60, Live_Knot 0.40, Resin 0.30"),
           ([("conf", "i", None)], "confidence of the detection"),
           ([("p", "i", None)], "position penalty (0 at the board edge, close to 1 at the centre)"),
           ([("d", "i", None)], "distance from the defect centre to the nearest side edge of the board")])
    para("The influence map keeps the largest score at every pixel, so overlapping defects are counted once. The damage "
         "score (DIS) and the recoverable area are:")
    eq("\"DIS\"=(\u2211_((x,y)) \u3016I(x,y)\u3017)/A_\"board\" ,\u2003I(x,y)=\"max\"_i\u2061s_i#(3.6)")
    eq("A_\"rec\"=A_\"board\"\u2009(1\u2212\"DIS\")#(3.7)")
    where([([("I(x, y)", None, None)], "highest influence score at pixel (x, y)"),
           ([("A", "board", None)], "board area in pixels (wood only, background excluded)"),
           ([("A", "rec", None)], "recoverable area of the board")])
    para("The grade follows from the damage score and three thresholds fitted on the validation boards:")
    eq("\"Grade\"={\u25a0(\"A\",&\"DIS\"<t_1@\"B\",&t_1\u2264\"DIS\"<t_2@\"C\",&t_2\u2264\"DIS\"<t_3@\"Reject\",&\"DIS\"\u2265t_3 )\u2524#(3.8)")
    where([([("t", "1", None), ("t", "2", None), ("t", "3", None)],
            "grade thresholds fitted on the validation boards (0.0012, 0.0032 and 0.0099 for the final detector)")])
    para("Our implementation reproduces the guide's worked example exactly (DIS = 0.020860, grade B).")

    # (d) statistics
    para("(d) Statistical validation", bold=True, align=0, space_after=4)
    para("Every improvement is reported with a 95% confidence interval from a board-level bootstrap, in which the test boards "
         "are resampled 1,000 times [20], and tested with the exact Wilcoxon signed-rank test on per-board differences [21]. "
         "Agreement between the model's grades and the annotation-based grades is measured by the quadratic weighted kappa [19]:")
    eq("\u03ba_w=1\u2212(\u2211_(i,j) \u3016w_ij\u2009O_ij\u3017)/(\u2211_(i,j) \u3016w_ij\u2009E_ij\u3017),\u2003w_ij=(i\u2212j)^2/(k\u22121)^2#(3.9)")
    where([([("O", "ij", None)], "number of boards with reference grade i and model grade j"),
           ([("E", "ij", None)], "number expected by chance"),
           ([("k", None, None)], "number of grades (4)")])

    doc.SaveAs2(OUT, 16)
    doc.ExportAsFixedFormat(OUT.replace(".docx", ".pdf"), 17)
    print("saved", OUT, "equations:", doc.OMaths.Count)
finally:
    doc.Close(False); w.Quit()
