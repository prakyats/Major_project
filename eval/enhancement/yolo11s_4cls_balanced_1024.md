| condition | raw | clahe | denoise | sharpen |
|---|---|---|---|---|
| normal | 74.8 | 65.8 | 75.3 | 73.8 |
| low_light | 50.0 | 27.7 | 48.0 | 49.3 |
| overexposed | 58.2 | 47.9 | 58.2 | 57.7 |
| blur | 73.3 | 62.2 | 72.9 | 75.1 |
| noise | 67.8 | 56.5 | 73.0 | 57.0 |
| low_contrast | 61.3 | 62.6 | 61.6 | 62.6 |

| comparison | mAP50 diff 95% CI | boards better / worse | Wilcoxon p |
|---|---|---|---:|
| normal: clahe - raw | [-11.2, -6.5] | 3 / 14 | 0.006 |
| normal: denoise - raw | [-1.0, +1.7] | 10 / 7 | 0.080 |
| normal: sharpen - raw | [-3.5, +0.3] | 4 / 12 | 0.083 |
| low_light: clahe - raw | [-27.8, -16.9] | 0 / 17 | 0.000 |
| low_light: denoise - raw | [-3.0, -1.1] | 3 / 14 | 0.040 |
| low_light: sharpen - raw | [-2.6, +0.2] | 4 / 13 | 0.007 |
| overexposed: clahe - raw | [-13.8, -8.1] | 2 / 15 | 0.006 |
| overexposed: denoise - raw | [-1.2, +1.0] | 6 / 11 | 0.782 |
| overexposed: sharpen - raw | [-1.7, +0.5] | 3 / 14 | 0.080 |
| blur: clahe - raw | [-13.6, -7.8] | 2 / 15 | 0.001 |
| blur: denoise - raw | [-1.5, +0.7] | 6 / 10 | 0.433 |
| blur: sharpen - raw | [-0.3, +3.9] | 12 / 4 | 0.105 |
| noise: clahe - raw | [-13.1, -8.5] | 2 / 15 | 0.000 |
| noise: denoise - raw | [+3.2, +7.2] | 13 / 4 | 0.006 |
| noise: sharpen - raw | [-13.1, -8.2] | 0 / 17 | 0.000 |
| low_contrast: clahe - raw | [-1.9, +5.4] | 10 / 7 | 0.431 |
| low_contrast: denoise - raw | [-1.3, +1.7] | 6 / 11 | 0.579 |
| low_contrast: sharpen - raw | [-0.3, +2.6] | 11 / 6 | 0.678 |
