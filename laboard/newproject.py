"""Setting → New: a form of every section of a project file (and the remote logins) that writes a new laboard toml
and loads it. Sections are grouped on the left (gcloud / az / aws / ssh as one Cloud group). [Project] is required;
every other section has a False / True switch by its name and is written only when True ([DB]'s switch is
[Project] DB). Nothing is written until Create and load, and an existing file is never overwritten."""
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect

from . import store, tomledit
from .theme import NEGATIVE
from .widgets import (CROSS, Box, Button, Flow, HLine, Label, LineEdit, Overlay, Scroll, Segmented, Stroke, card,
                      clear_layout, col, hbox, vbox, wrap)


def _text(key, desc, ph="", req=False):
    return dict(key=key, desc=desc, ph=ph, req=req, kind="text")


def _enum(key, desc):
    return dict(key=key, desc=desc, kind="enum", opts=("CSV", "DB"))


# (section, description, fields), in the order they are written
SCHEMA = (
    ("Project", "Raw data is shared by every task; each task has its own labels and predictions.", (
        _text("Name", "Project name. Empty: the root folder’s name.", "cifar10-resnet"),
        _text("Root", "Folder of the project’s git repository.", "~/projects/cifar10-resnet"),
        dict(key="Task", desc="One task or several. Saved comma-separated.", kind="chips", opts=tomledit.TASKS),
        dict(key="DB", desc='True when [Data], [Label] or [Prediction] uses Type = "DB".', kind="bool"))),
    ("DB", "Database connection. Shown and used when [Project] DB = True.", (
        _text("DB", "Database type, e.g. supabase.", "supabase"),
        _text("DB_ip", "Database address.", "http://127.0.0.1:54323/  or  postgresql://user:password@host:5432/db"))),
    ("Git", "Fallbacks when git can’t tell.", (
        _text("Remote", "Remote URL.", "github.com:user/repo.git"),
        _text("Branch", "Branch name.", "main"))),
    ("Path", "Each may hold one folder per task, e.g. Results/classification/<model>/.", (
        _text("Models", "Folder with model checkpoints.", "models/"),
        _text("Hyperparameter", "Folder with one sub-folder per training run.", "runs/"),
        _text("Results", "Folder with result files.", "results/"))),
    ("Data", "The raw data files, one list for every task.", (
        _enum("Type", "Where the file list comes from."),
        _text("File_path", "CSV: the csv listing the files.", "data/files.csv"),
        _text("Table", "DB: table with one row per file.", "raw_files"),
        _text("Raw", "CSV / DB: column with each raw file’s path.", "file_path"))),
    ("Label", "Ground truth, one column for every task.", (
        _enum("Type", "Where the labels come from."),
        _text("File_path", "CSV: the labels csv.", "data/labels.csv"),
        _text("Table", "DB: table with the labels.", "labels"),
        _text("Label", "Its column. A task column picks each task’s row.", "label"))),
    ("Prediction", "Any key can be set for one task as <Task>_<Key>, e.g. Instance_segmentation_Predict.", (
        _enum("Type", "Where the predictions come from."),
        _text("File_path", "CSV: result file name / glob under Path.Results/<task>.", "predictions_*.csv"),
        _text("Table", "DB: table with the predictions.", "predictions"),
        _text("Predict", "Predicted-class column.", "pred"),
        _text("Predict_score", "Score column.", "score"))),
    ("gcloud", "gcloud compute ssh <instance_name> --zone <zone>", (
        _text("instance_name", "The VM instance’s name.", "instance name", True),
        _text("zone", "Instance zone.", "us-west1-b"))),
    ("az", "az ssh vm --name <vm_name> --resource-group <resource-group>", (
        _text("vm_name", "The Azure VM’s name.", "VM name"),
        _text("resource-group", "Its resource group.", "resource group"))),
    ("aws", "Sends the public key (EC2 Instance Connect), then ssh -i <private key> <user>@<public ip>.", (
        _text("instance-id", "EC2 instance ID.", "i-0123456789abcdef0", True),
        _text("instance-os-user", "The login user, e.g. ec2-user, ubuntu.", "ec2-user", True),
        _text("ssh-public-key", "Public key. The private key is this file without .pub.", "file://~/.ssh/id_ed25519.pub",
              True),
        _text("availability-zone", "Its region finds the instance’s public ip.", "us-east-1a"))),
    ("ssh", "ssh -i ~/.ssh/<key_name> <user_name>@<ip>", (
        _text("key_name", "A key under ~/.ssh, or the key file’s own path when it has a \"/\".", "id_ed25519"),
        _text("user_name", "Login user. Empty: ssh’s default.", "ubuntu"),
        _text("ip", "Server address (ip or host name).", "192.168.0.10", True))),
)
CLOUD = ("gcloud", "az", "aws", "ssh")  # one "Cloud" group on the left
SHOWN = {"gcloud": "Google Cloud - gcloud", "az": "Azure - az", "aws": "AWS - aws", "ssh": "SSH - ssh"}  # card titles
REQUIRED = ("Project",)  # always written; every other section has a False / True switch
OFF = set(CLOUD)  # sections switched off at first (DB follows [Project] DB)
TITLE_BAR, TITLE_FG, TITLE_MUTE, CLOSE_BG = "#0e0f0c", "#e8ebe6", "#868685", "#2a2b28"  # dark in both themes


