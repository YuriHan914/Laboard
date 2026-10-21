<p align="center">
  <img src="../assets/LABOARD_SETTING.png" alt="Setting" width="900"/>
</p>

# Setting

**English** | [한국어](../ko/setting.md)

On the Setting page you can:

- load a project file
- read it in a preview
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

Notes include things like *Nothing found in paths.runs* or *DB … unavailable; using paths.data*.

## Preview

A read-only copy of the loaded file, with line numbers. Section headers (`[project]`, `[paths]`, …) are bold.

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
| Labels / inference | *Found* (result file, number of matches, columns) / *Not found* |

## Appearance

**Light / Dark** switches the theme straight away. The `--theme` option sets the theme at start.

## Left sidebar

**Recent projects** lists the project that is loaded now.

## Project file reference

Relative paths are resolved from the folder that holds the toml file.

```toml
[project]
name = "my-project"                # default: the root folder's name
root = "/path/to/repo"             # git history, branch and remote come from here
                                   # default: the first of paths.*, or the toml's folder

[paths]                            # absolute, or relative to the toml
data = "/path/to/data"
models = "/path/to/models"
runs = "/path/to/runs"
results = "/path/to/results"

[git]                              # optional fallbacks when git can't tell
# branch = "main"                  # when HEAD is detached or root is not a git repository
# remote = "github.com/me/repo"    # when there is no origin remote

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
result_file = "inference.csv"      # name / relative path / glob under paths.results; each match is one source
infer = "classification"           # any other key: a column shown on the Data page
score = "AD_result"
# path = "data_path"               # column that matches rows to data files (guessed when left out)
# label = "labels"                 # label column (guessed when left out)
```

| Section | Used by |
| --- | --- |
| `[project]`, `[git]` | Top bar, Home, git log popup |
| `[paths] data`, `[db]`, `[data]` | [Data](data.md), Home's Data card |
| `[paths] models`, `[models]` | [Model](model.md), Home's Model card |
| `[paths] runs` | [Run](run.md), Home's Latest run card |
| `[paths] results` | [Result](result.md), Home's Result card |
| `[labels]` | The [Data](data.md) page's label and prediction chips |

Only `[paths]` (or `[db]`) is needed to see anything. Any part that Laboard can't find stays empty, and
the Detected card shows which parts those are.
