import csv
import operator
import re
from pathlib import Path

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QMimeData, QObject, QPoint, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QDrag, QFontMetrics, QImageReader, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QGraphicsOpacityEffect, QSlider

from .. import readers, store
from ..charts import LineChart, Stage, Swatch, series_style
from ..theme import NEGATIVE_DARKEST, POSITIVE, POSITIVE_DEEP, WARNING, WARNING_CONTENT, WARNING_DEEP, T, font
from ..widgets import (Box, Button, Check, Chevron, ClickTrap, Dot, EdgeResize, Flow, HLine, HScroll, Label, LineEdit,
                       MenuButton, Pager, Pill, Popover, Scroll, card, clear_layout, elided, empty_state, grid, hbox,
                       menu_item, vbox, wrap)

COMPARE_SIZE = 10
GROUP_COLORS = (POSITIVE_DEEP, POSITIVE, WARNING, WARNING_DEEP, WARNING_CONTENT, NEGATIVE_DARKEST)
MAX_COMPARE = COMPARE_SIZE * len(GROUP_COLORS)
MAX_CHARTS = 60
CHART_W, CHART_MIN = 360, 200
PLOT_H = (80, 1000)


def _ema(vals, sm):
    out, acc = [], None
    for v in vals:
        acc = v if acc is None else sm * acc + (1 - sm) * v
        out.append(acc)
    return out


def _fmt(v):
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 1000:
        return f"{v / 1000:.3g}k" if a < 1e6 else f"{v:.1e}".replace("e+0", "e")
    if a < 0.01:
        return f"{v:.1e}".replace("e-0", "e-")
    return f"{v:.3g}" if a >= 0.1 else f"{v:.2g}"


def _thin(xs, ys, n=400):
    step = max(1, len(ys) // n)
    return xs[::step], ys[::step]


def _kind(path):
    name, ext = path.name, path.suffix.lower()[1:]
    if "tfevents" in name:
        return "TensorBoard", "tfevents"
    if ext in ("csv", "tsv", "jsonl"):
        return ("Weights & Biases" if "wandb" in name else ext.upper()), "table"
    if ext in ("png", "jpg", "jpeg", "bmp", "gif", "webp"):
        return "Image", "image"
    return ("JSON" if ext == "json" else "Text"), "text"


_COMPARE = re.compile(r"^\s*(>=|<=|!=|==|=|>|<)\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)\s*$", re.I)
_OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "=": operator.eq, "==": operator.eq,
        "!=": operator.ne}


def _number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _matcher(text):
    m = _COMPARE.match(text)
    if m:
        op, num = _OPS[m.group(1)], float(m.group(2))
        return lambda v: (x := _number(v)) is not None and op(x, num)
    t = text.strip().lower()
    return lambda v: t in ("" if v is None else str(v)).lower()


def _blank(v):
    return v is None or str(v).strip() == ""


