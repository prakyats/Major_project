## Board-level bootstrap, val split (17 boards, 714 images, B=2000, seed 42)

| Model | mAP50 | 95% CI | mAP50-95 | 95% CI | Live_Knot AP50 [95% CI] | Dead_Knot AP50 [95% CI] | Resin AP50 [95% CI] | Crack AP50 [95% CI] |
|---|---:|---|---:|---|---|---|---|---|
| 8-class YOLO11s baseline (4 classes scored) | 72.4 | [66.1, 79.3] | 34.7 | [30.8, 39.8] | 75.6 [70.1, 80.5] | 79.3 [73.5, 86.1] | 75.3 [67.4, 86.9] | 59.5 [41.6, 76.0] |
| 4-class plain | 71.0 | [65.1, 78.2] | 34.5 | [31.1, 38.7] | 77.4 [72.4, 81.9] | 78.7 [72.8, 85.4] | 73.7 [65.1, 87.4] | 54.2 [37.6, 69.3] |
| 4-class sqrt-balanced | 73.8 | [68.0, 80.8] | 35.4 | [31.5, 40.2] | 79.1 [73.8, 84.4] | 78.0 [72.6, 84.1] | 79.3 [73.6, 90.9] | 58.7 [42.6, 74.1] |

| Difference (paired) | mAP50 diff | 95% CI | share of resamples with diff <= 0 | Crack AP50 diff | 95% CI |
|---|---:|---|---:|---:|---|
| 4-class plain minus 8-class YOLO11s baseline (4 classes scored) | -1.4 | [-2.8, +0.5] | 0.92 | -5.3 | [-10.0, +1.4] |
| 4-class sqrt-balanced minus 8-class YOLO11s baseline (4 classes scored) | +1.3 | [-0.4, +4.5] | 0.07 | -0.8 | [-5.4, +6.5] |
| 4-class sqrt-balanced minus 4-class plain | +2.8 | [+0.0, +6.4] | 0.02 | +4.5 | [-0.7, +11.3] |