def _group(section):
    return "Cloud" if section in CLOUD else section


def _free_path(folder):
    """laboard.toml in ``folder``, or laboard_2.toml, … when it is taken."""
    f, n = folder / "laboard.toml", 2
    while f.exists():
        f, n = folder / f"laboard_{n}.toml", n + 1
    return f


class CreateProject(Overlay):
    """The New project file window (see the module doc), at most 1180 × 900 and smaller in a smaller window."""
    W, H = 1180, 900

    def __init__(self, app):
        super().__init__(app)
        self.app, self.values, self.group = app, {}, "Project"
        self.on = {name: name not in OFF for name, _, _ in SCHEMA}  # written or not; see enabled()
        loaded = store.PROJECT.get("toml")
        self.folder = Path(loaded).parent if loaded else Path.home()

        close = Box(bg=CLOSE_BG, radius=12, on_click=self.close,
                    layout=hbox(Stroke(CROSS, 10, TITLE_FG, 1.5), align=Qt.AlignmentFlag.AlignCenter))
        close.setFixedSize(24, 24)
        bar = Box(bg=TITLE_BAR, radius=0, layout=hbox(
            (Label("Laboard", 13, 600, TITLE_FG), 1),
            (Label("Create project file — laboard.toml", 13, 400, TITLE_MUTE, align=Qt.AlignmentFlag.AlignCenter), 2),
            (hbox("stretch", close), 1), spacing=12, margins=(16, 0, 10, 0), align=Qt.AlignmentFlag.AlignVCenter))
        bar.setFixedHeight(38)
        bar.setStyleSheet(f"QFrame#{bar.objectName()}{{background:{TITLE_BAR};border-top-left-radius:12px;"
                          "border-top-right-radius:12px;}")

        self.nav = vbox(spacing=2)
        side = Box(bg="surf", radius=16, layout=vbox(Label("Sections", 16, 600, lh=24), 8, self.nav, "stretch",
                                                     margins=(8, 16, 8, 16)))
        side.layout().itemAt(0).widget().setContentsMargins(10, 0, 10, 0)
        side.setFixedWidth(230)

        self.cards = vbox(spacing=12)
        self.scroll = Scroll(wrap(vbox(self.cards, "stretch")))
        self.path = LineEdit("", size=13, pad=(8, 12), mono=True)
        self.path.setText(str(_free_path(self.folder)))
        self.path.setFixedHeight(40)
        self.path.returnPressed.connect(self.create)
        self.error = Label("", 12, 400, NEGATIVE, wrap=True)
        self.error.hide()
        foot = Box(bg="surf", radius=16, layout=hbox(
            (vbox(Label("Save to", 13, 600, lh=18), 6, self.path, self.error, spacing=0), 1), 12,
            vbox("stretch", hbox(Button("Cancel", "tertiary", on_click=self.close), 10,
                                 Button("Create and load", "primary", on_click=self.create))),
            margins=(20, 14, 20, 14)))
        right = vbox((self.scroll, 1), 12, foot)

        self.panel = Box(bg="bg", radius=12, layout=vbox(bar, hbox(side, 12, (right, 1), margins=(12, 12, 12, 12)), 1))
        self.panel.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=64, offset=QPointF(0, 24),
                                                               color=QColor(14, 15, 12, 102)))
        self.setLayout(vbox("stretch", hbox("stretch", self.panel, "stretch"), "stretch"))
        self._fit()
        self.show_group("Project")

    def _fit(self):
        super()._fit()
        if getattr(self, "panel", None) is not None:  # fits the window, as large as the design at most
            self.panel.setFixedSize(min(self.W, self.width() - 48), min(self.H, self.height() - 48))

    # ------------------------------------------------------------ the form
    def enabled(self, name):
        """Whether section ``name`` is written: always for [Project], [Project] DB for [DB], else its switch."""
        if name in REQUIRED:
            return True
        return self.values.get("Project.DB") is True if name == "DB" else self.on[name]

    def switch(self, name, on):
        if name == "DB":
            self.values["Project.DB"] = on  # the same choice as [Project] DB
        else:
            self.on[name] = on
        self.show_group(self.group, keep_scroll=True)

    def show_group(self, group, keep_scroll=False):
        """List the groups on the left with ``group`` picked, and show its sections' cards on the right (from the top,
        unless ``keep_scroll``: a switch flipped in place)."""
        at = self.scroll.verticalScrollBar().value() if keep_scroll else 0
        groups = list(dict.fromkeys(_group(s[0]) for s in SCHEMA))
        self.group = group if group in groups else "Project"
        clear_layout(self.nav)
        for g in groups:
            secs = [s for s in SCHEMA if _group(s[0]) == g]
            on, n = g == self.group, sum(len(s[2]) for s in secs)
            used = any(self.enabled(s[0]) for s in secs)  # a group with nothing switched on is greyed
            self.nav.addWidget(Box(bg="sel" if on else None, radius=10, hover=None if on else "surf2",
                                   on_click=lambda g=g: self.show_group(g), layout=hbox(
                                       (Label(g, 14, 600 if on else 400, "selfg" if on else "ink" if used else "mute",
                                              lh=20), 1), 8,
                                       Label(str(n), 12, 400, "mute"), margins=(10, 7, 10, 7),
                                       align=Qt.AlignmentFlag.AlignVCenter)))
        clear_layout(self.cards)
        for name, desc, fields in SCHEMA:
            if _group(name) == self.group:
                self.cards.addWidget(self._card(name, desc, fields))
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(at))  # once the new cards are laid out

    def _card(self, name, desc, fields):
        """A section's card: its name with the False / True switch (or "required"), what it is for, and its keys,
        greyed and inert while switched off."""
        on = self.enabled(name)
        head = hbox(Label(SHOWN.get(name, name), 18, 600, "ink" if on else "mute", mono=True, lh=24), spacing=12,
                    align=Qt.AlignmentFlag.AlignVCenter)
        if name in REQUIRED:
            head.addWidget(Label("required", 11, 600, NEGATIVE, lh=14))
        head.addStretch(1)
        if name not in REQUIRED:  # the Light / Dark switch of Setting's Appearance, smaller, at the right end
            head.addWidget(Segmented([(False, "False"), (True, "True")], on, lambda v, n=name: self.switch(n, v),
                                     size=12, pad=(4, 14), outer=3, gap=2))
        rows = vbox()
        for f in fields:
            key = hbox(Label(f["key"], 13, 600, mono=True, lh=18), spacing=6, align=Qt.AlignmentFlag.AlignVCenter)
            if f.get("req"):
                key.addWidget(Label("required", 11, 600, NEGATIVE, lh=14))
            key.addStretch(1)
            left = vbox("stretch", key, 2, Label(f["desc"], 12, 400, "mute", wrap=True), "stretch")  # centred
            rows.addWidget(HLine())
            rows.addLayout(hbox((left, 10), 20, (self._editor(name, f), 13), margins=(0, 10, 0, 10),
                                align=Qt.AlignmentFlag.AlignVCenter))
        body = wrap(vbox(Label(desc, 13, 400, "body", wrap=True), 8, rows))
        if not on:
            body.setEnabled(False)  # kept as typed, but not written
            fade = QGraphicsOpacityEffect(body)
            fade.setOpacity(0.4)
            body.setGraphicsEffect(fade)
        return card(head, 4, body, pad=(24, 20, 24, 20))

    def _editor(self, section, f):
        """The input for one key: a text box, a False / True or CSV / DB switch, or task chips."""
        fid = f"{section}.{f['key']}"
        if f["kind"] == "text":
            box = LineEdit(f.get("ph", ""), size=13, pad=(8, 12), mono=True)
            box.setFixedHeight(40)
            box.setText(self.values.get(fid, ""))
            box.textChanged.connect(lambda t: self.values.__setitem__(fid, t))
            return box
        if f["kind"] in ("bool", "enum"):
            opts = [(False, "False"), (True, "True")] if f["kind"] == "bool" else [(o, o) for o in f["opts"]]
            cur = self.values.get(fid, False if f["kind"] == "bool" else None)

            def pick(v):
                self.values[fid] = v
                seg.select(v)
                if fid == "Project.DB":  # [DB]'s switch is the same choice
                    self.show_group(self.group, keep_scroll=True)
            seg = Segmented(opts, cur, pick, size=13, pad=(6, 16))
            return wrap(hbox(seg, "stretch"))
        chips = Flow(spacing=6, fill=False)
        for o in f["opts"]:
            chips.add(self._chip(fid, o), stretch=0)
        return wrap(chips)

    def _chip(self, fid, option):
        """One task of the Task chips: dark when picked; a click picks it or not."""
        lbl = Label(option, 12, 600, lh=18)
        chip = Box(bg=None, radius=999, layout=hbox(lbl, margins=(12, 5, 12, 5)))

        def paint():
            on = option in self.values.get(fid, ())
            chip.restyle(bg="tab" if on else None, border=f"1px solid {col('tab' if on else 'ink')}")
            lbl.setStyleSheet(f"color:{col('tabfg' if on else 'ink')};background:transparent;")

        def flip():
            picked = set(self.values.get(fid, ()))
            picked ^= {option}
            self.values[fid] = picked
            paint()
        chip.clicked.connect(flip)
        chip.setCursor(Qt.CursorShape.PointingHandCursor)
        paint()
        return chip

    # ------------------------------------------------------------ writing
    def missing(self):
        """``[section] key`` of the required keys left empty in the sections switched on."""
        return [f"[{name}] {f['key']}" for name, _, fields in SCHEMA if self.enabled(name)
                for f in fields if f.get("req") and not str(self.values.get(f"{name}.{f['key']}") or "").strip()]

    def text(self):
        """The toml of the form: [Project] and every section switched on."""
        lines = ["# Laboard project file, made with Setting → New. Empty values (\"\") count as not set."]
        for name, _, fields in SCHEMA:
            if not self.enabled(name):
                continue
            lines += ["", f"[{name}]"]
            for f in fields:
                v = self.values.get(f"{name}.{f['key']}")
                if f["kind"] == "bool":
                    value = tomledit.written(bool(v))
                elif f["kind"] == "chips":
                    value = tomledit.literal(", ".join(t for t in f["opts"] if t in (v or ())))
                else:
                    value = tomledit.literal((v or "").strip())
                lines.append(f"{f['key']} = {value}")
        return "\n".join(lines) + "\n"

    def create(self):
        """Write the file where Save to says (relative: under the loaded project's folder) and load it."""
        raw = self.path.text().strip()
        if not raw:
            return self._fail("Type where to save the project file.")
        if self.missing():
            return self._fail("Fill in the required keys, or switch their section off: " + ", ".join(self.missing()))
        f = Path(raw).expanduser()
        f = f if f.is_absolute() else self.folder / f
        f = f if f.suffix == ".toml" else f.with_name(f.name + ".toml")
        if f.exists():
            return self._fail(f"{f} already exists; it is never overwritten. Choose another name.")
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(self.text())
        except OSError as e:
            return self._fail(f"Could not write {f}: {e}")
        self.close()
        self.app.s.pending_toml = None
        self.app.load_project(str(f))

    def _fail(self, message):
        self.error.setText(message)
        self.error.show()
