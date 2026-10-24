<p align="center">
  <img src="../assets/LABOARD_SETTING.png" alt="Setting" width="900"/>
</p>

# Setting

**English** | [한국어](../ko/setting.md)

On the Setting page you can:

- load a project file
- edit its values one by one, and save the result as a new file
- check what Laboard found in each place it points to
- switch the theme

Laboard opens on this page when it starts without a project.

## Load project file

1. Type a path to a `.toml` file, or click **Browse** to pick one. Browse only fills in the path.
2. Click **Load** or press Enter to load it.

What can happen:

| Situation | Result |
| --- | --- |
| The field is empty | The status bar says *Choose a project file first* |
| The file isn't a `.toml` | The status bar says *Not a .toml file* |
| The file is missing or broken | The error appears in the status bar, and the previous project stays loaded |
| Loading succeeds | Every page reloads, and the status bar shows `Loaded <path>` with any notes |

Notes include things like *Nothing found in Path.Runs*, *[Data] Type is not set* or *DB … unavailable (…)*.
See [Common notes](data.md#common-notes) in the Data docs for what to do about each.

## Project file

The loaded file, shown two ways:

- **Fields** lists every value by section. **Edit** next to a value opens a popup to change it: **Save**
  (or Enter) applies it and reloads the project, **Cancel** leaves it as it was.
  - The list is fixed: every key of a classification project (those in `template.toml` at the repository root)
    in the same order, whatever the loaded file holds. A key the file leaves out, or leaves empty, shows empty;
    other keys the file has are listed after them. `[DB]` is shown only while `[Project] DB` is True, `Table`
    only for `Type = "DB"`, and `[Prediction] Format` only for `Type = "Folder"`.
  - Hovering a key or its value shows what to put in it; the Edit popup shows the same description.
    These descriptions are built into Laboard and don't depend on the file.
  - Saved values apply to this session only: the toml file on disk is never changed. The header then says
    *Edited*; **Load** reads the file again and drops the edits.
  - **Save as…** (shown once something is edited) writes the edited project to a new toml, by default
    `<name>_edited.toml`, and loads it. It refuses to overwrite the loaded file.
  - `[Project] Task`, `[Project] DB`, `[Data] Type`, `[Prediction] Type` and `[Prediction] Format` are
    drop-downs. These keys are listed even when the file leaves them out; the empty choice removes the key.
  - Other values are typed. A path also has a folder icon in the box that opens a file or folder picker:
    a file for `Type = "CSV"`, a folder for `Type = "Folder"` and for `[Path]`.
  - Comments, order and layout are kept; only the edited line changes. A value that isn't valid toml
    isn't applied, and the popup says why.
  - The page keeps its scroll position when Save reloads it.
- **Text** is a read-only copy with line numbers. Section headers (`[Project]`, `[Path]`, …) are bold.

## Detected

What Laboard found for each part of the project, with a status badge:

| Row | Badges |
| --- | --- |
| Git repository | *Found* (branch · number of commits) / *Not found* |
| Snapshot | *Past commit*, only while viewing an older commit |
| Database | *Connected* / *Unreachable* (with the error) |
| Data | *Found* (source · files · folders · size) / *Not found* |
| Models | *Found* / *Not found* |
| Runs | *Found* / *Not found* |
| Results | *Found* / *Not found* |
| TensorBoard | *Found*, when event files are under the results |
| Weights & Biases | *Offline*, when `offline-run-*` folders are under the results |
| Prediction | *Found* (`[Prediction] Type = …` · sources · files with a prediction · columns) / *Not found*. Classification projects |
| Labels / inference | *Found* (result file, number of matches, columns) / *Not found*. Older format |

## Appearance

**Light / Dark** switches the theme straight away. The `--theme` option sets the theme at start.

## Left sidebar

**Recent projects** lists the project that is loaded now.

## Project file reference

The project file is toml. `template.toml` at the repository root lists every key with empty values; copy it
to start. Setting's **Fields** shows and edits the same keys in the same order.

- **Names:** section and key names start with a capital letter (`DB` all in capitals, the paths section is
  `[Path]`). Lower-case names are read the same way.
- **Paths:** absolute, or relative to the folder that holds the toml.
- **Empty values:** leave keys you don't use as `""`. An empty key counts as not set.
- **True / False:** Laboard writes `True` / `False`; standard toml `true` / `false` is read too.

### Full example (classification project)

```toml
[Project]
Name = "Anomaly-Detection"
Root = "/mnt/data/github/Anomaly-Detection/test_projects"
Task = "classification"            # classification | object detection | segmentation
DB = False                         # True when [Data] / [Prediction] uses Type = "DB"

[DB]                               # used only with DB = True (and only shown in Setting then)
DB = "supabase"
DB_ip = "http://127.0.0.1:54323/"

[Git]
Remote = "github.com:YuriHan914/Anomaly-Detection.git"
Branch = "main"

[Path]
Models = "/mnt/data/github/Anomaly-Detection/test_projects/Models"
Runs = "/mnt/data/github/Anomaly-Detection/test_projects/Runs"
Results = "/mnt/data/github/Anomaly-Detection/test_projects/Results"

[Data]
Type = "CSV"                       # CSV | DB | Folder
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Table = ""                         # Type = "DB" only
Label = "label"

[Prediction]
Type = "CSV"                       # CSV | DB | Folder
Path = "inference.csv"
Table = ""                         # Type = "DB" only
Format = ""                        # Type = "Folder" only: txt | json
Predict = "classification"
Predict_score = "AD_score"
```

### Keys by section

**`[Project]`**

| Key | What to put in it |
| --- | --- |
| `Name` | Project name shown in the top bar and on Home. Empty: the Root folder's name |
| `Root` | Folder of the project's git repository; git history, branch and remote come from it. Empty: the first of the data / `[Path]` paths, or the toml's folder |
| `Task` | `classification` reads `[Data]` / `[Prediction]`. `object detection` / `segmentation` use the [older format](#older-format) |
| `DB` | `True` when `[Data]` or `[Prediction]` uses `Type = "DB"`. `False`: no database |

**`[DB]`** (with `[Project] DB = True`)

| Key | What to put in it |
| --- | --- |
| `DB` | Database kind: `supabase` |
| `DB_ip` | Database address: a Supabase URL (`http://127.0.0.1:54323/` → its Postgres on port 54322), or `postgresql://user:password@host:5432/dbname` |

When the defaults don't fit, add `Port`, `User`, `Password`, `Database` (defaults 54322 / postgres /
postgres / postgres) and `Limit` (most rows read, default 200,000).

**`[Git]`** fallbacks used only when git can't tell.

| Key | What to put in it |
| --- | --- |
| `Remote` | Remote shown when there is no origin remote, e.g. `github.com:user/repo.git` |
| `Branch` | Branch shown when HEAD is detached or Root isn't a git repository, e.g. `main` |

**`[Path]`**

| Key | What to put in it |
| --- | --- |
| `Models` | Folder of model checkpoints (.pt, .onnx, .safetensors, …) → [Model](model.md) page |
| `Runs` | Folder with one sub-folder per training run holding json / yaml / toml configs → [Run](run.md) page |
| `Results` | Folder of result files (csv, logs, images, TensorBoard events, …) → [Result](result.md) page. `[Prediction] Type = "CSV"` looks here too |

**`[Data]` / `[Prediction]`** the keys used depend on `Type`. For each Type's details and the columns it needs,
see [Data setup](data.md#data-setup) and [Prediction setup](data.md#prediction-setup-prediction) in the
Data page docs.

| Key | What to put in it |
| --- | --- |
| `[Data] Type` | `DB` / `CSV` / `Folder` |
| `[Data] File_path` | CSV: the csv listing the files · Folder: a dataset folder laid out as `split/label/file` |
| `[Data] Table` | DB: the table with one row per file |
| `[Data] Label` | DB / CSV: the ground-truth column. Empty: `label` |
| `[Prediction] Type` | `CSV` / `DB` / `Folder` |
| `[Prediction] Path` | CSV: result file name / glob under `[Path] Results` · Folder: the folder of prediction files |
| `[Prediction] Table` | DB: the table holding the predictions |
| `[Prediction] Format` | Folder: `txt` (`<class> [score]`) / `json` |
| `[Prediction] Predict` | Predicted-class column (json: key) |
| `[Prediction] Predict_score` | Score column (json: key) |

### Where each section is used

| Section | Used by |
| --- | --- |
| `[Project]`, `[Git]` | Top bar, Home, git log popup |
| `[Data]`, `[DB]` | [Data](data.md), Home's Data card |
| `[Prediction]` | The [Data](data.md) page's predictions |
| `[Path] Models` | [Model](model.md), Home's Model card |
| `[Path] Runs` | [Run](run.md), Home's Latest run card |
| `[Path] Results` | [Result](result.md), Home's Result card |

Any part that Laboard can't find stays empty; the Detected card and the status bar show which.

### Older format

When `Task` is empty or not `classification`, the older format is read: `[Path] Data` says where the data is
and `[Labels]` where predictions are. See the [older format](data.md#older-format-task-is-not-classification)
in the Data docs for the order sources are tried in.

```toml
[Path]
Data = "/path/to/data"             # a data folder, a file list (csv / tsv / jsonl / parquet), or a section name such as "DB"

[DB]                               # used before Path.Data when reachable
Supabase = "http://127.0.0.1:54323/"
Table = "my_table"                 # or "schema.table"
# Dsn = "postgresql://user:pw@host:5432/db"
# Columns = { Path = "file_path", Split = "type" }   # the ground truth is always the "label" column

[Models]                           # optional
# Extensions = [".pt", ".onnx"]

[Labels]                           # optional (also read when spelled [Lables])
Result_file = "inference.csv"      # name / glob under Path.Results; each match is one source
Infer = "classification"           # any other key: a column shown on the Data page
Score = "AD_result"
# Path = "data_path"               # column matching rows to data files (guessed when left out)
```
