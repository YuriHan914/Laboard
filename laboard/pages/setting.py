"""Setting: load a laboard .toml project file, preview it, show what was detected."""
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog

from .. import store, theme
from ..widgets import Box, Button, Flow, HLine, Label, LineEdit, Scroll, Segmented, badge, breakable, card, hbox, vbox, wrap


def _toml_lines(lines):
    out = []
    for i, text in enumerate(lines, 1):
        t = text.strip()
        head = t.startswith("[") and t.endswith("]")
        num = Label(str(i), 13.5, 400, "mute", mono=True, align=Qt.AlignmentFlag.AlignRight, lh=23)
        num.setFixedWidth(34)
        line = Label(breakable(text or " "), 13.5, 600 if head else 400, mono=True, wrap=True)  # wraps when narrow
        line.setMinimumHeight(23)
        row = hbox(num, 18, (line, 1))
        row.setAlignment(num, Qt.AlignmentFlag.AlignTop)
        out.append(row)
    return out


def build(app):
    path = store.PROJECT.get("toml", "")
    path_edit = LineEdit("Choose a laboard .toml project file", size=15, pad=(11, 16), mono=True)
    path_edit.setFixedHeight(Button.height_for("md"))  # same height as Browse / Load so the row lines up
    path_edit.setText(app.s.pending_toml if app.s.pending_toml is not None else path)
    path_edit.textChanged.connect(lambda t: setattr(app.s, "pending_toml", t))  # survives re-renders until loaded

    def browse():
        """Only fill in the path; loading waits for Load."""
        f, _ = QFileDialog.getOpenFileName(app, "Choose project file", os.path.dirname(path_edit.text()),
                                           "Laboard project (*.toml)")
        if f:
            path_edit.setText(f)

    def load_typed():
        f = path_edit.text().strip()
        if not f:
            app.status("Choose a project file first (Browse)")
        elif not f.endswith(".toml"):
            app.status(f"Not a .toml file: {f}")
        else:
            app.load_project(f)

    path_edit.returnPressed.connect(load_typed)
    load = card(
        Label("Load project file", 32, 900, display=True, spacing=-0.5), 10,
        Label("A project file tells Laboard where your data, models, runs and logs live, and which git repo to track.",
              14, 400, "body", wrap=True), 18,
        Label("Project file", 14, 600, lh=20), 8,
        # field and buttons share one row of equal height, so their tops and bottoms line up
        hbox((path_edit, 1), 12, Button("Browse", size="md", on_click=browse), 12,
             Button("Load", "primary", "md", on_click=load_typed), align=Qt.AlignmentFlag.AlignVCenter),
        pad=(32, 28, 32, 28))

    name = os.path.basename(path) or "Project file"
    preview = vbox(hbox(Label(name, 16, 600, lh=24), "stretch", Label("Read-only preview", 12, 400, "mute"),
                        margins=(24, 4, 24, 10)), margins=(0, 14, 0, 14))
    for row in _toml_lines(store.TOML):
        preview.addLayout(row)
    if not store.TOML:
        none = Label("No project file loaded.", 13, 400, "mute")
        none.setContentsMargins(24, 0, 24, 0)
        preview.addWidget(none)
    preview.addStretch(1)

    det = vbox(Label("Detected", 16, 600, lh=24), 10)
    for k, v, tone, status in store.DETECTED:
        tag = badge(status, tone)
        row = hbox((vbox(Label(k, 14, 600, lh=20), 2, Label(breakable(v), 12, 400, "body", mono=True, wrap=True)), 1), 12, tag,
                   margins=(0, 8, 0, 8))
        row.setAlignment(tag, Qt.AlignmentFlag.AlignVCenter)  # only the badge: a centred row would keep one line's height
        det.addLayout(row)
        det.addWidget(HLine())
    if not store.DETECTED:
        det.addWidget(Label("Load a project file to see what Laboard finds.", 13, 400, "mute", wrap=True))
    look = card(Label("Appearance", 16, 600, lh=24), 12,
                hbox(Segmented([("light", "Light"), ("dark", "Dark")], theme.current, lambda k: app.set(theme=k),
                               size=14, pad=(7, 20), outer=4, gap=4), "stretch"), pad=(24, 20, 24, 20))
    lower = Flow()  # the Detected / Appearance column moves under the preview when the centre is narrow
    lower.add(Box(bg="surf", radius=16, layout=preview), 420, 6)
    lower.add(vbox(card(det, pad=(24, 20, 24, 20)), 12, look, "stretch"), 340, 5)
    return Scroll(wrap(vbox(load, 12, lower, "stretch")))
