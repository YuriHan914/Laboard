import logging
import os

from PyQt6.QtCore import QCoreApplication, Qt, QUrl
from PyQt6.QtGui import QColor

from . import theme

try:
    import netron
    from PyQt6 import sip
    from PyQt6.QtWebEngineCore import QWebEngineScript
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

logging.getLogger("netron").setLevel(logging.WARNING)
_view, _path, _address = None, None, None
_win = None
SIDEBAR_FONT_PX = 14
SIDEBAR_WIDTH = 0.7


def prepare():
    if AVAILABLE:
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


def url():
    return f"http://{_address[0]}:{_address[1]}" if _address else ""


def _new_view(parent=None):
    v = QWebEngineView(parent)
    script = QWebEngineScript()
    script.setName("laboard-sidebar-size")
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
    script.setSourceCode(f"""(() => {{ const s = document.createElement('style');
        s.textContent = '.sidebar {{ zoom: {SIDEBAR_FONT_PX / 11:.4f}; '
            + 'width: calc(min(calc(100% * 0.6), 42em) * {SIDEBAR_WIDTH}) !important; }}';
        document.head.appendChild(s); }})();""")
    v.page().scripts().insert(script)
    v.loadFinished.connect(lambda ok: _apply_theme(v))
    return v


def _apply_theme(v):
    dark = theme.current == "dark"
    v.page().setBackgroundColor(QColor(theme.T.stage))
    v.page().runJavaScript(f"""(dark => {{
        const seen = window.laboardDark = window.laboardDark || new Set();
        for (const sheet of document.styleSheets) {{
            let rules;
            try {{ rules = sheet.cssRules; }} catch (e) {{ continue; }}
            for (const r of rules)
                if (r.media && (seen.has(r) || r.media.mediaText.includes('prefers-color-scheme: dark'))) {{
                    seen.add(r);
                    r.media.mediaText = dark ? 'all' : 'not all';
                }}
        }}
        let s = document.getElementById('laboard-stage');
        if (!s && document.head) {{
            s = document.createElement('style');
            s.id = 'laboard-stage';
            document.head.appendChild(s);
        }}
        if (s) s.textContent = '.default, .target, .welcome {{ background-color: {theme.T.stage} !important; }}';
    }})({'true' if dark else 'false'});""")


def attach(win):
    global _view, _win
    _win = win
    if AVAILABLE and _view is None:
        _view = _new_view(win)
        _view.load(QUrl("about:blank"))
        _stow(_view)


def _stow(v):
    v.setGeometry(0, 0, 1, 1)
    v.show()
    v.lower()


def park(win):
    if _view is not None and not sip.isdeleted(_view) and _view.parent() is not win:
        _view.setParent(win)
        _stow(_view)


def view(path):
    global _view, _path, _address
    if _view is None or sip.isdeleted(_view):
        _view, _path = _new_view(_win), None
    if path != _path:
        if _address:
            netron.stop(_address)
        _address = netron.serve(path, address=("localhost", 0), browse=False)
        _path = path
        _view.load(QUrl(url()))
    _apply_theme(_view)
    _view.show()
    return _view
