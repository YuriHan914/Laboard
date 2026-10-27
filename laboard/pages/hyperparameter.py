"""Hyperparameter tab: launch info, progress, and hyperparameters read from each training run's configs."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from .. import store
from ..charts import Meter
from ..widgets import (Box, Button, Chevron, Flow, HLine, HScroll, Label, Pager, Scroll, SearchField, card, clear_layout,
                       elided, empty_state, hbox, mono_span, vbox, wrap)


def _run(app):
    """(info, hyperparameter sections) for the selected run."""
    return store.RUN_DETAILS[app.s.sel["hyperparameter"]]


def _header(app):
    R = _run(app)[0]
    sub = Label(f"{R['cmd']} · commit {mono_span(R['commit'])} · {R['started']}", 13, 400, "body", rich=True, wrap=True)
    open_folder = Button("Open folder", on_click=lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(R["path"])))
    top = Flow(spacing=16, fill=False)  # the button wraps under the title when the centre is narrow
    top.add(vbox(elided(app.s.sel["hyperparameter"], 32, 900, display=True, spacing=-0.5), 8, sub), 240)
    top.add(open_folder, stretch=0)
    progress = hbox((Meter(R["progress"], 8), 1), 16, Label(R["epoch"], 14, 600), 16, Label(R["eta"], 14, 400, "body"),
                    align=Qt.AlignmentFlag.AlignVCenter)
    return card(top, 16, progress, pad=(24, 20, 24, 20))


def _matches(title, rows, q):
    """(rows shown, rows that match) of a section for the search ``q`` (lower case; "" shows every row): the rows
    whose key, value or source holds it, or every row when the section's title does. A shown row is (number from 0,
    key, value, matches)."""
    title_hit = bool(q) and q in title.lower()
    out = [(i, k, v, bool(q) and any(q in str(t).lower() for t in (k, v, src))) for i, (k, v, src) in enumerate(rows)]
    out = [r for r in out if not q or title_hit or r[3]]
    return out, sum(r[3] for r in out)


def _section(app, title, file, rows, numbered, total, searching):
    """A config file's rows (``_matches``) as a key / value table under a header that opens and closes it,
    ``app.s.table_rows`` rows a page (set in Setting) under a ``Pager`` when they don't fit on one. Tables start
    closed, except while ``searching``: then they start open and the matching rows are highlighted. ``total``: the
    file's row count, shown next to the rows found."""
    per = app.s.table_rows
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
        for j in range(page * per, min((page + 1) * per, len(rows))):
            i, k, v, hit = rows[j]
            r = (j - page * per) * 2
            line = HLine()
            g.addWidget(line, r, 0, 1, vc + 1)
            shown.append(line)
            if hit:  # under the row's labels (made before them, so drawn first)
                mark = Box(bg="sel", radius=8)
                g.addWidget(mark, r + 1, 0, 1, vc + 1)
                shown.append(mark)
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
    key = (app.s.sel["hyperparameter"], file)

    def show_page(n):
        n = app.s.run_page[key] = max(0, min(n, pager.pages - 1))  # kept across re-renders
        fill(n)
        pager.set_page(n)
        table.widget().adjustSize()
        table.updateGeometry()

    pager = Pager(per, len(rows), show_page)
    body = wrap(vbox(8, table, *((10, pager) if pager.pages > 1 else ())))
    chev = Chevron("body", 0)

    def show(opened):
        """Open or close the table in place (a re-render would lose the page's scroll position); its rows are only
        built the first time it opens."""
        if opened and not shown:
            show_page(app.s.run_page.get(key, 0))
        chev.rotation = 90 if opened else 0
        chev.update()
        body.setVisible(opened)

    opened = [searching or key in app.s.run_open]

    def toggle():
        opened[0] = not opened[0]
        app.s.run_open = app.s.run_open | {key} if opened[0] else app.s.run_open - {key}
        show(opened[0])

    n = f"{len(rows):,} of {total:,} rows" if searching else f"{total:,} row{'s' if total != 1 else ''}"
    name, src = elided(title, 15, 600, lh=22), elided(file, 12, 400, "mute", mono=True)
    # elided labels take any width they're given: cap them at their text so the count and file name keep apart
    name.setMaximumWidth(name.fontMetrics().horizontalAdvance(title) + 4)
    src.setMaximumWidth(min(260, src.fontMetrics().horizontalAdvance(file) + 4))
    head = Box(bg=None, radius=8, on_click=toggle, layout=hbox(
        chev, 10, (name, 1), 10, Label(n, 12, 400, "mute"), "stretch", 16, (src, 1), align=Qt.AlignmentFlag.AlignVCenter))
    box = card(head, body, pad=(22, 14, 22, 14))
    show(opened[0])  # hidden once it has a parent (no window flash)
    return box


def build(app):
    if app.s.sel["hyperparameter"] not in store.RUN_DETAILS:
        return empty_state("No hyperparameters", "Load a project file in Setting. Folders under its Path.Hyperparameter that hold config files "
                                      "(json, yaml, toml) show up here.")
    R, sections = _run(app)
    srcs = R["sources"]
    files = ", ".join(mono_span(f) for f in srcs[:4]) + (f" +{len(srcs) - 4} more" if len(srcs) > 4 else "")
    hp_top = Flow(spacing=16, fill=False)  # the controls wrap under the title when the centre is narrow
    hp_top.add(vbox(Label("Hyperparameters", 16, 600, lh=24),
                    Label(f"Read from source at launch · {files}", 13, 400, "body", rich=True, wrap=True)), 240)
    search = SearchField("Search hyperparameters", app.s.hp_query, lambda text: find(text))
    hp_top.add(search, stretch=0)
    hp_head = card(hp_top, pad=(24, 16, 24, 16))
    found = vbox(spacing=12)  # one card per config file, as wide as the column

    def fill():
        """The cards of the config files with rows matching the search (all of them without one)."""
        clear_layout(found)
        q, hits = app.s.hp_query.strip().lower(), 0
        for title, file, rows, numbered in sections:
            shown, n = _matches(title, rows, q)
            hits += n
            if shown:
                found.addWidget(_section(app, title, file, shown, numbered, len(rows), bool(q)))
        if q and not found.count():
            found.addWidget(card(Label(f"No hyperparameters match “{app.s.hp_query.strip()}”.", 14, 400, "body", wrap=True),
                                 pad=(24, 32, 24, 32), radius=16))
        search.set_count(hits if q else None)

    def find(text):
        """Search as you type: only the cards change, so the box keeps the focus and the page its scroll."""
        app.s.hp_query = text
        app.s.run_page = {}  # page 1 of what's found
        fill()

    fill()
    left = vbox(hp_head, 12, found)

    return Scroll(wrap(vbox(_header(app), 12, left, "stretch")))
