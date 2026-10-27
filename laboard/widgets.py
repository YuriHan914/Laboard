import itertools
import re

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, QRegularExpression, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen, QRegularExpressionValidator
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QApplication, QComboBox, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel,
                             QLayout, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QWidgetItem)

from . import theme
from .theme import T, font, qc

_ids = itertools.count()


def col(c):
    return T[c] if c in T else c


def _fill(layout, items):
    for it in items:
        if it is None:
            continue
        if it == "stretch":
            layout.addStretch(1)
        elif isinstance(it, int):
            layout.addSpacing(it)
        elif isinstance(it, tuple):
            w, stretch = it
            (layout.addLayout if not isinstance(w, QWidget) else layout.addWidget)(w, stretch)
        elif isinstance(w := it, QWidget):
            layout.addWidget(w)
        else:
            layout.addLayout(w)
    return layout


def hbox(*items, spacing=0, margins=(0, 0, 0, 0), align=None):
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(*margins)
    if align is not None:
        lay.setAlignment(align)
    return _fill(lay, items)


def vbox(*items, spacing=0, margins=(0, 0, 0, 0), align=None):
    lay = QVBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(*margins)
    if align is not None:
        lay.setAlignment(align)
    return _fill(lay, items)


def wrap(layout):
    w = QWidget()
    w.setLayout(layout)
    return w


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class Box(QFrame):
    clicked = pyqtSignal()

    def __init__(self, bg="surf", radius=16, border=None, hover=None, layout=None, on_click=None, parent=None):
        super().__init__(parent)
        self.setObjectName(f"b{next(_ids)}")
        self._style = dict(bg=bg, radius=radius, border=border, hover=hover)
        self.restyle()
        if layout is not None:
            self.setLayout(layout)
        if on_click:
            self.clicked.connect(on_click)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def resizeEvent(self, e):
        if self._style["radius"] >= 999:
            self.restyle()
        super().resizeEvent(e)

    def restyle(self, **kw):
        self._style.update(kw)
        s = self._style
        radius = min(self.width(), self.height()) // 2 if s["radius"] >= 999 else s["radius"]
        css = f"QFrame#{self.objectName()}{{background:{col(s['bg']) if s['bg'] else 'transparent'};border-radius:{radius}px;"
        css += f"border:{s['border']};}}" if s["border"] else "border:none;}"
        if s["hover"]:
            css += f"QFrame#{self.objectName()}:hover{{background:{col(s['hover'])};}}"
        self.setStyleSheet(css)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def takes_clicks(self):
        return self.receivers(self.clicked) > 0


def card(*items, pad=(20, 20, 20, 20), spacing=0, radius=16, bg="surf"):
    return Box(bg=bg, radius=radius, layout=vbox(*items, spacing=spacing, margins=pad))


class Label(QLabel):
    _selected = None
    _clipboard_hooked = False

    def __init__(self, text="", size=14, weight=400, color="ink", mono=False, display=False, spacing=0.0,
                 lh=None, wrap=False, rich=False, align=None, elide=False, select=None):
        super().__init__(text)
        self.setFont(font(size, weight, mono=mono, display=display, spacing=spacing))
        self._color = color
        self.setStyleSheet(f"color:{col(color)};background:transparent;selection-background-color:{T.sel};"
                           f"selection-color:{T.selfg};")
        self.setTextFormat(Qt.TextFormat.RichText if rich else Qt.TextFormat.PlainText)
        self._elide = elide
        if wrap:
            self.setWordWrap(True)
        if lh and not wrap:
            self.setFixedHeight(lh)
        if align is not None:
            self.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        self._select = select
        if select:
            self._selectable(True)
        if elide:
            self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.setToolTip(text)

    def minimumSizeHint(self):
        if self._elide:
            return QSize(0, super().minimumSizeHint().height())
        return super().minimumSizeHint()

    def _selectable(self, on):
        flags = Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        self.setTextInteractionFlags(flags if on else Qt.TextInteractionFlag.NoTextInteraction)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus if on else Qt.FocusPolicy.NoFocus)
        if on and not Label._clipboard_hooked:
            Label._clipboard_hooked = True
            QApplication.clipboard().dataChanged.connect(_unbreak_clipboard)

    def showEvent(self, e):
        if self._select is None:
            w, clicks = self.parentWidget(), False
            while w is not None and not clicks:
                clicks = isinstance(w, Box) and w.takes_clicks()
                w = w.parentWidget()
            self._selectable(not clicks)
        super().showEvent(e)

    def mousePressEvent(self, e):
        last = Label._selected
        if last is not None and last is not self and not sip.isdeleted(last) and last.hasSelectedText():
            last.setSelection(0, 0)
        Label._selected = self
        super().mousePressEvent(e)

    def paintEvent(self, e):
        if not self._elide or self.hasSelectedText():
            return super().paintEvent(e)
        p = QPainter(self)
        p.setFont(self.font())
        p.setPen(qc(col(self._color)))
        txt = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        p.drawText(self.rect(), int(self.alignment() | Qt.AlignmentFlag.AlignVCenter), txt)


