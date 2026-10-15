"""
bri_validate_full.py - BRI validation for the final detector: WBF of the two full-dataset YOLO11s 4-class models
(1024 + 1280, NOTES.md section 23b). Fused predictions are built from the Kaggle validator captures on the ORIGINAL
validation / test images (same boards and labels as every earlier BRI validation), with the fusion settings chosen on
the full validation split (eval/math_model/full_dataset.json), then bri_validate.py runs unchanged.
"""
import glob, json, sys, subprocess
from pathlib import Path
from math_model import fuse
from eval_full import new

cfg = json.loads(Path("eval/math_model/full_dataset.json").read_text())["chosen"]
NAMES = ["Live_Knot", "Dead_Knot", "Resin", "Crack"]
for split in ["val", "test"]:
    local = {Path(p).stem.split("_", 1)[1]: Path(p).stem for p in glob.glob(f"dataset_4cls/{split}/images/*.jpg")}
    fused = fuse(new(f"{split}_orig"), cfg["weights"], cfg["t_iou"])
    assert {s.split("_", 1)[1] for s in fused} == set(local), split
    out = {local[s.split("_", 1)[1]]: [(NAMES[k], c, b) for b, c, k in zip(im["pred_boxes"], im["pred_conf"], im["pred_cls"]) if c >= 0.25]
           for s, im in fused.items()}
    Path(f"eval/bri/pred_fusion_full_1024_{split}.json").write_text(json.dumps(out))
sys.exit(subprocess.call([sys.executable, "bri_validate.py", "--weights", "weights/fusion_full.pt", "--imgsz", "1024"]))