class RecordTable(Box):
    FOLD_COLS, FOLD_ROWS, PREVIEW, PREVIEW_COLS = 5, 10, 6, 5
    FOLDED_COL_W = 60

    def __init__(self, app, key, cols, recs, more):
        super().__init__(bg="surf", radius=16, layout=vbox(margins=(0, 8, 0, 8)))
        self.app, self.key, self.cols, self.recs, self.more = app, key, cols, recs, more
        self.view = app.s.table_view.setdefault(key, dict(sort=None, filters={}, hidden=set()))
        self.per_page = app.s.table_rows
        self.flow = None
        self.fold_h = 0
        cell, head = QFontMetrics(font(13, mono=True)), QFontMetrics(font(12, 600, mono=True))
        sample = recs[:500]
        self.widths = {c: min(280, max(72, head.horizontalAdvance(c) + 30, *(cell.horizontalAdvance(str(r.get(c, "")))
                                                                            for r in sample)) + 16) for c in cols}
        self.head, self.rows = vbox(), vbox()
        self.table = wrap(vbox(self.head, self.rows))
        self.scroll = HScroll(self.table)
        self.pager = Pager(self.per_page, len(recs), self.show_page)
        self.foldable = len(cols) >= self.FOLD_COLS and len(recs) >= self.FOLD_ROWS
        self.size = elided("", 13, 600, select=False)
        self.columns = MenuButton("Columns", self._columns_menu, min_width=0, pad=(12, 4, 10, 4), gap=8)
        self.reset = Button("Reset", "tertiary", compact=True, on_click=self._reset)
        tools = ClickTrap()
        tools.setLayout(hbox(self.reset, 8, self.columns, align=Qt.AlignmentFlag.AlignVCenter))
        self.tools = tools
        bar = hbox(margins=(24, 6, 24, 8), align=Qt.AlignmentFlag.AlignVCenter)
        if self.foldable:
            self.chev = Chevron("mute", 0)
            self.fold_note = elided("", 12, 400, "mute", align=Qt.AlignmentFlag.AlignRight, select=False)
            bar.addWidget(self.chev)
            bar.addSpacing(10)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.clicked.connect(self.toggle)
        bar.addWidget(self.size, 1)
        if self.foldable:
            bar.addWidget(self.fold_note, 1)
            bar.addSpacing(12)
        bar.addWidget(tools)
        self.layout().addLayout(bar)
        self.layout().addWidget(self.scroll)
        self.layout().addWidget(self.pager)
        self.layout().addStretch(1)
        self._apply(app.s.table_page.get(key, 0))

    @property
    def folded(self):
        return self.foldable and self.key not in self.app.s.table_open

    def takes_clicks(self):
        return self.folded

    def toggle(self):
        self.app.s.table_open ^= {self.key}
        self.show_page(self.page)
        self._fit_flow()

    def place(self, flow, chart_h=0):
        self.flow, self.fold_h = flow, chart_h
        flow.add(self, CHART_W)
        flow.set_steady(self, True)
        self._fit_flow()

    def _fit_flow(self):
        if self.flow is not None:
            self.flow.set_width(self, None if self.folded else 10 ** 6)
            self.setMinimumHeight(self.fold_h if self.folded else 0)

    def _apply(self, page=0):
        v = self.view
        self.shown_cols = [c for c in self.cols if c not in v["hidden"]]
        tests = [(c, _matcher(t)) for c, t in v["filters"].items() if t.strip()]
        recs = [r for r in self.recs if all(test(r.get(c)) for c, test in tests)] if tests else list(self.recs)
        if v["sort"]:
            c, up = v["sort"]
            blank = [r for r in recs if _blank(r.get(c))]
            full = [r for r in recs if not _blank(r.get(c))]
            nums = [_number(r.get(c)) for r in full]
            if all(n is not None for n in nums):
                order = sorted(range(len(full)), key=nums.__getitem__, reverse=not up)
            else:
                order = sorted(range(len(full)), key=lambda i: str(full[i].get(c)).lower(), reverse=not up)
            recs = [full[i] for i in order] + blank
        self.view_recs = recs
        self.pager.set_total(len(recs))
        self.pages = self.pager.pages
        total = f"{len(self.recs):,}{'+' if self.more else ''}"
        ncols = f"{len(self.shown_cols)} of {len(self.cols)}" if v["hidden"] else f"{len(self.cols)}"
        nrows = f"{len(recs):,} of {total}" if tests else total
        self.size.setText(f"{ncols} columns · {nrows} rows")
        self.size.setToolTip(self.size.text())
        self.reset.setVisible(bool(v["hidden"] or tests or v["sort"]))
        self.show_page(page)

    def _set(self, **kw):
        self.view.update(kw)
        self._apply(0)

    def _sort(self, col, up):
        self._set(sort=None if up is None else (col, up))

    def _filter(self, col, text):
        self._set(filters={**self.view["filters"], col: text} if text.strip() else
                  {c: t for c, t in self.view["filters"].items() if c != col})

    def _hide(self, col, hidden):
        self._set(hidden=self.view["hidden"] | {col} if hidden else self.view["hidden"] - {col})

    def _reset(self):
        self._set(sort=None, filters={}, hidden=set())

    def _column_menu(self, col, anchor):
        sort = self.view["sort"]
        up, down = sort == (col, True), sort == (col, False)
        pop = None

        def then_close(f):
            return lambda: pop.done(f)

        box = LineEdit("Text, or > 0.5", size=13, pad=(6, 10))
        box.setText(self.view["filters"].get(col, ""))
        box.textChanged.connect(lambda t: self._filter(col, t))
        box.returnPressed.connect(lambda: pop.done())
        last = len(self.shown_cols) == 1
        title = Label(col, 12, 600, "mute", mono=True, lh=28, elide=True)
        title.setContentsMargins(4, 0, 4, 0)
        items = vbox(title, 2,
                     menu_item("Sort ascending", then_close(lambda: self._sort(col, None if up else True)), on=up),
                     menu_item("Sort descending", then_close(lambda: self._sort(col, None if down else False)), on=down),
                     8, HLine(), 8, Label("Filter", 12, 600, "body", lh=20), 4, box, 4,
                     Label("Text it holds, or > >= < <= = != with a number", 11, 400, "mute", wrap=True), 8, HLine(), 4,
                     menu_item("Hide column", then_close(lambda: self._hide(col, True)), enabled=not last),
                     margins=(8, 8, 8, 4))
        pop = Popover(anchor, items, min_width=260)
        pop.show()
        box.setFocus()

    def _columns_menu(self):
        def flip(col, check):
            hidden = col not in self.view["hidden"]
            if hidden and len(self.shown_cols) == 1:
                return
            self._hide(col, hidden)
            check.set_checked(not hidden)

        rows = vbox(margins=(4, 4, 4, 4))
        for c in self.cols:
            check = Check(c not in self.view["hidden"], 16)
            rows.addWidget(Box(bg=None, radius=8, hover="surf2", on_click=lambda c=c, k=check: flip(c, k),
                               layout=hbox(check, 10, (Label(c, 13, 400, mono=True, lh=20, elide=True), 1),
                                           margins=(10, 7, 12, 7), align=Qt.AlignmentFlag.AlignVCenter)))
        rows.addWidget(HLine())
        rows.addWidget(menu_item("Show all", lambda: pop.done(lambda: self._set(hidden=set()))))
        fm = QFontMetrics(font(13, mono=True))
        pop = self.columns.pop(rows, min_width=min(360, max(220, self.columns.width(),
                                                             60 + max(map(fm.horizontalAdvance, self.cols)))))

    def _row(self, cols, vals=None):
        header = vals is None
        g = grid(len(cols), spacing=0)
        for i, c in enumerate(cols):
            g.setColumnMinimumWidth(i, self.FOLDED_COL_W if self.folded else self.widths[c])
            if header and not self.folded:
                g.addWidget(self._head_cell(c), 0, i)
            else:
                g.addWidget(Label(str(c if header else vals[i]), 12 if header else 13, 600 if header else 400,
                                  "body" if header else "ink", mono=True, elide=True), 0, i)
        live = header and not self.folded
        g.setContentsMargins(18 if live else 24, 6 if live else 10 if header else 8, 30 if live else 24,
                             6 if live else 10 if header else 8)
        if not live:
            return vbox(g, HLine())
        trap = ClickTrap()
        trap.setLayout(g)
        return vbox(trap, HLine())

    def _head_cell(self, col):
        sort, filtered = self.view["sort"], bool(self.view["filters"].get(col, "").strip())
        on = filtered or (sort and sort[0] == col)
        cell = Box(bg=None, radius=8, hover="surf2")
        cell.setLayout(hbox((Label(col, 12, 600, "ink" if on else "body", mono=True, elide=True), 1),
                            *((4, Label("↑" if sort[1] else "↓", 12, 600, "ink")) if sort and sort[0] == col else ()),
                            *((4, Dot("ink", 6)) if filtered else ()), 6, Chevron("mute", 90),
                            margins=(6, 4, 6, 4), align=Qt.AlignmentFlag.AlignVCenter))
        cell.setCursor(Qt.CursorShape.PointingHandCursor)
        cell.setToolTip(col)
        cell.clicked.connect(lambda: self._column_menu(col, cell))
        return cell

    def show_page(self, n):
        self.page = n = max(0, min(n, self.pages - 1))
        self.app.s.table_page[self.key] = n
        clear_layout(self.head)
        clear_layout(self.rows)
        cols = self.shown_cols[:self.PREVIEW_COLS] if self.folded else self.shown_cols
        recs = self.view_recs
        shown = recs[:self.PREVIEW] if self.folded else recs[n * self.per_page:(n + 1) * self.per_page]
        self.head.addLayout(self._row(cols))
        for r in shown:
            self.rows.addLayout(self._row(cols, [r.get(c, "") for c in cols]))
        if not shown:
            none = Label("No rows match the filters" if self.recs else "No rows", 13, 400, "mute", lh=40)
            none.setContentsMargins(24, 0, 24, 0)
            self.rows.addWidget(none)
        if self.foldable:
            self.chev.rotation = 0 if self.folded else 90
            self.chev.update()
            hidden = f" · first {len(cols)} of {len(self.shown_cols)} columns" if len(cols) < len(self.shown_cols) else ""
            self.fold_note.setText(f"first {self.PREVIEW} rows{hidden} · click to expand" if self.folded else "click to fold")
        self.tools.setVisible(not self.folded)
        self.pager.setVisible(not self.folded)
        self.pager.set_page(n)
        self.table.updateGeometry()
        self.scroll.updateGeometry()