def _unbreak_clipboard():
    cb = QApplication.clipboard()
    text = cb.text()
    if "\u200b" in text:
        cb.setText(text.replace("\u200b", ""))


def mono_span(text, color="ink", size=None):
    s = f"font-size:{size}px;" if size else ""
    return f'<span style="font-family:\'{theme.MONO_FAMILY}\';color:{col(color)};{s}">{text}</span>'


def caption(text, color="mute", size=12, **kw):
    return Label(text, size, 400, color, **kw)


def breakable(text):
    return re.sub(r"([/_=:-]|[.,](?!\d))", "\\1\u200b", text)


def elided(text, *args, **kw):
    lab = Label(text, *args, elide=True, **kw)
    lab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    return lab


class Tip(QWidget):
    WIDTH, RADIUS = 360, 12
    _shared = None

    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.title = Label("", 13, 600, theme.WISE_GREEN, mono=True)
        self.body = Label("", 13, 400, theme.WISE_GREEN, wrap=True)
        self.body.setFixedWidth(self.WIDTH)
        self.setLayout(vbox(self.title, 4, self.body, margins=(16, 12, 16, 14)))
        self.timer = QTimer(self, singleShot=True, interval=15000, timeout=self.hide)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(qc(T.grid), 1) if theme.current == "dark" else Qt.PenStyle.NoPen)
        p.setBrush(qc(theme.INK))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), self.RADIUS, self.RADIUS)

    @classmethod
    def show_at(cls, pos, title, text):
        tip = cls._shared = cls._shared or cls()
        tip.title.setText(title)
        tip.title.setVisible(bool(title))
        tip.body.setText(text)
        tip.adjustSize()
        x, y = pos.x() + 12, pos.y() + 18
        screen = QApplication.screenAt(pos)
        if screen:
            area = screen.availableGeometry()
            x = max(area.left(), min(x, area.right() - tip.width()))
            y = y if y + tip.height() <= area.bottom() else pos.y() - tip.height() - 8
        tip.move(x, y)
        tip.update()
        tip.show()
        tip.timer.start()

    @classmethod
    def hide_tip(cls, *_):
        if cls._shared is not None and not sip.isdeleted(cls._shared):
            cls._shared.hide()


class _TipFilter(QObject):
    def eventFilter(self, obj, e):
        t = e.type()
        if t == QEvent.Type.ToolTip and getattr(obj, "_tip", None):
            Tip.show_at(e.globalPos(), *obj._tip)
            return True
        if t in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress, QEvent.Type.Hide):
            Tip.hide_tip()
        return False


_tip_filter = None


def set_tip(widget, title, text):
    global _tip_filter
    _tip_filter = _tip_filter or _TipFilter()
    widget._tip = (title, text)
    widget.installEventFilter(_tip_filter)
    widget.destroyed.connect(Tip.hide_tip)


class Pill(QLabel):
    def __init__(self, text, bg="surf2", fg="ink", size=12, weight=600, pad=(4, 10), mono=False, radius=None):
        super().__init__(text)
        self.setFont(font(size, weight, mono=mono))
        r = radius if radius is not None else (self.fontMetrics().height() + 2 * pad[0]) // 2
        self.setStyleSheet(f"background:{col(bg)};color:{col(fg)};border-radius:{r}px;padding:{pad[0]}px {pad[1]}px;")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


BADGE_TONES = {"positive": (theme.WISE_GREEN_PALE, theme.POSITIVE_DEEP), "negative": (theme.NEGATIVE_BG, theme.CANVAS),
               "warning": (theme.WARNING, theme.WARNING_CONTENT), "neutral": (theme.CANVAS_SOFT, theme.INK)}


def badge(text, tone="positive"):
    bg, fg = BADGE_TONES[tone]
    return Pill(text, bg, fg, size=12, pad=(2, 10))


class Dot(QWidget):
    def __init__(self, color, size=8, ring=None):
        super().__init__()
        self.color, self.ring = color, ring
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        if self.ring:
            p.setPen(QPen(qc(col(self.ring)), 2))
            r = r.adjusted(1, 1, -1, -1)
        else:
            p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc(col(self.color)) if self.color else Qt.BrushStyle.NoBrush)
        p.drawEllipse(r)


class HLine(QWidget):
    def __init__(self, color="line", height=1):
        super().__init__()
        self.setFixedHeight(height)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(f"background:{col(color)};")


