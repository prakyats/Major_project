"""Generate the Kaggle notebooks for Option A on the full dataset: YOLO11s 4-class partial balance at 1024 / 1280,
plus a CPU smoke test that runs the identical pipeline on a tiny slice (no GPU quota) before the real runs.
New images come from the Kaggle mirror kirs0816/wood-surface-defects (all 20,276 images of Kodytek et al. as JPEG,
COCO labels; verified 2026-10-15: 43,974 boxes = Zenodo, 3,953/4,000 subset label files identical, rest within 1 px).
The 4,000 subset images keep their original JPEGs and labels, so val_orig / test_orig match the deployed evaluation.
usage: python make_nb.py 1024 | 1280 | smoke"""
import json, os, sys

MODE = sys.argv[1]
SMOKE = MODE == "smoke"
IMGSZ = 1024 if SMOKE else int(MODE)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"full_{MODE}")
os.makedirs(ROOT, exist_ok=True)
NAME = "wood-full4-smoke" if SMOKE else f"wood-full4-v2-{IMGSZ}"

md0 = f"""# Full dataset (20,276 images, 407 boards), YOLO11s 4 classes, partial balance, imgsz {IMGSZ} rect{' - CPU SMOKE TEST' if SMOKE else ''}
Plan fixed beforehand in NOTES.md section 23. Our 81 boards keep their split; new boards 70/18/12 (seed 42).
Epochs 40, patience 15, batch 32, lr0 0.001, seed 42, with a wall-clock guard below the 12 h session limit. After training,
the official evaluator's predictions are saved for the original 714 val images, the full val split, the original 469 test
images and the full test split (fusion is done offline)."""

c1 = """!pip -q install ultralytics==8.4.142
import os, glob, json, time, subprocess, sys, shutil, collections
T0 = time.time()
SUB = os.path.dirname(glob.glob('/kaggle/input/**/dataset_clean/board_split.json', recursive=True)[0])
MIRROR = os.path.dirname(glob.glob('/kaggle/input/**/bbox_coco_dataset.json', recursive=True)[0])
SCRIPTS = os.path.dirname(glob.glob('/kaggle/input/**/prepare_full.py', recursive=True)[0])
sys.path.insert(0, SCRIPTS)
print(SUB, MIRROR, SCRIPTS)
assert len(glob.glob(MIRROR + '/IMAGE/*.jpg')) == 20276, 'mirror images'
assert 'max_hours' in open(SCRIPTS + '/train_yolo11m.py').read(), 'scripts dataset is outdated (no time guard)'"""

c2 = """# full set in prepare_full's layout: images = mirror JPEGs, labels = COCO -> YOLO (8 classes, our id order);
# the 4,000 subset images get their original labels (prepare_full takes their original JPEGs itself)
FULL = '/kaggle/tmp/full'; os.makedirs(FULL + '/images', exist_ok=True); os.makedirs(FULL + '/labels', exist_ok=True)
j = json.load(open(MIRROR + '/bbox_coco_dataset.json'))
IDS = {'Quartzity': 0, 'Live knot': 1, 'Marrow': 2, 'Resin': 3, 'Dead knot': 4, 'Knot with crack': 5, 'Knot missing': 6, 'Crack': 7}
cat = {c['id']: IDS.get(c['name']) for c in j['categories']}
assert sorted(v for v in cat.values() if v is not None) == list(range(8)), cat
img = {i['id']: i for i in j['images']}
rows = collections.defaultdict(list); dropped = collections.Counter()
for a in j['annotations']:
    c = cat[a['category_id']]
    if c is None:
        dropped[a['category_id']] += 1; continue
    i = img[a['image_id']]; W, H = i['width'], i['height']; x, y, w, h = a['bbox']
    rows[i['file_name'][:-4]].append(f'{c} {(x + w / 2) / W:.6f} {(y + h / 2) / H:.6f} {w / W:.6f} {h / H:.6f}')
assert len(j['images']) == 20276 and len(j['annotations']) == 43974 and sum(dropped.values()) == 106, (len(j['images']), len(j['annotations']), dropped)
subset_lab = {os.path.basename(p)[:-4].split('_', 1)[1]: p for p in glob.glob(SUB + '/*/labels/*.txt')}
assert len(subset_lab) == 4000, len(subset_lab)
for i in j['images']:
    s = i['file_name'][:-4]
    os.symlink(f"{MIRROR}/IMAGE/{i['file_name']}", f'{FULL}/images/{s}.jpg')
    if s in subset_lab:
        shutil.copy2(subset_lab[s], f'{FULL}/labels/{s}.txt')
    else:
        open(f'{FULL}/labels/{s}.txt', 'w').write(''.join(r + '\\n' for r in rows[s]))
assert len(os.listdir(FULL + '/images')) == len(os.listdir(FULL + '/labels')) == 20276
assert len({s[:4] for s in rows} | {s[:4] for s in subset_lab}) <= 407 and len({i['file_name'][:4] for i in j['images']}) == 407
print('full set ready', f'{(time.time()-T0)/60:.1f} min')"""

