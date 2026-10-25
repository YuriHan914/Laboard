"""Data: file viewer with Raw / Predict / Both, thumbnails, split info."""
import os
from datetime import datetime

from PyQt6 import sip
from PyQt6.QtCore import QRect, QRectF, QSize, Qt
from PyQt6.QtGui import QImageReader, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QScrollArea, QSizePolicy, QWidget

from .. import labels as label_values, project, store
from ..charts import Stage, StackedBar, ZoomView
from ..theme import T, font, qc
from ..widgets import (Box, Button, Combo, Dot, HLine, Label, Scroll, Segmented, badge, card, col, elided, empty_state, hbox,
                       kv_row, scrollbar_css, stat_tile, vbox, wrap)


class _Slot(QWidget):
    """Holds one widget and swaps it for another in place, so a new selection doesn't rebuild the window."""

    def __init__(self, child):
        super().__init__()
        self.setLayout(vbox())
        self.child = child
        self.layout().addWidget(child, 1)

    def swap(self, child):
        old, self.child = self.child, child
        self.layout().replaceWidget(old, child)
        old.hide()
        old.deleteLater()


class StageArea(QWidget):
    """Fills its space with one pane, or two panes side by side with a 2px divider."""

    def __init__(self, panes, mode, bg):
        super().__init__()
        self.panes, self.mode, self.bg = panes, mode, bg
        for p in panes:
            p.setParent(self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200)

    def paintEvent(self, e):
        if self.bg and len(self.panes) == 2:  # only the divider: the rounded outer corners stay the box's colour
            left, right = self.panes[0].geometry(), self.panes[1].geometry()
            QPainter(self).fillRect(QRect(left.right() + 1, 0, right.left() - left.right() - 1, self.height()), qc(self.bg))

    def resizeEvent(self, e):
        w, h = self.width(), self.height()
        if self.mode == "both":
            half = (w - 2) // 2
            self.panes[0].setGeometry(0, 0, half, h)
            self.panes[1].setGeometry(w - half, 0, half, h)
        else:
            self.panes[0].setGeometry(0, 0, w, h)


_thumbs = {}


def _thumb(path):
    if path.rsplit(".", 1)[-1].lower() not in project.IMAGE_EXT:
        return None
    if path not in _thumbs:
        r = QImageReader(path)
        r.setScaledSize(QSize(76, 76))
        _thumbs[path] = QPixmap.fromImage(r.read())
    return _thumbs[path]