class Overlay(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        win.installEventFilter(self)
        self._fit()

    def _fit(self):
        top = 40 if getattr(self.win, "frameless", False) else 0
        self.setGeometry(0, top, self.win.width(), self.win.height() - top)

    def eventFilter(self, obj, e):
        if obj is self.win and e.type() == QEvent.Type.Resize:
            self._fit()
        return False

    def paintEvent(self, e):
        QPainter(self).fillRect(self.rect(), QColor(14, 15, 12, 115))

    def mousePressEvent(self, e):
        e.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()

    def open(self):
        self.show()
        self.raise_()
        self.setFocus()


class Button(QPushButton):
    @staticmethod
    def _metrics(size, compact=False, pad=None):
        fs, own = (13, (4, 14)) if compact else (14, (8, 16)) if size == "sm" else (16, (12, 24))
        pad = pad or own
        return fs, pad, pad[0] * 2 + (20 if fs <= 14 else 24)

    @staticmethod
    def height_for(size, compact=False, pad=None):
        return Button._metrics(size, compact, pad)[2]

    def __init__(self, text, variant="secondary", size="sm", on_click=None, compact=False, pad=None, min_width=0):
        super().__init__(text)
        fs, pad, hgt = self._metrics(size, compact, pad)
        self.setFont(font(fs, 600))
        dark = theme.current == "dark"
        bg, hover, fg, border = {
            "primary": (theme.WISE_GREEN, theme.WISE_GREEN_PALE, theme.INK, "none"),
            "tertiary": ("transparent", T.surf2, T.ink, "none"),
            "outline": ("transparent", T.surf2, T.ink, f"1px solid {T.ink}"),
            "sage": (theme.WISE_GREEN_ACTIVE if dark else theme.SAGE, theme.WISE_GREEN if dark else theme.SAGE_HOVER,
                     theme.INK, "1px solid transparent"),
            "solid": (T.tab, "#d4d8d1" if dark else "#2a2b28", T.tabfg, f"1px solid {T.tab}"),
        }.get(variant, (T.surf2, T.grid, T.ink, "none"))
        self.setFixedHeight(hgt)
        if min_width:
            self.setMinimumWidth(min_width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"QPushButton{{background:{bg};color:{fg};border:{border};border-radius:{min(24, hgt // 2)}px;"
                           f"padding:0 {pad[1]}px;}}QPushButton:hover{{background:{hover};}}"
                           f"QPushButton:pressed{{padding-top:1px;}}")
        if on_click:
            self.clicked.connect(on_click)


class Segmented(Box):
    def __init__(self, options, current, on_select, size=12, pad=(5, 12), outer=3, gap=2, on=("surf", "ink"),
                 off=("transparent", "body"), expand=False, dots=None):
        lay = hbox(spacing=gap, margins=(outer,) * 4)
        super().__init__(bg="surf2", radius=999, layout=lay)
        self.setSizePolicy(QSizePolicy.Policy.Preferred if expand else QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.on, self.off, self.items = on, off, {}
        for key, label in options:
            sel = key == current
            bg, fg = on if sel else off
            inner = hbox(spacing=5, align=Qt.AlignmentFlag.AlignCenter)
            if dots and dots.get(key):
                inner.addWidget(Dot(dots[key], 7))
            lbl = Label(label, size, 600, fg)
            inner.addWidget(lbl)
            item = Box(bg=bg, radius=999, layout=inner, on_click=(lambda k=key: on_select(k)) if on_select else None)
            inner.setContentsMargins(pad[1], pad[0], pad[1], pad[0])
            lay.addWidget(item, 1 if expand else 0)
            self.items[key] = (item, lbl)

    def select(self, current):
        for key, (item, lbl) in self.items.items():
            bg, fg = self.on if key == current else self.off
            item.restyle(bg=bg)
            lbl._color = fg
            lbl.setStyleSheet(f"color:{col(fg)};background:transparent;")


class LineEdit(QLineEdit):
    def __init__(self, placeholder="", size=14, pad=(8, 12), width=None, mono=False):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setFont(font(size, mono=mono))
        if width:
            self.setFixedWidth(width)
        self.setStyleSheet(f"QLineEdit{{border:1px solid {T.ink};border-radius:12px;padding:{pad[0] - 1}px {pad[1] - 1}px;"
                           f"background:{T.surf};color:{T.ink};selection-background-color:{T.sel};selection-color:{T.selfg};}}"
                           f"QLineEdit::placeholder{{color:{T.mute};}}")


class Combo(QComboBox):
    def __init__(self, options, current, on_change, size=13):
        super().__init__()
        self.setFont(font(size))
        for key, text in options:
            self.addItem(text, key)
        keys = [k for k, _ in options]
        self.setCurrentIndex(keys.index(current) if current in keys else 0)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"QComboBox{{border:1px solid {T.ink};border-radius:12px;padding:5px 12px;background:{T.surf};"
                           f"color:{T.ink};}}QComboBox::drop-down{{border:none;width:20px;}}"
                           f"QComboBox QAbstractItemView{{background:{T.surf};color:{T.ink};selection-background-color:{T.sel};"
                           f"selection-color:{T.selfg};border:1px solid {T.line};}}")
        self.currentIndexChanged.connect(lambda i: on_change(self.itemData(i)))


class MenuButton(Box):
    def __init__(self, text, on_open, min_width=120, pad=(16, 10, 14, 10), gap=12):
        super().__init__(bg="surf", radius=12, border=f"1px solid {T.ink}", hover="surf2")
        self.chev = Chevron("ink", 90)
        self.setLayout(hbox((Label(text, 14, 600, lh=20), 1), gap, self.chev, margins=pad,
                            align=Qt.AlignmentFlag.AlignVCenter))
        self.setMinimumWidth(min_width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(on_open)

    def opened(self, on):
        self.restyle(bg="surf2" if on else "surf")
        self.chev.rotation = -90 if on else 90
        self.chev.update()

    def pop(self, content, **kw):
        pop = Popover(self, content, right=True, on_close=lambda: sip.isdeleted(self) or self.opened(False), **kw)
        self.opened(True)
        pop.show()
        return pop


class Select(MenuButton):
    def __init__(self, options, current, on_change, min_width=120):
        super().__init__(dict(options).get(current, ""), self.open, min_width)
        self.options, self.current, self.on_change = options, current, on_change

    def open(self):
        def choose(key):
            pop.done(lambda: key != self.current and self.on_change(key))

        rows = vbox(*[menu_item(text, lambda k=key: choose(k), on=key == self.current) for key, text in self.options],
                     margins=(4, 4, 4, 4))
        pop = self.pop(rows, min_width=max(120, self.width()))


class Popover(QFrame):
    PAD = (16, 0, 16, 32)
    _open = set()

    def __init__(self, anchor, content, right=False, min_width=0, on_close=None):
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.on_close = on_close
        panel = Box(bg="surf", radius=12, border=f"1px solid {T.line}", layout=content)
        panel.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=40, offset=QPointF(0, 12), color=QColor(14, 15, 12, 61)))
        panel.setMinimumWidth(min_width)
        self.setLayout(vbox(panel, margins=self.PAD))
        self.adjustSize()
        at = anchor.mapToGlobal(QPoint(anchor.width() if right else 0, anchor.height() + 6))
        self.move(at.x() - self.width() + self.PAD[2] if right else at.x() - self.PAD[0], at.y() - self.PAD[1])

    def showEvent(self, e):
        Popover._open.add(self)
        super().showEvent(e)

    def hideEvent(self, e):
        Popover._open.discard(self)
        if self.on_close:
            self.on_close()
        super().hideEvent(e)

    def done(self, then=None):
        QTimer.singleShot(0, lambda: (self.close(), then and then()))


