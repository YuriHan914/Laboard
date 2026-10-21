# Laboard (PyQt6)

Desktop implementation of the `Experiment Tracker v2` design from `project/`.

## Run

```bash
pip install -r requirements.txt
python -m laboard                    # nothing loaded: opens on Setting and asks for a project .toml
python -m laboard --project project.toml            # loads it and opens on Home
python -m laboard --project project.toml --tab data --theme dark
python -m laboard --frameless        # dark custom title bar from the mockup
python -m laboard --screenshot out.png   # render once and save (works with QT_QPA_PLATFORM=offscreen)
```

## Layout

| File | What it holds |
| --- | --- |
| `app.py` | Main window, top bar (tabs, branch chip, Light/Dark, "Show project as of" git-log popup), status bar, CLI |
| `sidebar.py` | Left column per tab: project card + root folders (Home), folders + split filter (Data), file lists |
| `pages/*.py` | One module per tab: Home, Data, Model, Run, Result, Setting |
| `widgets.py` | Wise DS building blocks: rounded boxes, pills, segmented controls, buttons, badges, stat tiles |
| `charts.py` | QPainter charts and the image/video stage |
| `theme.py` | Wise tokens, light/dark palettes, bundled Inter/Figtree fonts |
| `store.py` | The data every page reads; empty until a project is loaded |
| `project.py` | Loads a project toml into `store` |
| `readers.py` | csv / jsonl / tfevents / text readers for the Result tab |
| `modelinfo.py` | Parameters, inputs/outputs and per-layer counts read from model files, no GPU or torch needed |
| `netronview.py` | Serves the selected model with netron and shows it in a QWebEngineView |
| `torchgraph.py` | Layer-sequence ONNX for torch.save checkpoints, which store no wiring |

## Loading a real project

```bash
python -m laboard --project path/to/project.toml
```

or **Setting → Browse / Load** inside the app. `project.py` reads the toml into `store.py`; there is
no example data, so sections it finds nothing for stay empty (the Setting tab's *Detected* card
shows what was found). A file that fails to load keeps the previous project. Nothing depends on
particular file names, counts or formats.

```toml
[project]
name = "my-project"
root = "/path/to/repo"            # git history, branch, remote come from here

[paths]                            # absolute, or relative to the toml
data = "/path/to/data"
models = "/path/to/models"
runs = "/path/to/runs"
results = "/path/to/results"

[db]                               # optional; used before paths.data when reachable
supabase = "http://127.0.0.1:54323/"   # local Supabase → its Postgres on port 54322
table = "my_table"                 # or "schema.table"
# dsn = "postgresql://user:pw@host:5432/db"   # any Postgres instead of a Supabase URL
# port / user / password / database / limit   # overrides (defaults: 54322 / postgres / postgres / postgres)
# columns = { path = "file_path", label = "class", split = "type" }

[data]                             # optional
# table = "index.csv"              # a csv / tsv / jsonl / parquet listing the files
# columns = { path = "img", label = "cls", split = "subset" }

[models]                           # optional
# extensions = [".pt", ".onnx"]

[labels]                           # optional (also read when spelled [lables])
result_file = "inference.csv"      # name / relative path / glob under paths.results; one source per match
infer = "classification"           # every other key: a column shown in the Data tab's Inference pane
score = "AD_result"
# path = "data_path"               # column matching rows to data files (guessed when left out)
# label = "labels"                 # label column (guessed when left out)
```

With `[labels]`, the Data tab takes each file's label and inference values from the result file
(rows are matched by path, or by file name); when several files match, a *Results* drop-down
picks the source. A value equal to the label is green, a different class red, anything else grey.

| Section | Where it comes from |
| --- | --- |
| Data | `[db]` table → else a table file under `paths.data` whose path column points at existing files → else every file under `paths.data`. Path / label / split columns are matched by common names (`file_path`, `class`, `type`, …) or guessed from values; `columns` overrides. Splits are `train` / `valid` / `test` (`val`, `validation`, … accepted); a folder scan takes split and label from ImageFolder-style paths (`train/<label>/x.jpg`). |
| Models | Files with a checkpoint extension (`.pt .pth .ckpt .onnx .safetensors .msgpack .engine .h5 …`); every file when none match. The graph is [Netron](https://netron.app) in an embedded web view (`netronview.py`); parameter counts and properties are read by `modelinfo.py` (onnx / safetensors header / msgpack / a torch-free restricted unpickler). Weight-only formats (safetensors, msgpack) have no wiring, so Netron lists their modules. `torch.save` checkpoints (`.pt .pth .ckpt .bin`) default to *Layer sequence*: `torchgraph.py` types each module from its tensors (Conv / Linear / BatchNorm / Norm / Embedding) and chains them in registration order as a shape-only ONNX file for Netron; *As stored* shows the file itself. TorchScript files carry their graph and open directly. TensorRT engines are tied to one TensorRT build and only show their header. |
| Runs | Every folder under `paths.runs` (3 levels deep) holding `.json` / `.yaml` / `.toml` configs; `trainer_state.json` gives progress. |
| Results | Every file under `paths.results`: csv / tsv / jsonl and TensorBoard events are charted, text and json shown, images displayed. |
| Git | `git log` (last 100 commits of the branch and its upstream) and `git status` in `project.root`. Commits are marked *Local · not pushed*, *Remote · not pulled* or shared, from the remote-tracking branch as of the last fetch; the *Show project as of* popup filters All / Local / Remote and has a **Fetch** button (Laboard never fetches on its own). |

**Show project as of** (top bar) reloads every page as of the chosen commit, read-only: paths
inside the repo come from a `git archive` snapshot in the temp folder (deleted when Laboard exits;
the working tree, index and HEAD are never touched), and db rows created after the commit are
hidden. Paths git doesn't track, or that lie outside the repo, have no history and stay empty.

Images on the Data (and Result) tab: scroll to zoom around the cursor, Shift+scroll or drag to pan,
double-click to fit. In *Both* mode the two panes zoom and pan together.

Model, Run and Result lists are folder trees that start collapsed; click a folder to open it.
File names that repeat in different folders are listed by their relative path. Long lists show
200 rows around the selection; type in the filter box to search all of them.
