"""Result: charts from csv / jsonl / TensorBoard files, text and json, images."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics, QImageReader
from PyQt6.QtWidgets import QSlider

from .. import readers, store
from ..charts import LineChart, Stage, Swatch, series_style
from ..theme import WARNING, T, font
from ..widgets import (Box, Button, Check, Chevron, EdgeResize, Flow, HLine, HScroll, Label, Pill, Scroll, card, clear_layout, elided,
                       empty_state, grid, hbox, vbox, wrap)

MAX_COMPARE = 10  # charts that can be ticked at once (one colour slot each)
MAX_CHARTS = 16  # numeric series charted per file
PLOT_H = (80, 1000)  # px a chart's plot can be dragged between


def _ema(vals, sm):
    out, acc = [], None
    for v in vals:
        acc = v if acc is None else sm * acc + (1 - sm) * v
        out.append(acc)
    return out


def _fmt(v):
    """Short axis label: fits the chart's 34px y-label column."""
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


class RecordTable(Box):
    """Every column of a csv / tsv / jsonl file, PAGE rows at a time with Previous / Next. Columns are sized to
    their contents (within limits), and the table scrolls sideways when the centre is narrower than they are.
    A big table (FOLD_COLS+ columns and FOLD_ROWS+ rows) starts folded: a chart-sized card of its first PREVIEW
    rows and PREVIEW_COLS columns, squeezed to fit (one cell of ``flow``, the chart grid). A click on it unfolds it
    to the full width and back, and that stays while the page is shown. It has just those two sizes: folded, it
    keeps a chart cell's size whatever the charts beside it do."""

    PAGE = 50
    FOLD_COLS, FOLD_ROWS, PREVIEW, PREVIEW_COLS = 5, 10, 6, 5
    FOLDED_COL_W = 60  # folded, columns share the card's width down to this, values shortened with "…"

    def __init__(self, app, key, cols, recs, more):
        super().__init__(bg="surf", radius=16, layout=vbox(margins=(0, 8, 0, 8)))
        self.app, self.key, self.cols, self.recs, self.more = app, key, cols, recs, more
        self.flow = None  # the grid it sits in when it folds (place())
        self.fold_h = 0  # folded, at least this tall: a chart card's height
        cell, head = QFontMetrics(font(13, mono=True)), QFontMetrics(font(12, 600, mono=True))
        sample = recs[:500]
        self.widths = [min(280, max(72, head.horizontalAdvance(c), *(cell.horizontalAdvance(str(r.get(c, ""))) for r in sample))
                           + 16) for c in cols]
        self.head, self.rows = vbox(), vbox()
        self.table = wrap(vbox(self.head, self.rows))
        self.scroll = HScroll(self.table)
        self.where = elided("", 12, 400, "mute")  # shortens before the buttons get pushed out
        self.prev = Button("Previous", on_click=lambda: self.show_page(self.page - 1))
        self.next = Button("Next", on_click=lambda: self.show_page(self.page + 1))
        self.foldable = len(cols) >= self.FOLD_COLS and len(recs) >= self.FOLD_ROWS
        if self.foldable:
            self.chev = Chevron("mute", 0)
            self.fold_note = Label("", 12, 400, "mute")
            total = f"{len(recs):,}{'+' if more else ''}"
            self.layout().addLayout(hbox(self.chev, 10, Label(f"{len(cols)} columns · {total} rows", 13, 600), "stretch",
                                         self.fold_note, margins=(24, 6, 24, 8), align=Qt.AlignmentFlag.AlignVCenter))
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.clicked.connect(self.toggle)
        self.layout().addWidget(self.scroll)
        self.nav = wrap(hbox(self.where, "stretch", self.prev, 8, self.next, margins=(24, 10, 24, 4),
                             align=Qt.AlignmentFlag.AlignVCenter))
        self.layout().addWidget(self.nav)
        self.layout().addStretch(1)  # made taller than its rows (folded, to match the charts): the space goes below
        self.pages = max(1, -(-len(recs) // self.PAGE))
        self.show_page(app.s.table_page.get(key, 0))

    @property
    def folded(self):
        return self.foldable and self.key not in self.app.s.table_open

    def toggle(self):
        self.app.s.table_open ^= {self.key}
        self.show_page(self.page)
        self._fit_flow()

    def place(self, flow, chart_h=0):
        """Sit in ``flow`` (the chart grid): one cell while folded, a column wide and ``chart_h`` (a chart card's
        default height) tall; a whole row at its own height when open."""
        self.flow, self.fold_h = flow, chart_h
        flow.add(self, 360)
        flow.set_steady(self, True)  # a chart widened beside it doesn't squeeze it
        self._fit_flow()

    def _fit_flow(self):
        if self.flow is not None:
            self.flow.set_width(self, None if self.folded else 10 ** 6)  # Flow caps it at the row's width
            self.setMinimumHeight(self.fold_h if self.folded else 0)

    def _row(self, vals, header=False):
        """One table row; ``vals`` may be cut short (a folded table), the columns still line up."""
        g = grid(len(vals), spacing=0)
        for i, (v, w) in enumerate(zip(vals, self.widths)):
            g.setColumnMinimumWidth(i, self.FOLDED_COL_W if self.folded else w)  # the same in every row: columns line up
            g.addWidget(Label(str(v), 12 if header else 13, 600 if header else 400, "body" if header else "ink", mono=True,
                              elide=True), 0, i)
        g.setContentsMargins(24, 10 if header else 8, 24, 10 if header else 8)
        return vbox(g, HLine())

    def show_page(self, n):
        self.page = n = max(0, min(n, self.pages - 1))
        self.app.s.table_page[self.key] = n  # kept across re-renders
        clear_layout(self.head)
        clear_layout(self.rows)
        cols = self.cols[:self.PREVIEW_COLS] if self.folded else self.cols
        shown = self.recs[:self.PREVIEW] if self.folded else self.recs[n * self.PAGE:(n + 1) * self.PAGE]
        self.head.addLayout(self._row(cols, True))
        for r in shown:
            self.rows.addLayout(self._row([r.get(c, "") for c in cols]))
        if self.foldable:
            self.chev.rotation = 0 if self.folded else 90
            self.chev.update()
            hidden = f" · first {len(cols)} of {len(self.cols)} columns" if len(cols) < len(self.cols) else ""
            self.fold_note.setText(f"first {self.PREVIEW} rows{hidden} · click to expand" if self.folded else "click to fold")
        self.nav.setVisible(not self.folded)
        lo, hi = n * self.PAGE + 1, min((n + 1) * self.PAGE, len(self.recs))
        total = f"{len(self.recs):,}{'+' if self.more else ''}"
        self.where.setText(f"Rows {lo:,}–{hi:,} of {total} · page {n + 1} of {self.pages}" if self.recs else "No rows")
        self.prev.setEnabled(n > 0)
        self.next.setEnabled(n < self.pages - 1)
        self.table.updateGeometry()
        self.scroll.updateGeometry()


class ResultPage(Scroll):
    """The centre: one result file. ``side`` is the right panel that overlays the ticked charts; it opens only
    while at least one is ticked (``right_on``)."""

    def __init__(self, app):
        self.app = app
        s = app.s
        sel = s.sel["result"]
        self.file = str(store.RESULT_PATHS[sel])
        self.charts = []  # [(chart, lo, hi, xs, ys)]
        self.series = {}  # tag -> (xs, ys, x name) as charted, for the comparison
        self.cmp_chart = None  # built after the charts (_compare_panel)
        self.chart_h = 0  # a chart card's height at the default plot height (0: no charts)
        super().__init__(wrap(self._file(sel, store.RESULT_PATHS[sel])))
        self.side = self._compare_panel()
        self.right_on = bool(self._picked())

    def _smoothing(self, head):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 19)
        slider.setValue(round(self.app.s.smooth / 0.05))
        slider.setFixedWidth(140)
        slider.setStyleSheet(f"QSlider::groove:horizontal{{height:4px;background:{T.surf2};border-radius:2px;}}"
                             f"QSlider::sub-page:horizontal{{background:{T.ink};border-radius:2px;}}"
                             f"QSlider::handle:horizontal{{background:{T.ink};width:14px;height:14px;margin:-5px 0;border-radius:7px;}}")
        self.smooth_label = Label(f"{self.app.s.smooth:.2f}", 13, mono=True)
        self.smooth_label.setFixedWidth(36)
        slider.valueChanged.connect(self.on_smooth)
        head.add(hbox(Label("Smoothing", 13, 400, "body"), 10, slider, 10, self.smooth_label, align=Qt.AlignmentFlag.AlignVCenter),
                 stretch=0)

    def _file(self, sel, path):
        """Charts + table, text, or image for one result file."""
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
        except (OSError, UnicodeDecodeError) as e:
            parsed = f"could not read: {e}"
        root = Path(store.PROJECT["path"])
        where = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        title = hbox(elided(path.name, 30, 900, display=True, spacing=-0.5), 12, Pill(source, "surf2", "ink", pad=(4, 12)),
                     "stretch", align=Qt.AlignmentFlag.AlignVCenter)
        head = Flow(spacing=20, fill=False)  # smoothing wraps under the title when the centre is narrow
        head.add(vbox(title, 8, Label(f"{where} · {parsed}", 13, 400, "body", elide=True)), 260)
        if charts:
            self._smoothing(head)
        body.addWidget(card(head, pad=(24, 18, 24, 18)))

        if charts:
            # three per row, fewer when the centre is narrow; each card keeps its own height (fill=False), so resizing
            # one doesn't stretch its neighbour
            g = self.chart_flow = Flow(per_row=3, fill=False)
            for tag, xs, ys, xname in charts[:MAX_CHARTS]:
                xs, ys = _thin(list(xs), list(ys))
                lo, hi = min(ys), max(ys)
                ch = LineChart((), ())  # ticks: set_y_range, set_axis
                ch.set_y_range(lo, hi, _fmt)
                ch.set_axis(lambda f, xs=xs: xs[round(f * (len(xs) - 1))], xname)  # points are evenly spaced
                self.charts.append((ch, lo, hi, xs, ys))
                self.series[tag] = (xs, ys, xname)
                summary = f"last {_fmt(ys[-1])} · min {_fmt(lo)} · max {_fmt(hi)}"
                box = g.add(self._chart_card(str(path), tag, summary, ch), 360)
                if not self.chart_h:  # a chart card at the default plot height, for the folded table to match
                    self.chart_h = box.sizeHint().height() - (ch.plot_h - LineChart.PLOT_H)
                g.set_width(box, self.app.s.chart_size.get((str(path), tag), (None,))[0])
            body.addLayout(g)
            if len(charts) > MAX_CHARTS:
                body.addWidget(Label(f"{len(charts) - MAX_CHARTS} more numeric series not shown", 12, 400, "mute"))
            self.on_smooth(round(self.app.s.smooth / 0.05))
        if isinstance(extra, RecordTable) and extra.foldable:  # a cell after the charts, the width of a row when open
            if not charts:
                g = self.chart_flow = Flow(per_row=3, fill=False)
                body.addLayout(g)
            extra.place(g, self.chart_h)
            body.addStretch(1)
        elif isinstance(extra, RecordTable):  # as tall as its rows, spare height below the page
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
            color = "c3" if "WARN" in t else "#d03238" if "ERROR" in t or "Traceback" in t else "ink"  # c3: #b86700 light
            safe = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
            log.addWidget(Label(f"<span style='color:#868685'>{i:<5}</span>{safe}", 13, mono=True,
                                color=color, rich=True, lh=22, select=True))
        log.addStretch(1)
        return Box(bg="stage", radius=16, border=f"1px solid {T.line}", layout=log)

    SELECTED = f"3px solid #054d28" #{WARNING}
    UNSELECTED = "3px solid transparent"  # same width, so selecting doesn't shift the chart

    def _chart_card(self, file, tag, summary, chart):
        """A chart card that is selected by clicking anywhere on it: a check in its top-right corner and a thick
        warning-coloured border. Selections are kept per file across re-renders."""
        key = (file, tag)
        on = key in self.app.s.chart_sel
        check = Check(on)
        head = hbox(elided(tag, 14, 600, mono=True), 12, Label(summary, 12, 400, "body"), "stretch", 12, check,
                    align=Qt.AlignmentFlag.AlignBottom)
        head.setAlignment(check, Qt.AlignmentFlag.AlignTop)
        box = card(head, 12, chart, pad=(22, 18, 22, 18))
        box.restyle(border=self.SELECTED if on else self.UNSELECTED)
        box.setCursor(Qt.CursorShape.PointingHandCursor)

        def toggle():
            picked = self.app.s.chart_sel
            if key in picked:
                del picked[key]
            else:
                taken = {slot for (f, _), slot in picked.items() if f == file}
                if len(taken) >= MAX_COMPARE:
                    return self.app.status(f"Up to {MAX_COMPARE} charts can be compared; untick one first")
                picked[key] = min(set(range(MAX_COMPARE)) - taken)  # its colour stays while others come and go
            on = key in picked
            box.restyle(border=self.SELECTED if on else self.UNSELECTED)
            check.set_checked(on)
            self._refresh_compare()
            self.app.show_right(bool(self._picked()))
        box.clicked.connect(toggle)
        self._resizable(box, chart, key, "lrb", corners=("lt",))
        return box

    def _resizable(self, box, chart, key, edges, corners=()):
        """Drag the card's edges to size it: the bottom sets the chart's height, left/right its width in the grid.
        Sizes last while the page is shown (``chart_size``: key -> (width or None, plot height))."""
        sizes = self.app.s.chart_size
        if key in sizes:
            chart.set_plot_h(sizes[key][1])
        start = {}

        def begin():
            start.update(w=box.width(), h=chart.plot_h)

        def drag(dw, dh):
            width = sizes.get(key, (None,))[0]
            if dw:
                width = round(min(max(start["w"] + dw, 280), self.chart_flow.geometry().width()))
                self.chart_flow.set_width(box, width)
            h = round(min(max(start["h"] + dh, PLOT_H[0]), PLOT_H[1]))
            chart.set_plot_h(h)
            sizes[key] = (width, h)
        EdgeResize(box, begin, drag, edges, corners)

    def _picked(self):
        """[(tag, colour slot)] ticked in this file, in slot order."""
        return sorted(((t, slot) for (f, t), slot in self.app.s.chart_sel.items() if f == self.file and t in self.series),
                      key=lambda ts: ts[1])

    def _compare_panel(self):
        self.cmp_chart = LineChart((), (), plot_h=260)
        self.cmp_count = Label("", 12, 400, "mute")
        self.cmp_legend = vbox(spacing=8)
        panel = card(hbox(Label("Compare", 16, 600, lh=24), "stretch", self.cmp_count, align=Qt.AlignmentFlag.AlignVCenter), 2,
                     Label("Ticked charts on one shared axis", 12, 400, "body", wrap=True), 14, self.cmp_chart, 16,
                     self.cmp_legend, pad=(22, 18, 22, 18))
        self._resizable(panel, self.cmp_chart, "compare", "b")  # its width is the panel's (the gutter line)
        side = Scroll(wrap(vbox(panel, "stretch")))
        side.setFixedWidth(480)  # its width when it opens; then the user's (SideHandle)
        self._refresh_compare()
        return side

    def _refresh_compare(self):
        """Redraw the comparison: every ticked series in its slot colour on one y axis (their joint min..max) and
        one x axis (their joint range), with the current smoothing, plus a legend naming each colour."""
        picked = self._picked()
        self.cmp_count.setText(f"{len(picked)} of {MAX_COMPARE}")
        clear_layout(self.cmp_legend)
        if not picked:
            self.cmp_chart.set_hover([])
            return self.cmp_chart.set_series([])
        data = [(t, slot, *self.series[t]) for t, slot in picked]
        lo, hi = min(min(ys) for *_, ys, _ in data), max(max(ys) for *_, ys, _ in data)
        x0, x1 = min(xs[0] for _, _, xs, _, _ in data), max(xs[-1] for _, _, xs, _, _ in data)
        span, xspan = (hi - lo) or 1, (x1 - x0) or 1
        self.cmp_chart.set_y_range(lo, hi, _fmt)
        rows = []
        for tag, slot, xs, ys, _ in data:
            sm = _ema(ys, self.app.s.smooth)
            color, dashed = series_style(slot)
            rows.append(dict(name=tag, color=color, dashed=dashed, x01=[(x - x0) / xspan for x in xs],
                             y01=[(y - lo) / span for y in sm], xs=xs, ys=ys, smooth=sm if self.app.s.smooth else None))
        self.cmp_chart.set_series([(r["y01"], r["color"], 2, r["x01"], r["dashed"]) for r in rows])
        self.cmp_chart.set_hover(rows)
        self.cmp_chart.set_axis(lambda f: x0 + f * xspan, data[0][4])
        for tag, slot, xs, ys, _ in data:
            self.cmp_legend.addLayout(hbox(Swatch(*series_style(slot)), 10, elided(tag, 13, 600, mono=True), "stretch", 12,
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
        if self.cmp_chart is not None:
            self._refresh_compare()


def build(app):
    if app.s.sel["result"] not in store.RESULT_PATHS:
        return empty_state("No results", "Load a project file in Setting. Every file under its paths.results shows up here.")
    page = ResultPage(app)
    return page, page.side
