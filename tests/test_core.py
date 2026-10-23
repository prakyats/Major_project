"""Unit tests (white box) for the grading (BRI), fusion and evaluation helpers. Run: python -m pytest tests --cov"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bri
from eval_capture import iou_matrix, match, wilcoxon_exact
from math_model import wbf_image


def test_bri_reproduces_guide_worked_example():
    dets = [("Crack", 0.90, (1300, 480, 1700, 600)), ("Knot_with_crack", 0.85, (1600, 500, 1900, 640)),
            ("Live_Knot", 0.85, (60, 300, 180, 420)), ("Resin", 0.60, (2500, 60, 2620, 130))]
    r = bri.board_report(dets, (1024, 2800), None, edges="image", taus=(0.01, 0.03, 0.06))
    assert abs(r["DIS"] - 0.020860) < 1e-5 and r["grade"] == "B" and r["union_px"] == 102800


def test_bri_clean_board_is_grade_a():
    r = bri.board_report([], (1024, 2800), None, edges="image", taus=(0.01, 0.03, 0.06))
    assert r["DIS"] == 0 and r["grade"] == "A" and r["recoverable_pct"] == 100


def test_grade_thresholds():
    taus = (0.0012, 0.0032, 0.0099)
    assert [bri.grade(x, taus) for x in (0.0, 0.002, 0.005, 0.0165)] == ["A", "B", "C", "Reject"]


def test_position_penalty_grows_away_from_edge():
    near = bri.position_penalty((10, 400, 60, 500), 2800, 1024, 0, 2800)
    far = bri.position_penalty((1375, 400, 1425, 500), 2800, 1024, 0, 2800)
    assert 0 <= near < far <= 1


def test_quadratic_weighted_kappa_perfect_and_chance():
    a = [0, 1, 2, 3, 0, 1, 2, 3]
    assert abs(bri.quadratic_weighted_kappa(a, a) - 1.0) < 1e-9
    assert bri.quadratic_weighted_kappa(a, a[::-1]) < 0.5


def test_iou_matrix_identity_and_disjoint():
    m = iou_matrix([[0, 0, 10, 10]], [[0, 0, 10, 10], [20, 20, 30, 30]])
    assert abs(m[0, 0] - 1) < 1e-6 and m[0, 1] == 0


def test_wbf_merges_agreeing_boxes_and_downweights_single_model_boxes():
    a = dict(pred_boxes=[[0, 0, 10, 10]], pred_conf=[0.8], pred_cls=[1])
    b = dict(pred_boxes=[[1, 1, 11, 11], [50, 50, 60, 60]], pred_conf=[0.8, 0.8], pred_cls=[1, 1])
    boxes, conf, cls = wbf_image([a, b], [1, 1], 0.55)
    assert len(boxes) == 2                       # the two agreeing boxes merge, the lone box stays
    lone = conf[[i for i, bx in enumerate(boxes) if bx[0] > 40][0]]
    merged = conf[[i for i, bx in enumerate(boxes) if bx[0] < 40][0]]
    assert merged > lone                         # seen by one model only -> lower confidence


def test_match_counts_true_positive_once():
    iou = np.array([[0.9, 0.7]])                 # one ground-truth box, two predictions of the same class
    tp = match([0, 0], [0], iou)
    assert tp[:, 0].sum() == 1


def test_wilcoxon_exact_all_positive_is_small_p():
    assert wilcoxon_exact(np.arange(1, 13, dtype=float))["p"] < 0.01
