---
title: Wood Defect Detection YOLO11
emoji: 🪵
colorFrom: yellow
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
---

# AI-Based Wood Quality Assessment

Finds surface defects on sawn-timber line-scan board images and grades each board (A / B / C / Reject) with the
Board Recoverability Index, with the recoverable area and an editable value estimate.

**Default model:** weighted box fusion of two YOLO11s models (1024 and 1280 px) trained on the full Kodytek, Bodzas
and Bilik (2022) dataset (F1000Research 10:581; 20,276 images, 407 boards), 4 classes: Live_Knot, Dead_Knot, Resin,
Crack. Test mAP50 76.9 on the original 12 held-out boards and 81.3 on 51 further unseen boards. The 8-class
YOLO11m / YOLO11s models from the mid-term review remain selectable. Runs on CPU.

VTU major project, Dept. of CSBS, Dayananda Sagar College of Engineering, 2026-27. Guide: Mrs. Aparna H D. Team 4.
