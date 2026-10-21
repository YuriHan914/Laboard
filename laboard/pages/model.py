"""Model: the selected model file in Netron, with properties and parameters read from the file."""
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices

from .. import modelinfo, netronview, sidebar, store, torchgraph
from ..charts import Meter
from ..widgets import Box, Button, Label, Scroll, Segmented, card, empty_state, hbox, stat_tile, vbox, wrap


def _graph_card(app, sel, path, fmt):
    head = hbox(Label(fmt, 13, 400, "body"), 12, (Label(sel, 16, 600, lh=24, elide=True), 1),
                margins=(20, 14, 20, 14), align=Qt.AlignmentFlag.AlignVCenter)
    note = None
    if netronview.AVAILABLE and torchgraph.is_pickle(path):
        # a torch.save checkpoint has no wiring: by default draw its modules in registration order instead
        head.addWidget(Segmented([("inferred", "Layer sequence"), ("stored", "As stored")], app.s.pt_view,
                                 lambda k: app.set(pt_view=k)))
        head.addSpacing(12)
        if app.s.pt_view == "inferred":
            built = torchgraph.build(path)
            if built:
                path = str(built)
                note = Label("Layer types are inferred from tensor names and shapes, in the order the modules were "
                             "registered. Checkpoints don't store how layers connect, so branches and skips aren't shown.",
                             12, 400, "mute", wrap=True)
                note.setContentsMargins(20, 0, 20, 10)
    if fmt.startswith("TensorRT"):  # engines are compiled for one TensorRT build; netron can't list their layers
        msg = Label("TensorRT engines are compiled for one TensorRT version and GPU, so their layers can't be read "
                    "without that runtime. Open the ONNX file the engine was built from to see the graph.", 28, 400,
                    "body", align=Qt.AlignmentFlag.AlignCenter, wrap=True)
        graph = Box(bg="bg", radius=12, layout=vbox("stretch", msg, "stretch", margins=(64, 24, 64, 24)))
    elif netronview.AVAILABLE:
        graph = netronview.view(path)
        head.addWidget(Button("Open in browser", on_click=lambda: QDesktopServices.openUrl(QUrl(netronview.url()))))
    else:
        note = Label("Install netron and PyQt6-WebEngine to see the model graph: pip install -r requirements.txt", 14, 400,
                     "body", align=Qt.AlignmentFlag.AlignCenter, wrap=True)
        graph = Box(bg="bg", radius=12, layout=vbox("stretch", note, "stretch", margins=(24, 24, 24, 24)))
    return Box(bg="surf", radius=16, layout=vbox(head, *([note] if note else []), (hbox(graph, margins=(12, 0, 12, 12)), 1)))


def _props(file_info, meta):
    tiles = hbox(*[stat_tile(k, v, value_size=22, lh=30) for k, v in meta["stats"] + file_info["stats"]], spacing=10)
    body = vbox(Label("Model properties", 16, 600, lh=24), 12, tiles, 12)
    for k, v in meta["props"] + file_info["props"]:
        body.addLayout(hbox(Label(k, 13, 400, "body"), 12, (Label(v, 13, mono=True, elide=True, align=Qt.AlignmentFlag.AlignRight), 1),
                            margins=(0, 5, 0, 5)))
    return card(body)


def _layers(layers):
    biggest = max(n for _, n in layers) or 1
    body = vbox(Label("Parameters by layer", 16, 600, lh=24), 10)
    for name, n in layers:
        val = Label(modelinfo.count(n), 13, align=Qt.AlignmentFlag.AlignRight)
        val.setFixedWidth(60)
        nl = Label(name, 13)
        nl.setFixedWidth(130)
        nl.setText(nl.fontMetrics().elidedText(name, Qt.TextElideMode.ElideMiddle, 130))
        nl.setToolTip(name)
        body.addLayout(hbox(nl, 10, (Meter(max(1, n / biggest * 100), 8), 1), 10, val, margins=(0, 4, 0, 4),
                            align=Qt.AlignmentFlag.AlignVCenter))
    return card(body)


def build(app):
    sel = app.s.sel["model"]
    if sel not in store.MODEL_INFO:
        return empty_state("No models", "Load a project file in Setting. Model files under its paths.models show up here.")
    file_info = store.MODEL_INFO[sel]
    meta = modelinfo.inspect(file_info["path"])
    fmt = dict(meta["props"]).get("Format", "")
    side = vbox(_props(file_info, meta))
    if meta["layers"]:
        side.addSpacing(12)
        side.addWidget(_layers(meta["layers"]))
    side.addStretch(1)
    side = Scroll(wrap(side))
    side.setFixedWidth(sidebar.WIDTH)  # as wide as the left panel
    return _graph_card(app, sel, file_info["path"], fmt), side
