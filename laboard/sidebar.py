from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QSizePolicy, QWidget

from . import store
from .theme import font
from .widgets import (Box, Button, Chevron, Dot, FolderIcon, Label, LineEdit, Pill, Scroll, Segmented, card, clear_layout,
                      col, hbox, vbox, wrap)


def _open_folder(app, path):
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path(store.PROJECT.get("path", "")).expanduser() / p
    if p.is_dir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
    else:
        app.status(f"Folder not found: {p}")


TREE_TABS = ("model", "hyperparameter", "result")


def _items(app):
    s, tab = app.s, app.s.tab
    if tab == "home":
        return ("Root folders", f"{len(store.ROOT_FOLDERS)} folders", "Filter folders",
                [dict(label=n, meta=m, kind="root", path=p) for n, m, p in store.ROOT_FOLDERS])
    if tab == "data":
        if s.folder not in store.DATA_FOLDERS:
            return "Files", "", "Filter files", []
        fd = store.DATA_FOLDERS[s.folder]
        rows = []
        for i, n in enumerate(fd["files"]):
            sp = store.split_of(s.folder, i)
            if s.split_filter in ("all", sp):
                rows.append(dict(label=n, ext=fd["ext"], dot=store.SPLITS[sp][1], meta=store.SPLITS[sp][0]))
        return "Files", f"{len(rows)} of {fd['n']} · {s.folder}/", "Filter files", rows
    if tab in ("model", "result"):
        files = store.MODEL_FILES if tab == "model" else store.RESULT_FILES
        title = "Model files" if tab == "model" else "Result files"
        return title, f"{len(files):,} file{'s' if len(files) != 1 else ''}", "Filter files", [
            dict(key=key, label=Path(key).name, ext=ext, meta=size, folder=folder) for key, ext, size, folder in files]
    if tab == "hyperparameter":
        return "Hyperparameter", f"{len(store.RUNS)} set{'s' if len(store.RUNS) != 1 else ''}", "Filter sets", [
            dict(key=n, label=Path(n).name, meta=m, folder=str(Path(n).parent) if "/" in n else "") for n, m in store.RUNS]
    return "Recent projects", "", "Filter projects", [dict(label=n, meta=m, ext="TOML") for n, m in store.RECENT_PROJECTS]


def _row(app, it):
    s, tab = app.s, app.s.tab
    kind = it.get("kind", "file")
    key = it.get("key", it["label"])
    sel = kind == "file" and key == s.sel[tab]
    pad_left = 10 + it.get("depth", 0) * 14
    lay = hbox(spacing=8, margins=(pad_left, 6, 10, 6))
    if kind == "folder" and "path" in it:
        lay.addWidget(Chevron("ink", 90 if it["open"] else 0))
    if it.get("dot"):
        lay.addWidget(Dot(it["dot"], 8))
    if kind == "root":
        lay.addWidget(FolderIcon())
    if it.get("ext"):
        tag = Pill(it["ext"], "surf2", "body", size=10, pad=(1, 4), mono=True, radius=4)
        tag.setMinimumWidth(38)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(tag)
    weight = 600 if kind == "folder" or sel else 400
    color = "body" if kind == "folder" else "selfg" if sel else "ink"
    name = Label(it["label"], 14, weight, color, elide=True)
    lay.addWidget(name, 1)
    if it.get("meta"):
        meta = Label(it["meta"], 12, 400, "mute", elide=kind == "root", align=Qt.AlignmentFlag.AlignRight)
        if kind == "root":
            meta.setMaximumWidth(120)
        lay.addWidget(meta)
    if kind == "root":
        lay.addWidget(Button("Open", compact=True, on_click=lambda: _open_folder(app, it["path"])))
    if kind == "folder":
        on_click = (lambda: app.toggle_dir(tab, it["path"])) if "path" in it else None
    else:
        on_click = None if kind == "root" else lambda: app.pick(tab, key)
    row = Box(bg="sel" if sel else None, radius=10, layout=lay, on_click=on_click,
              hover=None if sel or on_click is None else "surf2")
    row.setMinimumHeight(34)
    row.key = key if kind == "file" else None
    row.name = name
    return row


def _project_card(app):
    def kv(k, v, mono=False):
        return k, Label(v, 12 if mono else 13, 400, "ink", mono=mono, elide=True)

    grid_rows = [kv("Remote", store.PROJECT["remote"], True), kv("Branch", store.PROJECT["branch"]),
                 kv("Commits", store.PROJECT["commits"]), kv("Hyperparameter sets", store.PROJECT["runs_linked"])]
    rows = vbox(spacing=6, margins=(0, 12, 0, 0))
    for k, w in grid_rows:
        kl = Label(k, 13, 400, "body", lh=20)
        kl.setFixedWidth(96)
        rows.addLayout(hbox(kl, 12, (w, 1)))
    name = Label(store.PROJECT["name"], 20, 600, spacing=-0.4, lh=28)
    return card(Label("Project", 13, 400, "body", lh=20),
                hbox(name, 8, *([Pill(app.task, "sel", "selfg", pad=(3, 10))] if app.task else []), "stretch",
                     align=Qt.AlignmentFlag.AlignVCenter),
                rows, pad=(18, 18, 18, 16))


