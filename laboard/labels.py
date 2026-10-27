"""Ground truth / prediction values as text and as shapes drawn over the image.

A label is a plain value (a class name) or json in coco format, as made by Data_prep/raw_to_csv:

* ``["cat", "dog"]``: class names (classification);
* ``[{"category", "bbox"}]``: boxes, coco [x, y, w, h] (object detection);
* ``[{"category", "segmentation"}]``: polygons [[x1, y1, x2, y2, …], …] or uncompressed RLE
  {"counts", "size"} (instance / semantic segmentation);
* ``[{"category", "bbox", "keypoints"}]``: [x, y, v] per keypoint (pose-estimation);
* ``{"mask_path", "segments_info"}``: a coco panoptic png and its segments (panoptic segmentation).
"""
import json
import zlib
from collections import Counter
from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBitmap, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QRegion, QTransform

from . import remote
from .theme import font

# distinct hues that read over any photo; a category always gets the same one
PALETTE = ("#ff5c5c", "#ffb020", "#f7e14b", "#7bd84a", "#2ec4b6", "#3fa7ff", "#7c6cff", "#d45cff", "#ff6fb1",
           "#00e0a0", "#ff8a3d", "#9fe870")
# coco person keypoints (17): limbs as 1-based keypoint pairs
COCO_SKELETON = ((16, 14), (14, 12), (17, 15), (15, 13), (12, 13), (6, 12), (7, 13), (6, 7), (6, 8), (7, 9), (8, 10),
                 (9, 11), (2, 3), (1, 2), (1, 3), (2, 4), (3, 5), (4, 6), (5, 7))
MAX_TEXT = 60  # characters of a summary


@lru_cache(maxsize=256)
def _loads(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


def parse(value):
    """The label as a list / dict when it is json of one, else the value itself (None for none)."""
    if value is None or isinstance(value, (list, dict)):
        return value
    v = _loads(str(value)) if str(value)[:1] in "[{" else value
    return v if isinstance(v, (list, dict)) else value


def _objects(v):
    """The {"category", …} objects of a parsed label (panoptic: its segments)."""
    if isinstance(v, dict):
        v = v.get("segments_info", [])
    return [o for o in v if isinstance(o, dict)] if isinstance(v, list) else []


def categories(value):
    """Class names a label holds: the value itself, a list of names, or the objects' categories."""
    v = parse(value)
    if v is None:
        return []
    if not isinstance(v, (list, dict)):
        return [str(v)]
    if isinstance(v, list) and all(not isinstance(x, (list, dict)) for x in v):
        return [str(x) for x in v]
    return [str(o["category"]) for o in _objects(v) if o.get("category") is not None]


def summary(value):
    """Short text for a label: as is, the names of a list, or the object count and categories."""
    v = parse(value)
    if v is None:
        return None
    if not isinstance(v, (list, dict)):
        text = str(v)
    elif isinstance(v, list) and all(not isinstance(x, (list, dict)) for x in v):
        text = ", ".join(map(str, v)) or "none"
    else:
        objs = _objects(v)
        counts = Counter(str(o.get("category", "?")) for o in objs)
        what = ("segment" if isinstance(v, dict) else "object") + ("" if len(objs) == 1 else "s")
        names = ", ".join(c if n == 1 else f"{c} ×{n}" for c, n in counts.most_common())
        text = f"{len(objs)} {what}" + (f" · {names}" if names else "")
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 1] + "…"


def color(category):
    return PALETTE[zlib.crc32(str(category).encode()) % len(PALETTE)]


def _polygons(seg):
    """QPainterPath of a coco segmentation: polygons, or uncompressed RLE (column-major runs, 0s first)."""
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    if isinstance(seg, list):
        for poly in seg:
            if isinstance(poly, list) and len(poly) >= 6:
                path.moveTo(poly[0], poly[1])
                for i in range(2, len(poly) - 1, 2):
                    path.lineTo(poly[i], poly[i + 1])
                path.closeSubpath()
    elif isinstance(seg, dict) and isinstance(seg.get("counts"), list) and seg.get("size"):
        h = seg["size"][0]
        at = 0
        for i, n in enumerate(seg["counts"]):
            if i % 2:  # a run of 1s, split at column ends
                start, end = at, at + n
                while start < end:
                    x, y = divmod(start, h)
                    run = min(end - start, h - y)
                    path.addRect(QRectF(x, y, 1, run))
                    start += run
            at += n
    return path


