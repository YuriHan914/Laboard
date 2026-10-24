# 🧪 Laboard

*[한국어](README.ko.md)*

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Docs/assets/LABOARD_LOGO_DARK.png"/>
    <img src="Docs/assets/LABOARD_LOGO.png" alt="Laboard" width="136"/>
  </picture>
</p>

</br></br>

<table>
  <tr>
    <td align="center" width="50%"><img src="Docs/assets/LABOARD_HOME.png" alt="Home (light)"/><br/><sub>Light</sub></td>
    <td align="center" width="50%"><img src="Docs/assets/LABOARD_HOME_DARK.png" alt="Home (dark)"/><br/><sub>Dark</sub></td>
  </tr>
</table>

</br></br>

A PyQt6 desktop experiment tracker for machine-learning projects. Point it at one project file (`.toml`)
that says where your data, models, training runs and results live and which git repository to follow,
and Laboard shows all of them in one window.

Laboard only reads: it never edits your files, your database or your repository. The one exception is
the **Fetch** button in the git log popup, which runs `git fetch` and so updates only the
remote-tracking branches.

</br>

---

## 🚀 Features

* Data viewer with train / valid / test splits, labels and model predictions side by side
* Model graphs in an embedded [Netron](https://netron.app) view, with parameter counts — no GPU or torch needed
* Training runs: progress, every hyperparameter from the config files, GPU status
* Result charts from csv / jsonl / TensorBoard files, with smoothing and multi-curve comparison
* Git history, and the whole project viewed as of any earlier commit
* Data from a Postgres / Supabase table, a table file, or a folder scan
* Light and dark themes

---

## 🛠️ Installation

```bash
git clone https://github.com/YuriHan914/EX_Tool.git
cd EX_Tool

# Python 3.11+
pip install -r requirements.txt
```

---

## ▶️ Quick Start

Write a project file:

```toml
[project]
name = "my-project"
root = "/path/to/repo"

[paths]
data = "/path/to/data"
models = "/path/to/models"
runs = "/path/to/runs"
results = "/path/to/results"
```

Then run:

```bash
python -m laboard --project project.toml
```

Started without `--project`, Laboard opens on **Setting** and asks you to load a project file
(**Browse → Load**). The full project file reference is in [Setting](Docs/en/setting.md#project-file-reference).

### Command-line options

| Option | Effect |
| --- | --- |
| `--project TOML` | Load this project file at start and open on Home |
| `--tab home\|data\|model\|run\|result\|setting` | Start on this tab. The default is `home`, or `setting` when no project is given |
| `--theme light\|dark` | Start in the light or dark theme (default: light) |
| `--frameless` | Draw Laboard's own dark title bar instead of the system one |
| `--screenshot out.png` | Render the window once, save it as a PNG and exit. Works headless with `QT_QPA_PLATFORM=offscreen` |

---

## 📚 Documentation

Each page has a detailed guide in [Docs](Docs/README.md):

| Page | What it is for |
| --- | --- |
| [Home](Docs/en/home.md) | Data / model / latest run / result summaries, next to the git history |
| [Data](Docs/en/data.md) | Browse every data file, its split and label, and compare it with model predictions |
| [Model](Docs/en/model.md) | A model file's graph in Netron, its properties and parameters by layer |
| [Hyperparameter](Docs/en/run.md) | A training run's progress, all of its hyperparameters, and the GPU |
| [Result](Docs/en/result.md) | Charts from csv / jsonl / TensorBoard, curve comparison, tables, logs and images |
| [Setting](Docs/en/setting.md) | Load a project file, see what was detected, switch the theme; the project file reference |

---

## 🖥️ The Window

### Top bar

- **Tabs** switch between the six pages.
- **Branch chip** shows where the repository is, for example
  `main @a1b2c3d · 2 uncommitted · ↑1 ↓0 vs origin/main`: the current branch and commit, how many
  files are uncommitted (or `clean`), and how many commits are ahead of / behind the upstream. While you
  are looking at an older commit it reads `detached @<hash> · read-only snapshot`.
- **Show project as of** opens the git log popup:
  - Commits are grouped by day with their message, hash, author and time. The commit on screen is
    highlighted, and `HEAD` is marked.
  - With an upstream, the popup also shows ahead / behind counts, when it was last fetched, and an
    **All / Local / Remote** filter. Commits only on one side are marked *Local · not pushed* or
    *Remote · not pulled*, as of the last fetch. Laboard never fetches on its own; click **Fetch**.
  - Click a commit to reload every page as of that commit. **Back to latest**, or the `HEAD` commit,
    returns to the current state.

### Viewing a past commit

Viewing an older commit is read-only and never touches your working tree, index or `HEAD`:

- Paths inside the repository are read from a `git archive` snapshot in the temp folder, deleted when
  Laboard exits.
- Database rows created after the commit's time are hidden (this needs a `created`-type column).
- Paths that git doesn't track, or that lie outside the repository, have no history and stay empty.
  The status bar says which ones.
- What you have selected on each page is kept, as long as it still exists at that commit.

### Left sidebar

Each page has a list on the left: root folders (Home), data folders and files (Data), model files
(Model), hyperparameter sets (Hyperparameter), result files (Result) and recent projects (Setting). All of them share:

- **Filter box:** shows only the rows whose name contains the typed text (not case-sensitive).
- **Folder trees** (Model, Hyperparameter, Result): folders start collapsed; click one to open it. A folder that
  only contains one subfolder is merged into a single row (`a/b/c/`). While you type a filter, every
  folder holding a match opens.
- **Long lists:** only 200 rows around the selection are built at a time; use the filter to reach the rest.
- **Repeated names:** files with the same name in different folders are listed by their relative path.

### Side panels

- Drag the gutter beside a panel to resize it, up to 70% of the window width. Narrower than 40 px, it hides.
- Double-click a gutter to hide the panel, or to bring it back at its original width.
- When the window is too narrow for everything, the page scrolls sideways instead of squeezing.

### What is kept when you switch tabs

- **Kept:** the item selected on each page (file, model, run).
- **Reset:** how the page is viewed — filters, zoom, the Raw / Predict view, ticked charts, chart
  sizes, table pages, expanded folders and panel widths.

### Status bar

- **Left:** the folders the project points at (models, runs, results), the Python and PyQt6 versions,
  and where the data came from.
- **Middle:** the latest message, such as `Loaded …` with notes from loading, a load error, or the
  read-only snapshot notice.
- **Right:** GPU 0 utilisation (if `nvidia-smi` is available) and when the project was loaded.