c3 = """DF, D4 = '/kaggle/tmp/dataset_full', '/kaggle/tmp/dataset_full4'
assert subprocess.call([sys.executable, f'{SCRIPTS}/prepare_full.py', '--subset', SUB, '--full', FULL, '--out', DF]) == 0
assert subprocess.call([sys.executable, f'{SCRIPTS}/build_balanced.py', '--src', DF, '--out', D4, '--seed', '42', '--variants', 'sqrt']) == 0
for key in ('val_orig', 'test_orig'):
    lines = open(f'{DF}/{key}.txt').read().split()
    open(f'{D4}/{key}.txt', 'w').write('\\n'.join(l.replace(DF + '/', D4 + '/') for l in lines) + '\\n')
names = 'nc: 4\\nnames:\\n  0: Live_Knot\\n  1: Dead_Knot\\n  2: Resin\\n  3: Crack\\n'
open(f'{D4}/data_valorig.yaml', 'w').write(f'path: {D4}\\ntrain: train_sqrt/images\\nval: {D4}/val_orig.txt\\ntest: {D4}/test_orig.txt\\n\\n' + names)
# the original val/test images must carry exactly the 4-class labels the deployed models were scored on
EXPECT = {'val_orig': (714, [713, 482, 88, 111]), 'test_orig': (469, [406, 343, 69, 95])}
for key, (n_img, boxes) in EXPECT.items():
    paths = open(f'{D4}/{key}.txt').read().split()
    cnt = collections.Counter()
    for p in paths:
        assert os.path.exists(p), p
        lp = p.replace('/images/', '/labels/')[:-4] + '.txt'
        cnt.update(int(l.split()[0]) for l in open(lp).read().splitlines() if l.strip())
    got = [cnt[i] for i in range(4)]
    print(key, len(paths), 'images', got, 'boxes')
    assert len(paths) == n_img and got == boxes, (key, len(paths), got)
rep = json.load(open(f'{D4}/balance_report.json'))
n_train = len(os.listdir(f'{D4}/train_sqrt/images'))
print(json.dumps({k: rep[k] for k in ('train_plain', 'train_sqrt', 'val', 'test')}), 'train images', n_train)
assert n_train > 12000 and min(rep['train_sqrt'].values()) > 1000
shutil.copy2(f'{D4}/balance_report.json', '/kaggle/working/balance_report.json')
shutil.copy2(f'{DF}/board_split.json', '/kaggle/working/board_split_full.json')
print(f'prep {(time.time()-T0)/60:.0f} min')"""

