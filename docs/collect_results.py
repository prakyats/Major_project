"""
collect_results.py - gather every number the final deck quotes into docs/final_results.json, from the result files
in eval/ and runs_log/ (missing items stay null and the deck prints "pending"). Run from the repo root.
"""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def metrics(path):
    """evaluate.py csv -> {class: [P, R, F1, mAP50, mAP50-95]}"""
    p = ROOT / path
    if not p.exists():
        return None
    rows = list(csv.reader(open(p, encoding="utf-8")))
    return {r[0]: [float(x) for x in r[1:6]] for r in rows[1:]}


def js(path):
    p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def results_csv(path):
    p = ROOT / path
    if not p.exists():
        return None
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    k = {x.strip(): x for x in rows[0]}
    m50 = [float(r[k["metrics/mAP50(B)"]]) for r in rows]; m95 = [float(r[k["metrics/mAP50-95(B)"]]) for r in rows]
    fit = [0.1 * a + 0.9 * b for a, b in zip(m50, m95)]
    b = max(range(len(fit)), key=fit.__getitem__)
    return dict(epochs=len(rows), best_epoch=b + 1)


R = {}
R["test8"] = {"YOLO11m": metrics("eval/yolo11m_final/test_metrics.csv"), "YOLO11s": metrics("eval/yolo11s_baseline/test_metrics.csv")}
R["fusion8"] = js("eval/math_model/8cls_m_s.json")
models4 = {"plain_1024": "yolo11s_4cls_plain", "full_1024": "yolo11s_4cls_full", "sqrt_1024": "yolo11s_4cls_sqrt",
           "sqrt_1280": "yolo11s_4cls_sqrt_1280", "plain_1280": "yolo11s_4cls_plain_1280"}
R["val4"] = {k: metrics(f"eval/{v}/val_metrics.csv") for k, v in models4.items()}
R["test4"] = {k: metrics(f"eval/{v}/test_metrics.csv") for k, v in models4.items()}
R["runs4"] = {k: results_csv(f"runs_log/{d}/results.csv") for k, d in {
    "plain_1024": "run4_yolo11s_4cls_plain_v1", "full_1024": "run4_yolo11s_4cls_full_v1", "sqrt_1024": "run4_yolo11s_4cls_sqrt_v1",
    "sqrt_1280": "run5_yolo11s_4cls_sqrt_1280_v1", "plain_1280": "run5_yolo11s_4cls_plain_1280_v1"}.items()}
R["hours4"] = (js("runs_log/run4_4cls_kaggle_v1/runs_done.json") or {}).get("hours")
R["sel1280"] = js("runs_log/run5_4cls_1280_v1/selection.json")
R["hours1280"] = (js("runs_log/run5_4cls_1280_v1/runs_done.json") or {}).get("hours")
R["fusion4"] = js("eval/math_model/4cls_fusion.json")
R["stats4"] = js("eval/stats_4cls.json")
R["final"] = js("docs/final_model.json")
fin = R["final"] or {}
R["bri"] = js(f"eval/bri/bri_validation_{fin.get('bri_tag', 'yolo11s_4cls_balanced_1024')}.json")
R["enh"] = js(f"eval/enhancement/{fin.get('enh_tag', 'yolo11s_4cls_balanced_1024')}.json")
R["wiou"] = js("runs_log/run6_final_wiou_seeds_v1/selection.json")
R["balance"] = js("runs_log/run4_4cls_kaggle_v1/balance_report.json")
out = ROOT / "docs" / "final_results.json"
out.write_text(json.dumps(R, indent=1), encoding="utf-8")
print("written", out, {k: (v is not None) for k, v in R.items()})
