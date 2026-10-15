"""Generate the Kaggle CPU notebook that converts the full Kodytek et al. dataset (Zenodo 4694695) to JPEG + YOLO labels.
Images already in our 4,000-image subset are skipped (they are reused from prakyats/wood-defects-clean)."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))

md0 = """# Full dataset conversion (CPU): Zenodo 4694695 -> JPEG q95 + YOLO labels (8 classes, our id order)
Reads each BMP straight out of the ten 15 GB zips with HTTP range requests (no 156 GB download to disk), re-encodes at
JPEG quality 95 (matches the existing subset: PSNR 36.64 dB vs the BMP), and writes YOLO labels for all 20,276 images.
Images already in the 4,000-image subset are not re-encoded (the training notebook takes them from wood-defects-clean)."""

c1 = r'''import io, os, glob, json, time, zipfile, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
cv2.setNumThreads(1)
OUT = '/kaggle/working/full'; os.makedirs(OUT + '/images', exist_ok=True); os.makedirs(OUT + '/labels', exist_ok=True)
BASE = 'https://zenodo.org/records/4694695/files/'
IDS = {'quartzity': 0, 'live_knot': 1, 'marrow': 2, 'resin': 3, 'dead_knot': 4, 'knot_with_crack': 5, 'knot_missing': 6, 'crack': 7}
have = set()
for p in glob.glob('/kaggle/input/**/dataset_clean/*/images/*.jpg', recursive=True):
    have.add(os.path.basename(p).split('_', 1)[1][:-4])
print('images already in the subset:', len(have))

class HttpFile(io.RawIOBase):
    def __init__(s, url):
        s.url = url; s.pos = 0
        s.size = int(urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=120).headers['Content-Length'])
    def seekable(s): return True
    def readable(s): return True
    def tell(s): return s.pos
    def seek(s, o, w=0):
        s.pos = o if w == 0 else (s.pos + o if w == 1 else s.size + o); return s.pos
    def readinto(s, b):
        if s.pos >= s.size: return 0
        end = min(s.size, s.pos + len(b)) - 1
        for attempt in range(6):
            try:
                d = urllib.request.urlopen(urllib.request.Request(s.url, headers={'Range': f'bytes={s.pos}-{end}'}), timeout=120).read()
                break
            except Exception as e:
                time.sleep(5 * (attempt + 1))
        else:
            raise IOError('range read failed')
        b[:len(d)] = d; s.pos += len(d); return len(d)'''

c2 = r'''# labels for all images (8 classes in our id order; Blue_Stain and overgrown dropped)
lab = '/kaggle/working/bbox.zip'
urllib.request.urlretrieve(BASE + 'Bouding_Boxes.zip?download=1', lab)
z = zipfile.ZipFile(lab); n_lab, dropped = 0, {}
for name in z.namelist():
    if not name.endswith('_anno.txt'): continue
    stem = os.path.basename(name)[:-9]; rows = []
    for ln in z.read(name).decode().splitlines():
        v = ln.split()
        if len(v) != 5: continue
        c = IDS.get(v[0].lower())
        if c is None:
            dropped[v[0]] = dropped.get(v[0], 0) + 1; continue
        x1, y1, x2, y2 = (float(x.replace(',', '.')) for x in v[1:])   # some files use decimal commas
        rows.append(f'{c} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}')
    open(f'{OUT}/labels/{stem}.txt', 'w').write('\n'.join(rows) + ('\n' if rows else ''))
    n_lab += 1
os.remove(lab)
print('label files:', n_lab, 'dropped classes:', dropped)'''

c3 = r'''done, lock, t0 = [0], threading.Lock(), time.time()
def convert(zname):
    zi = zipfile.ZipFile(io.BufferedReader(HttpFile(BASE + zname + '?download=1'), 1 << 23))
    todo = [i for i in zi.infolist() if i.filename.endswith('.bmp') and os.path.basename(i.filename)[:-4] not in have]
    for info in todo:
        stem = os.path.basename(info.filename)[:-4]
        dst = f'{OUT}/images/{stem}.jpg'
        if os.path.exists(dst): continue
        im = cv2.imdecode(np.frombuffer(zi.read(info), np.uint8), cv2.IMREAD_COLOR)
        cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        with lock:
            done[0] += 1
            if done[0] % 500 == 0:
                print(f'{done[0]} images, {(time.time() - t0) / 60:.1f} min', flush=True)
    return zname, len(todo)
with ThreadPoolExecutor(5) as ex:
    for zname, k in ex.map(convert, [f'Images{i}.zip' for i in range(1, 11)]):
        print(zname, 'converted', k, flush=True)
imgs = len(glob.glob(OUT + '/images/*.jpg'))
gb = sum(os.path.getsize(p) for p in glob.glob(OUT + '/images/*.jpg')) / 1e9
print(f'new images: {imgs}, {gb:.1f} GB, total time {(time.time() - t0) / 60:.1f} min')
json.dump(dict(new_images=imgs, gb=gb, skipped_existing=len(have)), open('/kaggle/working/convert_report.json', 'w'))'''


def cell(src, kind="code"):
    c = {"cell_type": kind, "metadata": {}, "source": src.splitlines(keepends=True)}
    if kind == "code":
        c.update(execution_count=None, outputs=[])
    return c


nb = {"cells": [cell(md0, "markdown"), cell(c1), cell(c2), cell(c3)],
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open(os.path.join(ROOT, "wood-full-convert.ipynb"), "w"), indent=1)
meta = {"id": "prakyats/wood-full-convert", "title": "wood-full-convert", "code_file": "wood-full-convert.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True, "enable_gpu": False,
        "enable_internet": True, "dataset_sources": ["prakyats/wood-defects-clean"],
        "competition_sources": [], "kernel_sources": []}
json.dump(meta, open(os.path.join(ROOT, "kernel-metadata.json"), "w"), indent=1)
for c in nb["cells"]:
    if c["cell_type"] == "code":
        compile("".join(c["source"]), "cell", "exec")
print("notebook written")