if SMOKE:
    c4 = """# smoke: same training entry point on a tiny slice, on CPU (1 epoch), then the same capture code
import random
random.seed(0)
tr = sorted(glob.glob(f'{D4}/train_sqrt/images/*.jpg')); random.shuffle(tr)
for key, src in (('mini_train', tr[:48]), ('mini_val', open(f'{D4}/val_orig.txt').read().split()[:24]),
                 ('mini_test', open(f'{D4}/test_orig.txt').read().split()[:24])):
    open(f'{D4}/{key}.txt', 'w').write('\\n'.join(src) + '\\n')
open(f'{D4}/data_mini.yaml', 'w').write(f'path: {D4}\\ntrain: {D4}/mini_train.txt\\nval: {D4}/mini_val.txt\\ntest: {D4}/mini_test.txt\\n\\n' + names)
IMGSZ, RUN = 1024, 'smoke'
cmd = [sys.executable, f'{SCRIPTS}/train_yolo11m.py', '--data', f'{D4}/data_mini.yaml', '--name', RUN, '--device', 'cpu',
       '--model', 'yolo11s.pt', '--batch', '8', '--lr0', '0.001', '--patience', '15', '--epochs', '1', '--imgsz', '1024',
       '--max-hours', '0.0001', '--project', '/kaggle/working/outputs']
print(' '.join(cmd)); rc = subprocess.call(cmd)
W = f'/kaggle/working/outputs/{RUN}/weights/best.pt'
assert rc == 0 and os.path.exists(W), rc"""
    c5 = """from eval_capture import capture
res = {}
for tag, sp in (('mini_val', 'val'), ('mini_test', 'test')):
    d = capture(W, f'{D4}/data_mini.yaml', sp, IMGSZ, cache_dir=f'/kaggle/working/capture/{tag}', device='cpu')
    res[tag] = dict(map50=d['map50'], map=d['map'], images=len(d['images']))
    assert len(d['images']) == 24, res
print(res)
json.dump(dict(ok=True, capture=res, train_images=n_train, prep_min=round((time.time()-T0)/60, 1)), open('/kaggle/working/smoke_ok.json', 'w'))
print('SMOKE OK', f'{(time.time()-T0)/60:.0f} min')"""
else:
    c4 = f"""IMGSZ, RUN = {IMGSZ}, 'yolo11s_full4_sqrt_{IMGSZ}'
MAXH = round(11.0 - (time.time() - T0) / 3600 - 0.8, 2)   # leave ~0.8 h for the last epoch, final val and the captures
cmd = [sys.executable, f'{{SCRIPTS}}/train_yolo11m.py', '--data', f'{{D4}}/data_sqrt.yaml', '--name', RUN, '--device', '0',
       '--model', 'yolo11s.pt', '--batch', '32', '--lr0', '0.001', '--patience', '15', '--epochs', '40', '--imgsz', str(IMGSZ),
       '--max-hours', str(MAXH), '--project', '/kaggle/working/outputs', '--persist', '/kaggle/working/persist']
print(' '.join(cmd)); t = time.time(); rc = subprocess.call(cmd)
W = f'/kaggle/working/outputs/{{RUN}}/weights/best.pt'
print('exit', rc, os.path.exists(W), f'{{(time.time()-t)/3600:.2f}} h')
assert os.path.exists(W)"""
    c5 = """from eval_capture import capture
res = {}
for tag, yml, sp in (('val_orig', 'data_valorig.yaml', 'val'), ('test_orig', 'data_valorig.yaml', 'test'),
                     ('val_full', 'data_sqrt.yaml', 'val'), ('test_full', 'data_sqrt.yaml', 'test')):
    d = capture(W, f'{D4}/{yml}', sp, IMGSZ, cache_dir=f'/kaggle/working/capture/{tag}', device='0')
    res[tag] = dict(map50=d['map50'], map=d['map'], images=len(d['images']))
    print(tag, res[tag], flush=True)
    json.dump(res, open('/kaggle/working/summary.json', 'w'), indent=1)
print(f'total {(time.time()-T0)/3600:.2f} h')"""


def cell(src, kind="code"):
    c = {"cell_type": kind, "metadata": {}, "source": src.splitlines(keepends=True)}
    if kind == "code":
        c.update(execution_count=None, outputs=[])
    return c


nb = {"cells": [cell(md0, "markdown"), cell(c1), cell(c2), cell(c3), cell(c4), cell(c5)],
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open(os.path.join(ROOT, f"{NAME}.ipynb"), "w"), indent=1)
meta = {"id": f"prakyats/{NAME}", "title": NAME, "code_file": f"{NAME}.ipynb", "language": "python",
        "kernel_type": "notebook", "is_private": True, "enable_gpu": not SMOKE, "enable_internet": True,
        "dataset_sources": ["prakyats/wood-defects-clean", "prakyats/wood-defects-scripts", "kirs0816/wood-surface-defects"],
        "competition_sources": [], "kernel_sources": []}
if not SMOKE:
    meta["machine_shape"] = "NvidiaTeslaT4"
json.dump(meta, open(os.path.join(ROOT, "kernel-metadata.json"), "w"), indent=1)
for c in nb["cells"]:
    if c["cell_type"] == "code":
        compile("".join(l for l in c["source"] if not l.lstrip().startswith("!")), "cell", "exec")
print("written", NAME)
