---
title: Wood Defect Detection YOLO11
emoji: 🪵
colorFrom: yellow
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
---

# Wood surface defect detection (YOLO11m vs YOLO11s)

Sawn-timber line-scan images, 8 defect classes (Quartzity, Live_Knot, Marrow, Resin, Dead_Knot,
Knot_with_crack, Knot_missing, Crack), trained on a board-level split of the Kodytek, Bodzas & Bilik (2022)
dataset (F1000Research 10:581). Upload a board image on the first tab, or compare ground truth and
prediction on held-out test boards on the second. Runs on CPU.

VTU major project, DSCE CSBS 2026-27.
