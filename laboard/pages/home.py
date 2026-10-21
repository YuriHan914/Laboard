"""Home: Data / Model / Latest run / Result summary cards, plus the git history."""
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .. import store
from ..charts import AccuracyChart, DataChangeChart, StackedBar
from ..theme import T, qc
from ..widgets import (Box, Dot, Flow, HLine, Label, Pill, Scroll, Segmented, card, caption, empty_state, grid, hbox, link,
                       mono_span, stat_tile, vbox, wrap)

D = store.DASH


def _head(title, on_open, *extra):
    return hbox(Label(title, 18, 600, spacing=-0.3, lh=24), 10, *extra, "stretch", link("Open", on_open),
                align=Qt.AlignmentFlag.AlignVCenter)


def _tiles(*tiles):
    g = grid(3, spacing=10)
    for i, t in enumerate(tiles):
        g.addWidget(stat_tile(*t), 0, i)
    return g


def _summary_card(*items):
    c = card(*items, "stretch", pad=(24, 22, 24, 22), spacing=16)
    c.setMinimumWidth(0)
    return c


def _missing(app, title, tab, text):
    return _summary_card(_head(title, lambda: app.set(tab=tab)), Label(text, 13, 400, "body", wrap=True))


def _data_card(app):
    if not store.DATA_FOLDERS:
        return _missing(app, "Data", "data", "No data found in the [db] table or paths.data.")
    legend = hbox(spacing=16)
    for name, n, dot in D["splits"]:
        legend.addLayout(hbox(Dot(dot, 8), 6, Label(name, 12, 400, "body"), 4, Label(n, 12, 600), align=Qt.AlignmentFlag.AlignVCenter))
    legend.addStretch(1)
    footer = vbox(HLine(), 12, legend)
    note = Label(D["task_note"], 13, 400, "body", wrap=True)
    cap, src = D["changes_caption"]
    changes = D["data_changes"]
    chart = vbox(hbox(caption(cap), "stretch", caption(src)), 6,
                 DataChangeChart(changes, vmax=max(max(a, r) for _, _, a, r in changes))) if changes else vbox()
    return _summary_card(
        vbox(_head("Data", lambda: app.set(tab="data"), Pill(app.task, "surf2", "ink")), 8, note),
        _tiles(*D["tiles"]), chart, footer)


def _model_card(app):
    if not store.MODEL_FILES:
        return _missing(app, "Model", "model", "No model files found in paths.models.")
    total = sum(n for _, n, _, _ in D["formats"])
    legend = hbox(spacing=18)
    for name, n, ext, c in D["formats"]:
        legend.addLayout(hbox(Dot(c, 8), 6, Label(name, 13, 400, "body"), 4, Label(str(n), 13, 600), 4,
                              Label(ext, 11, 400, "mute", mono=True), align=Qt.AlignmentFlag.AlignVCenter))
    legend.addStretch(1)

    def row(cells, header=False):
        g = grid(4, spacing=0, hspacing=10)
        g.setColumnStretch(1, 0)
        g.setColumnStretch(2, 0)
        g.setColumnStretch(3, 0)
        g.setColumnMinimumWidth(1, 120)
        g.setColumnMinimumWidth(2, 76)
        g.setColumnMinimumWidth(3, 76)
        for i, (t, kw) in enumerate(cells):
            opts = dict(size=12 if header else 13, weight=600 if header else 400, color="body" if header else "ink",
                        align=Qt.AlignmentFlag.AlignRight if i >= 2 else Qt.AlignmentFlag.AlignLeft)
            g.addWidget(Label(t, **{**opts, **kw}), 0, i)
        g.setContentsMargins(0, 8, 0, 8)
        return vbox(g, HLine())

    cols = D["model_cols"]
    table = vbox(row([(c, {}) for c in cols], header=True))
    for name, fmt, n, acc in D["models"]:
        table.addLayout(row([(name, dict(weight=600, elide=True)), (fmt, dict(mono=True, color="body", size=12)), (f"{n}×", {}),
                             (acc, {})]))
    t1, t2, t3 = D["model_tiles"]
    return _summary_card(
        _head("Model", lambda: app.set(tab="model")),
        _tiles((t1, D["models_n"]), (t2, D["trained_n"]), (t3, D["last_trained"])),
        vbox(caption("Format"), 8, StackedBar([(n / total, c) for _, n, _, c in D["formats"]]), 10, legend),
        table)


def _run_card(app):
    if not store.RUNS:
        return _missing(app, "Latest run", "run", "No runs found in paths.runs.")
    run_name, commit, rest = D["run_note"]
    note = Label(f"{run_name} · commit {mono_span(commit)} · {rest}", 13, 400, "body", rich=True, wrap=True)
    g = grid(2, spacing=0, hspacing=24)
    for i, (k, v) in enumerate(D["hp"]):
        r, c = i // 2, i % 2
        g.addLayout(vbox(hbox(Label(k, 13, 400, "body"), 12, (Label(v, 13, 400, mono=True, align=Qt.AlignmentFlag.AlignRight, elide=True), 1),
                              margins=(0, 7, 0, 7)), HLine()), r, c)
    return _summary_card(vbox(_head("Latest run", lambda: app.set(tab="run")), 8, note), g)


