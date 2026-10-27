# Setting

<p align="center">
  <img src="../assets/LABOARD_SETTING.png" alt="Setting" width="900"/>
</p>



**English** | [한국어](../ko/setting.md)

On the Setting page you can:

- load a project file, or make a new one (**New**)
- edit its values one by one, and save the result as a new file
- check what Laboard found in each place it points to
- switch the theme
- change how many rows Result and Hyperparameter tables show per page

Laboard opens on this page when it starts without a project.

## Load project file

1. Type a path to a `.toml` file, or click **Browse** to pick one. Browse only fills in the path.
2. Click **Load** or press Enter to load it.

**New** opens **Create project file**, a form of every section:

- **Sections** (left): Project, DB, Git, Path, Data, Label, Prediction and Cloud (the logins: Google Cloud - gcloud,
  Azure - az, AWS - aws, SSH - ssh), each with its number of keys. A group with nothing switched on is greyed.
- **On / off:** Project is `required` and always written. Every other section has a **False / True** switch by its
  name, like Setting's Light / Dark: True writes it, False greys it out and leaves it out of the file (what you typed
  is kept). Git, Path, Data, Label and Prediction start True, the logins False. DB's switch is the same choice as
  `[Project] DB`.
- **Keys** (right): each with what to put in it and an example; `required` marks the keys a login can't do without.
  Task is picked as chips (several allowed, saved comma-separated), DB as False / True and each Type as CSV / DB.
