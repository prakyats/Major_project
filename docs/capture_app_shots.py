"""
capture_app_shots.py - screenshots of the running web application (python app.py, port 7860) for the Phase-I report.
Drives the installed Microsoft Edge with Playwright. Output: docs/report_shots/*.png (full-page; cropped later).
"""
import time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "report_shots"; OUT.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:7860/"
BOARDS = ROOT / "October 23 test" / "test_boards"

for _ in range(120):                                   # wait for the app to come up
    try:
        urlopen(URL, timeout=2); break
    except Exception:
        time.sleep(2)

with sync_playwright() as pw:
    br = pw.chromium.launch(channel="msedge", headless=True)
    pg = br.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.25)
    pg.goto(URL); pg.get_by_role("button", name="Analyse image").wait_for(timeout=120000)
    time.sleep(2)
    pg.screenshot(path=str(OUT / "01_home.png"))

    def analyse(img, name, expect):
        pg.locator("input[type=file]").first.set_input_files(str(img))
        time.sleep(2)
        pg.get_by_role("button", name="Analyse image").click()
        pg.get_by_text(expect).first.wait_for(timeout=180000)
        time.sleep(3)
        pg.screenshot(path=str(OUT / name), full_page=True)

    analyse(BOARDS / "115100055.jpg", "03_detect_clean.png", "Grade A")      # also warms the models up
    pg.reload(); pg.get_by_role("button", name="Analyse image").wait_for(timeout=120000); time.sleep(2)
    analyse(BOARDS / "114500011.jpg", "02_detect_reject.png", "Grade Reject")

    pg.get_by_role("tab", name="Test boards: ground truth vs prediction").click(); time.sleep(1)
    dd = pg.get_by_label("Test image")
    dd.click(); dd.fill("7559bb_114500011"); time.sleep(1); pg.keyboard.press("Enter"); time.sleep(1)
    pg.get_by_role("button", name="Show").click()
    pg.get_by_text("Grade from the model").first.wait_for(timeout=180000); time.sleep(3)
    pg.screenshot(path=str(OUT / "04_test_boards.png"), full_page=True)

    for tab, name in (("Results", "05_results.png"), ("Legend", "06_legend.png")):
        pg.get_by_role("tab", name=tab).click(); time.sleep(2)
        pg.screenshot(path=str(OUT / name), full_page=True)
    br.close()
print("saved", sorted(p.name for p in OUT.glob("*.png")))
