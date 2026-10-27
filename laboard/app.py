import argparse
import subprocess
import sys
from types import SimpleNamespace

from PyQt6 import sip
from PyQt6.QtCore import QPoint, QPointF, QRectF, QSettings, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QMainWindow, QSizePolicy, QWidget

from . import netronview, project, sidebar, store, theme
from .pages import data, home, hyperparameter, model, result, setting
from .theme import T
from .widgets import (Box, Button, Chevron, Collapsing, Dot, HLine, InfoIcon, Label, Logo, Overlay, Pill, Scroll, Segmented, SideHandle,
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
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedHeight(40)
        self.setStyleSheet("TitleBar{background:#0e0f0c;border-bottom:1px solid #2a2b28;}")
        left = hbox(Logo(22), 8, Label("Laboard", 13, 600, "#e8ebe6"), "stretch", align=Qt.AlignmentFlag.AlignVCenter)
        title = f"{store.PROJECT['name']} — {store.PROJECT['toml']}" if store.PROJECT else "No project loaded"
        mid = Label(title, 13, 400, "#868685", align=Qt.AlignmentFlag.AlignCenter, select=False)
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
    try:
        n = int(QSettings("Laboard", "Laboard").value("table_rows", store.TABLE_ROWS_DEFAULT))
    except (TypeError, ValueError):
        n = store.TABLE_ROWS_DEFAULT
    return n if n in store.TABLE_ROWS else store.TABLE_ROWS_DEFAULT


CENTER_MIN = 620

LOG_FILTERS = [("all", "All"), ("local", "Local"), ("remote", "Remote")]


def in_filter(c, kind):
    return kind == "all" or c[7] in (kind, "both")


class Dialog(Overlay):
    def __init__(self, win, title, text, button="Cancel", body=None, actions=None):
        super().__init__(win)
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


class CommitPicker(QFrame):
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
        self.rows.invalidate()
        self.sc.setFixedHeight(min(480, self.sc.widget().layout().sizeHint().height() + 4))
        self.adjustSize()
        pos = self.anchor.mapToGlobal(QPoint(self.anchor.width(), self.anchor.height()))
        self.move(pos.x() - self.width() + 24, pos.y())

    def set_filter(self, kind):
        self.app.s.log_filter = kind
        if self.seg is not None:
            self.seg.select(kind)
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
        self.setMinimumHeight(760)
        self._status_msg = None
        self.dialog = None
        self.toml_text = None
        self.side_widths = {}
        self.handles, self.page, self.center_min, self.own_centre = [], None, CENTER_MIN, None
        self.top_min = 0
        self._left_page = False
        netronview.attach(self)
        self.reset_state(start_tab)
        self.render()

    @staticmethod
    def view_state():
        return dict(
            hist_filter="all", open_commit=_first(store.COMMITS) or None, smooth=0.6, split_filter="all",
            view_mode="raw", zoom=None, pending_toml=None, pt_view="inferred", log_filter="all",
            toml_view="fields",
            setting_scroll=0,
            table_page={},
            table_open=set(),
            table_view={},
            run_page={},
            run_open=set(),
            hp_query="",
            chart_sel={},
            chart_size={},
            open_dirs=dict(model=set(), hyperparameter=set(), result=set()))

    def reset_state(self, tab="home"):
        folder = next(iter(store.DATA_FOLDERS), "")
        prefs = getattr(self, "s", None)
        self.s = SimpleNamespace(
            table_rows=prefs.table_rows if prefs else _saved_rows(),
            tab=tab, folder=folder, view_commit=None, infer_source=next(iter(store.INFERENCE), None),
            task=store.TASKS[0] if store.TASKS else None,
            sel=dict(home=store.PROJECT.get("hot_file", ""), data=store.DATA_FOLDERS[folder]["files"][0] if folder else "",
                     model=_first(store.MODEL_FILES), hyperparameter=_first(store.RUNS), result=_first(store.RESULT_FILES),
                     setting=_first(store.RECENT_PROJECTS)),
            **self.view_state())
        self.task = store.DASH.get("task", "")
        self.setWindowTitle(f"Laboard — {store.PROJECT['name']} — {store.PROJECT['toml']}" if store.PROJECT else "Laboard")

    def load_project(self, path, commit=None, text=None):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            notes = project.load(path, commit, text)
        except Exception as e:
            self._status_msg = f"Could not load {path}{' at ' + commit if commit else ''}: {e}"
            self.render()
            return
        finally:
            QApplication.restoreOverrideCursor()
        same = store.PROJECT["toml"] == getattr(self, "_toml", None)
        old = self.s
        self.reset_state(self.s.tab)
        if same:
            for k in self.view_state().keys() - {"open_commit"}:
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
        self.dialog = Dialog(self, title, text, body=body, actions=actions)
        self.dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.dialog.open()
        return self.dialog

    def show_no_project(self):
        self.show_dialog("Load a project file", "No project is loaded yet. Go to Setting, open Load project file "
                                                "and click Browse to load a laboard.toml.", actions=[("Close", "tertiary", None)])

    def show_commit(self, commit):
        self.load_project(store.PROJECT["toml"], commit, self.toml_text)

    def side_scale(self):
        return SideHandle.DESIGN_WIDTH

    def side_room(self):
        return self.width() - 24 - 12 * sum(not h.closed for h in self.handles) - 1

    def drag_side(self, handle, w, start):
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
        centre = self.own_centre or max(self.center_min, self.top_min - 24)
        free = self.width() - 24 - centre
        fold = getattr(self.page, "fold_left", 0)
        order = self.handles[::-1] if fold else self.handles
        for h in order:
            want = 0 if h.closed else min(round(h.share() * self.side_scale()), h.max_width())
            w = max(0, min(want, free - 12))
            least = fold if fold and h is self.handles[0] else SideHandle.SNAP
            w = 0 if w < min(want, least) else w
            show = not h.closed and free >= 12 and (w > 0 or want == 0)
            h.apply(w if show else 0)
            h.setVisible(show)
            free -= (12 + w) if show else 0
        if self.page is not None:
            self.page.setMinimumWidth(max(1, min(self.center_min, free + centre)))

    def show_right(self, on):
        h = self.handles[-1]
        if on and h.share() == 0:
            self.side_widths[h.key] = self.side_widths.pop(h.key + ":last", h.default)
        elif not on and h.share() > 0:
            self.side_widths[h.key + ":last"] = h.share()
            self.side_widths[h.key] = 0
        h.closed = not on
        self.fit_sides()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit_sides()

    def set(self, **kw):
        if "theme" in kw:
            theme.set_theme(kw.pop("theme"))
        if "table_rows" in kw:
            QSettings("Laboard", "Laboard").setValue("table_rows", kw["table_rows"])
        if kw.get("tab", self.s.tab) != self.s.tab:
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
        old, self.s.sel = self.s.sel, {**self.s.sel, tab: name}
        page = PAGES.get(tab)
        if tab == self.s.tab and hasattr(page, "select") and page.select(self, name):
            if not self.file_list.mark(name):
                self.file_list.populate(self.file_list.search.text())
            return
        self.s.sel = old
        self.set(sel={**self.s.sel, tab: name})

    def view_index(self):
        hashes = [c[0] for c in store.COMMITS]
        for h in (self.s.view_commit, store.PROJECT.get("head")):
            if h in hashes:
                return hashes.index(h)
        return 0

    def fetch_remote(self):
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

    def render(self):
        netronview.park(self)
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
        page = PAGES[self.s.tab].build(self)
        page, right = page if isinstance(page, tuple) else (page, None)
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        old_x = self.body_scroll.horizontalScrollBar().value() if old is not None and not self._left_page else 0
        self._left_page = False
        self.body_scroll = Scroll(wrap(body), horizontal=True)
        if right is not None and hasattr(page, "right_on"):
            self.show_right(page.right_on)
        self.fit_sides()
        self.body_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QTimer.singleShot(0, lambda: self.body_scroll.horizontalScrollBar().setValue(old_x))
        lay.addWidget(self.body_scroll, 1)
        lay.addWidget(self.status_bar())
        root.setLayout(lay)
        self.setCentralWidget(root)
        if old is not None:
            old.deleteLater()
        if self.dialog is not None and not sip.isdeleted(self.dialog) and self.dialog.isVisible():
            self.dialog.raise_()

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
        right = Collapsing(chip, picker)
        row = hbox(tabs, 20, (right, 1), align=Qt.AlignmentFlag.AlignVCenter)
        bar.setLayout(hbox(brand, 28, (row, 1), margins=(24, 0, 20, 0)))
        self.top_min = bar.minimumSizeHint().width()
        return bar

    def status_bar(self):
        bar = Box(bg="surf", radius=0)
        bar.setFixedHeight(30)
        bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
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
    qapp.setWindowIcon(theme.logo_icon())
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