def _folders_card(app):
    s = app.s
    body = vbox(hbox(Label("Folders", 16, 600, lh=24), "stretch", Label(f"{len(store.DATA_FOLDERS)} · data/", 12, 400, "mute"),
                     margins=(10, 0, 10, 8)))
    rows = vbox()
    for name, fd in store.DATA_FOLDERS.items():
        on = name == s.folder
        lay = hbox(FolderIcon("selfg" if on else "ink"), 10, (Label(name, 14, 600 if on else 400, "selfg" if on else "ink",
                                                                    elide=True), 1),
                   Label(f"{fd['n']:,}", 12, 400, "mute"),
                   margins=(10 + (14 if "/" in name else 0), 7, 10, 7))
        rows.addWidget(Box(bg="sel" if on else None, radius=10, layout=lay, hover=None if on else "surf2",
                           on_click=lambda n=name, f=fd: app.set(folder=n, sel={**s.sel, "data": f["files"][0]})))
    if len(store.DATA_FOLDERS) > 9:
        sc = Scroll(wrap(vbox(rows, "stretch")))
        sc.setFixedHeight(9 * 36)
        body.addWidget(sc)
    else:
        body.addLayout(rows)
    return card(body, pad=(8, 16, 8, 10))


def _tree(app, items, query):
    root = {"dirs": {}, "files": []}
    for it in items:
        node = root
        for part in Path(it["folder"]).parts:
            node = node["dirs"].setdefault(part, {"dirs": {}, "files": []})
        node["files"].append(it)

    def count(node):
        return len(node["files"]) + sum(count(c) for c in node["dirs"].values())

    def matches(node):
        return any(query in it["label"].lower() for it in node["files"]) or any(map(matches, node["dirs"].values()))

    opened, rows = app.s.open_dirs[app.s.tab], []

    def walk(node, prefix, depth):
        for name, child in node["dirs"].items():
            while len(child["dirs"]) == 1 and not child["files"]:
                sub, child = next(iter(child["dirs"].items()))
                name = f"{name}/{sub}"
            if query and not matches(child):
                continue
            path = prefix + name
            is_open = bool(query) or path in opened
            rows.append(dict(label=name + "/", kind="folder", path=path, open=is_open, depth=depth, meta=f"{count(child):,}"))
            if is_open:
                walk(child, path + "/", depth + 1)
        for it in node["files"]:
            if not query or query in it["label"].lower():
                rows.append({**it, "depth": depth})

    walk(root, "", 0)
    return rows


class FileList(Box):
    MAX_ROWS = 200

    def __init__(self, app):
        self.app = app
        title, count, ph, self.rows = _items(app)
        lay = vbox()
        super().__init__(bg="surf", radius=16, layout=lay)
        lay.addLayout(hbox(Label(title, 16, 600, spacing=-0.2, lh=24), "stretch", Label(count, 12, 400, "mute"),
                           margins=(18, 16, 18, 8), align=Qt.AlignmentFlag.AlignBottom))
        self.search = LineEdit(ph)
        self.search.textChanged.connect(self.populate)
        lay.addLayout(hbox(self.search, margins=(12, 0, 12, 8)))
        if app.s.tab == "data" and store.DATA_FOLDERS:
            opts = [("all", "All"), ("train", "Train"), ("valid", "Valid"), ("test", "Test")]
            seg = Segmented(opts, app.s.split_filter, lambda k: app.set(split_filter=k), expand=True, pad=(5, 0),
                            dots={k: store.SPLITS[k][1] for k in ("train", "valid", "test")})
            lay.addLayout(hbox(seg, margins=(12, 0, 12, 8)))
        self.list = vbox(spacing=2, margins=(8, 4, 8, 12))
        inner = wrap(vbox(self.list, "stretch"))
        self.scroll = Scroll(inner)
        lay.addWidget(self.scroll, 1)
        self.populate("")

    def mark(self, key):
        rows = [w for w in (self.list.itemAt(i).widget() for i in range(self.list.count())) if getattr(w, "key", None)]
        hit = next((r for r in rows if r.key == key), None)
        if hit is None:
            return False
        for r in rows:
            sel = r is hit
            r.restyle(bg="sel" if sel else None, hover=None if sel else "surf2")
            r.name.setFont(font(14, 600 if sel else 400))
            r.name._color = "selfg" if sel else "ink"
            r.name.setStyleSheet(f"color:{col(r.name._color)};background:transparent;")
        self.scroll.ensureWidgetVisible(hit, 0, 40)
        return True

    def populate(self, text):
        clear_layout(self.list)
        q = text.strip().lower()
        if self.app.s.tab in TREE_TABS:
            rows = _tree(self.app, self.rows, q)
        else:
            rows = [it for it in self.rows if not q or q in it["label"].lower()]
        start = 0
        if len(rows) > self.MAX_ROWS:
            sel = self.app.s.sel[self.app.s.tab]
            at = next((i for i, it in enumerate(rows) if it.get("key", it["label"]) == sel), 0)
            start = max(0, min(at - self.MAX_ROWS // 2, len(rows) - self.MAX_ROWS))
        for it in rows[start:start + self.MAX_ROWS]:
            self.list.addWidget(_row(self.app, it))
        if len(rows) > self.MAX_ROWS:
            more = Label(f"Showing {start + 1:,}–{start + self.MAX_ROWS:,} of {len(rows):,} · type to filter", 12, 400, "mute")
            more.setContentsMargins(10, 8, 10, 4)
            self.list.addWidget(more)


WIDTH = 320


def build(app):
    side = QWidget()
    side.setFixedWidth(WIDTH)
    lay = vbox(spacing=12)
    if app.s.tab == "home" and store.PROJECT:
        lay.addWidget(_project_card(app))
    if app.s.tab == "data" and store.DATA_FOLDERS:
        lay.addWidget(_folders_card(app))
    app.file_list = FileList(app)
    lay.addWidget(app.file_list, 1)
    side.setLayout(lay)
    side.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    return side
