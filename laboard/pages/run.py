"""Hyperparameter (the "run" tab): launch info, progress, and hyperparameters read from each training run's configs."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from .. import store
from ..charts import Meter
from ..widgets import (Box, Button, Chevron, Flow, HLine, HScroll, Label, Scroll, card, elided, empty_state, hbox, mono_span,
                       vbox, wrap)

PAGE = 20  # rows of a config file per page; more get Previous / Next


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


def _section(app, title, file, rows, numbered):
    """A config file's rows as a key / value table under a header that opens and closes it (closed at first),
    PAGE rows at a time with Previous / Next."""
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
    shown = []  # the widgets of the rows on screen

    def fill(page):
        """Put the rows of ``page`` in the table, in place of the ones there."""
        for w in shown:
            g.removeWidget(w)
            w.hide()
            w.deleteLater()
        shown.clear()
        for i in range(page * PAGE, min((page + 1) * PAGE, len(rows))):
            k, v, _src = rows[i]
            r = (i - page * PAGE) * 2
            line = HLine()
            g.addWidget(line, r, 0, 1, vc + 1)
            shown.append(line)
            if numbered:
                n = Label(str(i + 1), 12, 600, "mute")
                g.addWidget(n, r + 1, 0, Qt.AlignmentFlag.AlignTop)
                shown.append(n)
            key = Label(k, 13, 600 if numbered else 400, "ink" if numbered else "body", wrap=True)
            val = Label("\u200b".join(v), 13, 400, mono=True, wrap=True)  # zero-width spaces: long values wrap anywhere
            for w in (key, val):
                w.setContentsMargins(0, 7, 0, 7)
            g.addWidget(key, r + 1, kc, Qt.AlignmentFlag.AlignTop)
            g.addWidget(val, r + 1, vc, Qt.AlignmentFlag.AlignTop)
            shown.extend((key, val))

    table = HScroll(wrap(g))
    pages = max(1, -(-len(rows) // PAGE))
    key = (app.s.sel["run"], file)
    where = elided("", 12, 400, "mute")  # shortens before the buttons get pushed out
    prev = Button("Previous", on_click=lambda: show_page(app.s.run_page.get(key, 0) - 1))
    nxt = Button("Next", on_click=lambda: show_page(app.s.run_page.get(key, 0) + 1))

    def show_page(n):
        n = app.s.run_page[key] = max(0, min(n, pages - 1))  # kept across re-renders
        fill(n)
        lo, hi = n * PAGE + 1, min((n + 1) * PAGE, len(rows))
        where.setText(f"Rows {lo:,}–{hi:,} of {len(rows):,}")
        prev.setEnabled(n > 0)
        nxt.setEnabled(n < pages - 1)
        table.widget().adjustSize()
        table.updateGeometry()

    body = wrap(vbox(8, table, *((10, hbox((where, 1), 12, prev, 8, nxt, align=Qt.AlignmentFlag.AlignVCenter))
                                 if pages > 1 else ())))
    chev = Chevron("body", 0)

    def show(opened):
        """Open or close the table in place (a re-render would lose the page's scroll position); its rows are only
        built the first time it opens."""
        if opened and not shown:
            show_page(app.s.run_page.get(key, 0))
        chev.rotation = 90 if opened else 0
        chev.update()
        body.setVisible(opened)

    def toggle():
        app.s.run_open ^= {key}
        show(key in app.s.run_open)

    n = f"{len(rows):,} row{'s' if len(rows) != 1 else ''}"
    name, src = elided(title, 15, 600, lh=22), elided(file, 12, 400, "mute", mono=True)
    # elided labels take any width they're given: cap them at their text so the count and file name keep apart
    name.setMaximumWidth(name.fontMetrics().horizontalAdvance(title) + 4)
    src.setMaximumWidth(min(260, src.fontMetrics().horizontalAdvance(file) + 4))
    head = Box(bg=None, radius=8, on_click=toggle, layout=hbox(
        chev, 10, (name, 1), 10, Label(n, 12, 400, "mute"), "stretch", 16, (src, 1), align=Qt.AlignmentFlag.AlignVCenter))
    box = card(head, body, pad=(22, 14, 22, 14))
    show(key in app.s.run_open)  # every table starts closed; hidden once it has a parent (no window flash)
    return box


def build(app):
    if app.s.sel["run"] not in store.RUN_DETAILS:
        return empty_state("No hyperparameters", "Load a project file in Setting. Folders under its Path.Hyperparameter that hold config files "
                                      "(json, yaml, toml) show up here.")
    R, sections = _run(app)
    srcs = R["sources"]
    files = ", ".join(mono_span(f) for f in srcs[:4]) + (f" +{len(srcs) - 4} more" if len(srcs) > 4 else "")
    hp_top = Flow(spacing=16, fill=False)  # the controls wrap under the title when the centre is narrow
    hp_top.add(vbox(Label("Hyperparameters", 16, 600, lh=24),
                    Label(f"Read from source at launch · {files}", 13, 400, "body", rich=True, wrap=True)), 240)
    hp_top.add(Button("Re-read", on_click=lambda: app.load_project(store.PROJECT["toml"], text=app.toml_text)), stretch=0)
    hp_head = card(hp_top, pad=(24, 16, 24, 16))
    left = vbox(hp_head, spacing=12)  # one card per row, as wide as the column
    for title, file, rows, numbered in sections:
        left.addWidget(_section(app, title, file, rows, numbered))

    return Scroll(wrap(vbox(_header(app), 12, left, "stretch")))
