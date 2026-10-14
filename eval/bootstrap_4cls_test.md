## Board-level bootstrap, test split (12 boards, 469 images, B=2000, seed 42)

| Model | mAP50 | 95% CI | mAP50-95 | 95% CI | Live_Knot AP50 [95% CI] | Dead_Knot AP50 [95% CI] | Resin AP50 [95% CI] | Crack AP50 [95% CI] |
|---|---:|---|---:|---|---|---|---|---|
| 8-class YOLO11s baseline (4 classes scored) | 66.3 | [57.7, 78.3] | 32.0 | [27.9, 37.8] | 71.2 [65.4, 77.0] | 85.4 [77.8, 90.0] | 56.9 [39.9, 83.7] | 51.8 [33.1, 71.0] |
| 4-class plain | 68.4 | [60.8, 79.1] | 32.6 | [29.1, 38.1] | 72.2 [64.5, 77.2] | 85.0 [77.6, 89.2] | 59.8 [45.6, 84.8] | 56.3 [40.0, 74.6] |
| 4-class sqrt-balanced | 68.2 | [61.1, 78.9] | 32.8 | [28.4, 39.8] | 75.3 [69.3, 79.8] | 84.1 [74.2, 89.2] | 64.1 [47.6, 87.4] | 49.2 [35.6, 67.8] |

| Difference (paired) | mAP50 diff | 95% CI | share of resamples with diff <= 0 | Crack AP50 diff | 95% CI |
|---|---:|---|---:|---:|---|
| 4-class plain minus 8-class YOLO11s baseline (4 classes scored) | +2.0 | [-1.5, +4.4] | 0.13 | +4.5 | [-3.7, +10.6] |
| 4-class sqrt-balanced minus 8-class YOLO11s baseline (4 classes scored) | +1.9 | [-1.4, +4.5] | 0.11 | -2.6 | [-7.1, +4.5] |
| 4-class sqrt-balanced minus 4-class plain | -0.2 | [-2.1, +2.6] | 0.53 | -7.2 | [-10.6, +0.6] |