def _panoptic(path, segments):
    """The segments of a coco panoptic png (a pixel's id = R + 256 G + 256² B), each in its category's colour."""
    # MaskOutColor: the matching pixels are black (index 0), which a QBitmap / QRegion counts as set
    ids = QImage(path).convertToFormat(QImage.Format.Format_RGB32)
    if ids.isNull():
        return None
    out = QImage(ids.size(), QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    for seg in segments:
        sid = seg.get("id")
        if not isinstance(sid, int):
            continue
        mask = ids.createMaskFromColor(QColor(sid % 256, sid // 256 % 256, sid // 65536 % 256).rgb(), Qt.MaskMode.MaskOutColor)
        fill = QColor(color(seg.get("category", "")))
        fill.setAlpha(110)
        p.setClipRegion(QRegion(QBitmap.fromImage(mask)))
        p.fillRect(out.rect(), fill)
    p.end()
    return QPixmap.fromImage(out)


class Overlay:
    """The shapes of one label, drawn by ``Stage`` over its image."""

    def __init__(self, value):
        v = parse(value)
        self.shapes = []  # (category, outline path, filled, keypoints [(x, y)] , limbs [(i, j)])
        self.mask = None
        if isinstance(v, dict) and v.get("mask_path"):
            self.mask = _panoptic(remote.local(str(v["mask_path"])), _objects(v))
        for o in _objects(v):
            cat = o.get("category", "")
            if isinstance(v, dict):  # panoptic segments: the mask is drawn, the boxes only carry the names
                path = QPainterPath()
                if isinstance(o.get("bbox"), list) and len(o["bbox"]) == 4:
                    path.addRect(QRectF(*o["bbox"]))
                self.shapes.append((cat, path, None, [], []))
                continue
            path, filled = QPainterPath(), False
            if o.get("segmentation") is not None:
                path, filled = _polygons(o["segmentation"]), True
            elif isinstance(o.get("bbox"), list) and len(o["bbox"]) == 4:
                path.addRect(QRectF(*o["bbox"]))
            points, limbs = [], []
            kp = o.get("keypoints")
            if isinstance(kp, list) and len(kp) >= 3:
                points = [(kp[i], kp[i + 1]) if kp[i + 2] else None for i in range(0, len(kp) - 2, 3)]
                limbs = [(a - 1, b - 1) for a, b in COCO_SKELETON] if len(points) == 17 else []
            self.shapes.append((cat, path, filled, points, limbs))

    def __bool__(self):
        return bool(self.shapes) or self.mask is not None

    def paint(self, p, rect, scale):
        """Draw over the image shown in ``rect`` at ``scale`` (view px per image px)."""
        p.save()
        to_view = QTransform(scale, 0, 0, scale, rect.x(), rect.y())
        if self.mask is not None:
            p.drawPixmap(rect, self.mask, QRectF(self.mask.rect()))
        names = []
        for cat, path, filled, points, limbs in self.shapes:
            c = QColor(color(cat))
            view = to_view.map(path)
            if filled is not None and not path.isEmpty():
                if filled:
                    fill = QColor(c)
                    fill.setAlpha(70)
                    p.fillPath(view, fill)
                p.setPen(QPen(c, 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(view)
            if points:
                p.setPen(QPen(c, 2))
                for a, b in limbs:
                    if points[a] and points[b]:
                        p.drawLine(to_view.map(QPointF(*points[a])), to_view.map(QPointF(*points[b])))
                p.setPen(QPen(QColor("#ffffff"), 1))
                p.setBrush(c)
                for pt in points:
                    if pt:
                        p.drawEllipse(to_view.map(QPointF(*pt)), 3.5, 3.5)
            if cat and not path.isEmpty():
                box = view.boundingRect()
                names.append((cat, c, QPointF(box.x(), box.y()) if filled is not None else box.center()))
        p.setFont(font(11, 600))
        fm = p.fontMetrics()
        for cat, c, at in names:  # names last, so no shape covers them
            w = fm.horizontalAdvance(cat) + 10
            chip = QRectF(at.x(), at.y() - 18, w, 18) if at.y() >= rect.y() + 18 else QRectF(at.x(), at.y(), w, 18)
            if self.mask is not None:  # panoptic: centred on the segment
                chip.moveCenter(at)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(chip, 4, 4)
            p.setPen(QColor("#0e0f0c"))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, cat)
        p.restore()
