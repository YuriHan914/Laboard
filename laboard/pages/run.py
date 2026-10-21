"""Run: launch info, progress, and hyperparameters read from the training source."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from .. import store
from ..charts import Meter
from ..widgets import (Button, Flow, HLine, HScroll, Label, Scroll, Segmented, card, elided, empty_state, hbox, mono_span,
                       vbox, wrap)


def _run(app):
    """(info, hyperparameter sections) for the selected run."""
    return store.RUN_DETAILS[app.s.sel["run"]]


def _header(app):
    R = _run(app)[0]
    sub = Label(f"{R['cmd']} · commit {mono_span(R['commit'])} · {R['started']}", 13, 400, "body", rich=True, wrap=True)
    open_folder = Button("Open folder", on_click=lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(R["path"])))
    top = Flow(spacing=16, fill=False)  # the button wraps under the title when the centre is narrow
    top.add(vbox(elided(app.s.sel["run"], 32, 900, display=True, spacing=-0.5), 8, sub), 240)
    top.add(open_folder, stretch=0)
    progress = hbox((Meter(R["progress"], 8), 1), 16, Label(R["epoch"], 14, 600), 16, Label(R["eta"], 14, 400, "body"),
                    align=Qt.AlignmentFlag.AlignVCenter)
    return card(top, 16, progress, pad=(24, 20, 24, 20))


def _section(title, file, rows, numbered, show_src):
    g = QGridLayout()
    g.setContentsMargins(0, 0, 0, 0)
    g.setHorizontalSpacing(12)
    g.setVerticalSpacing(0)
    c = 0
    if numbered:
        g.setColumnMinimumWidth(c, 20)
        c += 1
    kc, vc = c, c + 1
    g.setColumnMinimumWidth(kc, 110)
    g.setColumnMinimumWidth(vc, 200)  # narrower than all the columns, the table scrolls sideways (HScroll)
    g.setColumnStretch(kc, 8)
    g.setColumnStretch(vc, 14)
    if show_src:
        g.setColumnMinimumWidth(vc + 1, 112)
    ncols = vc + 2 if show_src else vc + 1
    for i, (k, v, src) in enumerate(rows):
        r = i * 2
        g.addWidget(HLine(), r, 0, 1, ncols)
        if numbered:
            g.addWidget(Label(str(i + 1), 12, 600, "mute"), r + 1, 0, Qt.AlignmentFlag.AlignTop)
        key = Label(k, 13, 600 if numbered else 400, "ink" if numbered else "body", wrap=True)
        val = Label("\u200b".join(v), 13, 400, mono=True, wrap=True)  # zero-width spaces: long values wrap anywhere
        for w in (key, val):
            w.setContentsMargins(0, 7, 0, 7)
        g.addWidget(key, r + 1, kc, Qt.AlignmentFlag.AlignTop)
        g.addWidget(val, r + 1, vc, Qt.AlignmentFlag.AlignTop)
        if show_src:
            s = Label(src, 11.5, 400, "mute", mono=True, align=Qt.AlignmentFlag.AlignRight)
            s.setContentsMargins(0, 7, 0, 7)
            g.addWidget(s, r + 1, vc + 1, Qt.AlignmentFlag.AlignTop)
    head = hbox(elided(title, 15, 600, lh=22), "stretch", elided(file, 12, 400, "mute", mono=True), align=Qt.AlignmentFlag.AlignBottom)
    return card(head, 8, HScroll(wrap(g)), pad=(22, 18, 22, 18))


def build(app):
    if app.s.sel["run"] not in store.RUN_DETAILS:
        return empty_state("No runs", "Load a project file in Setting. Folders under its paths.runs that hold config files "
                                      "(json, yaml, toml) show up here.")
    R, sections = _run(app)
    show_src = app.s.show_src
    srcs = R["sources"]
    files = ", ".join(mono_span(f) for f in srcs[:4]) + (f" +{len(srcs) - 4} more" if len(srcs) > 4 else "")
    hp_top = Flow(spacing=16, fill=False)  # the controls wrap under the title when the centre is narrow
    hp_top.add(vbox(Label("Hyperparameters", 16, 600, lh=24),
                    Label(f"Read from source at launch · {files}", 13, 400, "body", rich=True, wrap=True)), 240)
    hp_top.add(hbox(Segmented([("on", "Show source"), ("off", "Values only")], "on" if show_src else "off",
                              lambda k: app.set(show_src=k == "on")), 16,
                    Button("Re-read", on_click=lambda: app.load_project(store.PROJECT["toml"])),
                    align=Qt.AlignmentFlag.AlignVCenter), stretch=0)
    hp_head = card(hp_top, pad=(24, 16, 24, 16))
    # two masonry-ish columns, like a CSS grid with align-items:start; one column when narrow
    g = Flow(per_row=2, fill=False)
    for title, file, rows, numbered in sections:
        g.add(_section(title, file, rows, numbered, show_src), 360)
    left = vbox(hp_head, 12, g)

    gpu = vbox(Label(store.GPU["name"] or "GPU", 16, 600, lh=24), 12)
    for k, v, pct in store.GPU["rows"]:
        gpu.addLayout(vbox(hbox(Label(k, 13, 400, "body"), "stretch", Label(v, 13)), 4, Meter(pct, 6), margins=(0, 0, 0, 10)))
    if not store.GPU["rows"]:
        gpu.addWidget(Label("nvidia-smi returned nothing", 13, 400, "mute"))
    right = card(gpu)
    right.setFixedWidth(360)

    lower = Flow(fill=False)  # the GPU card moves under the hyperparameters when they'd get too narrow
    lower.add(left, 480)
    lower.add(right, 360, 0)
    return Scroll(wrap(vbox(_header(app), 12, lower, "stretch")))
