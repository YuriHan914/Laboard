"""Laboard main window: title bar, top bar, sidebar + page, status bar."""
import argparse
import subprocess
import sys
from types import SimpleNamespace

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QPoint, QPointF, QRectF, QSettings, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QMainWindow, QSizePolicy, QWidget

from . import netronview, project, sidebar, store, theme
from .pages import data, home, hyperparameter, model, result, setting
from .theme import T
from .widgets import (Box, Button, Chevron, Collapsing, Dot, HLine, InfoIcon, Label, Logo, Pill, Scroll, Segmented, SideHandle,
                      SplashLogo, clear_layout, hbox, mono_span, vbox, wrap)

TABS = [("home", "Home"), ("data", "Data"), ("model", "Model"), ("hyperparameter", "Hyperparameter"), ("result", "Result"), ("setting", "Setting")]
PAGES = dict(home=home, data=data, model=model, hyperparameter=hyperparameter, result=result, setting=setting)


class WindowButton(QWidget):
    def __init__(self, kind, on_click):
        super().__init__()
        self.kind, self.on_click = kind, on_click
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        self.on_click()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2a2b28"))
        p.drawEllipse(QRectF(0, 0, 24, 24))
        p.setPen(QPen(QColor("#e8ebe6"), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        o = QPointF(7, 7)
        if self.kind == "min":
            p.drawLine(o + QPointF(1, 5), o + QPointF(9, 5))
        elif self.kind == "max":
            p.drawRect(QRectF(o + QPointF(1.5, 1.5), o + QPointF(8.5, 8.5)))
        else:
            p.drawLine(o + QPointF(2, 2), o + QPointF(8, 8))
            p.drawLine(o + QPointF(8, 2), o + QPointF(2, 8))


class TitleBar(QFrame):
    """Dark 40px title bar, used when the window runs frameless."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedHeight(40)
        self.setStyleSheet("TitleBar{background:#0e0f0c;border-bottom:1px solid #2a2b28;}")
        left = hbox(Logo(22), 8, Label("Laboard", 13, 600, "#e8ebe6"), "stretch", align=Qt.AlignmentFlag.AlignVCenter)
        title = f"{store.PROJECT['name']} — {store.PROJECT['toml']}" if store.PROJECT else "No project loaded"
        mid = Label(title, 13, 400, "#868685", align=Qt.AlignmentFlag.AlignCenter, select=False)  # dragging it moves the window
        btns = hbox("stretch", WindowButton("min", win.showMinimized), WindowButton("max", self.toggle_max),
                    WindowButton("close", win.close), spacing=8)
        self.setLayout(hbox((left, 1), (mid, 2), (btns, 1), margins=(16, 0, 10, 0), spacing=12))

    def toggle_max(self):
        self.win.showNormal() if self.win.isMaximized() else self.win.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.win.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        self.toggle_max()


def _saved_rows():
    """Rows a page of Result / Hyperparameter tables as last picked in Setting (QSettings), else the default."""
    try:
        n = int(QSettings("Laboard", "Laboard").value("table_rows", store.TABLE_ROWS_DEFAULT))
    except (TypeError, ValueError):
        n = store.TABLE_ROWS_DEFAULT
    return n if n in store.TABLE_ROWS else store.TABLE_ROWS_DEFAULT


CENTER_MIN = 620  # every page's centre shrinks with the window down to this (about the Data viewer's own minimum)

LOG_FILTERS = [("all", "All"), ("local", "Local"), ("remote", "Remote")]


def in_filter(c, kind):
    """Local: the local branch's history (unpushed + shared). Remote: the upstream's (shared + not pulled)."""
    return kind == "all" or c[7] in (kind, "both")


class Dialog(QWidget):
    """Modal card over a dimmed window (below the frameless title bar): icon, title, text, an optional ``body``
    widget (e.g. an input) and buttons: ``actions`` [(text, variant, on_click)], by default one dismiss button.
    An on_click of None closes the dialog.

    A child of the main window, so it covers whatever page is rendered; MainWindow.render keeps it on top.
    """

    def __init__(self, win, title, text, button="Cancel", body=None, actions=None):
        super().__init__(win)
        self.win = win
        card = Box(bg="surf", radius=24)
        card.setFixedWidth(520)
        card.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=64, offset=QPointF(0, 24), color=QColor(14, 15, 12, 89)))
        icon = Box(bg="surf2", radius=22, layout=hbox(InfoIcon(22), align=Qt.AlignmentFlag.AlignCenter))
        icon.setFixedSize(44, 44)
        words = vbox(Label(title, 22, 600, spacing=-0.4, lh=28), 6, Label(text, 14, 400, "body", wrap=True),
                     *((16, body) if body is not None else ()))
        buttons = hbox("stretch", spacing=8, margins=(28, 24, 28, 28))
        for text_, variant, on_click in actions or [(button, "tertiary", None)]:
            buttons.addWidget(Button(text_, variant, on_click=on_click or self.close))
        card.setLayout(vbox(hbox(vbox(icon, "stretch"), 16, (words, 1), margins=(28, 28, 28, 0)), buttons))
        self.setLayout(vbox("stretch", hbox("stretch", card, "stretch"), "stretch"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        win.installEventFilter(self)
        self._fit()

    def _fit(self):
        top = 40 if self.win.frameless else 0
        self.setGeometry(0, top, self.win.width(), self.win.height() - top)

    def eventFilter(self, obj, e):
        if obj is self.win and e.type() == QEvent.Type.Resize:
            self._fit()
        return False

    def paintEvent(self, e):
        QPainter(self).fillRect(self.rect(), QColor(14, 15, 12, 115))  # rgba(14,15,12,.45)

    def mousePressEvent(self, e):
        e.accept()  # the overlay is modal: clicks don't reach the page below

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()

    def open(self):
        self.show()
        self.raise_()
        self.setFocus()


class CommitPicker(QFrame):
    """'Show project as of' popup: git log grouped by day, split into local and remote commits."""

    def __init__(self, app, anchor):
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.app, self.anchor = app, anchor
        P = store.PROJECT
        panel = Box(bg="surf", radius=16, border=f"1px solid {T.line}")
        shadow = QGraphicsDropShadowEffect(blurRadius=40, offset=QPointF(0, 12), color=QColor(14, 15, 12, 60))
        panel.setGraphicsEffect(shadow)
        lay = vbox(margins=(8, 8, 8, 8))
        title = hbox(Label("Git log", 14, 600), "stretch", margins=(10, 8, 10, 4), align=Qt.AlignmentFlag.AlignVCenter)
        if P.get("upstream"):
            title.addWidget(Button("Fetch", compact=True, on_click=self.fetch))
            sync = (f"{mono_span(P['branch_name'])} ⇄ {mono_span(P['upstream'])} · {P['ahead']} ahead · {P['behind']} behind"
                    f" · fetched {P['fetched']}")
        else:
            sync = f"{mono_span(P.get('branch_name', ''))} has no upstream: every commit is local"
        lay.addLayout(title)
        note = Label(sync, 12, 400, "body", rich=True, wrap=True)
        note.setContentsMargins(10, 0, 10, 8)
        lay.addWidget(note)
        self.seg = None
        if P.get("upstream"):
            self.seg = Segmented(LOG_FILTERS, app.s.log_filter, self.set_filter, expand=True, pad=(5, 0))
            lay.addLayout(hbox(self.seg, margins=(10, 0, 10, 4)))
        self.rows = vbox()
        self.sc = Scroll(wrap(vbox(self.rows, "stretch")))
        lay.addWidget(self.sc)
        back = Label("<u>Back to latest</u>", 13, 600, rich=True, select=False)
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.mousePressEvent = lambda e: self.choose(None)
        lay.addWidget(HLine())
        lay.addLayout(hbox(Label("Older snapshots are read-only", 12, 400, "mute"), "stretch", back, margins=(10, 10, 10, 4)))
        panel.setLayout(lay)
        panel.setFixedWidth(460)
        self.setLayout(vbox(panel, margins=(24, 8, 24, 40)))
        self.populate()

    def populate(self):
        clear_layout(self.rows)
        last_day = ""
        cur, head = self.app.view_index(), store.PROJECT.get("head")
        shown = [(i, c) for i, c in enumerate(store.COMMITS) if in_filter(c, self.app.s.log_filter)]
        for i, c in shown:
            day, t = c[4].split(", ")
            if day != last_day:
                d = Label(day.upper(), 11, 600, "mute", spacing=0.4, lh=28)
                d.setContentsMargins(10, 10, 10, 4)
                d.setAlignment(Qt.AlignmentFlag.AlignBottom)
                self.rows.addWidget(d)
                last_day = day
            on = i == cur
            meta = Label(f"{mono_span(c[0], 'body')} · {c[2]} · {t}", 12, 400, "mute", rich=True, lh=16)
            text = vbox(Label(c[1], 13, 600, "selfg" if on else "ink", elide=True, lh=20), meta)
            dot = Dot("ink" if on else "surf", 10, ring="ink")
            row = hbox(vbox(5, dot, "stretch"), 12, (text, 1), spacing=6, margins=(10, 8, 10, 8))
            badge = home.where_badge(c)
            if badge:
                row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            if c[0] == head:
                row.addWidget(Pill("HEAD", "tab", "tabfg", size=11, pad=(1, 8)), 0, Qt.AlignmentFlag.AlignTop)
            self.rows.addWidget(Box(bg="sel" if on else None, radius=10, hover=None if on else "surf2", layout=row,
                                    on_click=lambda h=c[0]: self.choose(None if h == head else h)))
        if not shown:
            empty = Label("No commits here.", 13, 400, "mute")
            empty.setContentsMargins(10, 10, 10, 10)
            self.rows.addWidget(empty)
        self.rows.invalidate()  # the scroll area was built empty; size it to the rows just added
        self.sc.setFixedHeight(min(480, self.sc.widget().layout().sizeHint().height() + 4))
        self.adjustSize()
        pos = self.anchor.mapToGlobal(QPoint(self.anchor.width(), self.anchor.height()))
        self.move(pos.x() - self.width() + 24, pos.y())

    def set_filter(self, kind):
        self.app.s.log_filter = kind
        if self.seg is not None:
            self.seg.select(kind)  # the popup isn't rebuilt: move the white segment to the choice here
        self.populate()

    def fetch(self):
        self.close()
        QTimer.singleShot(0, self.app.fetch_remote)

    def choose(self, h):
        self.close()
        QTimer.singleShot(0, lambda: self.app.show_commit(h))


def _first(rows, keep=lambda r: True):
    return next((r[0] for r in rows if keep(r)), "")


class MainWindow(QMainWindow):
    def __init__(self, start_tab="home", theme_name="light", frameless=False):
        super().__init__()
        self.frameless = frameless
        theme.set_theme(theme_name)
        if frameless:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.resize(1920, 1080)
        self.setMinimumHeight(760)  # width: the top bar up to the Setting tab, which leaves the centre CENTER_MIN
        self._status_msg = None
        self.dialog = None
        self.toml_text = None  # the loaded project file as edited in Setting, or None: as on disk
        self.side_widths = {}  # side panel widths the user dragged, by SideHandle key, as shares of side_scale()
        self.handles, self.page, self.center_min, self.own_centre = [], None, CENTER_MIN, None
        self.top_min = 0  # the top bar's minimum width, which is the window's
        self._left_page = False  # the next render shows another tab: start its scroll at the left
        netronview.attach(self)  # before the window is shown, so adding the graph later doesn't recreate the window
        self.reset_state(start_tab)
        self.render()

    @staticmethod
    def view_state():
        """How a page is being looked at (filters, modes, zoom, ticks, table page, typed input), as it starts. It
        lasts only while the user stays on the page: switching tabs puts all of it back to this."""
        return dict(
            hist_filter="all", open_commit=_first(store.COMMITS) or None, smooth=0.6, split_filter="all",
            view_mode="raw", zoom=None, pending_toml=None, pt_view="inferred", log_filter="all",
            toml_view="fields",  # Setting: project file shown as fields or as text
            setting_scroll=0,  # Setting: how far the page is scrolled, kept when Edit → Save reloads it
            table_page={},  # Result csv table: page shown, by file
            table_open=set(),  # big Result csv tables the user unfolded, by file
            table_view={},  # Result csv tables: dict(sort=(column, ascending) | None, filters={column: text}, hidden=set()), by file
            run_page={},  # Hyperparameter tables: page shown, by (run, file)
            run_open=set(),  # Hyperparameter tables the user opened (all start closed), by (run, file)
            hp_query="",  # Hyperparameter: the search typed above the config tables
            chart_sel={},  # Result charts the user ticked: (file, tag) -> colour slot in the comparison
            chart_size={},  # Result charts the user resized: (file, tag) or "compare" -> (width or None, plot height)
            open_dirs=dict(model=set(), hyperparameter=set(), result=set()))  # sidebar tree folders the user expanded

    def reset_state(self, tab="home"):
        """Selections pointing at the first item of what ``store`` holds; empty strings when it holds nothing."""
        folder = next(iter(store.DATA_FOLDERS), "")
        prefs = getattr(self, "s", None)  # what's picked in Setting lasts across tabs and projects
        self.s = SimpleNamespace(
            table_rows=prefs.table_rows if prefs else _saved_rows(),  # Result / Hyperparameter tables: rows a page
            tab=tab, folder=folder, view_commit=None, infer_source=next(iter(store.INFERENCE), None),
            task=store.TASKS[0] if store.TASKS else None,  # Data: the task whose labels and predictions are shown
            sel=dict(home=store.PROJECT.get("hot_file", ""), data=store.DATA_FOLDERS[folder]["files"][0] if folder else "",
                     model=_first(store.MODEL_FILES), hyperparameter=_first(store.RUNS), result=_first(store.RESULT_FILES),
                     setting=_first(store.RECENT_PROJECTS)),
            **self.view_state())
        self.task = store.DASH.get("task", "")
        self.setWindowTitle(f"Laboard — {store.PROJECT['name']} — {store.PROJECT['toml']}" if store.PROJECT else "Laboard")

    def load_project(self, path, commit=None, text=None):
        """Load ``path``; with ``commit``, show the project as of that commit (the repository itself is only read).
        ``text``: the project file's content edited in Setting, used instead of the file (which isn't written)."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            notes = project.load(path, commit, text)
        except Exception as e:  # missing file, bad toml, unexpected layout: store still holds the previous project
            self._status_msg = f"Could not load {path}{' at ' + commit if commit else ''}: {e}"
            self.render()
            return
        finally:
            QApplication.restoreOverrideCursor()
        same = store.PROJECT["toml"] == getattr(self, "_toml", None)
        old = self.s
        self.reset_state(self.s.tab)
        if same:  # switching commits stays on the page: keep how it is viewed, and what's selected where it still exists
            for k in self.view_state().keys() - {"open_commit"}:  # the commit list itself changed
                setattr(self.s, k, getattr(old, k))
            if old.infer_source in store.INFERENCE:
                self.s.infer_source = old.infer_source
            if old.task in store.TASKS:
                self.s.task = old.task
            valid = dict(model=store.MODEL_INFO, hyperparameter=store.RUN_DETAILS, result=store.RESULT_PATHS)
            for tab, keys in valid.items():
                if old.sel[tab] in keys:
                    self.s.sel[tab] = old.sel[tab]
            if old.folder in store.DATA_FOLDERS and old.sel["data"] in store.DATA_FOLDERS[old.folder]["files"]:
                self.s.folder, self.s.sel["data"] = old.folder, old.sel["data"]
        self._toml = store.PROJECT["toml"]
        self.toml_text = text
        self.s.view_commit = commit
        head = f"Showing {commit} · read-only snapshot" if commit else f"Loaded {path}"
        self._status_msg = " · ".join([head, *notes])
        self.render()

    def show_dialog(self, title, text, body=None, actions=None):
        """Open a modal ``Dialog`` (see there) and return it."""
        self.dialog = Dialog(self, title, text, body=body, actions=actions)
        self.dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.dialog.open()
        return self.dialog

    def show_no_project(self):
        self.dialog = Dialog(self, "Load a project file", "No project is loaded yet. Go to Setting, open Load project file "
                                                          "and click Browse to load a laboard.toml.", button="Close")
        self.dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.dialog.open()

    def show_commit(self, commit):
        """Show every page as of ``commit`` (None: the latest)."""
        self.load_project(store.PROJECT["toml"], commit, self.toml_text)

    def side_scale(self):
        """What side panel shares are of: the design width, so a share is a fixed size in px (a panel doesn't grow
        or shrink with the window; it only gives way when there's no room, see fit_sides)."""
        return SideHandle.DESIGN_WIDTH

    def side_room(self):
        """Width left for the side panels once the margins, the open panels' gutters and a 1px centre are taken
        out of the window's."""
        return self.width() - 24 - 12 * sum(not h.closed for h in self.handles) - 1

    def drag_side(self, handle, w, start):
        """``handle``'s panel dragged to ``w`` px (``start``: every panel's width when the drag began). Widening it
        first narrows the centre down to its minimum, then the other panel as if the user dragged that one too
        (hiding it under SNAP); the centre never goes below its minimum."""
        scale, room = self.side_scale(), self.side_room()
        w = max(0, min(w, handle.max_width(), room + 1 - self.center_min))
        w = 0 if w < SideHandle.SNAP else w
        excess = w + sum(start[h] for h in self.handles if h is not handle) + self.center_min - 1 - room
        for h in self.handles:
            if h is not handle:
                other = start[h] - min(max(excess, 0), start[h])
                other = 0 if other < SideHandle.SNAP else other
                excess -= start[h] - other
                self.side_widths[h.key] = other / scale
        self.side_widths[handle.key] = w / scale
        self.fit_sides()

    def fit_sides(self):
        """Size the side panels to their own widths (shares of side_scale(), within SideHandle max_width) as far as
        the window allows with the centre at center_min. The left panel is filled first and the right one gets
        what is left: as the window narrows the right panel shrinks away first, then the left one; as it widens
        the left one grows back to its width first, then the right one, a pixel at a time. A panel squeezed to
        nothing hides with its gutter, and at the window's minimum width both are gone and the centre has it all,
        so the page doesn't scroll sideways. A page with its own centre_min (Result's charts) narrows to that first
        and keeps its panels until then, even at the window's minimum width; with ``fold_left`` the right panel is
        filled first, so past that the left one folds away once narrower than ``fold_left`` px. Any panel squeezed
        below SideHandle.SNAP folds."""
        # the left panel reaches 0 as the window reaches its minimum, unless the page's own minimum is narrower
        centre = self.own_centre or max(self.center_min, self.top_min - 24)
        free = self.width() - 24 - centre  # for the panels and their gutters
        fold = getattr(self.page, "fold_left", 0)
        order = self.handles[::-1] if fold else self.handles
        for h in order:  # left first, or right first with fold_left
            want = 0 if h.closed else min(round(h.share() * self.side_scale()), h.max_width())
            w = max(0, min(want, free - 12))
            least = fold if fold and h is self.handles[0] else SideHandle.SNAP
            w = 0 if w < min(want, least) else w  # squeezed too narrow to use: folded
            # a gutter stays for a panel the user dragged shut (to drag it back), not for one with no room
            show = not h.closed and free >= 12 and (w > 0 or want == 0)
            h.apply(w if show else 0)
            h.setVisible(show)
            free -= (12 + w) if show else 0
        if self.page is not None:
            # at least 1px: Qt reads a minimum of 0 as unset and falls back to the content's own minimum
            self.page.setMinimumWidth(max(1, min(self.center_min, free + centre)))

    def show_right(self, on):
        """Open the right panel (at the width it had) with its gutter, or close both: for a page whose panel only
        has something to show sometimes, such as Result's comparison."""
        h = self.handles[-1]
        if on and h.share() == 0:
            self.side_widths[h.key] = self.side_widths.pop(h.key + ":last", h.default)
        elif not on and h.share() > 0:
            self.side_widths[h.key + ":last"] = h.share()
            self.side_widths[h.key] = 0
        h.closed = not on  # fit_sides shows or hides it
        self.fit_sides()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit_sides()

    # ---------------------------------------------------------- state
    def set(self, **kw):
        if "theme" in kw:
            theme.set_theme(kw.pop("theme"))
        if "table_rows" in kw:  # picked in Setting: also kept for the next start
            QSettings("Laboard", "Laboard").setValue("table_rows", kw["table_rows"])
        if kw.get("tab", self.s.tab) != self.s.tab:  # leaving a page drops everything adjusted on it
            vars(self.s).update(self.view_state())
            self.side_widths.clear()
            self._left_page = True
        for k, v in kw.items():
            setattr(self.s, k, v)
        QTimer.singleShot(0, self.render)

    def toggle_dir(self, tab, path):
        dirs = self.s.open_dirs[tab]
        self.set(open_dirs={**self.s.open_dirs, tab: dirs - {path} if path in dirs else dirs | {path}})

    def pick(self, tab, name):
        """Select ``name`` on ``tab``. A page with ``select(app, name)`` (Data) shows it in place, without the
        flicker of rebuilding the window; otherwise the window re-renders."""
        old, self.s.sel = self.s.sel, {**self.s.sel, tab: name}
        page = PAGES.get(tab)
        if tab == self.s.tab and hasattr(page, "select") and page.select(self, name):
            if not self.file_list.mark(name):  # its row isn't among the rows built: rebuild the list only
                self.file_list.populate(self.file_list.search.text())
            return
        self.s.sel = old
        self.set(sel={**self.s.sel, tab: name})

    def view_index(self):
        """Index in COMMITS of the commit shown: the chosen one, else HEAD (remote-only commits may come before it)."""
        hashes = [c[0] for c in store.COMMITS]
        for h in (self.s.view_commit, store.PROJECT.get("head")):
            if h in hashes:
                return hashes.index(h)
        return 0

    def fetch_remote(self):
        """git fetch the upstream's remote (updates remote-tracking refs only), then reload the current view."""
        P = store.PROJECT
        remote = P["upstream"].split("/", 1)[0]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            r = subprocess.run(["git", "fetch", "--quiet", remote], cwd=P["path"], capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            r = SimpleNamespace(returncode=1, stderr=str(e))
        finally:
            QApplication.restoreOverrideCursor()
        if r.returncode:
            self.status(f"git fetch {remote} failed: {r.stderr.strip()[:160]}")
            return
        self.load_project(P["toml"], self.s.view_commit, self.toml_text)

    def status(self, msg):
        self._status_msg = msg
        self.status_label.setText(msg)
        self.status_label.setToolTip(msg)

    # ---------------------------------------------------------- build
    def render(self):
        netronview.park(self)  # keep the model graph's web view out of the page about to be deleted
        old = self.centralWidget()
        root = QWidget()
        root.setObjectName("root")
        root.setStyleSheet(f"QWidget#root{{background:{T.bg};}} QToolTip{{color:{T.ink};background:{T.surf};border:1px solid {T.line};}}")
        lay = vbox()
        if self.frameless:
            lay.addWidget(TitleBar(self))
        lay.addWidget(self.top_bar())
        body = hbox(margins=(12, 12, 12, 12))
        side = sidebar.build(self)
        page = PAGES[self.s.tab].build(self)  # the centre, or (centre, right panel)
        page, right = page if isinstance(page, tuple) else (page, None)
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # a page may set its own narrowest centre (centre_min), which it reaches before the side panels shrink
        self.own_centre = getattr(page, "centre_min", None)
        self.page, self.center_min = page, self.own_centre or max(CENTER_MIN, page.minimumSizeHint().width())
        self.handles = [SideHandle(side, self, f"left:{self.s.tab}")]
        body.addWidget(side)
        body.addWidget(self.handles[0])
        body.addWidget(page, 1)
        if right is not None:
            self.handles.append(SideHandle(right, self, self.s.tab, right=True))
            body.addWidget(self.handles[1])
            body.addWidget(right)
        # fit_sides hides the panels before the centre would go below its minimum; scrolling sideways is only a fallback
        # for a centre whose own minimum is wider than the window allows
        old_x = self.body_scroll.horizontalScrollBar().value() if old is not None and not self._left_page else 0
        self._left_page = False
        # wrapped before the panels are shown or hidden: setVisible on a widget with no parent yet opens it as a
        # window of its own for a moment (a popup that flashes on every re-render)
        self.body_scroll = Scroll(wrap(body), horizontal=True)
        if right is not None and hasattr(page, "right_on"):  # a panel that only sometimes has something to show
            self.show_right(page.right_on)
        self.fit_sides()
        self.body_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QTimer.singleShot(0, lambda: self.body_scroll.horizontalScrollBar().setValue(old_x))  # once the range is known
        lay.addWidget(self.body_scroll, 1)
        lay.addWidget(self.status_bar())
        root.setLayout(lay)
        self.setCentralWidget(root)
        if old is not None:
            old.deleteLater()
        if self.dialog is not None and not sip.isdeleted(self.dialog) and self.dialog.isVisible():
            self.dialog.raise_()  # the new page was stacked above it

    def top_bar(self):
        bar = Box(bg="surf", radius=0)
        bar.setFixedHeight(68)
        brand = SplashLogo()
        tabs = Segmented(TABS, self.s.tab, lambda k: self.set(tab=k), size=14, pad=(8, 22), outer=4, gap=4,
                         on=("tab", "tabfg"), off=("transparent", "ink"))
        if store.COMMITS:
            P = store.PROJECT
            i = self.view_index()
            latest = self.s.view_commit is None
            c = store.COMMITS[i]
            if latest:
                sync = f" · ↑{P['ahead']} ↓{P['behind']} vs {P['upstream']}" if P.get("upstream") else ""
                state = f"{P['dirty']}{sync}"
            else:
                state = "remote commit · read-only snapshot" if c[7] == "remote" else "read-only snapshot"
            chip_text = (f"<b>{P['branch_name'] if latest else 'detached'}</b> <span style='color:{T.mute}'>@</span>{mono_span(c[0])} "
                         f"<span style='color:{T.body}'>· {state}</span>")
            when = f"<b>{('Latest · ' if latest else '') + c[4]}</b> {mono_span('· ' + c[0], 'body', 12)}"
        else:
            chip_text = "not a git repository" if store.PROJECT else "No project loaded"
            when = "—"
        chip = Box(bg="surf2", radius=17, layout=hbox(Label(chip_text, 13, 500, rich=True), margins=(14, 7, 14, 7)))
        picker_text = vbox(Label("Show project as of", 11, 400, "mute", lh=14), Label(when, 13, 600, rich=True, lh=18))
        picker = Box(bg="surf", radius=12, border=f"1px solid {T.ink}", hover="surf2" if store.COMMITS else None,
                     layout=hbox((picker_text, 1), 12, Chevron(), margins=(16, 6, 12, 6), align=Qt.AlignmentFlag.AlignVCenter))
        picker.setMinimumWidth(300)
        if store.COMMITS:
            picker.clicked.connect(lambda: CommitPicker(self, picker).show())
        # the 68px logo sits outside the centred row so it doesn't stretch the chip and picker to its height
        right = Collapsing(chip, picker)
        row = hbox(tabs, 20, (right, 1), align=Qt.AlignmentFlag.AlignVCenter)
        bar.setLayout(hbox(brand, 28, (row, 1), margins=(24, 0, 20, 0)))
        self.top_min = bar.minimumSizeHint().width()
        return bar

    def status_bar(self):
        bar = Box(bg="surf", radius=0)
        bar.setFixedHeight(30)
        bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)  # clips its text instead of widening the window
        lay = hbox(spacing=0, margins=(18, 0, 18, 0))
        if store.STATUS["watching"]:
            lay.addWidget(Dot(theme.POSITIVE, 7))
            lay.addSpacing(6)
            lay.addWidget(Label(store.STATUS["watching"], 12, 400, "body"))
        for t in store.STATUS["left"]:
            lay.addSpacing(20)
            lay.addWidget(Label(t, 12, 400, "body"))
        lay.addSpacing(20)
        self.status_label = Label(self._status_msg or "", 12, 400, "body", elide=True, align=Qt.AlignmentFlag.AlignRight)
        self.status_label.setToolTip(self._status_msg or "")
        lay.addWidget(self.status_label, 1)
        for t in store.STATUS["right"]:
            lay.addSpacing(20)
            lay.addWidget(Label(t, 12, 400, "body"))
        bar.setLayout(lay)
        return bar


def main(argv=None):
    ap = argparse.ArgumentParser(prog="laboard", description="Laboard — ML experiment tracker")
    ap.add_argument("--tab", choices=[t for t, _ in TABS], help="start tab (default: home, or setting without --project)")
    ap.add_argument("--theme", default="light", choices=["light", "dark"])
    ap.add_argument("--frameless", action="store_true", help="draw the dark custom title bar instead of the WM's")
    ap.add_argument("--screenshot", metavar="PNG", help="render once, save a screenshot and exit")
    ap.add_argument("--project", metavar="TOML", help="load a laboard .toml project at start")
    args, qt_args = ap.parse_known_args(argv)
    netronview.prepare()
    qapp = QApplication([sys.argv[0], *qt_args])
    qapp.setApplicationName("Laboard")
    qapp.setDesktopFileName("laboard")
    qapp.setWindowIcon(theme.logo_icon())  # title bar / taskbar / alt-tab
    theme.load_fonts()
    qapp.setFont(theme.font(14))
    win = MainWindow(args.tab or ("home" if args.project else "setting"), args.theme, args.frameless)
    if args.project:
        win.load_project(args.project)
    win.show()
    if not args.project and not args.screenshot:
        win.show_no_project()
    if args.screenshot:
        def shot():
            win.grab().save(args.screenshot)
            qapp.quit()
        QTimer.singleShot(400, shot)
    return qapp.exec()
