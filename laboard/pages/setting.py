import os
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFileDialog, QLineEdit, QStyle

from .. import store, theme, tomledit
from ..newproject import CreateProject
from ..widgets import (Box, Button, Combo, Flow, HLine, Label, LineEdit, Scroll, Segmented, Select, badge, breakable, card,
                       hbox, set_tip, vbox, wrap)

ROW_H = Button.height_for("sm")


def _toml_lines(lines):
    out = []
    for i, text in enumerate(lines, 1):
        t = text.strip()
        head = t.startswith("[") and t.endswith("]")
        num = Label(str(i), 13.5, 400, "mute", mono=True, align=Qt.AlignmentFlag.AlignRight, lh=23)
        num.setFixedWidth(34)
        line = Label(breakable(text or " "), 13.5, 600 if head else 400, mono=True, wrap=True)
        line.setMinimumHeight(23)
        row = hbox(num, 18, (line, 1))
        row.setAlignment(num, Qt.AlignmentFlag.AlignTop)
        out.append(row)
    return out


def _show(v):
    if v is None:
        return ""
    return v if isinstance(v, str) else tomledit.written(v)


def _is_path(sec, key, v):
    s, k = tomledit.canon(sec), key.lower()
    return s == "paths" or k in ("root", "file_path") or (s == "prediction" and k == "path") or \
        (isinstance(v, str) and v.startswith(("/", "~", "./", "../")))


def _wants_file(sec, key, v, cfg):
    s, k = tomledit.canon(sec), key.lower()
    if s == "paths" or k == "root":
        return False
    if k in ("file_path", "path") and s in ("data", "prediction"):
        kind = str(cfg.get(s, {}).get("type") or "").lower()
        if kind == "csv":
            return True
    p = Path(str(v or "")).expanduser()
    return p.is_file() or bool(p.suffix)


def _input(app, sec, key, orig, cfg, toml, draft):
    opts = tomledit.enum(sec, key) or ((True, False) if isinstance(orig, bool) else None)
    if opts:
        same = next((o for o in opts if isinstance(o, str) and isinstance(orig, str) and o.lower() == orig.lower()), orig)
        opts = list(opts) + [v for v in (same,) if v is not None and v not in opts]
        by_key = {_show(o): o for o in opts}
        box = Combo([("", "")] + [(k, k) for k in by_key], _show(same) if same is not None else "",
                    lambda k: draft.update(value=by_key.get(k)), size=14)
        box.setFixedHeight(ROW_H)
        return box
    edit = LineEdit(f"{sec}.{key}" if sec else key, size=13.5, mono=True)
    edit.setFixedHeight(ROW_H)
    edit.setText("" if orig is None else _show(orig))
    typed = str if isinstance(orig, str) or orig is None else tomledit.Raw
    edit.textChanged.connect(lambda text: draft.update(value=typed(text)))
    if _is_path(sec, key, orig):
        def pick():
            cur = Path(os.path.expanduser(edit.text().strip() or "."))
            start = str(cur if cur.is_dir() else cur.parent if cur.parent.is_dir() else Path(toml).parent)
            if _wants_file(sec, key, edit.text(), cfg):
                f, _ = QFileDialog.getOpenFileName(app, f"Choose {sec}.{key}", start)
            else:
                f = QFileDialog.getExistingDirectory(app, f"Choose {sec}.{key}", start)
            if f:
                edit.setText(f)
        icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        act = edit.addAction(icon, QLineEdit.ActionPosition.TrailingPosition)
        act.setToolTip("Choose from the file system")
        act.triggered.connect(pick)
    return edit


def _save(app, sec, key, orig, toml, value, error):
    if (value == orig and type(value) is type(orig)) or (orig is None and value in (None, "")):
        return True
    try:
        text = tomledit.save("\n".join(store.TOML), {(sec, key): value})
    except Exception as e:
        error.setText(f"Not applied: {e}")
        error.show()
        return False
    app.load_project(toml, app.s.view_commit, text)
    return True


def _edit(app, sec, key, orig, cfg, toml):
    draft = dict(value=orig)
    field = _input(app, sec, key, orig, cfg, toml, draft)
    error = Label("", 12, 400, "#d03238", wrap=True)
    error.hide()
    shown = tomledit.title(key)
    where = f"[{tomledit.title(sec)}] {shown}" if sec else shown
    pick = " Type it, or pick one with the folder icon." if not isinstance(field, Combo) and _is_path(sec, key, orig) else ""
    dialog = None

    def save():
        if _save(app, sec, key, orig, toml, draft["value"], error):
            dialog.close()

    dialog = app.show_dialog(f"Edit {shown}", f"{where} · {tomledit.describe(sec, key)}{pick}", vbox(field, 8, error),
                             [("Cancel", "secondary", None), ("Save", "primary", save)])
    if isinstance(field, LineEdit):
        field.returnPressed.connect(save)
    field.setFocus()


def _save_as(app, toml):
    src = Path(toml)
    f, _ = QFileDialog.getSaveFileName(app, "Save edited project file", str(src.with_name(f"{src.stem}_edited.toml")),
                                       "Laboard project (*.toml)")
    if not f:
        return
    f = Path(f if f.endswith(".toml") else f + ".toml")
    if f.resolve() == src.resolve():
        app.status(f"Not saved: {src.name} is the loaded project file; it is never overwritten. Choose another name.")
        return
    f.write_text("\n".join(store.TOML) + "\n")
    app.load_project(str(f))


def _hidden(sec, key, cfg):
    s, k = tomledit.canon(sec), key.lower()
    if s not in ("data", "label", "prediction"):
        return False
    kind = str(cfg.get(s, {}).get("type") or "").lower()
    return (k == "table" and kind != "db") or (k == "file_path" and kind == "db")


