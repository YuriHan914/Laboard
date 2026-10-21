"""Netron inside the Model page: a local netron server for the selected file, shown in a web view.

Netron parses models in JavaScript (ONNX, PyTorch, safetensors, Flax, TensorRT, Keras, TFLite, ...),
so nothing here needs a GPU, CUDA or a matching TensorRT. ``netron`` and ``PyQt6-WebEngine`` are
optional: without them ``AVAILABLE`` is False and the Model page says what to install.
"""
import logging
import os

from PyQt6.QtCore import QCoreApplication, Qt, QUrl

try:
    import netron
    from PyQt6 import sip
    from PyQt6.QtWebEngineCore import QWebEngineScript
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # must be imported before QApplication exists
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

logging.getLogger("netron").setLevel(logging.WARNING)  # netron logs every request at INFO
_view, _path, _address = None, None, None
SIDEBAR_FONT_PX = 14  # netron's detail panel uses 11px item text; scale the whole panel so 11px becomes this
SIDEBAR_WIDTH = 0.7  # of netron's own panel width (min(60%, 42em), set inline when the panel opens)


def prepare():
    """Call before creating QApplication: WebEngine needs shared GL contexts; software rendering keeps it GPU-free."""
    if AVAILABLE:
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


def url():
    return f"http://{_address[0]}:{_address[1]}" if _address else ""


def _new_view(parent=None):
    """A web view that styles every netron page it loads (the installed netron files stay untouched)."""
    v = QWebEngineView(parent)
    script = QWebEngineScript()
    script.setName("laboard-sidebar-size")
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
    # zoom, not font-size: names, widths and padding grow together so the panel layout holds.
    # The width rule needs !important to beat the inline width netron sets each time the panel opens.
    script.setSourceCode(f"""(() => {{ const s = document.createElement('style');
        s.textContent = '.sidebar {{ zoom: {SIDEBAR_FONT_PX / 11:.4f}; '
            + 'width: calc(min(calc(100% * 0.6), 42em) * {SIDEBAR_WIDTH}) !important; }}';
        document.head.appendChild(s); }})();""")
    v.page().scripts().insert(script)
    return v


def attach(win):
    """Create the one web view as a hidden child of ``win`` before it is first shown. Adding the first web view
    to a window that is already on screen makes Qt recreate the native window (the app flickers and seems to
    restart), so this happens up front, once."""
    global _view
    if AVAILABLE and _view is None:
        _view = _new_view(win)
        _view.load(QUrl("about:blank"))  # creates the GL child that makes Qt pick the window's surface type
        _stow(_view)


def _stow(v):
    """Keep the view visible but 1×1 under the page: hiding it could let Qt switch the window back."""
    v.setGeometry(0, 0, 1, 1)
    v.show()
    v.lower()


def park(win):
    """Before a page is torn down: take the view out of it (back onto ``win``, stowed) so it isn't deleted
    with the page and doesn't reload when the Model tab comes back."""
    if _view is not None and not sip.isdeleted(_view) and _view.parent() is not win:
        _view.setParent(win)
        _stow(_view)


def view(path):
    """The web view showing ``path``: the same widget every time (see attach / park); it reloads only when
    another file is chosen, and the previous file's server is stopped."""
    global _view, _path, _address
    if _view is None or sip.isdeleted(_view):
        _view, _path = _new_view(), None
    if path != _path:
        if _address:
            netron.stop(_address)
        _address = netron.serve(path, address=("localhost", 0), browse=False)
        _path = path
        _view.load(QUrl(url()))
    _view.show()
    return _view