class Thumb(QWidget):
    WINDOW = 30  # thumbs built on each side of the selection

    def __init__(self, short, dot, selected, on_click, path=None):
        super().__init__()
        self.short, self.dot, self.selected, self.on_click = short, dot, selected, on_click
        self.pix = _thumb(path) if path else None
        self.setFixedSize(80, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        self.on_click()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(2, 2, 76, 76)
        if self.selected:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qc(T.ink))
            p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), 10, 10)
        path = QPainterPath()
        path.addRoundedRect(r, 8, 8)
        p.save()
        p.setClipPath(path)
        p.fillRect(r, qc(T.bg))
        if self.pix and not self.pix.isNull():
            p.drawPixmap(r.toRect(), self.pix)
        else:
            p.translate(r.center())
            p.rotate(-45)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qc(T.surf2))
            k = -120
            while k < 120:
                p.drawRect(QRectF(k, -120, 8, 240))
                k += 16
        p.restore()
        p.setFont(font(10, 600, mono=True))
        tw = p.fontMetrics().horizontalAdvance(self.short)
        chip = QRectF(r.x() + 4, r.bottom() - 4 - 16, tw + 10 + 10, 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc(T.surf))
        p.drawRoundedRect(chip, 4, 4)
        p.setBrush(qc(col(self.dot)))
        p.drawEllipse(QRectF(chip.x() + 5, chip.center().y() - 3, 6, 6))
        p.setPen(qc(T.body))
        p.drawText(chip.adjusted(15, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, self.short)


GOOD, BAD, PLAIN = "#2ead4b", "#d03238", None  # PLAIN: neither matches nor contradicts the label


def _task(app):
    """The task shown: the one picked in the header, else a task project's first (None without tasks)."""
    return app.s.task if app.s.task in store.TASKS else (store.TASKS[0] if store.TASKS else None)


def _sources(app):
    """{name: source} of the shown task's predictions (every source without tasks)."""
    task = _task(app)
    return {k: v for k, v in store.INFERENCE.items() if v.get("task") in (None, task)}


def _source(app):
    """(name, source) of the predictions shown: the one picked under Results, else the task's first."""
    srcs = _sources(app)
    name = app.s.infer_source if app.s.infer_source in srcs else next(iter(srcs), None)
    return name, srcs.get(name)


def _label(app, row):
    """The row's ground truth for the shown task."""
    task = _task(app)
    return row["labels"].get(task) if task and "labels" in row else row["label"]


def _result(app, row):
    """The prediction record for ``row`` in the shown source, or None (no source, or row not in it)."""
    src = _source(app)[1]
    if not src:
        return None
    return src["by_path"].get(os.path.normpath(row["path"])) or src["by_name"].get(os.path.basename(row["path"]))


def _label_and_prediction(app, row):
    """(label, prediction rows as (key, value, tone)) for the shown task. The label is always the data row's ground
    truth; the predictions come from the task's prediction source, or without any from the data's ``predict``
    column. A value equal to the label is green, another label value red."""
    if store.INFERENCE:
        name, src = _source(app)
        if src is None:
            return _label(app, row) or "n/a", [("", f"no predictions for {_task(app)}", PLAIN)]
        rec = _result(app, row)
        if rec is None:
            return _label(app, row) or "n/a", [("", f"not in {src['rel']}", PLAIN)]
        label, classes = _label(app, row), set(store.CLASSES)
        chips = []
        for key, v in rec["values"].items():
            tone = PLAIN if v in (None, "") else GOOD if str(v) == str(label) else BAD if v in classes else PLAIN
            chips.append((key, "—" if v in (None, "") else label_values.summary(v), tone))
        return label or "n/a", chips
    if row["predict"] in (None, ""):
        return row["label"] or "n/a", [("pred", "none · predict column is empty", PLAIN)]
    return row["label"] or "n/a", [("pred", str(row["predict"]), GOOD if str(row["predict"]) == str(row["label"]) else BAD)]


def _overlays(app, row):
    """(label overlay, prediction overlay) of the shown task: shapes of a json label / of the first json value of the
    row's prediction record."""
    rec = _result(app, row) if store.INFERENCE else None
    pred = next((v for v in rec["values"].values() if isinstance(label_values.parse(v), (list, dict))), None) if rec else None
    return label_values.Overlay(_label(app, row)), label_values.Overlay(pred)


def _dims(path):
    if path.rsplit(".", 1)[-1].lower() not in project.IMAGE_EXT:
        return "—"
    size = QImageReader(path).size()
    return f"{size.width()}×{size.height()}" if size.isValid() else "—"


def _viewer(app, fd, files, di, sel):
    s = app.s
    row = fd["rows"][di]
    sp = store.split_of(s.folder, di)
    split_label, split_dot = store.SPLITS[sp]
    mode = s.view_mode
    ext = row["path"].rsplit(".", 1)[-1].upper() if "." in row["path"] else "FILE"
    path = row["path"] if ext.lower() in project.IMAGE_EXT else None  # other formats show the placeholder
    label, chips = _label_and_prediction(app, row)
    meta, pred = f"{_dims(row['path'])} {ext}", dict(chips=chips, top=[])
    label_shapes, pred_shapes = _overlays(app, row) if path else (None, None)
    both = mode == "both"
    # a zoom per pane (Raw / Predict move on their own in Both), kept across re-renders until another file is shown
    if not s.zoom or s.zoom[0] != row["path"]:
        s.zoom = (row["path"], dict(raw=ZoomView(), inference=ZoomView()))
    views = s.zoom[1]
    for v in views.values():
        v.panes = []
    panes = []
    if mode != "inference":
        panes.append(Stage(sel, meta, "raw", label=label_values.summary(label), path=path, radius=12, view=views["raw"],
                           overlay=label_shapes))
    if mode != "raw":
        panes.append(Stage(sel, meta, "inference", pred=pred, path=path, radius=12, view=views["inference"],
                           overlay=pred_shapes))
    area = StageArea(panes, mode, "#868685" if both else None)
    stage = Box(bg="stage", radius=12, border=f"1px solid {T.line}", layout=vbox(area, margins=(1, 1, 1, 1)))

    split_pill = Box(bg="surf2", radius=12, layout=hbox(Dot(split_dot, 8), 6, Label(split_label, 12, 600),
                                                        margins=(10, 4, 10, 4), align=Qt.AlignmentFlag.AlignVCenter))
    modes = Segmented([("raw", "Raw"), ("inference", "Predict"), ("both", "Both")], mode,
                      lambda k: restate(app, view_mode=k), size=13, pad=(6, 16))
    srcs, task = _sources(app), _task(app)
    if len(srcs) > 1:  # one result file per model: choose which one the predictions come from
        shown = lambda k: k.removeprefix(f"{task} · ") if task else k  # the task is picked beside it
        source = Combo([(k, shown(k)) for k in srcs], _source(app)[0], lambda k: restate(app, infer_source=k))
        modes = hbox(Label("Results", 13, 400, "body"), 8, source, 12, modes, align=Qt.AlignmentFlag.AlignVCenter)
    if len(store.TASKS) > 1:  # a multi-task project: whose labels and predictions are shown
        pick = Combo([(t, t[:1].upper() + t[1:]) for t in store.TASKS], task, lambda k: restate(app, task=k, infer_source=None))
        modes = hbox(Label("Task", 13, 400, "body"), 8, pick, 12, modes, align=Qt.AlignmentFlag.AlignVCenter)
    head = hbox(elided(sel, 16, 600, lh=24), 10, split_pill, "stretch", 16, modes, margins=(20, 14, 20, 14), align=Qt.AlignmentFlag.AlignVCenter)

    names = [n for n, _ in files]
    pos = names.index(sel) if sel in names else 0
    step = lambda d: names and app.pick("data", names[(pos + d) % len(names)])
    hint = elided("Scroll to zoom · Shift+scroll or drag to pan · double-click to fit" if path else "", 12, 400, "mute")
    # Reset puts every pane (Raw and Predict) back to its first view: fitted and centred
    reset = Button("Reset", on_click=lambda: [v.reset() for v in views.values()]) if path else None
    nav = hbox(reset, 12 if reset else 0, hint, "stretch", 12, Label(f"{di + 1} of {fd['n']}", 13, 600, "body"), 12,
               Button("Previous", on_click=lambda: step(-1)), 8, Button("Next", on_click=lambda: step(1)),
               margins=(20, 12, 20, 0), align=Qt.AlignmentFlag.AlignVCenter)

    thumbs = hbox(spacing=4, margins=(18, 12, 18, 12))
    lo = max(0, pos - Thumb.WINDOW)
    for n, i in files[lo:pos + Thumb.WINDOW + 1]:
        thumbs.addWidget(Thumb(n.rsplit(".", 1)[0][-6:], store.SPLITS[store.split_of(s.folder, i)][1], n == sel,
                               lambda n=n: app.pick("data", n), path=fd["rows"][i]["path"]))
    thumbs.addStretch(1)
    strip = QScrollArea()
    strip.setWidget(wrap(thumbs))
    strip.widget().setAutoFillBackground(False)
    strip.viewport().setAutoFillBackground(False)
    strip.setWidgetResizable(True)
    strip.setFrameShape(QScrollArea.Shape.NoFrame)
    strip.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    strip.setStyleSheet(scrollbar_css())
    strip.setFixedHeight(80 + 24 + 10)

    return Box(bg="surf", radius=16, layout=vbox(head, (hbox(stage, margins=(20, 0, 20, 0)), 1), nav, strip))


def _splits_card(app):
    sf = app.s.split_filter
    total = sum(n for _, n, _ in store.SPLIT_TOTALS)
    src, desc = store.SPLIT_SOURCE
    # rows bleed 8px into the card padding so their hover fill lines up with the text above
    body = vbox(vbox(hbox(Label("Data splits", 16, 600, lh=24), "stretch", Label(src, 12, 400, "mute", mono=True)), 4,
                     Label(desc, 12, 400, "body", wrap=True), 12,
                     StackedBar([(n / total, store.SPLITS[k][1]) for k, n, _ in store.SPLIT_TOTALS]), 12, margins=(8, 0, 8, 0)))
    for k, n, frm in store.SPLIT_TOTALS:
        name, dot = store.SPLITS[k]
        pct = n / total
        row = hbox(Dot(dot, 10), 10, (vbox(Label(name, 13, 600), Label(frm, 11.5, 400, "mute", elide=True)), 1), 10,
                   Label(f"{n:,}", 13, 600), 10,
                   Label("<0.1%" if pct < 0.001 else f"{pct * 100:.1f}%", 12, 400, "body", align=Qt.AlignmentFlag.AlignRight),
                   margins=(8, 7, 8, 7), align=Qt.AlignmentFlag.AlignVCenter)
        row.itemAt(row.count() - 1).widget().setFixedWidth(44)
        body.addWidget(Box(bg="surf2" if sf == k else None, radius=10, hover=None if sf == k else "surf2", layout=row,
                           on_click=lambda k=k: app.set(split_filter="all" if sf == k else k)))
    if store.SPLIT_OVERLAP:
        check, result, tone = store.SPLIT_OVERLAP
        body.addLayout(vbox(10, HLine(), hbox(Label(check, 13, 400, "body"), "stretch", badge(result, tone),
                                              margins=(0, 12, 0, 0)), margins=(8, 0, 8, 0)))
    return card(body, pad=(12, 20, 12, 20))


def _info_card(app, fd, di, sel):
    s = app.s
    sp = store.split_of(s.folder, di)
    r = fd["rows"][di]
    ext = r["path"].rsplit(".", 1)[-1].upper() if "." in r["path"] else "—"
    label, _ = _label_and_prediction(app, r)
    if len(store.TASKS) > 1:  # every task's ground truth
        labels = [(f"Label · {t}", label_values.summary(r["labels"].get(t)) or "—") for t in store.TASKS]
    else:
        labels = [("Label", label_values.summary(label))]
    rows = [("Path", r["path"]), ("Split", store.SPLITS[sp][0]), ("Dimensions", _dims(r["path"])), ("Format", ext),
            *labels, ("Size", f"{r['bytes'] / 1024:.0f} KB" if r["bytes"] else "missing"),
            ("Modified", datetime.fromtimestamp(r["mtime"]).strftime("%b %d, %H:%M") if r["mtime"] else "—")]
    if r["created"]:
        rows.append(("Created", r["created"].strftime("%b %d, %Y %H:%M")))
    if r["trained"] is not None:
        rows.append(("Trained", "yes" if r["trained"] else "no"))
    if r["id"] is not None:
        rows.append(("Row", f"{store.SPLIT_SOURCE[0]} · id {r['id']}"))
    src = _source(app)[1]
    if src:
        rec = _result(app, r)
        for key, column in src["shows"].items():
            v = rec["values"].get(key) if rec else None
            rows.append((f"{key} · {column}", "—" if v in (None, "") else label_values.summary(v)))
        rows.append(("Result file", src["rel"] if rec else f"{src['rel']} · no row"))
    body = vbox(Label("File info", 16, 600, lh=24), 10)
    for k, v in rows:
        body.addWidget(kv_row(k, v))
    return card(body)


def _folder_card(fd):
    tiles = hbox(stat_tile("Files", f"{fd['n']:,}", value_size=22, lh=30), 12, stat_tile("Size", fd["size"], value_size=22, lh=30))
    folders = {os.path.dirname(r["path"]) for r in fd["rows"]}
    note = Label(f"From {store.SPLIT_SOURCE[0]} · {len(folders)} director{'y' if len(folders) == 1 else 'ies'} on disk",
                 13, 400, "body", wrap=True)
    return card(Label("Folder summary", 16, 600, lh=24), 12, tiles, 12, note)


def build(app):
    s = app.s
    if s.folder not in store.DATA_FOLDERS:
        return empty_state("No data", "Load a project file in Setting. Data comes from its [db] table or paths.data.")
    fd = store.DATA_FOLDERS[s.folder]
    sel = s.sel["data"] if s.sel["data"] in fd["files"] else fd["files"][0]
    di = fd["files"].index(sel)
    files = [(n, i) for i, n in enumerate(fd["files"]) if s.split_filter in ("all", store.split_of(s.folder, i))]
    viewer, info = _Slot(_viewer(app, fd, files, di, sel)), _Slot(_info_card(app, fd, di, sel))
    app.data_slots = (viewer, info)
    side = Scroll(wrap(vbox(_splits_card(app), info, _folder_card(fd), "stretch", spacing=12)))
    side.setFixedWidth(340)
    return viewer, side


def select(app, name):
    """Show file ``name`` of the open folder by swapping the viewer and File info in place (Previous / Next, a
    thumbnail, the file list), not by rebuilding the window, which flickers. False when the page must be rebuilt."""
    fd = store.DATA_FOLDERS.get(app.s.folder)
    slots = getattr(app, "data_slots", None)
    if not fd or name not in fd["files"] or not slots or any(sip.isdeleted(x) for x in slots):
        return False
    _swap(app, fd, name)
    return True


def restate(app, **kw):
    """Change how the shown file is viewed (task, Raw / Predict / Both, results source): only the viewer and File info
    depend on it, so they are swapped in place like ``select`` instead of rebuilding the window, which flickers."""
    fd = store.DATA_FOLDERS.get(app.s.folder)
    slots = getattr(app, "data_slots", None)
    if not fd or not slots or any(sip.isdeleted(x) for x in slots):
        return app.set(**kw)
    vars(app.s).update(kw)
    _swap(app, fd, app.s.sel["data"] if app.s.sel["data"] in fd["files"] else fd["files"][0])


def _swap(app, fd, name):
    s, di = app.s, fd["files"].index(name)
    files = [(n, i) for i, n in enumerate(fd["files"]) if s.split_filter in ("all", store.split_of(s.folder, i))]
    viewer, info = app.data_slots
    viewer.swap(_viewer(app, fd, files, di, name))
    info.swap(_info_card(app, fd, di, name))