def _result_card(app):
    if not store.RESULT_FILES:
        return _missing(app, "Result", "result", "No files found in paths.results.")
    rows = D["accuracy_csv"]
    if not rows:  # no accuracy.csv among the results
        return _summary_card(
            vbox(_head("Result", lambda: app.set(tab="result"), Label(store.RESULT_ROOT, 12, 400, "mute", mono=True)), 8,
                 Label("No accuracy.csv found in the results folder. Open the Result tab to browse csv, logs and images.",
                       13, 400, "body", wrap=True)),
            _tiles(*D.get("result_counts", [])))

    def key(swatch, text):
        return hbox(swatch, 6, Label(text, 12, 400, "body"), align=Qt.AlignmentFlag.AlignVCenter)

    def line(c):
        w = Box(bg=c, radius=2)
        w.setFixedSize(16, 3)
        return w

    sq = Box(bg="grid", radius=2)
    sq.setFixedSize(10, 10)
    legend = hbox(key(line("ink"), "train loss"), 18, key(line("c2"), "valid loss"), 18, key(sq, "inference ms / image"), "stretch")
    return _summary_card(
        vbox(_head("Result", lambda: app.set(tab="result"), Label(D["accuracy_path"], 12, 400, "mute", mono=True)), 10, legend),
        AccuracyChart(rows),
        _tiles((f"Best valid loss · {D['best_valid'][0]}", D["best_valid"][1]), (f"Fastest · {D['fastest'][0]}", D["fastest"][1]),
               ("Rows in csv", str(len(rows)))))


class Timeline(QWidget):
    def __init__(self, filled):
        super().__init__()
        self.filled = filled
        self.setFixedWidth(12)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(QRectF(5, 16, 2, self.height() - 16), qc(T.grid))
        p.setPen(QPen(qc(T.ink), 2))
        p.setBrush(qc(T.ink if self.filled else T.surf))
        p.drawEllipse(QRectF(1, 5, 10, 10))


WHERE_BADGE = {"local": ("Local · not pushed", "#ffc091", "#0e0f0c"), "remote": ("Remote · not pulled", "#38c8ff", "#0e0f0c")}


def where_badge(c):
    """Pill for a commit that is only local or only on the remote; None when it is on both (or there's no upstream)."""
    if c[7] in WHERE_BADGE and store.PROJECT.get("upstream"):
        text, bg, fg = WHERE_BADGE[c[7]]
        return Pill(text, bg, fg, size=11, pad=(1, 8))
    return None


REF_STYLE = {"tab": ("tab", "tabfg"), "soft": ("surf2", "body"), "green": ("#e2f6d5", "#054d28")}


def _history(app):
    s = app.s
    target = s.sel["home"]

    def touches(c):
        return any(p.endswith(target) or p == target for p, *_ in c[5])

    last_touch = next((c for c in store.COMMITS if touches(c)), store.COMMITS[0] if store.COMMITS else None)
    seg = Segmented([("all", "All"), ("file", "This file")], s.hist_filter, lambda k: app.set(hist_filter=k))
    lst = vbox()
    for c in store.COMMITS[app.view_index():]:  # history up to the commit being shown
        if s.hist_filter == "file" and not touches(c):
            continue
        is_open = c[0] == s.open_commit
        title = hbox(spacing=6, align=Qt.AlignmentFlag.AlignVCenter)
        title.addWidget(Label(c[1], 14, 600))
        for ref, k in c[6]:
            title.addWidget(Pill(ref, *REF_STYLE[k], size=11, pad=(1, 8)))
        badge = where_badge(c)
        if badge:
            title.addWidget(badge)
        title.addStretch(1)
        n = len(c[5])
        meta = Label(f"{mono_span(c[0], 'body')} · {c[2]} · {c[4]} · {n} file{'s' if n != 1 else ''}", 12, 400, "mute", rich=True, lh=18)
        content = vbox(title, meta, margins=(0, 0, 0, 10))
        if is_open:
            files = vbox(spacing=2, margins=(10, 6, 10, 6))
            for path, add, rem in c[5]:
                files.addLayout(hbox(Label(path, 12.5, mono=True), "stretch",
                                     Label(f"<span style='color:#2ead4b'>{add}</span> <span style='color:#d03238'>{rem}</span>",
                                           12.5, mono=True, rich=True)))
            content.addSpacing(8)
            content.addWidget(Box(bg="surf", radius=10, layout=files))
        row = Box(bg="surf2" if is_open else None, radius=12, hover=None if is_open else "surf2",
                  layout=hbox(Timeline(c is last_touch), 12, (content, 1), margins=(8, 8, 8, 0)),
                  on_click=lambda h=c[0]: app.set(open_commit=None if s.open_commit == h else h))
        lst.addWidget(row)
    if not store.COMMITS:
        lst.addWidget(Label(f"{store.PROJECT['path']} is not a git repository.", 13, 400, "body", wrap=True))
    lst.addStretch(1)
    body = vbox(hbox(Label("Git history", 16, 600, lh=24), "stretch", seg, margins=(20, 18, 20, 10), align=Qt.AlignmentFlag.AlignVCenter))
    body.addWidget(Scroll(wrap(vbox(lst, margins=(12, 0, 12, 12)))), 1)
    hist = Box(bg="surf", radius=16, layout=body)
    hist.setFixedWidth(480)
    return hist


def build(app):
    if not store.PROJECT:
        return empty_state("No project loaded", "Open Setting and load a laboard .toml project file.")
    g = Flow(per_row=2)  # two columns; one when the centre is too narrow, the cards then scroll vertically
    for c in (_data_card(app), _model_card(app), _run_card(app), _result_card(app)):
        g.add(c, 380)
    cards = Scroll(wrap(vbox(g, "stretch")))
    return cards, _history(app)