- **Save to:** where the file goes (relative: under the loaded project's folder). It starts as `laboard.toml` there,
  or `laboard_2.toml`, … when that is taken.
- **Create and load** writes the toml with [Project] and the sections switched on, and loads it. A `required` key
  left empty in a section switched on stops it with a note under Save to, as does an existing file (never
  overwritten). **Cancel**, **×** or Esc closes it without writing anything.

What can happen:

| Situation | Result |
| --- | --- |
| The field is empty | The status bar says *Choose a project file first* |
| The file isn't a `.toml` | The status bar says *Not a .toml file* |
| The file is missing or broken | The error appears in the status bar, and the previous project stays loaded |
| Loading succeeds | Every page reloads, and the status bar shows `Loaded <path>` with any notes |

Notes include things like *Nothing found in Path.Hyperparameter*, *[Data] Type is not set* or *DB … unavailable (…)*.
See [Common notes](data.md#common-notes) in the Data docs for what to do about each.

## Project file

The loaded file, shown two ways:

- **Fields** lists every value by section. **Edit** next to a value opens a popup to change it: **Save**
  (or Enter) applies it and reloads the project, **Cancel** leaves it as it was.
  - The list is fixed: every key of `[Project]` … `[Prediction]` in `template.toml` at the repository root, in the
    same order, whatever the loaded file holds. A key the file leaves out, or leaves empty, shows empty; other keys
    and sections the file has (such as the logins `[gcloud]`, `[ssh]`, …) are listed after them. `[DB]` is shown only
    while `[Project] DB` is True, `Table` only for `Type = "DB"`.
  - Hovering a key or its value shows what to put in it; the Edit popup shows the same description.
    These descriptions are built into Laboard and don't depend on the file.
  - Saved values apply to this session only: the toml file on disk is never changed. The header then says
    *Edited*; **Load** reads the file again and drops the edits.
  - **Save Changed** (shown once something is edited) writes the edited project to a new toml, by default
    `<name>_edited.toml`, and loads it. It refuses to overwrite the loaded file.
  - `[Project] DB` and `[Data]` / `[Label]` / `[Prediction]` `Type` are drop-downs (`True` / `False`,
    `CSV` / `DB`); the empty choice removes the key.
  - Other values are typed. A path also has a folder icon in the box that opens a file or folder picker:
    a file for `Type = "CSV"`, a folder for `[Path]`.
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
| Hyperparameter | *Found* (folder · number of sets) / *Not found* |
| Results | *Found* / *Not found* |
| TensorBoard | *Found*, when event files are under the results |
| Weights & Biases | *Offline*, when `offline-run-*` folders are under the results |
| Prediction | *Found* (`[Prediction] Type = …` · sources · files with a prediction · columns) / *Not found*. Classification projects |
| Labels / inference | *Found* (result file, number of matches, columns) / *Not found*. Older format |

## Appearance

**Light / Dark** switches the theme straight away. The `--theme` option sets the theme at start.

## Items per page

Picks how many rows a Result page table (csv / tsv / jsonl) and a Hyperparameter config table show per page:
**20 / 30 / 40 / 50 / 100**. The default is 30. The choice applies at once and stays across tabs, project reloads and restarts (saved in the user
settings; on Linux `~/.config/Laboard/Laboard.conf`).

## Left sidebar

**Recent projects** lists the project that is loaded now.

## Project file reference

The project file is toml. Start one with **New** in Setting ([Load project file](#load-project-file)), or copy
[`template.toml`](../../template.toml) at the repository root (`cp template.toml my_project.toml`): it lists every key,
empty, or with an example to replace (`Task`, the login sections). Delete the login sections you don't use. Setting's
**Fields** shows and edits the same keys in the same order.

- **Names:** section and key names start with a capital letter (`DB` all in capitals, the paths section is
  `[Path]`). Names are read in any case, so `[paths]` is the same as `[Path]`.
- **Paths:** absolute, or relative to the folder that holds the toml.
- **Empty values:** leave keys you don't use as `""`. An empty key counts as not set.
- **True / False:** Laboard writes `True` / `False`; standard toml `true` / `false` is read too.
- **Remote paths:** any path can be on another machine, written `<host>:<path>`
  ([Files on a remote server](#files-on-a-remote-server)).

### Full example

```toml
[Project]
Name = "wafer-defect"              # empty: the Root folder's name
Root = "/path/to/repo"             # the project's git repository
Task = "classification, object detection"   # one task or several, comma-separated
DB = False                         # True when [Data] / [Label] / [Prediction] uses Type = "DB"

[DB]                               # used only with DB = True (and only shown in Setting then)
DB = "supabase"
DB_ip = "http://127.0.0.1:54322/"
# DB_ip = "postgresql://user:pw@host:5432/db"                 # PostgreSQL
# DB_ip = "mysql://user:pw@host:3306/db"                      # MySQL (MariaDB: mariadb://…)
# DB_ip = "sqlite:///data.db"                                 # SQLite (relative to the toml)
# DB_ip = "mssql://user:pw@host:1433/db"                      # MSSQL
# DB_ip = "oracle://user:pw@host:1521/?service_name=XEPDB1"   # Oracle

[Git]                              # fallbacks when git can't tell
Remote = "github.com:user/repo.git"
Branch = "main"

[Path]                             # each may hold one folder per task, e.g. Results/classification/<model>/
Models = "/path/to/repo/Models"
Hyperparameter = "/path/to/repo/Runs"
Results = "/path/to/repo/Results"

[Data]                             # the raw data files, one list for every task
Type = "CSV"                       # CSV | DB
File_path = "data.csv"             # CSV: the csv listing the files
Table = ""                         # DB: the table with one row per file
Raw = "file_path"                  # the column with each raw file's path

[Label]                            # the ground truth
Type = "CSV"                       # CSV | DB
File_path = ""                     # empty: the [Data] csv
Table = ""                         # empty: the [Data] table
Label = "label"                    # the ground-truth column; a task column gives each task its own row

[Prediction]                       # <Task>_<Key> sets a key for one task, e.g. Object_detection_Predict
Type = "CSV"                       # CSV | DB
File_path = "inference.csv"        # looked for under Path.Results/<task>/
Table = ""                         # DB: the table with the predictions
Predict = "predict"
Predict_score = "score"
```

### Keys by section

**`[Project]`**

| Key | Needed | What to put in it | Example |
| --- | --- | --- | --- |
| `Name` | optional | Project name shown in the top bar and on Home. Empty: the name of the `Root` folder | `"wafer-defect"` |
| `Root` | optional | Folder of the project's git repository. The git history, branch and remote shown in Laboard come from it. Empty: guessed from the paths you set, or the toml's folder | `"/path/to/repo"` |
| `Task` | **required** | One task, or several separated by commas: `classification`, `object detection` (`detection`), `instance segmentation`, `semantic segmentation`, `panoptic segmentation`, `anomaly detection`, `pose-estimation` (`keypoints`). Case, spaces, `_` and `-` don't matter. Empty: the [older format](#older-format) | `"classification, object detection"` |
| `DB` | with `Type = "DB"` | `True` when `[Data]`, `[Label]` or `[Prediction]` uses `Type = "DB"`. `False`: no database is read | `True` |

**`[DB]`**: the database connection. It is used, and shown in Setting, only when `[Project] DB = True`.
Supported databases: Supabase, PostgreSQL, MySQL, MariaDB, SQLite, MSSQL, Oracle. All but SQLite need their driver installed: `pip install ".[postgres]"` (PostgreSQL, Supabase), `".[mysql]"` (MySQL, MariaDB), `".[mssql]"`, `".[oracle]"`.

| Key | Needed | What to put in it | Example |
| --- | --- | --- | --- |
| `DB` | with DB | Database kind, shown only: `supabase`, `postgresql`, `mysql`, `mariadb`, `sqlite`, `mssql`, `oracle` | `"supabase"` |
| `DB_ip` | with DB | Database address: a Supabase URL (its Postgres on port 54322 is used), or a database URL ([database address](data.md#type--db)) | `"http://127.0.0.1:54323/"`, `"mysql://user:pw@host:3306/db"`, `"sqlite:///data.db"` |
| `Port`, `User`, `Password`, `Database` | optional | Not in the template. With a Supabase URL, add them when the defaults don't fit: 54322 / `postgres` / `postgres` / `postgres` | `Port = 5432` |
| `Limit` | optional | Most rows read from a table. Default 200,000 | `Limit = 500000` |

**`[Git]`**: used only when git can't tell.

| Key | Needed | What to put in it | Example |
| --- | --- | --- | --- |
| `Remote` | optional | Remote shown when the repository has no `origin` remote | `"github.com:user/repo.git"` |
| `Branch` | optional | Branch shown when `HEAD` is detached or `Root` isn't a git repository | `"main"` |

**`[Path]`**: each folder may hold one sub-folder per task, e.g. `Models/classification/<model>/`.

| Key | Needed | What to put in it | Shown on |
| --- | --- | --- | --- |
| `Models` | optional | Folder of model checkpoints (`.pt`, `.pth`, `.onnx`, `.safetensors`, `.ckpt`, …), sub-folders included | [Model](model.md) |
| `Hyperparameter` | optional | Folder with one sub-folder per training run, each holding json / yaml / toml configs (and `trainer_state.json`) | [Hyperparameter](hyperparameter.md) |
| `Results` | optional | Folder of result files: csv, logs, images, TensorBoard events. `[Prediction] Type = "CSV"` looks for its files here (`Results/<task>/`) | [Result](result.md) |

**`[Data]`**: the list of raw data files. All tasks share one list ([Data setup](data.md#data-setup)).

| Key | `CSV` | `DB` | What to put in it | Example |
| --- | --- | --- | --- | --- |
| `Type` | required | required | Where the list comes from: `CSV` or `DB` | `"CSV"` |
| `File_path` | required | – | The csv (or tsv / jsonl / parquet) with one row per raw file | `"data.csv"` |
| `Table` | – | required | The table with one row per raw file, `table` or `schema.table` | `"semiconductor"` |
| `Raw` | optional | optional | The column with each raw file's path. Empty: guessed from `file_path`, `data_path`, `path`, `image`, `filename`, … | `"file_path"` |

**`[Label]`**: the ground truth. Its rows are matched to the data files by their file-path column
([Label setup](data.md#label-setup-label)).

| Key | `CSV` | `DB` | What to put in it | Example |
| --- | --- | --- | --- | --- |
| `Type` | required | required | Where the labels are: `CSV` or `DB` | `"CSV"` |
| `File_path` | optional | – | The labels csv. Empty: the `[Data]` csv | `"labels.csv"` |
| `Table` | – | optional | The labels table. Empty: the `[Data]` table | `"semiconductor"` |
| `Label` | for labels | for labels | The ground-truth column, shared by every task. A table with one row per file and task (a `task` column) gives each task the label in its own row | `"label"` |

Without `Label`, there is no ground truth.

**`[Prediction]`**: the model's predictions. Any key can be set for a single task as `<Task>_<Key>`, e.g.
`Instance_segmentation_Predict` ([Prediction setup](data.md#prediction-setup-prediction)).

| Key | `CSV` | `DB` | What to put in it | Example |
| --- | --- | --- | --- | --- |
| `Type` | required | required | Where the predictions are: `CSV` or `DB` | `"CSV"` |
| `File_path` | required | – | Result file name or glob, looked for under `[Path] Results/<task>/` (all of `Results` without task folders), or an absolute path. Each matching file is one source you can pick on the Data page | `"inference.csv"` |
| `Table` | – | required | The table holding the predictions | `"semiconductor"` |
| `Predict` | required | required | The predicted-class column | `"predict"` |
| `Predict_score` | optional | optional | The score column | `"score"` |

### Files on a remote server

Write a path as `<host>:<path>` to read it from another machine. It works for every path:

- the `[Path]` folders, e.g. `Hyperparameter = "gcloud:~/laboard/Runs"`;
- `[Data]` / `[Label]` / `[Prediction]` `File_path`, e.g. `File_path = "ssh:~/wafer/data.csv"`;
- the file-path column of a csv or DB table, e.g. `ssh:/data/wafer/train/Normal/0001.jpg`.

`ssh:/…` is an absolute path on the server, and `ssh:~/…` a path under the login user's home folder. Laboard logs
in to the server and never changes anything on it.

**Example csv** (`data.csv`, next to the project file):

```csv
file_path,type,label
ssh:/data/wafer/train/Normal/0001.jpg,train,Normal
ssh:~/wafer/valid/Scratch/0102.jpg,valid,Scratch
ssh:~/wafer/test/Donut/0203.jpg,test,Donut
```

**Example project file** (`my_project.toml`, which holds the login too):

```toml
[Data]
Type = "CSV"
File_path = "data.csv"
Raw = "file_path"

[ssh]                    # logs in with: ssh -i ~/.ssh/my-key ubuntu@1.2.3.4
key_name = "my-key"      # a key under ~/.ssh, or the key file's own path when it has a "/"
user_name = "ubuntu"
ip = "1.2.3.4"
```

**What is read, and when**

| Path | On every load | Later |
| --- | --- | --- |
| `[Path] Models` | Copied to a temp folder: files under 500 MB | – |
| `[Path] Hyperparameter` | Copied: only the config files (json / yaml / toml under 2 MB) | – |
| `[Path] Results` | Copied: files under 50 MB | – |
| `[Data]` / `[Label]` / `[Prediction]` `File_path` | Copied: the file (under 50 MB). Relative paths inside a remote csv are read under its folder on the server | – |
| Data files a csv / table lists | Only their size and time, in one ssh call per server | The Data page copies the file it shows, and its thumbnails, and keeps them until Laboard exits |

While you view an [older commit](../../README.md#viewing-a-past-commit), remote `[Path]` folders stay empty: they
have no git history.

**How to log in: the project file's login sections**

The part before the colon names a section of the project file itself (with Setting's edits, when there are any):

| Prefix | Section | How it logs in | Keys |
| --- | --- | --- | --- |
| `ssh:` | `[ssh]` | `ssh -i ~/.ssh/<key_name> <user_name>@<ip>` | `key_name`, `user_name`, `ip` (required) |
| `gcloud:` | `[gcloud]` | `gcloud compute ssh <instance_name> --zone <zone>` | `instance_name` (required), `zone` |
| `az:` | `[az]` | `az ssh vm --name <vm_name> --resource-group <resource-group>` | `vm_name`, `resource-group` |
| `aws:` | `[aws]` | sends the public key with `aws ec2-instance-connect send-ssh-public-key`, then `ssh -i <private key> <instance-os-user>@<public ip>` | `instance-id`, `instance-os-user`, `ssh-public-key` (required), `availability-zone` |
| `abc:` | `[abc]` | the login named in its `type` key | as for that type |

```toml
[gcloud]                        # gcloud compute ssh my-vm --zone us-west1-b
instance_name = "my-vm"
zone = "us-west1-b"

[az]                            # az ssh vm --name my-vm --resource-group my-rg
vm_name = "my-vm"
resource-group = "my-rg"

[aws]                           # sends the public key, then ssh -i ~/.ssh/my-key ec2-user@<public ip>
instance-id = "i-0123456789abcdef0"
instance-os-user = "ec2-user"
ssh-public-key = "~/.ssh/my-key.pub"
availability-zone = "us-east-1a"

[ssh]                           # ssh -i ~/.ssh/my-key ubuntu@1.2.3.4
key_name = "my-key"
user_name = "ubuntu"
ip = "1.2.3.4"

[train-vm]                      # for train-vm:… paths; type says how to log in
type = "gcloud"
instance_name = "train-vm"
zone = "asia-northeast3-a"
```

- **Type:** a section's `type` key, else its name: `gcloud`, `az`, `aws` or `ssh`. A section of any name can instead
  hold the login command, `command = "ssh -i ~/.ssh/my-key ubuntu@1.2.3.4"`, used as written.
- **Other keys** of a gcloud / az / aws section are passed on as `--key value` (`true`: the bare flag), e.g.
  `project = "my-gcp-project"`, `tunnel-through-iap = true`. `_` and `-` in key names are the same.
- **gcloud:** the first call runs gcloud once with `--dry-run` to get the plain ssh command it uses. Later calls run
  that ssh directly over one shared connection, so they take milliseconds instead of gcloud's seconds.
- **aws:** the private key is `ssh-public-key` without `.pub` (or `private-key`), and the address is the instance's
  public ip (or `host`). The sent key lasts 60 s and is sent again when a login fails.
- **No password prompt:** the login must work without one. Use a key without a passphrase or one loaded in
  `ssh-agent`, and connect once by hand so the server's host key is known.
- **When it fails:** the status bar says why, e.g. `the project file has no [ssh] section`,
  `[ssh] in the project file: no ip`. Data files are still listed, and Detected shows *Remote data files · Unreachable*.
- **Keep a project file with logins out of public repositories.** It holds ips, user names and instance names.

### Where each section is used

| Section | Used by |
| --- | --- |
| `[Project]`, `[Git]` | Top bar, Home, git log popup |
| `[Data]`, `[DB]` | [Data](data.md), Home's Data card |
| `[Label]` | The [Data](data.md) page's ground truth and class list |
| `[Prediction]` | The [Data](data.md) page's predictions |
| `[Path] Models` | [Model](model.md), Home's Model card |
| `[Path] Hyperparameter` | [Hyperparameter](hyperparameter.md), Home's Latest hyperparameter card |
| `[Path] Results` | [Result](result.md), Home's Result card |
| `[gcloud]`, `[az]`, `[aws]`, `[ssh]` (or any name) | Logging in for `host:path` values ([Files on a remote server](#files-on-a-remote-server)) |

Any part that Laboard can't find stays empty; the Detected card and the status bar show which.

### Older format

When `Task` is empty, the older format is read: `[Path] Data` says where the data is
and `[Labels]` where predictions are. See the [older format](data.md#older-format-task-is-empty)
in the Data docs for the order sources are tried in.

```toml
[Path]
Data = "/path/to/data.csv"         # a file list (csv / tsv / jsonl / parquet), or a section name such as "DB"

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
