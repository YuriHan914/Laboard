"""Small building blocks that mirror the prototype's inline-styled elements."""
import itertools
import re

from PyQt6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit, QPushButton,
                             QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QWidgetItem)

from . import theme
from .theme import T, font, qc

_ids = itertools.count()


def col(c):
    """Resolve a palette key ('ink', 'c2', ...) or pass a literal colour through."""
    return T[c] if c in T else c


# ------------------------------------------------------------------ layouts
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
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


# ------------------------------------------------------------------ boxes
class Box(QFrame):
    """A rounded, filled container (the prototype's styled <div>)."""
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
        # QSS ignores radii above half the height, so resolve "pill" (999) per size
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


def card(*items, pad=(20, 20, 20, 20), spacing=0, radius=16, bg="surf"):
    return Box(bg=bg, radius=radius, layout=vbox(*items, spacing=spacing, margins=pad))


# ------------------------------------------------------------------ text
class Label(QLabel):
    def __init__(self, text="", size=14, weight=400, color="ink", mono=False, display=False, spacing=0.0,
                 lh=None, wrap=False, rich=False, align=None, elide=False, select=False):
        super().__init__(text)
        self.setFont(font(size, weight, mono=mono, display=display, spacing=spacing))
        self._color = color
        self.setStyleSheet(f"color:{col(color)};background:transparent;")
        self.setTextFormat(Qt.TextFormat.RichText if rich else Qt.TextFormat.PlainText)
        self._elide = elide
        if wrap:
            self.setWordWrap(True)
        if lh and not wrap:
            self.setFixedHeight(lh)
        if align is not None:
            self.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        if select:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if elide:
            self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.setToolTip(text)

    def minimumSizeHint(self):
        if self._elide:
            return QSize(0, super().minimumSizeHint().height())
        return super().minimumSizeHint()

    def paintEvent(self, e):
        if not self._elide:
            return super().paintEvent(e)
        p = QPainter(self)
        p.setFont(self.font())
        p.setPen(qc(col(self._color)))
        txt = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        p.drawText(self.rect(), int(self.alignment() | Qt.AlignmentFlag.AlignVCenter), txt)


def mono_span(text, color="ink", size=None):
    s = f"font-size:{size}px;" if size else ""
    return f'<span style="font-family:\'{theme.MONO_FAMILY}\';color:{col(color)};{s}">{text}</span>'


def h(text, size=16, weight=600, lh=24, **kw):
    return Label(text, size, weight, lh=lh, **kw)


def caption(text, color="mute", size=12, **kw):
    return Label(text, size, 400, color, **kw)


def breakable(text):
    """``text`` with zero-width spaces after path and identifier separators, so a wrapping Label can break long
    paths and keys there instead of only at spaces. Commas and points inside numbers (7,011 / 332.2) stay whole."""
    return re.sub(r"([/_=:-]|[.,](?!\d))", "\\1\u200b", text)


def elided(text, *args, **kw):
    """A Label at its full width when there's room that shortens with "…" when squeezed (a plain elide Label
    instead shares spare width with stretches)."""
    lab = Label(text, *args, elide=True, **kw)
    lab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    return lab


class Pill(QLabel):
    """Rounded tag: chip, badge, ref label."""

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


# ------------------------------------------------------------------ controls
class Button(QPushButton):
    """Wise DS Button: secondary (soft fill), primary (green) or tertiary (text only), sm / md."""

    @staticmethod
    def _metrics(size, compact=False):
        """(font size, (v pad, h pad), height) for a size."""
        fs, pad = (13, (4, 14)) if compact else (14, (8, 16)) if size == "sm" else (16, (12, 24))
        return fs, pad, pad[0] * 2 + (20 if fs <= 14 else 24)

    @staticmethod
    def height_for(size, compact=False):
        return Button._metrics(size, compact)[2]

    def __init__(self, text, variant="secondary", size="sm", on_click=None, compact=False):
        super().__init__(text)
        fs, pad, hgt = self._metrics(size, compact)
        self.setFont(font(fs, 600))
        bg, hover, fg = {"primary": (theme.WISE_GREEN, theme.WISE_GREEN_PALE, theme.INK),
                         "tertiary": ("transparent", T.surf2, T.ink)}.get(variant, (T.surf2, T.grid, T.ink))
        self.setFixedHeight(hgt)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"QPushButton{{background:{bg};color:{fg};border:none;border-radius:{min(24, hgt // 2)}px;"
                           f"padding:0 {pad[1]}px;}}QPushButton:hover{{background:{hover};}}"
                           f"QPushButton:pressed{{padding-top:1px;}}")
        if on_click:
            self.clicked.connect(on_click)