CHART_MIME = "application/x-laboard-chart"


class _Slider(QSlider):
    def sizeHint(self):
        return QSize(140, super().sizeHint().height())


class _CardDrag(QObject):
    def __init__(self, page, box, tag, chart):
        super().__init__(box)
        self.page, self.box, self.tag, self.chart = page, box, tag, chart
        self.start, self.dragged = None, False
        box.installEventFilter(self)

    def eventFilter(self, obj, e):
        t = e.type()
        if t == QEvent.Type.MouseButtonPress and e.button() == Qt.MouseButton.LeftButton:
            self.start = e.globalPosition().toPoint()
        elif t == QEvent.Type.MouseMove and self.start is not None and e.buttons() & Qt.MouseButton.LeftButton:
            if self.chart.view != (0.0, 1.0):
                self.start = None
            elif (e.globalPosition().toPoint() - self.start).manhattanLength() >= QApplication.startDragDistance():
                hot, self.start, self.dragged = self.box.mapFromGlobal(self.start), None, True
                self.chart.pan = None
                self.page.drag_card(self.box, self.tag, hot)
                return True
        elif t == QEvent.Type.MouseButtonRelease:
            self.start = None
            if self.dragged:
                self.dragged = False
                return True
        return False


class _CompareDrop(QObject):
    def __init__(self, page, panel, group):
        super().__init__(panel)
        self.page, self.panel, self.group = page, panel, group
        panel.setAcceptDrops(True)
        panel.installEventFilter(self)

    def eventFilter(self, obj, e):
        t = e.type()
        if t in (QEvent.Type.DragEnter, QEvent.Type.DragMove) and e.mimeData().hasFormat(CHART_MIME):
            self.panel.restyle(border=f"2px solid {GROUP_COLORS[self.group]}")
            e.acceptProposedAction()
            return True
        if t in (QEvent.Type.DragLeave, QEvent.Type.Drop):
            self.panel.restyle(border="2px solid transparent")
            if t == QEvent.Type.Drop and e.mimeData().hasFormat(CHART_MIME):
                e.acceptProposedAction()
                tag = bytes(e.mimeData().data(CHART_MIME)).decode()
                QTimer.singleShot(0, lambda: self.page.merge(tag, self.group))
            return True
        return False


