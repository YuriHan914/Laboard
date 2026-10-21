"""Custom-painted charts and viewers."""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QSizePolicy, QWidget

from . import theme
from .theme import T, font, qc
from .widgets import col


def _aa(w):
    p = QPainter(w)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    return p


class StackedBar(QWidget):
    """Horizontal pill split into coloured segments: [(fraction, colour)]."""

    def __init__(self, segments, height=12, gap=2, min_px=3):
        super().__init__()
        self.segments, self.gap, self.min_px = segments, gap, min_px
        self.setFixedHeight(height)

    def paintEvent(self, e):
        p = _aa(self)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), self.height() / 2, self.height() / 2)
        p.setClipPath(clip)
        avail = self.width() - self.gap * (len(self.segments) - 1)
        x = 0.0
        for frac, c in self.segments:
            w = max(self.min_px, avail * frac)
            p.fillRect(QRectF(x, 0, w, self.height()), qc(col(c)))
            x += w + self.gap


class Meter(QWidget):
    """Progress bar: track + rounded fill."""

    def __init__(self, pct, height=6, fill="ink", track="surf2"):
        super().__init__()
        self.pct, self.fill, self.track = pct, fill, track
        self.setFixedHeight(height)

    def paintEvent(self, e):
        p = _aa(self)
        r = self.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc(col(self.track)))
        p.drawRoundedRect(QRectF(self.rect()), r, r)
        w = self.width() * self.pct / 100
        if w > 0:
            p.setBrush(qc(col(self.fill)))
            p.drawRoundedRect(QRectF(0, 0, max(w, self.height()), self.height()), r, r)


class DataChangeChart(QWidget):
    """Images added (up, green) and removed (down, red) per data commit."""

    def __init__(self, changes, vmax):
        super().__init__()
        self.changes, self.vmax = changes, vmax
        self.setFixedHeight(76 + 1 + 52 + 4 + 28)

    def paintEvent(self, e):
        p = _aa(self)
        n = len(self.changes)
        gap = 8
        cw = (self.width() - gap * (n - 1)) / n
        pos, neg = qc("#2ead4b"), qc("#d03238")
        lab = font(11, 600)
        for i, (hsh, date, add, rem) in enumerate(self.changes):
            x = i * (cw + gap)
            bw = cw * 0.6

            bx = x + (cw - bw) / 2
            ah = round(add / self.vmax * 56)
            dh = round(rem / self.vmax * 56)
            p.setPen(Qt.PenStyle.NoPen)
            if ah:
                path = QPainterPath()
                path.addRoundedRect(QRectF(bx, 76 - ah, bw, ah + 4), 4, 4)
                p.save()
                p.setClipRect(QRectF(bx, 0, bw, 76))
                p.fillPath(path, pos)
                p.restore()
                p.setFont(lab)
                p.setPen(pos)
                p.drawText(QRectF(x, 76 - ah - 17, cw, 14), Qt.AlignmentFlag.AlignCenter, f"+{add:,}")
            p.setPen(Qt.PenStyle.NoPen)
            p.fillRect(QRectF(x, 76, cw + (gap if i < n - 1 else 0), 1), qc(T.mute))
            if dh:
                path = QPainterPath()
                path.addRoundedRect(QRectF(bx, 73, bw, dh + 4), 4, 4)
                p.save()
                p.setClipRect(QRectF(bx, 77, bw, 52))
                p.fillPath(path, neg)
                p.restore()
                p.setFont(lab)
                p.setPen(neg)
                p.drawText(QRectF(x, 77 + dh + 3, cw, 14), Qt.AlignmentFlag.AlignCenter, f"−{rem:,}")
            p.setFont(font(11, 500, mono=True))
            p.setPen(qc(T.body))
            p.drawText(QRectF(x, 133, cw, 14), Qt.AlignmentFlag.AlignCenter, hsh)
            p.setFont(font(11))
            p.setPen(qc(T.mute))
            p.drawText(QRectF(x, 147, cw, 14), Qt.AlignmentFlag.AlignCenter, date)