def menu_item(text, on_click, on=False, enabled=True, mono=False):
    row = hbox(Label(text, 14, 600 if on else 400, "selfg" if on else "ink" if enabled else "mute", mono=mono, lh=20),
               "stretch", 12, Stroke(TICK, 12, "selfg") if on else None, margins=(12, 8, 12, 8),
               align=Qt.AlignmentFlag.AlignVCenter)
    return Box(bg="sel" if on else None, radius=8, hover="surf2" if enabled and not on else None, layout=row,
               on_click=on_click if enabled else None)


class ClickTrap(QWidget):
    def mousePressEvent(self, e):
        e.accept()

    def mouseReleaseEvent(self, e):
        e.accept()


TICK = ((2, 6.2), (4.6, 8.8), (10, 3.4))
ARROW_LEFT, ARROW_RIGHT = ((8.5, 3), (4.5, 7), (8.5, 11)), ((5.5, 3), (9.5, 7), (5.5, 11))
CROSS = ((2, 2), (8, 8), None, (8, 2), (2, 8))


class Stroke(QWidget):
    def __init__(self, points, size=12, color="ink", width=1.8, circle=None):
        super().__init__()
        self.points, self.color, self.width_, self.circle = points, color, width, circle
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(qc(col(self.color)), self.width_, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
        path, start = QPainterPath(), True
        for pt in self.points:
            if pt is None:
                start = True
            elif start:
                path.moveTo(*pt)
                start = False
            else:
                path.lineTo(*pt)
        if self.circle:
            cx, cy, r = self.circle
            path.addEllipse(QPointF(cx, cy), r, r)
        p.drawPath(path)


class SearchField(Box):
    def __init__(self, placeholder, text, on_change, width=300):
        super().__init__(bg="surf", radius=12, border=f"1px solid {T.ink}")
        self.input = QLineEdit(text)
        self.input.setPlaceholderText(placeholder)
        self.input.setFont(font(14))
        self.input.setStyleSheet(f"QLineEdit{{border:none;background:transparent;color:{T.ink};padding:0;}}")
        pal = self.input.palette()
        pal.setColor(pal.ColorRole.PlaceholderText, qc(T.mute))
        self.input.setPalette(pal)
        self.count = Label("", 12, 600, "body", lh=16)
        self.clear = Box(bg="surf2", radius=12, on_click=lambda: (self.input.clear(), self.input.setFocus()),
                         layout=hbox(Stroke(CROSS, 10, "ink", 1.6), align=Qt.AlignmentFlag.AlignCenter))
        self.clear.setFixedSize(24, 24)
        self.setLayout(hbox(Stroke(((11, 11), (14.5, 14.5)), 16, "body", 1.6, circle=(7, 7, 5)), (self.input, 1),
                            self.count, self.clear, spacing=8, margins=(12, 0, 6, 0), align=Qt.AlignmentFlag.AlignVCenter))
        self.setFixedSize(width, 38)
        self.input.textChanged.connect(on_change)
        self.set_count(None)

    def sizeHint(self):
        return self.minimumSize()

    def set_count(self, n):
        self.count.setVisible(n is not None)
        self.clear.setVisible(n is not None)
        if n is not None:
            self.count.setText(f"{n:,} match{'' if n == 1 else 'es'}")


class Pager(ClickTrap):
    def __init__(self, per, total, on_page):
        super().__init__()
        self.per, self.on_page, self.page = per, on_page, 0
        self.set_total(total)
        self.nav = hbox(spacing=4, align=Qt.AlignmentFlag.AlignVCenter)
        self.input = QLineEdit()
        self.input.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,6}")))
        self.input.setFixedWidth(44)
        self.input.setFont(font(14, 600))
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input.setStyleSheet(f"QLineEdit{{border:none;background:transparent;color:{T.ink};padding:0 4px 0 10px;}}")
        self.input.returnPressed.connect(self._typed)
        go = Box(bg="tab", radius=15, on_click=self._typed,
                 layout=hbox(Label("Go", 13, 600, "tabfg", lh=18), margins=(14, 0, 14, 0), align=Qt.AlignmentFlag.AlignVCenter))
        go.setFixedHeight(30)
        field = Box(bg="surf", radius=19, border=f"1px solid {T.ink}",
                    layout=hbox(self.input, go, margins=(3, 3, 3, 3), align=Qt.AlignmentFlag.AlignVCenter))
        field.setFixedHeight(38)
        rule = Box(bg="line", radius=0)
        rule.setFixedSize(1, 24)
        info = elided(f"{per} rows per page · change in Setting", 13, 400, "body")
        self.setLayout(vbox(HLine(), hbox((info, 1), 16, self.nav, 16, rule, 16, field, margins=(18, 12, 18, 12),
                                          align=Qt.AlignmentFlag.AlignVCenter)))

    def set_total(self, total):
        self.pages = max(1, -(-total // self.per))

    def set_page(self, n):
        self.page = n
        clear_layout(self.nav)
        self.nav.addWidget(self._pill([Stroke(ARROW_LEFT, 14, "ink" if n > 0 else "mute"), 6, "Previous"], n - 1,
                                      enabled=n > 0, pad=(10, 14)))
        nums = sorted({k for k in (0, self.pages - 1, n - 1, n, n + 1) if 0 <= k < self.pages})
        for i, k in enumerate(nums):
            if i and k - nums[i - 1] > 1:
                self.nav.addWidget(self._pill(["…"], None, enabled=False))
            self.nav.addWidget(self._pill([str(k + 1)], k, current=k == n))
        self.nav.addWidget(self._pill(["Next", 6, Stroke(ARROW_RIGHT, 14, "ink" if n < self.pages - 1 else "mute")], n + 1,
                                      enabled=n < self.pages - 1, pad=(14, 10)))
        self.input.setText(str(n + 1))

    def _pill(self, items, to, enabled=True, current=False, pad=(0, 0)):
        fg = "tabfg" if current else "ink" if enabled else "mute"
        items = [Label(it, 14, 600, fg, lh=20) if isinstance(it, str) else it for it in items]
        live = enabled and not current
        size = 35 if current else 36
        b = Box(bg="tab" if current else None, radius=999, hover="surf2" if live else None,
                on_click=(lambda: self.on_page(to)) if live else None,
                layout=hbox(*items, margins=(pad[0], 0, pad[1], 0), align=Qt.AlignmentFlag.AlignCenter))
        b.setFixedHeight(size)
        b.setMinimumWidth(size)
        return b

    def _typed(self):
        n = max(0, min(int(self.input.text() or 1) - 1, self.pages - 1))
        if n == self.page:
            self.input.setText(str(n + 1))
        else:
            self.on_page(n)


class Scroll(QScrollArea):
    def __init__(self, widget=None, horizontal=False):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        if not horizontal:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(scrollbar_css())
        self.viewport().setObjectName("vp")
        self.viewport().setStyleSheet("QWidget#vp{background:transparent;}")
        if widget is not None:
            self.setWidget(widget)
            widget.setAutoFillBackground(False)


class HScroll(Scroll):
    def __init__(self, widget):
        super().__init__(widget, horizontal=True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def content_width(self):
        return self.widget().minimumSizeHint().expandedTo(self.widget().minimumSize()).width()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        inner, need = self.widget(), self.content_width()
        h = inner.heightForWidth(max(w, need)) if inner.hasHeightForWidth() else inner.sizeHint().height()
        return h + (self.horizontalScrollBar().sizeHint().height() if w < need else 0)

    def sizeHint(self):
        return QSize(self.content_width(), self.heightForWidth(self.content_width()))

    def minimumSizeHint(self):
        return QSize(0, self.heightForWidth(max(self.width(), 1)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.updateGeometry()

    def wheelEvent(self, e):
        if abs(e.angleDelta().y()) <= abs(e.angleDelta().x()):
            return super().wheelEvent(e)
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            sb = self.horizontalScrollBar()
            sb.setValue(sb.value() - e.angleDelta().y() // 120 * sb.singleStep() * 3)
            return e.accept()
        page = self.parentWidget()
        while page is not None and not isinstance(page, QScrollArea):
            page = page.parentWidget()
        if page is not None:
            QApplication.sendEvent(page.verticalScrollBar(), e)
        else:
            e.ignore()


class EdgeResize(QObject):
    ZONE = 8
    CURSORS = {"h": Qt.CursorShape.SizeHorCursor, "v": Qt.CursorShape.SizeVerCursor,
               "\\": Qt.CursorShape.SizeFDiagCursor, "/": Qt.CursorShape.SizeBDiagCursor}

    def __init__(self, box, on_start, on_drag, edges="lrtb", corners=()):
        super().__init__(box)
        self.box, self.on_start, self.on_drag, self.edges, self.corners = box, on_start, on_drag, edges, corners
        self.rest = box.cursor()
        self.drag = None
        box.setMouseTracking(True)
        box.installEventFilter(self)

    def _zone(self, pos):
        h = "l" if pos.x() <= self.ZONE else "r" if pos.x() >= self.box.width() - self.ZONE else ""
        v = "t" if pos.y() <= self.ZONE else "b" if pos.y() >= self.box.height() - self.ZONE else ""
        if h and v and h + v in self.corners:
            return h, v
        h, v = (h if h in self.edges else ""), (v if v in self.edges else "")
        return (h, v) if h or v else None

    def _shape(self, zone):
        if zone is None:
            return self.rest
        h, v = zone
        if h and v:
            return self.CURSORS["\\" if (h, v) in (("l", "t"), ("r", "b")) else "/"]
        return self.CURSORS["h" if h else "v"]

    def eventFilter(self, obj, e):
        t = e.type()
        if t == QEvent.Type.MouseMove:
            if self.drag:
                start, (h, v) = self.drag
                d = e.globalPosition() - start
                self.on_drag({"r": d.x(), "l": -d.x()}.get(h, 0), {"b": d.y(), "t": -d.y()}.get(v, 0))
                return True
            self.box.setCursor(self._shape(self._zone(e.position())))
        elif t == QEvent.Type.MouseButtonPress and e.button() == Qt.MouseButton.LeftButton and self._zone(e.position()):
            self.drag = (e.globalPosition(), self._zone(e.position()))
            self.on_start()
            return True
        elif t == QEvent.Type.MouseButtonRelease and self.drag:
            self.drag = None
            return True
        elif t == QEvent.Type.Leave and not self.drag:
            self.box.setCursor(self.rest)
        return False


class Collapsing(QWidget):
    def __init__(self, *items, spacing=12):
        super().__init__()
        self.items = items
        self.setLayout(hbox("stretch", *items, spacing=spacing))

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    @staticmethod
    def need(w):
        return w.minimumSizeHint().expandedTo(w.minimumSize()).width()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        free = self.width()
        for w in reversed(self.items):
            need = self.need(w)
            fits = free >= need
            w.setVisible(fits)
            free = free - need - self.layout().spacing() if fits else -1


def scrollbar_css():
    return (f"QScrollArea{{background:transparent;border:none;}}"
            f"QScrollBar:vertical{{background:transparent;width:10px;margin:2px;}}"
            f"QScrollBar::handle:vertical{{background:{T.grid};border-radius:3px;min-height:30px;}}"
            f"QScrollBar:horizontal{{background:transparent;height:10px;margin:2px;}}"
            f"QScrollBar::handle:horizontal{{background:{T.grid};border-radius:3px;min-width:30px;}}"
            f"QScrollBar::add-line,QScrollBar::sub-line{{width:0;height:0;}}"
            f"QScrollBar::add-page,QScrollBar::sub-page{{background:transparent;}}")


def stat_tile(label, value, color="ink", value_size=24, lh=32):
    return Box(bg="surf2", radius=12, layout=vbox(
        Label(label, 12, 400, "body", lh=16),
        Label(value, value_size, 600, color, spacing=-0.6 if value_size >= 24 else -0.5, lh=lh),
        margins=(14, 12, 14, 12)))


def empty_state(title, text, pad=(32, 28, 32, 28)):
    return card(Label(title, 18, 600, lh=26), 6, Label(text, 14, 400, "body", wrap=True), "stretch", pad=pad)


def kv_row(k, v, mono=False, border=True, pad=6, v_color="ink", size=13):
    row = QFrame()
    row.setObjectName(f"r{next(_ids)}")
    if border:
        row.setStyleSheet(f"QFrame#{row.objectName()}{{border:none;border-bottom:1px solid {T.line};}}")
    vl = Label(v, size, 400, v_color, mono=mono, align=Qt.AlignmentFlag.AlignRight, elide=True)
    vl.setMinimumWidth(40)
    row.setLayout(hbox(Label(k, size, 400, "body"), 12, (vl, 1), margins=(0, pad, 0, pad)))
    return row


class Flow(QLayout):
    def __init__(self, spacing=12, per_row=None, fill=True, vspacing=None):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.blocks = []
        self.own = {}
        self.steady = set()
        self.gap, self.per_row, self.fill = spacing, per_row, fill
        self.vgap = spacing if vspacing is None else vspacing

    def set_steady(self, w, on):
        (self.steady.add if on else self.steady.discard)(w)
        self.invalidate()

    def set_width(self, w, width):
        if width is None:
            self.own.pop(w, None)
        else:
            self.own[w] = width
        self.invalidate()

    def add(self, w, min_width=None, stretch=1):
        if not isinstance(w, QWidget):
            w = wrap(w)
        if min_width is None:
            min_width = w.sizeHint().width()
        self.addChildWidget(w)
        self.blocks.append([QWidgetItem(w), min_width, stretch])
        self.invalidate()
        return w

    def addItem(self, item):
        self.blocks.append([item, item.minimumSize().width(), 1])

    def count(self):
        return len(self.blocks)

    def itemAt(self, i):
        return self.blocks[i][0] if 0 <= i < len(self.blocks) else None

    def takeAt(self, i):
        return self.blocks.pop(i)[0] if 0 <= i < len(self.blocks) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._place(width)

    def minimumSize(self):
        return QSize(max((it.minimumSize().width() for it, _, _ in self.blocks), default=0), 0)

    def sizeHint(self):
        width = sum(m for _, m, _ in self.blocks) + self.gap * max(len(self.blocks) - 1, 0)
        return QSize(width, self._place(width))

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect.width(), rect.x(), rect.y())

    def _cols(self, width):
        widest = max((m for _, m, _ in self.blocks), default=0)
        return max(1, min(self.per_row, (width + self.gap) // (widest + self.gap)))

    def _rows(self, width):
        shown = [b for b in self.blocks if not b[0].isEmpty()]
        n = self._cols(width) if self.per_row else None
        if n and not self.own:
            return [shown[i:i + n] for i in range(0, len(shown), n)]
        colw = (width - self.gap * (n - 1)) // n if n else 0
        rows, row, used = [], [], 0
        for b in shown:
            w = b[0].widget()
            need = min(self.own.get(w) or (colw if w in self.steady else 0) or b[1], width)
            capped = len(row) >= n if n else False
            if capped and all(self.own.get(x[0].widget()) for x in row + [b]):
                capped = False
            if row and (used + self.gap + need > width or capped):
                rows.append(row)
                row, used = [], 0
            used += (self.gap if row else 0) + need
            row.append(b)
        return rows + [row] if row else rows

    def _place(self, width, x0=None, y0=0):
        rows = self._rows(width)
        cols = self._cols(width) if self.per_row else 0
        y = y0
        for row in rows:
            own = [self.own.get(it.widget()) for it, _, _ in row] if cols else []
            if any(own):
                colw = (width - self.gap * (cols - 1)) // cols
                own = [o or (colw if it.widget() in self.steady else None) for o, (it, _, _) in zip(own, row)]
                free = own.count(None)
                rest = width - self.gap * (len(row) - 1) - sum(min(o, width) for o in own if o)
                widths = [min(o, width) if o else rest // max(free, 1) for o in own]
            elif cols:
                widths = [(width - self.gap * (cols - 1)) // cols] * len(row)
            else:
                spare = width - sum(m for _, m, _ in row) - self.gap * (len(row) - 1)
                total = sum(s for _, _, s in row)
                widths = [m + (max(spare, 0) * s // total if total else 0) for _, m, s in row]
            widths = [min(w, width) for w in widths]
            heights = [it.heightForWidth(w) if it.hasHeightForWidth() else it.sizeHint().height()
                       for (it, _, _), w in zip(row, widths)]
            heights = [max(h, it.minimumSize().height()) for h, (it, _, _) in zip(heights, row)]
            tall = max(heights)
            if x0 is not None:
                x = x0
                for (it, _, _), w, h in zip(row, widths, heights):
                    it.setGeometry(QRect(x, y, w, tall if self.fill else h))
                    x += w + self.gap
            y += tall + self.vgap
        return max(y - self.vgap - y0, 0)


def grid(cols, spacing=12, hspacing=None):
    g = QGridLayout()
    g.setContentsMargins(0, 0, 0, 0)
    g.setHorizontalSpacing(hspacing if hspacing is not None else spacing)
    g.setVerticalSpacing(spacing)
    for c in range(cols):
        g.setColumnStretch(c, 1)
    return g


def link(text, on_click):
    l = Label(f"<u>{text}</u>", 13, 600, rich=True, select=False)
    l.setCursor(Qt.CursorShape.PointingHandCursor)
    l.mousePressEvent = lambda e: on_click()
    return l


class FolderIcon(QWidget):
    def __init__(self, color="ink"):
        super().__init__()
        self.color = color
        self.setFixedSize(16, 14)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(qc(col(self.color)), 1.4))
        path = QPainterPath()
        path.moveTo(1, 2.5)
        path.quadTo(1, 1, 2.5, 1)
        path.lineTo(5.9, 1)
        path.lineTo(7.5, 2.8)
        path.lineTo(13.5, 2.8)
        path.quadTo(15, 2.8, 15, 4.3)
        path.lineTo(15, 11.5)
        path.quadTo(15, 13, 13.5, 13)
        path.lineTo(2.5, 13)
        path.quadTo(1, 13, 1, 11.5)
        path.closeSubpath()
        p.drawPath(path)


class Chevron(QWidget):
    def __init__(self, color="ink", rotation=90):
        super().__init__()
        self.color, self.rotation = color, rotation
        self.setFixedSize(12, 12)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(6, 6)
        p.rotate(self.rotation)
        p.translate(-6, -6)
        p.setPen(QPen(qc(col(self.color)), 1.6, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(4.5, 2.5)
        path.lineTo(8, 6)
        path.lineTo(4.5, 9.5)
        p.drawPath(path)


class SideHandle(QWidget):
    SNAP = 40
    MAX_SHARE = 0.7
    DESIGN_WIDTH = 1920

    def __init__(self, panel, app, key, right=False):
        super().__init__()
        self.panel, self.app, self.key, self.right = panel, app, key, right
        self.default = panel.minimumWidth() / self.DESIGN_WIDTH
        self.closed = False
        self.px = 0
        self.hover = self.drag = None
        self.setFixedWidth(12)
        self.setCursor(Qt.CursorShape.SplitHCursor)

    def share(self):
        return self.app.side_widths.get(self.key, self.default)

    def max_width(self):
        return round(self.app.width() * self.MAX_SHARE)

    def apply(self, w):
        self.px = w
        self.panel.setFixedWidth(max(w, 1))
        self.panel.setVisible(w > 0)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag = (e.globalPosition().x(), {h: h.px for h in self.app.handles})
            self.update()

    def mouseMoveEvent(self, e):
        if self.drag:
            x0, start = self.drag
            dx = e.globalPosition().x() - x0
            self.app.drag_side(self, start[self] - dx if self.right else start[self] + dx, start)

    def mouseReleaseEvent(self, e):
        self.drag = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        w = round(self.default * self.app.side_scale()) if self.px == 0 else 0
        self.app.drag_side(self, w, {h: h.px for h in self.app.handles})

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = self.hover or self.drag
        p.setPen(QPen(qc(T.mute if active else T.grid), 3 if active else 1.5, cap=Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(self.width() / 2, 8), QPointF(self.width() / 2, self.height() - 8))


class Check(QWidget):
    def __init__(self, checked=False, size=18):
        super().__init__()
        self.checked = checked
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_checked(self, on):
        self.checked = on
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if not self.checked:
            p.setPen(QPen(qc(T.mute), 1.5))
            p.setBrush(qc(T.surf))
            p.drawRoundedRect(r, 4, 4)
            return
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc(T.ink))
        p.drawRoundedRect(r, 4, 4)
        w, h = r.width(), r.height()
        tick = QPainterPath(QPointF(r.x() + w * 0.24, r.y() + h * 0.52))
        tick.lineTo(r.x() + w * 0.43, r.y() + h * 0.71)
        tick.lineTo(r.x() + w * 0.77, r.y() + h * 0.31)
        p.setPen(QPen(qc(T.surf), 2, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(tick)


class InfoIcon(QWidget):
    def __init__(self, size=22, color="ink"):
        super().__init__()
        self.color = color
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width() / 24, self.height() / 24)
        c = qc(col(self.color))
        p.setPen(QPen(c, 2))
        p.drawEllipse(QRectF(2.5, 2.5, 19, 19))
        p.setPen(QPen(c, 2.4, cap=Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(12, 11), QPointF(12, 17))
        p.drawLine(QPointF(12, 7.3), QPointF(12, 7.7))


class Logo(QLabel):
    def __init__(self, size):
        super().__init__()
        self.setFixedSize(size, size)
        self.setPixmap(theme.logo_pixmap(size, self.devicePixelRatioF()))


class SplashLogo(QWidget):
    MARK = 72

    def __init__(self, pad=10):
        super().__init__()
        self.svg = QSvgRenderer(str(theme.LOGO_SVG), self)
        self.text_font = font(26, 900, display=True, spacing=-0.5)
        self.setFixedSize(QFontMetrics(self.text_font).horizontalAdvance("Laboard") + 2 * pad, 68)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.MARK
        self.svg.render(p, QRectF((self.width() - s) / 2, (self.height() - s) / 2, s, s))
        fm = QFontMetrics(self.text_font)
        path = QPainterPath()
        path.addText((self.width() - fm.horizontalAdvance("Laboard")) / 2, (self.height() + fm.capHeight()) / 2,
                     self.text_font, "Laboard")
        p.strokePath(path, QPen(qc(T.surf), 2, join=Qt.PenJoinStyle.RoundJoin))
        p.fillPath(path, qc(T.ink))
