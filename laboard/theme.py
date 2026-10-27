from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

WISE_GREEN = "#9fe870"
WISE_GREEN_PALE = "#e2f6d5"
WISE_GREEN_ACTIVE = "#cdffad"
SAGE, SAGE_HOVER = "#e8ebe6", "#d9ddd6"
INK = "#0e0f0c"
CANVAS = "#ffffff"
CANVAS_SOFT = "#e8ebe6"
POSITIVE = "#2ead4b"
POSITIVE_DEEP = "#054d28"
WARNING = "#ffd11a"
WARNING_DEEP = "#b86700"
WARNING_CONTENT = "#4a3b1c"
NEGATIVE = "#d03238"
NEGATIVE_BG = "#320707"
NEGATIVE_DARKEST = "#a7000d"

PALETTES = {
    "light": dict(bg="#e8ebe6", surf="#ffffff", surf2="#e8ebe6", ink="#0e0f0c", body="#454745",
                  mute="#868685", line="#e8ebe6", sel="#e2f6d5", selfg="#0e0f0c", brand="#0e0f0c",
                  tab="#0e0f0c", tabfg="#ffffff", grid="#d4d8d1", c2="#38c8ff", c3="#b86700",
                  stage="#ffffff"),
    "dark": dict(bg="#0e0f0c", surf="#1a1b18", surf2="#262724", ink="#e8ebe6", body="#b4b8b1",
                 mute="#868685", line="#2a2b28", sel="#163300", selfg="#9fe870", brand="#9fe870",
                 tab="#e8ebe6", tabfg="#0e0f0c", grid="#30312e", c2="#38c8ff", c3="#ffc091",
                 stage="#0e0f0c"),
}


class _Palette(dict):
    __getattr__ = dict.__getitem__


T = _Palette(PALETTES["light"])
current = "light"


def set_theme(name):
    global current
    current = name
    T.clear()
    T.update(PALETTES[name])


def qc(color, alpha=None):
    c = QColor(color)
    if alpha is not None:
        c.setAlphaF(alpha)
    return c


BODY_FAMILY = "Inter"
DISPLAY_FAMILY = "Figtree"
MONO_FAMILY = "monospace"

FONT_DIR = Path(__file__).parent / "assets" / "fonts"
LOGO_SVG = Path(__file__).parent / "assets" / "logo" / "laboard_splash.svg"


def logo_icon():
    icon = QIcon()
    for size in (64, 256, 1024):
        icon.addPixmap(logo_pixmap(size))
    return icon


def logo_pixmap(px, dpr=1.0):
    side = round(px * dpr)
    pix = QPixmap(side, side)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(LOGO_SVG)).render(p)
    p.end()
    pix.setDevicePixelRatio(dpr)
    return pix


def load_fonts():
    global BODY_FAMILY, DISPLAY_FAMILY, MONO_FAMILY
    loaded = set()
    for f in FONT_DIR.iterdir():
        fid = QFontDatabase.addApplicationFont(str(f))
        if fid >= 0:
            loaded.update(QFontDatabase.applicationFontFamilies(fid))
    families = set(QFontDatabase.families())
    if "Inter" not in loaded:
        BODY_FAMILY = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    if "Figtree" not in loaded:
        DISPLAY_FAMILY = BODY_FAMILY
    for name in ("JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "Menlo"):
        if name in families:
            MONO_FAMILY = name
            break
    else:
        MONO_FAMILY = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()


def font(size=14, weight=400, mono=False, display=False, spacing=0.0):
    f = QFont(MONO_FAMILY if mono else DISPLAY_FAMILY if display else BODY_FAMILY)
    f.setPixelSize(round(size))
    f.setWeight(QFont.Weight(weight))
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f