class AccuracyChart(QWidget):
    """results/accuracy.csv per commit: loss lines (left axis) over ms/image bars (right axis)."""

    PLOT_H = 200

    def __init__(self, rows):
        super().__init__()
        self.rows = rows
        self.loss_max = max(max(r[2], r[3]) for r in rows) * 1.1 or 1
        self.ms_max = max(r[4] for r in rows) * 1.1 or 1
        self.setFixedHeight(self.PLOT_H + 8 + 28 + 16)

    def paintEvent(self, e):
        p = _aa(self)
        p.translate(0, 16)
        H = self.PLOT_H
        left, right = 34, 42
        pw = self.width() - left - right
        n = len(self.rows)
        p.setFont(font(11))
        p.setPen(qc(T.mute))
        lm, mm = self.loss_max, self.ms_max
        for i, (l, r) in enumerate([(f"{lm:.2g}", f"{mm:.2g} ms"), (f"{lm / 2:.2g}", f"{mm / 2:.2g} ms"), ("0", "0")]):
            y = i * H / 2
            p.drawText(QRectF(0, y - 6, 26, 12), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, l)
            p.drawText(QRectF(left + pw + 8, y - 6, 40, 12), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, r)
        cw = pw / n
        for i, (_, _, _, _, ms) in enumerate(self.rows):
            bh = ms / self.ms_max * H
            bw = cw * 0.46
            bx = left + i * cw + (cw - bw) / 2
            path = QPainterPath()
            path.addRoundedRect(QRectF(bx, H - bh, bw, bh + 4), 4, 4)
            p.save()
            p.setClipRect(QRectF(bx, 0, bw, H))
            p.fillPath(path, qc(T.grid))
            p.restore()
            p.setFont(font(10, 600))
            p.setPen(qc(T.mute))
            p.drawText(QRectF(left + i * cw, H - bh - 15, cw, 12), Qt.AlignmentFlag.AlignCenter, f"{ms:.1f}")
        dash = QPen(qc(T.grid), 1)
        dash.setDashPattern([3, 4])
        p.setPen(dash)
        p.drawLine(QPointF(left, H / 2), QPointF(left + pw, H / 2))
        p.setPen(QPen(qc(T.mute), 1))
        p.drawLine(QPointF(left, H - 0.5), QPointF(left + pw, H - 0.5))
        for idx, color in ((3, T.c2), (2, T.ink)):
            pts = [QPointF(left + (i + 0.5) * cw, H - r[idx] / self.loss_max * H) for i, r in enumerate(self.rows)]
            p.setPen(QPen(qc(color), 2.5, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline(pts)
        for i, (hsh, model, *_rest) in enumerate(self.rows):
            x = left + i * cw
            p.setFont(font(11, 500, mono=True))
            p.setPen(qc(T.body))
            p.drawText(QRectF(x, H + 8, cw, 14), Qt.AlignmentFlag.AlignCenter, hsh)
            p.setFont(font(11))
            p.setPen(qc(T.mute))
            p.drawText(QRectF(x, H + 22, cw, 14), Qt.AlignmentFlag.AlignCenter, model)


# Categorical series colours in fixed slot order (validated for adjacent-pair colour-blind separation on the
# light #ffffff and dark #1a1b18 surfaces). Three light slots sit under 3:1 against white, so every chart that
# uses them also shows a legend with the series names. There are eight; slots past them reuse the colours from
# the start, dashed, rather than inventing hues that can't be told apart.
SERIES = dict(light=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
              dark=["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"])


def series_style(slot):
    """(colour, dashed) for a series slot."""
    colors = SERIES[theme.current]
    return colors[slot % len(colors)], slot >= len(colors)


class Swatch(QWidget):
    """Legend key for a line series: a short stroke in its colour, dashed if the series is."""

    def __init__(self, color, dashed=False):
        super().__init__()
        self.color, self.dashed = color, dashed
        self.setFixedSize(22, 12)

    def paintEvent(self, e):
        p = _aa(self)
        pen = QPen(qc(self.color), 3, cap=Qt.PenCapStyle.RoundCap)
        if self.dashed:
            pen.setDashPattern([1.5, 1.5])
        p.setPen(pen)
        p.drawLine(QPointF(2, 6), QPointF(20, 6))


class LineChart(QWidget):
    """Result-page chart: series overlaid, values normalised to 0..1 by the caller.

    The pointer reads values out: a hairline snaps to the nearest data point and a tooltip next to the cursor
    lists every series there (``set_hover``). Ctrl+wheel zooms the x axis around the cursor, back out to the
    whole range, and dragging moves a zoomed view sideways; the x tick labels follow the view (``set_axis``).
    A plain wheel still scrolls the page, and a click that isn't a drag still reaches the card around it.
    """

    PLOT_H = 200
    LEFT = 44  # px for the y labels
    MAX_ZOOM = 50  # the view can narrow to 1/50 of the x range
    Y_STEP, X_STEP = 100, 180  # about one y tick per this many px of height, one x tick per this much width

    def __init__(self, y_labels, x_labels, plot_h=PLOT_H):
        super().__init__()
        self.y_labels, self.x_labels, self.plot_h = y_labels, x_labels, plot_h
        self.series = []  # [(values, colour, width)] spaced evenly, or (..., x positions 0..1[, dashed])
        self.hover_rows, self.x_name, self.pointer = [], "", None
        self.x_value = None  # x position 0..1 -> the x it stands for; set, the tick labels follow zooming
        self.y_range = None  # (lo, hi, format); set, the y ticks are worked out for the chart's height
        self.view = (0.0, 1.0)  # the part of the x range shown
        self.pan = None  # (pointer x, view) when the press began; ``moved`` once it turned into a drag
        self.moved = False
        self.setFixedHeight(plot_h + 8 + 12 + 8)
        self.setMouseTracking(True)

    def set_series(self, series):
        self.series = series
        self.update()

    def set_plot_h(self, h):
        self.plot_h = h
        self.setFixedHeight(h + 8 + 12 + 8)
        self.update()

    def set_y_range(self, lo, hi, fmt):
        """The values at the plot's bottom and top; a taller chart gets more ticks (Y_STEP)."""
        self.y_range = (lo, hi, fmt)
        self.update()

    def set_axis(self, x_value, x_name):
        """Label x ticks with ``x_value(position 0..1)`` (and ``x_name`` on the last), so zooming relabels them."""
        self.x_value, self.x_name = x_value, x_name
        self.update()

    def set_hover(self, rows):
        """What the pointer reads out, per series: dict(name, color, dashed, x01, y01, xs, ys, smooth), where x01/y01
        are the plotted positions (0..1) and xs/ys the data (smooth: the smoothed values drawn, or None)."""
        self.hover_rows = rows
        self.update()

    # ---------------------------------------------------------- view
    def _sx(self, f):
        """Screen x of x position ``f`` (0..1) in the current view."""
        v0, v1 = self.view
        return self.LEFT + (f - v0) / (v1 - v0) * (self.width() - self.LEFT)

    def _fx(self, x):
        v0, v1 = self.view
        return v0 + (x - self.LEFT) / (self.width() - self.LEFT) * (v1 - v0)

    def wheelEvent(self, e):
        if not e.modifiers() & Qt.KeyboardModifier.ControlModifier or not e.angleDelta().y():
            return super().wheelEvent(e)  # the page scrolls
        v0, v1 = self.view
        at = min(max(self._fx(e.position().x()), v0), v1)  # keep the x under the cursor in place
        span = min(max((v1 - v0) / 1.25 ** (e.angleDelta().y() / 120), 1 / self.MAX_ZOOM), 1.0)
        lo = at - (at - v0) / (v1 - v0) * span
        lo = min(max(lo, 0.0), 1.0 - span)
        self.view = (lo, lo + span)
        self._cursor()
        self.update()
        e.accept()

    def _cursor(self):
        if self.pan and self.moved:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self.view != (0.0, 1.0):
            self.setCursor(Qt.CursorShape.OpenHandCursor)  # zoomed: there is somewhere to drag to
        else:
            self.unsetCursor()  # the card's

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.pan, self.moved = (e.position().x(), self.view), False
        e.ignore()  # the card still sees the press (a plain click selects it)

    def mouseMoveEvent(self, e):
        self.pointer = e.position()
        if self.pan and e.buttons() & Qt.MouseButton.LeftButton:
            x0, (v0, v1) = self.pan
            dx = e.position().x() - x0
            if abs(dx) > 3 or self.moved:
                self.moved = True
                shift = -dx / (self.width() - self.LEFT) * (v1 - v0)
                lo = min(max(v0 + shift, 0.0), 1.0 - (v1 - v0))
                self.view = (lo, lo + (v1 - v0))
                self._cursor()
        self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        dragged = self.pan is not None and self.moved
        self.pan, self.moved = None, False
        self._cursor()
        if dragged:
            e.accept()  # a drag is not a click on the card
        else:
            e.ignore()

    def leaveEvent(self, e):
        self.pointer = None
        self.update()

    # ---------------------------------------------------------- paint
    def paintEvent(self, e):
        p = _aa(self)
        p.translate(0, 6)
        H, left = self.plot_h, self.LEFT
        pw = self.width() - left
        p.setFont(font(11))
        p.setPen(qc(T.mute))
        y_labels = self.y_labels
        if self.y_range is not None:  # bigger chart, more ticks
            lo, hi, fmt = self.y_range
            n = max(2, round(H / self.Y_STEP))
            y_labels = [fmt(hi - i * (hi - lo) / n) for i in range(n + 1)]
        k = max(len(y_labels) - 1, 1)
        for i, t in enumerate(y_labels):
            p.drawText(QRectF(0, i * H / k - 6, 34, 12), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, t)
        p.setPen(QPen(qc(T.grid), 1))
        for i in range(k):
            y = 0.5 if i == 0 else i * H / k
            p.drawLine(QPointF(left, y), QPointF(left + pw, y))
        p.setPen(QPen(qc(T.mute), 1))
        p.drawLine(QPointF(left, H - 0.5), QPointF(left + pw, H - 0.5))
        p.save()
        p.setClipRect(QRectF(left, -6, pw, H + 12))  # zoomed in, lines run past the plot's sides
        for vals, color, width, *rest in reversed(self.series):
            if len(vals) < 2:
                continue
            xs = rest[0] if rest else [i / (len(vals) - 1) for i in range(len(vals))]
            pts = [QPointF(self._sx(x), H - min(max(v, -0.1), 1) * H) for x, v in zip(xs, vals)]
            pen = QPen(qc(col(color)), width, join=Qt.PenJoinStyle.RoundJoin)
            if len(rest) > 1 and rest[1]:
                pen.setDashPattern([3, 2])
            p.setPen(pen)
            p.drawPolyline(pts)
        p.restore()
        p.setPen(qc(T.mute))  # axis text, not the last series' colour
        labels = self.x_labels
        if self.x_value is not None:  # wider chart, more ticks; zoomed, they follow the view
            v0, v1 = self.view
            n = max(2, round(pw / self.X_STEP))
            labels = [_num(self.x_value(v0 + j * (v1 - v0) / n)) for j in range(n + 1)]
            labels[-1] += f" {self.x_name}"
        n = len(labels)
        for i, t in enumerate(labels):
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(t)
            x = left + i * (pw - tw) / (n - 1) if n > 1 else left
            p.drawText(QPointF(x, H + 8 + fm.ascent()), t)
        if self.view != (0.0, 1.0):
            zoom = f"{1 / (self.view[1] - self.view[0]):.1f}×"
            p.drawText(QRectF(left, 2, pw - 4, 14), Qt.AlignmentFlag.AlignRight, zoom)
        self._paint_readout(p, H)

    def _paint_readout(self, p, H):
        """Hairline at the data x nearest the pointer, a dot on each series there, and the values beside the cursor."""
        if self.pointer is None or not self.hover_rows:
            return
        fx = self._fx(self.pointer.x())
        if not self.view[0] <= fx <= self.view[1] or not 0 <= self.pointer.y() - 6 <= H:
            return
        near = lambda r, f: min(range(len(r["x01"])), key=lambda i: abs(r["x01"][i] - f))
        snap = min((r["x01"][near(r, fx)] for r in self.hover_rows), key=lambda x: abs(x - fx))  # crosshair finds the X
        hits = [(r, near(r, snap)) for r in self.hover_rows]
        x = self._sx(snap)
        p.setPen(QPen(qc(T.mute), 1))
        p.drawLine(QPointF(x, 0), QPointF(x, H))
        for r, i in hits:
            p.setPen(QPen(qc(T.surf), 2))  # ring so the dot stands off the line
            p.setBrush(qc(col(r["color"])))
            p.drawEllipse(QPointF(self._sx(r["x01"][i]), H - min(max(r["y01"][i], -0.1), 1) * H), 4, 4)
        # tooltip: x on top, then per series the value (strong) and its name; a line key when there are several
        head = f"{self.x_name} {_num(hits[0][0]['xs'][hits[0][1]])}".strip()
        rows = []
        for r, i in hits:
            v, sm = _num(r["ys"][i]), r["smooth"]
            extra = f"smoothed {_num(sm[i])}" if sm is not None and _num(sm[i]) != v else ""
            rows.append((r, v, " · ".join(t for t in (r["name"], extra) if t)))
        strong, small = font(12, 600), font(11)
        key = 22 if len(rows) > 1 else 0
        p.setFont(strong)
        vw = max(p.fontMetrics().horizontalAdvance(v) for _, v, _ in rows)
        p.setFont(small)
        fm = p.fontMetrics()
        room = self.width() - 24 - key - vw - 8  # names shorten with "…" so the box never outgrows the chart
        names = [fm.elidedText(n, Qt.TextElideMode.ElideMiddle, max(room, 40)) for _, _, n in rows]
        nw = max(fm.horizontalAdvance(n) for n in names)
        w = min(12 + max(key + vw + (8 + nw if nw else 0), fm.horizontalAdvance(head)) + 12, self.width())
        h = 8 + 16 + len(rows) * 18 + 6
        bx = self.pointer.x() + 14
        if bx + w > self.width():
            bx = self.pointer.x() - 14 - w  # flip to the cursor's left near the right edge
        bx = min(max(bx, 0), self.width() - w)
        by = min(max(self.pointer.y() - 6 + 14, -6), self.height() - 6 - h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qc(T.ink, 0.92))
        p.drawRoundedRect(QRectF(bx, by, w, h), 8, 8)
        p.setPen(qc(T.mute))
        p.drawText(QRectF(bx + 12, by + 8, w - 24, 14), Qt.AlignmentFlag.AlignVCenter, head)
        for k, ((r, v, _), name) in enumerate(zip(rows, names)):
            y = by + 8 + 16 + k * 18
            if key:
                pen = QPen(qc(col(r["color"])), 3, cap=Qt.PenCapStyle.RoundCap)
                if r["dashed"]:
                    pen.setDashPattern([1.5, 1.5])
                p.setPen(pen)
                p.drawLine(QPointF(bx + 12, y + 9), QPointF(bx + 12 + 14, y + 9))
            p.setFont(strong)
            p.setPen(qc(T.surf))
            p.drawText(QRectF(bx + 12 + key, y, vw + 2, 18), Qt.AlignmentFlag.AlignVCenter, v)
            if name:
                p.setFont(small)
                p.setPen(qc(T.mute))
                p.drawText(QRectF(bx + 12 + key + vw + 8, y, nw + 2, 18), Qt.AlignmentFlag.AlignVCenter, name)


def _num(v):
    """A readout number: whole numbers and anything past 10,000 in full with separators, others to four digits."""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int) or abs(v) >= 1e4:
        return f"{v:,.0f}"
    return f"{v:.4g}"


class ZoomView:
    """Zoom and pan of one image, shared by every pane in ``panes`` (each Data pane has its own).

    ``zoom`` is relative to fitting the pane (1 = fit); ``cx, cy`` is the image point (0..1) at the pane centre,
    so the view survives pane resizes.
    """

    MAX = 40.0  # times the fitted size
    MIN_SCALE = 0.1  # zooming out stops at 10% of the image's own pixel size (or at fit, if that is already smaller)

    def __init__(self):
        self.zoom, self.cx, self.cy = 1.0, 0.5, 0.5
        self.panes = []

    def reset(self):
        """Back to how the image was first shown: fitted to the pane and centred."""
        self.zoom, self.cx, self.cy = 1.0, 0.5, 0.5
        self.update()

    def update(self):
        for pane in self.panes:
            pane.update()


class Stage(QWidget):
    """Dark image/video viewer pane with Raw / Predict overlays.

    Draws the file from ``path`` when it exists, otherwise a striped placeholder. On an image the
    wheel zooms around the cursor, Shift+wheel pans sideways, dragging pans and a double-click fits.
    """

    PAN_STEP = 60  # px per wheel notch with Shift
    KEEP = 48  # px of the image that stay in the pane however far it is dragged

    def __init__(self, name, meta, kind, label=None, pred=None, video=False, path=None, radius=4, view=None):
        """``radius``: corner radius of the parent area this pane fills (part of), so panes follow its rounding."""
        super().__init__()
        self.name, self.meta, self.kind, self.label, self.pred = name, meta, kind, label, pred
        self.video, self.radius = video, radius
        self.pix = QPixmap(path) if path else QPixmap()
        self.view = view or ZoomView()
        self.view.panes.append(self)
        self._drag = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if not self.pix.isNull():
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    # ---------------------------------------------------------- zoom / pan
    def _scale(self):
        fit = min(self.width() / self.pix.width(), self.height() / self.pix.height())
        return max(fit, 1e-6) * self.view.zoom  # a pane not laid out yet has size 0

    def _min_zoom(self):
        fit = min(self.width() / self.pix.width(), self.height() / self.pix.height())
        return min(1.0, ZoomView.MIN_SCALE / max(fit, 1e-6))

    def _clamp(self):
        """Let the image go anywhere it is dragged, as long as KEEP px of it (all of it, if smaller) stay in the pane."""
        v, s = self.view, self._scale()
        for axis, side, size in (("cx", self.width(), self.pix.width()), ("cy", self.height(), self.pix.height())):
            w = size * s  # the image's drawn size on this axis
            keep = min(self.KEEP, w)
            lo, hi = (keep - side / 2) / w, (side / 2 + w - keep) / w  # image edge at the far pane edge, minus keep
            setattr(v, axis, min(max(getattr(v, axis), lo), hi))

    def _image_rect(self):
        s = self._scale()
        w, h = self.pix.width() * s, self.pix.height() * s
        return QRectF(self.width() / 2 - self.view.cx * w, self.height() / 2 - self.view.cy * h, w, h)

    def _pan(self, dx, dy):
        s = self._scale()
        self.view.cx -= dx / (self.pix.width() * s)
        self.view.cy -= dy / (self.pix.height() * s)
        self._clamp()
        self.view.update()

    def wheelEvent(self, e):
        if self.pix.isNull():
            return super().wheelEvent(e)
        d = e.angleDelta()
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:  # some platforms turn Shift+wheel into x
            self._pan((d.y() or d.x()) / 120 * self.PAN_STEP, 0)
        elif d.y():
            v, pos, r = self.view, e.position(), self._image_rect()
            ix, iy = (pos.x() - r.x()) / r.width(), (pos.y() - r.y()) / r.height()  # image point under the cursor
            v.zoom = min(max(v.zoom * 1.25 ** (d.y() / 120), self._min_zoom()), ZoomView.MAX)
            s = self._scale()
            v.cx = ix - (pos.x() - self.width() / 2) / (self.pix.width() * s)
            v.cy = iy - (pos.y() - self.height() / 2) / (self.pix.height() * s)
            self._clamp()
            v.update()
        e.accept()

    def mousePressEvent(self, e):
        if not self.pix.isNull() and e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            d = e.position() - self._drag
            self._drag = e.position()
            self._pan(d.x(), d.y())

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, e):
        if not self.pix.isNull():
            self.view.reset()

    def resizeEvent(self, e):
        if not self.pix.isNull():
            self._clamp()

    def _chip(self, p, x, y, text, bg, fg="#e8ebe6"):
        p.setFont(font(12, 600))
        w = p.fontMetrics().horizontalAdvance(text) + 20
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(x, y, w, 24), 12, 12)
        p.setPen(qc(fg))
        p.drawText(QRectF(x, y, w, 24), Qt.AlignmentFlag.AlignCenter, text)
        return x + w + 6

    def _pred_box(self, p, x, y, rows, bg):
        """One rounded box, a line per (key, value, tone) as "key : value"; a dot in the tone's colour (None: no dot)
        marks a value that matches or contradicts the label. Returns the box's bottom."""
        key_font, val_font = font(12), font(12, 600)
        p.setFont(key_font)
        kw = max(p.fontMetrics().horizontalAdvance(k) for k, _, _ in rows)
        sep = p.fontMetrics().horizontalAdvance(" : ") if kw else 0
        p.setFont(val_font)
        vw = max(p.fontMetrics().horizontalAdvance(v) for _, v, _ in rows)
        dot = 14 if any(t for _, _, t in rows) else 0
        box = QRectF(x, y, 12 + dot + kw + sep + vw + 14, 8 + 20 * len(rows) + 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(box, 12, 12)
        for i, (k, v, tone) in enumerate(rows):
            line = QRectF(box.x() + 12, box.y() + 8 + 20 * i, box.width() - 24, 20)
            if tone:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qc(tone))
                p.drawEllipse(QPointF(line.x() + 4, line.center().y()), 4, 4)
            tx = line.x() + dot
            if k:
                p.setFont(key_font)
                p.setPen(qc("#b4b8b1"))
                p.drawText(QRectF(tx, line.y(), kw + sep, 20), Qt.AlignmentFlag.AlignVCenter, f"{k}")
                p.drawText(QRectF(tx + kw, line.y(), sep, 20), Qt.AlignmentFlag.AlignVCenter, " : ")
                tx += kw + sep
            p.setFont(val_font)
            p.setPen(qc("#ffffff"))
            p.drawText(QRectF(tx, line.y(), vw + 2, 20), Qt.AlignmentFlag.AlignVCenter, v)
        return box.bottom()

    def paintEvent(self, e):
        p = _aa(self)
        r = QRectF(self.rect())
        clip = QPainterPath()
        # round by the parent's rect: a pane filling half of it keeps square inner edges
        area = QRectF(self.parentWidget().rect()).translated(-QPointF(self.pos())) if self.parentWidget() else r
        clip.addRoundedRect(area, self.radius, self.radius)
        p.setClipPath(clip)
        if not self.pix.isNull():
            p.fillRect(r, qc("#ffffff"))
            # smooth when shrinking; nearest-neighbour when zoomed in so single pixels stay visible
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._scale() < 2)
            p.drawPixmap(self._image_rect(), self.pix, QRectF(self.pix.rect()))
            if self.view.zoom > 1:
                text = f"{self.view.zoom * 100:.0f}%"
                p.setFont(font(12, 600))
                self._chip(p, r.right() - 12 - (p.fontMetrics().horizontalAdvance(text) + 20), 12, text, qc("#0e0f0c", 0.7))
        else:
            p.fillRect(r, qc("#262724"))
            # 45° stripes, 14px wide
            p.save()
            p.translate(r.center())
            p.rotate(-45)
            span = int((r.width() + r.height()))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qc("#2e2f2c"))
            k = -span
            while k < span:
                p.drawRect(QRectF(k + 14, -span, 14, span * 2))
                k += 28
            p.restore()
            cy = r.center().y() - (30 if self.video else 0)
            p.setFont(font(14, 600, mono=True))
            p.setPen(qc("#b4b8b1"))
            p.drawText(QRectF(0, cy - 24, r.width(), 20), Qt.AlignmentFlag.AlignCenter, self.name)
            p.setFont(font(13))
            p.setPen(qc("#868685"))
            p.drawText(QRectF(0, cy + 4, r.width(), 18), Qt.AlignmentFlag.AlignCenter, self.meta)
            if self.video:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qc("#9fe870"))
                c = QPointF(r.center().x(), cy + 58)
                p.drawEllipse(c, 28, 28)
                tri = QPainterPath()
                tri.moveTo(c.x() - 5, c.y() - 9)
                tri.lineTo(c.x() + 9, c.y())
                tri.lineTo(c.x() - 5, c.y() + 9)
                tri.closeSubpath()
                p.fillPath(tri, qc("#0e0f0c"))
        chip = qc("#0e0f0c", 0.7)  # readable over the white background and over any image
        if self.kind == "raw":
            self._chip(p, 12, 12, f"label: {self.label}", chip)
        elif self.kind == "inference":
            pr = self.pred
            below = self._pred_box(p, 12, 12, pr["chips"], chip) if pr["chips"] else 12
            if not pr["top"]:
                return
            # Top-3 panel
            pw = min(300, r.width() - 24)
            box = QRectF(12, below + 8, pw, 10 + 14 + 6 + 3 * 22 + 4)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qc("#0e0f0c", 0.82))
            p.drawRoundedRect(box, 10, 10)
            p.setFont(font(11))
            p.setPen(qc("#868685"))
            p.drawText(QRectF(box.x() + 12, box.y() + 10, pw - 24, 14), Qt.AlignmentFlag.AlignLeft, pr.get("source", "Top-3"))
            p.drawText(QRectF(box.x() + 12, box.y() + 10, pw - 24, 14), Qt.AlignmentFlag.AlignRight, pr["ms"])
            for i, (c, prob) in enumerate(pr["top"]):
                y = box.y() + 30 + i * 22
                p.setFont(font(12))
                p.setPen(qc("#e8ebe6"))
                p.drawText(QRectF(box.x() + 12, y, 84, 16), Qt.AlignmentFlag.AlignVCenter, c)
                p.drawText(QRectF(box.right() - 52, y, 40, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{prob:.2f}")
                bx, bw = box.x() + 12 + 92, pw - 24 - 92 - 48
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qc("#30312e"))
                p.drawRoundedRect(QRectF(bx, y + 5, bw, 6), 3, 3)
                p.setBrush(qc("#e8ebe6"))
                p.drawRoundedRect(QRectF(bx, y + 5, max(6, bw * prob), 6), 3, 3)