class Segmented(Box):
    """Pill-shaped segmented control used for tabs, filters and toggles."""

    def __init__(self, options, current, on_select, size=12, pad=(5, 12), outer=3, gap=2, on=("surf", "ink"),
                 off=("transparent", "body"), expand=False, dots=None):
        lay = hbox(spacing=gap, margins=(outer,) * 4)
        super().__init__(bg="surf2", radius=999, layout=lay)
        self.setSizePolicy(QSizePolicy.Policy.Preferred if expand else QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.on, self.off, self.items = on, off, {}  # key -> (segment box, its label)
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
        """Show ``current`` as the chosen segment, in place (for a caller that doesn't re-render on select)."""
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
    """Drop-down in the LineEdit style; calls ``on_change(key)`` with the chosen option's key."""

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
            widget.setAutoFillBackground(False)  # setWidget() turns it on


class HScroll(Scroll):
    """Sideways-only scroll for a block that shouldn't get narrower than its minimum width, such as a table: it is
    as tall as its content and shows a scrollbar under it when the space is narrower. The wheel scrolls the page
    around it; Shift+wheel (or a sideways swipe) scrolls the block."""

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
        self.updateGeometry()  # its height depends on its width

    def wheelEvent(self, e):
        if abs(e.angleDelta().y()) <= abs(e.angleDelta().x()):
            return super().wheelEvent(e)
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:  # Shift+wheel: sideways, wherever the bar is
            sb = self.horizontalScrollBar()
            sb.setValue(sb.value() - e.angleDelta().y() // 120 * sb.singleStep() * 3)
            return e.accept()
        page = self.parentWidget()  # up/down scrolls the page around it, not the table sideways
        while page is not None and not isinstance(page, QScrollArea):
            page = page.parentWidget()
        if page is not None:
            QApplication.sendEvent(page.verticalScrollBar(), e)
        else:
            e.ignore()


class EdgeResize(QObject):
    """Lets the user resize ``box`` by dragging its edges and corners (``edges``: any of "l", "r", "t", "b"; the
    corners between two of them come with them, and ``corners`` such as "lt" add one whose edges are off), with
    the matching cursor near them. ``on_start()`` runs when a drag begins and ``on_drag(dw, dh)`` gets the change
    in size since: dragging the left or top edge outwards grows the box too (it stays where its layout puts it).
    A resize drag is never taken as a click on the box."""

    ZONE = 8  # px along each edge, inside the box's padding
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
        """(horizontal side "l"/"r"/"", vertical side "t"/"b"/"") under ``pos``, or None away from the edges."""
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
            return True  # not a click
        elif t == QEvent.Type.Leave and not self.drag:
            self.box.setCursor(self.rest)
        return False


class Collapsing(QWidget):
    """Right-aligned row that never widens its window: items that don't fit are hidden, leftmost first."""

    def __init__(self, *items, spacing=12):
        super().__init__()
        self.items = items
        self.setLayout(hbox("stretch", *items, spacing=spacing))

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    @staticmethod
    def need(w):
        return w.minimumSizeHint().expandedTo(w.minimumSize()).width()

    def full_width(self):
        """The width at which every item shows."""
        return sum(map(self.need, self.items)) + self.layout().spacing() * (len(self.items) - 1)

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


# ------------------------------------------------------------------ composites
def stat_tile(label, value, color="ink", value_size=24, lh=32):
    return Box(bg="surf2", radius=12, layout=vbox(
        Label(label, 12, 400, "body", lh=16),
        Label(value, value_size, 600, color, spacing=-0.6 if value_size >= 24 else -0.5, lh=lh),
        margins=(14, 12, 14, 12)))


def empty_state(title, text, pad=(32, 28, 32, 28)):
    """Card shown where a page or section has nothing to display yet."""
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
    """Blocks placed left to right that wrap onto the next row when the width runs out, like inline blocks.
    ``add`` gives each block the width it needs and a stretch. With ``per_row`` the rows are a grid of that many
    equal columns (fewer when they don't fit), except blocks given their own width (``set_width``): those keep it,
    the others in their row share what is left, and a block that would get less than its width wraps to the next
    row. Otherwise each row shares its spare width by stretch. A row is as tall as its tallest block; ``fill``
    stretches the others to match, else they keep their own height. ``vspacing`` is the gap between rows
    (default: ``spacing``)."""

    def __init__(self, spacing=12, per_row=None, fill=True, vspacing=None):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.blocks = []  # [QLayoutItem, min width, stretch]
        self.own = {}  # widget -> width the user gave it (grid mode)
        self.filling = set()  # widgets as tall as their row even without ``fill``
        self.steady = set()  # grid mode: widgets that keep a column's width while their neighbours take their own
        self.gap, self.per_row, self.fill = spacing, per_row, fill
        self.vgap = spacing if vspacing is None else vspacing

    def set_fill(self, w, on):
        """Make block ``w`` as tall as its row (on) or its own height (off), whatever ``fill`` says."""
        (self.filling.add if on else self.filling.discard)(w)
        self.invalidate()

    def set_steady(self, w, on):
        """Grid mode: block ``w`` keeps a column's width (on) instead of sharing what its row's other blocks leave."""
        (self.steady.add if on else self.steady.discard)(w)
        self.invalidate()

    def set_width(self, w, width):
        """Give block ``w`` its own width in grid mode (None: back to its column)."""
        if width is None:
            self.own.pop(w, None)
        else:
            self.own[w] = width
        self.invalidate()

    def add(self, w, min_width=None, stretch=1):
        """Add a block (widget or layout); ``min_width`` defaults to the block's preferred width."""
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
        # a block alone on its row may go below its wrap width, down to its own minimum
        return QSize(max((it.minimumSize().width() for it, _, _ in self.blocks), default=0), 0)

    def sizeHint(self):
        width = sum(m for _, m, _ in self.blocks) + self.gap * max(len(self.blocks) - 1, 0)
        return QSize(width, self._place(width))

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect.width(), rect.x(), rect.y())

    def _cols(self, width):
        """Grid mode: how many of the ``per_row`` columns fit (at least one)."""
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
            if row and (used + self.gap + need > width or len(row) == n):
                rows.append(row)
                row, used = [], 0
            used += (self.gap if row else 0) + need
            row.append(b)
        return rows + [row] if row else rows

    def _place(self, width, x0=None, y0=0):
        """Lay the blocks out in ``width`` (moving them only when ``x0`` is given); returns the height used."""
        rows = self._rows(width)
        cols = self._cols(width) if self.per_row else 0
        y = y0
        for row in rows:
            own = [self.own.get(it.widget()) for it, _, _ in row] if cols else []
            if any(own):  # rows packed so the others still get their width (_rows)
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
                    it.setGeometry(QRect(x, y, w, tall if self.fill or it.widget() in self.filling else h))
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
    l = Label(f"<u>{text}</u>", 13, 600, rich=True)
    l.setCursor(Qt.CursorShape.PointingHandCursor)
    l.mousePressEvent = lambda e: on_click()
    return l


# ------------------------------------------------------------------ icons
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
    """12px right-pointing chevron (M4.5 2.5 L8 6 L4.5 9.5), turned by ``rotation`` degrees: 90 points down."""

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
    """The 12px gutter beside a side panel. Dragging its line resizes ``panel`` live, from hidden up to 70% of the
    window as it is right now; a panel dragged wider squeezes the centre and then the other panel
    (``app.drag_side``). Double-click toggles hidden / the width the panel was built with. The width is kept in
    ``app.side_widths[key]`` as a share of ``app.side_scale()`` and survives re-renders; the panel gets it while the
    window has room, and gives way when it doesn't (``app.fit_sides``)."""

    SNAP = 40  # narrower than this (px) the panel just hides
    MAX_SHARE = 0.7  # of the current window width
    DESIGN_WIDTH = 1920  # the window width the panels' built widths are meant for

    def __init__(self, panel, app, key, right=False):
        super().__init__()
        self.panel, self.app, self.key, self.right = panel, app, key, right
        self.default = panel.minimumWidth() / self.DESIGN_WIDTH
        self.closed = False  # a panel with nothing to show (app.show_right): hidden with its gutter
        self.px = 0  # the panel's width as last applied
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
            self.drag = (e.globalPosition().x(), {h: h.px for h in self.app.handles})  # every panel's width at the start
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
    """A check box drawn in the theme's colours. It only shows ``checked``: clicks pass through to the parent,
    which owns the state (a whole card can be the click target)."""

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
    """'i' in a circle (24-unit icon: circle r9.5, stroke 2) drawn at ``size`` px."""

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
    """The Laboard logo, ``size`` px square, sharp on HiDPI screens."""

    def __init__(self, size):
        super().__init__()
        self.setFixedSize(size, size)
        self.setPixmap(theme.logo_pixmap(size, self.devicePixelRatioF()))


class SplashLogo(QWidget):
    """Top-bar brand: the splash mark centred behind a haloed "Laboard" wordmark, 68px tall."""

    MARK = 72

    def __init__(self, pad=10):
        super().__init__()
        self.svg = QSvgRenderer(str(theme.LOGO_DIR / "laboard_splash.svg"), self)
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
        # halo in the surface colour so the wordmark stays legible over the splash
        p.strokePath(path, QPen(qc(T.surf), 2, join=Qt.PenJoinStyle.RoundJoin))
        p.fillPath(path, qc(T.ink))
