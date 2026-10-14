"""
bri_validate_fused.py - BRI validation for the deployed detector (WBF of the four 4-class YOLO11s models).
Builds fused predictions from the validator captures (eval_capture.py) with the fusion settings chosen on validation
(eval/math_model/4cls_fusion.json), writes them in bri_validate.py's prediction-cache format, then runs bri_validate.
"""
import json, sys, subprocess
from pathlib import Path
from eval_capture import capture
from math_model import fuse

MODELS = [("weights/yolo11s_4cls_balanced.pt", "dataset_4cls/data_sqrt.yaml", 1024),
          ("weights/yolo11s_4cls_plain.pt", "dataset_4cls/data_plain.yaml", 1024),
          ("weights/yolo11s_4cls_sqrt_1280.pt", "dataset_4cls/data_sqrt.yaml", 1280),
          ("weights/yolo11s_4cls_plain_1280.pt", "dataset_4cls/data_plain.yaml", 1280)]
cfg = json.loads(Path("eval/math_model/4cls_fusion.json").read_text())["chosen"]
NAMES = ["Live_Knot", "Dead_Knot", "Resin", "Crack"]
for split in ["val", "test"]:
    caps = [capture(w, d, split, s) for w, d, s in MODELS]
    fused = fuse(caps, cfg["weights"], cfg["t_iou"])
    out = {s: [(NAMES[k], c, b) for b, c, k in zip(im["pred_boxes"], im["pred_conf"], im["pred_cls"]) if c >= 0.25]
           for s, im in fused.items()}
    Path(f"eval/bri/pred_fusion4_1024_{split}.json").write_text(json.dumps(out))
sys.exit(subprocess.call([sys.executable, "bri_validate.py", "--weights", "weights/fusion4.pt", "--imgsz", "1024"]))