def _fields(app, toml):
    try:
        text = "\n".join(store.TOML)
        sections, cfg = tomledit.fields(text), tomledit.normalize(tomledit.parse(text))
    except Exception as e:
        return vbox(Label(f"Can't read the project file: {e}", 13, 400, "mute", wrap=True), margins=(24, 0, 24, 0))
    body = vbox(margins=(24, 0, 24, 0))
    for sec, items in sections:
        if tomledit.canon(sec) == "db" and cfg.get("project", {}).get("db") is not True:
            continue
        body.addSpacing(10)
        body.addWidget(Label(f"[{tomledit.title(sec)}]" if sec else "Top level", 14, 600, mono=bool(sec), lh=22))
        body.addSpacing(4)
        for key, orig in items:
            if _hidden(sec, key, cfg):
                continue
            shown = tomledit.title(key)
            name = Label(shown, 13.5, 400, "body", mono=True)
            name.setFixedWidth(150)
            value = Label(breakable(_show(orig)), 13.5, 400, "mute" if orig is None else "ink", mono=True, wrap=True)
            value.setMinimumHeight(ROW_H)
            for w in (name, value):
                set_tip(w, f"{tomledit.title(sec)}.{shown}" if sec else shown, tomledit.describe(sec, key))
            edit = Button("Edit", on_click=lambda _checked=False, s=sec, k=key, o=orig: _edit(app, s, k, o, cfg, toml))
            body.addLayout(hbox(name, 12, (value, 1), 12, edit, margins=(0, 6, 0, 6), align=Qt.AlignmentFlag.AlignVCenter))
            body.addWidget(HLine())
    return body


def _keep_scroll(app, scroll):
    bar = scroll.verticalScrollBar()
    want = app.s.setting_scroll
    state = dict(done=not want)

    def ranged(_lo, hi):
        if not state["done"] and hi > 0:
            bar.setValue(min(want, hi))
            state["done"] = hi >= want

    def moved(value):
        if state["done"]:
            app.s.setting_scroll = value

    bar.rangeChanged.connect(ranged)
    bar.valueChanged.connect(moved)
    QTimer.singleShot(500, lambda: state.update(done=True))
    return scroll


def _new(app):
    app.dialog = CreateProject(app)
    app.dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    app.dialog.open()


def build(app):
    path = store.PROJECT.get("toml", "")
    path_edit = LineEdit("Choose a laboard .toml project file", size=15, pad=(11, 16), mono=True)
    path_edit.setFixedHeight(Button.height_for("md"))
    path_edit.setText(app.s.pending_toml if app.s.pending_toml is not None else path)
    path_edit.textChanged.connect(lambda t: setattr(app.s, "pending_toml", t))

    def browse():
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
        Label("A project file tells Laboard where your data, models, runs and logs live, and which git repo to track. "
              "New makes one from a form of every section.", 14, 400, "body", wrap=True), 18,
        Label("Project file", 14, 600, lh=20), 8,
        hbox((path_edit, 1), 12, Button("Browse", "outline", "md", on_click=browse, min_width=110), 12,
             Button("Load", "sage", "md", on_click=load_typed, min_width=110), 12,
             Button("New", "solid", "md", on_click=lambda: _new(app), min_width=110),
             align=Qt.AlignmentFlag.AlignVCenter),
        pad=(32, 28, 32, 28))

    name = os.path.basename(path) or "Project file"
    view = app.s.toml_view if store.TOML else "text"
    modes = Segmented([("fields", "Fields"), ("text", "Text")], view, lambda k: app.set(toml_view=k),
                      size=12, pad=(4, 12)) if store.TOML else Label("", 12)
    edited = store.PROJECT.get("edited")
    note = Label(f"Edited · {name} on disk is unchanged · Load to go back", 12, 400, "mute", wrap=True) if edited else None
    save = Button("Save Changed", "primary", on_click=lambda: _save_as(app, path)) if edited else None
    preview = vbox(hbox(Label(name, 16, 600, lh=24), 12, (note, 1) if note else "stretch", 12, save, 8 if save else 0, modes,
                        margins=(24, 4, 24, 10), align=Qt.AlignmentFlag.AlignVCenter), margins=(0, 14, 0, 14))
    if view == "fields":
        preview.addLayout(_fields(app, path))
    else:
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
        row.setAlignment(tag, Qt.AlignmentFlag.AlignVCenter)
        det.addLayout(row)
        det.addWidget(HLine())
    if not store.DETECTED:
        det.addWidget(Label("Load a project file to see what Laboard finds.", 13, 400, "mute", wrap=True))
    look = card(Label("Appearance", 16, 600, lh=24), 12,
                hbox(Segmented([("light", "Light"), ("dark", "Dark")], theme.current, lambda k: app.set(theme=k),
                               size=14, pad=(7, 20), outer=4, gap=4), "stretch"), pad=(24, 20, 24, 20))
    rows = Select([(n, str(n)) for n in store.TABLE_ROWS], app.s.table_rows, lambda n: app.set(table_rows=n))
    tables = Box(bg="surf", radius=16, layout=hbox(
        (vbox(Label("Items per page", 16, 600, lh=24), Label("How many rows Result and Hyperparameter tables show at once",
                                                             13, 400, "body", lh=20, wrap=True)), 1), 16, rows,
        margins=(24, 20, 24, 20), align=Qt.AlignmentFlag.AlignVCenter))
    lower = Flow()
    lower.add(Box(bg="surf", radius=16, layout=preview), 420, 6)
    lower.add(vbox(card(det, pad=(24, 20, 24, 20)), 12, look, 12, tables, "stretch"), 340, 5)
    return _keep_scroll(app, Scroll(wrap(vbox(load, 12, lower, "stretch"))))