class _PanelResize(QObject):
    def __init__(self, page, side):
        super().__init__(side)
        self.page = page
        side.installEventFilter(self)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.Resize and 0 <= e.size().width() < e.oldSize().width():
            self.page.unshare(e.oldSize().width() - e.size().width())
        return False


class ResultPage(Scroll):
    def __init__(self, app):
        self.app = app
        s = app.s
        sel = s.sel["result"]
        self.file = str(store.RESULT_PATHS[sel])
        self.charts = []
        self.series = {}
        self.cmp = None
        self.cards = {}
        self.chart_h = 0
        super().__init__(wrap(self._file(sel, store.RESULT_PATHS[sel])))
        self.centre_min = max(CHART_MIN, self.widget().minimumSizeHint().width()) + 10 if self.charts else None
        self.fold_left = 160 if self.charts else 0
        self.side = self._compare_panel()
        self.right_on = bool(self._picked())

    def _smoothing(self, head):
        slider = _Slider(Qt.Orientation.Horizontal)
        slider.setRange(0, 19)
        slider.setValue(round(self.app.s.smooth / 0.05))
        slider.setMinimumWidth(60)
        slider.setMaximumWidth(140)
        slider.setStyleSheet(f"QSlider::groove:horizontal{{height:4px;background:{T.surf2};border-radius:2px;}}"
                             f"QSlider::sub-page:horizontal{{background:{T.ink};border-radius:2px;}}"
                             f"QSlider::handle:horizontal{{background:{T.ink};width:14px;height:14px;margin:-5px 0;border-radius:7px;}}")
        self.smooth_label = Label(f"{self.app.s.smooth:.2f}", 13, mono=True)
        self.smooth_label.setFixedWidth(36)
        slider.valueChanged.connect(self.on_smooth)
        smoothing = hbox(elided("Smoothing", 13, 400, "body"), 10, slider, 10, self.smooth_label, align=Qt.AlignmentFlag.AlignVCenter)
        reset = Button("Reset", on_click=self.untick_all)
        head.add(vbox(smoothing, 8, hbox("stretch", reset)), stretch=0)

    def untick_all(self):
        picked = self.app.s.chart_sel
        gone = [k for k in picked if k[0] == self.file]
        if not gone:
            return self.app.status("No charts are ticked")
        for k in gone:
            del picked[k]
        for box, check in self.cards.values():
            box.restyle(border=self.UNSELECTED)
            check.set_checked(False)
        self._refresh_compare()
        self.app.show_right(False)
        self.app.status(f"Unticked {len(gone)} chart{'s' if len(gone) != 1 else ''}")

    def _file(self, sel, path):
        path = Path(path)
        source, kind = _kind(path)
        body = vbox(spacing=12)
        parsed, charts, extra = "", [], None
        try:
            if kind == "tfevents":
                tags = readers.tfevents(path)
                charts = [(tag, steps, vals, "step") for tag, (steps, vals) in tags.items() if len(vals) > 1]
                parsed = f"{len(tags)} scalar tag{'s' if len(tags) != 1 else ''}"
            elif kind == "table":
                cols, recs, more = readers.table(path)
                x_key, xs, series = readers.numeric(recs)
                charts = [(k, xs[:len(v)], v, x_key or "row") for k, v in series.items()]
                parsed = f"{len(cols)} columns · {len(recs):,}{'+' if more else ''} rows"
                extra = RecordTable(self.app, str(path), cols, recs, more)
            elif kind == "text":
                lines, parsed = readers.text(path)
                extra = self._text(lines) if lines else None
            else:
                size = QImageReader(str(path)).size()
                parsed = f"{size.width()}×{size.height()} {path.suffix[1:].upper()}" if size.isValid() else "unreadable image"
        except (OSError, UnicodeDecodeError, csv.Error) as e:
            parsed = f"could not read: {e}"
        root = Path(store.PROJECT["path"])
        where = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        title = hbox(elided(path.name, 30, 900, display=True, spacing=-0.5), 12, Pill(source, "surf2", "ink", pad=(4, 12)),
                     "stretch", align=Qt.AlignmentFlag.AlignVCenter)
        head = Flow(spacing=20, fill=False)
        head.add(vbox(title, 8, Label(f"{where} · {parsed}", 13, 400, "body", elide=True)), 260)
        if charts:
            self._smoothing(head)
        body.addWidget(card(head, pad=(24, 18, 24, 18)))

        if charts:
            g = self.chart_flow = Flow(per_row=3, fill=False)
            for tag, xs, ys, xname in charts[:MAX_CHARTS]:
                xs, ys = _thin(list(xs), list(ys))
                lo, hi = min(ys), max(ys)
                ch = LineChart((), ())
                ch.set_y_range(lo, hi, _fmt)
                ch.set_axis(lambda f, xs=xs: xs[round(f * (len(xs) - 1))], xname)
                self.charts.append((ch, lo, hi, xs, ys))
                self.series[tag] = (xs, ys, xname)
                summary = f"last {_fmt(ys[-1])} · min {_fmt(lo)} · max {_fmt(hi)}"
                box = g.add(self._chart_card(str(path), tag, summary, ch), CHART_W)
                if not self.chart_h:
                    self.chart_h = box.sizeHint().height() - (ch.plot_h - LineChart.PLOT_H)
                g.set_width(box, self.app.s.chart_size.get((str(path), tag), (None,))[0])
            body.addLayout(g)
            if len(charts) > MAX_CHARTS:
                body.addWidget(Label(f"{len(charts) - MAX_CHARTS} more numeric series not shown", 12, 400, "mute"))
            self.on_smooth(round(self.app.s.smooth / 0.05))
        if isinstance(extra, RecordTable) and extra.foldable:
            if not charts:
                g = self.chart_flow = Flow(per_row=3, fill=False)
                body.addLayout(g)
            extra.place(g, self.chart_h)
            body.addStretch(1)
        elif isinstance(extra, RecordTable):
            body.addWidget(extra)
            body.addStretch(1)
        elif extra is not None:
            body.addWidget(extra, 1)
        if kind == "image":
            st = Stage(sel, parsed, "none", path=str(path), radius=16)
            box = Box(bg="stage", radius=16, border=f"1px solid {T.line}", layout=vbox(st, margins=(1, 1, 1, 1)))
            box.setMinimumHeight(640)
            body.addWidget(box, 1)
        return body

    def _text(self, lines):
        log = vbox(margins=(22, 18, 22, 18))
        for i, t in enumerate(lines, 1):
            color = "c3" if "WARN" in t else "#d03238" if "ERROR" in t or "Traceback" in t else "ink"
            safe = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
            log.addWidget(Label(f"<span style='color:#868685'>{i:<5}</span>{safe}", 13, mono=True,
                                color=color, rich=True, lh=22, select=True))
        log.addStretch(1)
        return Box(bg="stage", radius=16, border=f"1px solid {T.line}", layout=log)

    UNSELECTED = "3px solid transparent"

    def _border(self, key):
        slot = self.app.s.chart_sel.get(key)
        return self.UNSELECTED if slot is None else f"3px solid {GROUP_COLORS[slot // COMPARE_SIZE]}"

    def _chart_card(self, file, tag, summary, chart):
        key = (file, tag)
        on = key in self.app.s.chart_sel
        check = Check(on)
        name = elided(tag, 14, 600, mono=True)
        name.setMinimumWidth(min(name.sizeHint().width(), 100))
        head = hbox(name, 12, elided(summary, 12, 400, "body"), "stretch", 12, check,
                    align=Qt.AlignmentFlag.AlignBottom)
        head.setAlignment(check, Qt.AlignmentFlag.AlignTop)
        box = card(head, 12, chart, pad=(22, 18, 22, 18))
        box.restyle(border=self._border(key))
        box.setCursor(Qt.CursorShape.PointingHandCursor)

        def toggle():
            picked = self.app.s.chart_sel
            if key in picked:
                del picked[key]
            else:
                taken = {slot for (f, _), slot in picked.items() if f == file}
                if len(taken) >= MAX_COMPARE:
                    return self.app.status(f"Up to {MAX_COMPARE} charts can be compared; untick one first")
                picked[key] = min(set(range(MAX_COMPARE)) - taken)
            on = key in picked
            box.restyle(border=self._border(key))
            check.set_checked(on)
            self._refresh_compare()
            self.app.show_right(bool(self._picked()))
        box.clicked.connect(toggle)
        self.cards[tag] = (box, check)
        _CardDrag(self, box, tag, chart)
        self._resizable(box, chart, key, "lrb", corners=("lt",))
        return box

    def _resizable(self, box, chart, key, edges, corners=(), flow=None):
        sizes = self.app.s.chart_size
        flow = flow or (lambda: self.chart_flow)
        if key in sizes:
            chart.set_plot_h(sizes[key][1])
        start = {}

        def begin():
            start.update(w=box.width(), h=chart.plot_h, narrowest=max(CHART_MIN, box.minimumSizeHint().width()))

        def drag(dw, dh):
            width = sizes.get(key, (None,))[0]
            if dw:
                room = flow().geometry().width() or flow().parentWidget().width()
                width = round(min(max(start["w"] + dw, start["narrowest"]), room))
                flow().set_width(box, width)
            h = round(min(max(start["h"] + dh, PLOT_H[0]), PLOT_H[1]))
            chart.set_plot_h(h)
            sizes[key] = (width, h)
        EdgeResize(box, begin, drag, edges, corners)

    def _picked(self):
        return sorted(((t, slot) for (f, t), slot in self.app.s.chart_sel.items() if f == self.file and t in self.series),
                      key=lambda ts: ts[1])

    def drag_card(self, box, tag, hot):
        image = box.grab()
        scale = min(1.0, 360 / max(1, box.width()))
        ghost = QPixmap(image.size() * scale)
        ghost.setDevicePixelRatio(image.devicePixelRatio())
        ghost.fill(Qt.GlobalColor.transparent)
        p = QPainter(ghost)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setOpacity(0.6)
        p.drawPixmap(QRectF(0, 0, box.width() * scale, box.height() * scale), image, QRectF(image.rect()))
        p.end()
        mime = QMimeData()
        mime.setData(CHART_MIME, tag.encode())
        drag = QDrag(box)
        drag.setMimeData(mime)
        drag.setPixmap(ghost)
        drag.setHotSpot(QPoint(round(hot.x() * scale), round(hot.y() * scale)))
        box.setGraphicsEffect(QGraphicsOpacityEffect(opacity=0.35))
        try:
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            if not sip.isdeleted(box):
                box.setGraphicsEffect(None)

    def merge(self, tag, group):
        key, picked = (self.file, tag), self.app.s.chart_sel
        name = "Compare" if group == 0 else f"Compare {group + 1}"
        cur = picked.get(key)
        if cur is not None and cur // COMPARE_SIZE == group:
            return self.app.status(f"{tag} is already in {name}")
        taken = {slot for (f, _), slot in picked.items() if f == self.file}
        free = sorted(set(range(group * COMPARE_SIZE, (group + 1) * COMPARE_SIZE)) - taken)
        if not free:
            return self.app.status(f"{name} already holds {COMPARE_SIZE} charts; untick one there first")
        picked[key] = free[0]
        if tag in self.cards:
            box, check = self.cards[tag]
            box.restyle(border=self._border(key))
            check.set_checked(True)
        self._refresh_compare()
        self.app.show_right(True)
        self.app.status(f"{tag} merged into {name}")

    def _compare_panel(self):
        self.cmp = {}
        self.cmp_flow = Flow(per_row=1, fill=False)
        side = Scroll(wrap(vbox(self.cmp_flow, "stretch")))
        side.setFixedWidth(480)
        _PanelResize(self, side)
        self._refresh_compare()
        return side

    def unshare(self, by):
        flow, sizes = self.cmp_flow, self.app.s.chart_size
        if not flow.own:
            return
        width = flow.geometry().width()
        alone = lambda w: {row[0][0].widget() for row in flow._rows(w) if len(row) == 1}
        was, now = alone(width), alone(width - by)
        for g, c in self.cmp.items():
            card = c["card"]
            if card in now and card in flow.own and (card not in was or flow.own[card] >= width - by):
                flow.set_width(c["card"], None)
                if ("compare", g) in sizes:
                    sizes[("compare", g)] = (None, sizes[("compare", g)][1])

    def _compare_card(self, group):
        chart, count, legend = LineChart((), (), plot_h=260), Label("", 12, 400, "mute"), vbox(spacing=8)
        name = "Compare" if group == 0 else f"Compare {group + 1}"
        about = "Ticked charts on one shared axis" if group == 0 else \
            f"Ticked charts {group * COMPARE_SIZE + 1}–{(group + 1) * COMPARE_SIZE} on one shared axis"
        panel = card(hbox(Dot(GROUP_COLORS[group], 10), 8, Label(name, 16, 600, lh=24), "stretch", count,
                          align=Qt.AlignmentFlag.AlignVCenter), 2,
                     Label(about, 12, 400, "body", wrap=True), 14, chart, 16, legend, pad=(22, 18, 22, 18))
        key = ("compare", group)
        self._resizable(panel, chart, key, "lrb", corners=("lt",), flow=lambda: self.cmp_flow)
        self.cmp_flow.set_width(panel, self.app.s.chart_size.get(key, (None,))[0])
        panel.restyle(border="2px solid transparent")
        _CompareDrop(self, panel, group)
        return dict(card=panel, chart=chart, count=count, legend=legend)

    def _refresh_compare(self):
        groups = {}
        for t, slot in self._picked():
            groups.setdefault(slot // COMPARE_SIZE, []).append((t, slot % COMPARE_SIZE))
        flow = self.cmp_flow
        for g in [g for g in self.cmp if g not in groups]:
            gone = self.cmp.pop(g)["card"]
            flow.takeAt(next(i for i, (it, _, _) in enumerate(flow.blocks) if it.widget() is gone))
            flow.set_width(gone, None)
            gone.hide()
            gone.deleteLater()
        new = [g for g in groups if g not in self.cmp]
        for g in sorted(groups):
            if g not in self.cmp:
                self.cmp[g] = self._compare_card(g)
            self._draw_compare(self.cmp[g], groups[g])
        if new:
            while flow.count():
                flow.takeAt(0)
            for g in sorted(self.cmp):
                flow.add(self.cmp[g]["card"], CHART_W)

    def _draw_compare(self, c, picked):
        c["count"].setText(f"{len(picked)} of {COMPARE_SIZE}")
        clear_layout(c["legend"])
        data = [(t, slot, *self.series[t]) for t, slot in picked]
        lo, hi = min(min(ys) for *_, ys, _ in data), max(max(ys) for *_, ys, _ in data)
        x0, x1 = min(xs[0] for _, _, xs, _, _ in data), max(xs[-1] for _, _, xs, _, _ in data)
        span, xspan = (hi - lo) or 1, (x1 - x0) or 1
        c["chart"].set_y_range(lo, hi, _fmt)
        rows = []
        for tag, slot, xs, ys, _ in data:
            sm = _ema(ys, self.app.s.smooth)
            color, dashed = series_style(slot)
            rows.append(dict(name=tag, color=color, dashed=dashed, x01=[(x - x0) / xspan for x in xs],
                             y01=[(y - lo) / span for y in sm], xs=xs, ys=ys, smooth=sm if self.app.s.smooth else None))
        c["chart"].set_series([(r["y01"], r["color"], 2, r["x01"], r["dashed"]) for r in rows])
        c["chart"].set_hover(rows)
        c["chart"].set_axis(lambda f: x0 + f * xspan, data[0][4])
        for tag, slot, xs, ys, _ in data:
            c["legend"].addLayout(hbox(Swatch(*series_style(slot)), 10, elided(tag, 13, 600, mono=True), "stretch", 12,
                                       Label(f"last {_fmt(ys[-1])}", 12, 400, "body"), align=Qt.AlignmentFlag.AlignVCenter))

    def on_smooth(self, v):
        self.app.s.smooth = v * 0.05
        self.smooth_label.setText(f"{self.app.s.smooth:.2f}")
        for ch, lo, hi, xs, ys in self.charts:
            span = (hi - lo) or 1
            sm = _ema(ys, self.app.s.smooth)
            y01 = [(y - lo) / span for y in sm]
            ch.set_series([(y01, "ink", 2.25)])
            n = (len(ys) - 1) or 1
            ch.set_hover([dict(name="", color="ink", dashed=False, x01=[i / n for i in range(len(ys))], y01=y01, xs=xs, ys=ys,
                               smooth=sm if self.app.s.smooth else None)])
        if self.cmp is not None:
            self._refresh_compare()


def build(app):
    if app.s.sel["result"] not in store.RESULT_PATHS:
        return empty_state("No results", "Load a project file in Setting. Every file under its paths.results shows up here.")
    page = ResultPage(app)
    return page, page.side
