# Data

<p align="center">
  <img src="../assets/LABOARD_DATA.png" alt="Data" width="900"/>
</p>



The Data page is a viewer for every file in the dataset. For each file you can see:

- the file itself
- its split (train / valid / test)
- its label
- what a model predicted for it

## Data setup

Three sections of the project file (toml) decide what the Data page shows.

| Section | Decides | Per task? |
| --- | --- | --- |
| `[Data]` | The raw data files | One list shared by every task |
| `[Label]` | Each file's ground truth | One `Label` column shared by every task; a task column gives each task its own rows ([Label setup](#label-setup-label)) |
| `[Prediction]` | Each file's model prediction | Read for each task ([Prediction setup](#prediction-setup-prediction)) |

This format applies when `[Project] Task` names one or more of the tasks below ([Task: single / multi](#task-single--multi)).
With an empty Task, the [older format](#older-format-task-is-empty) is used.

| `[Data] Type` | Where the file list comes from | Split |
| --- | --- | --- |
| `DB` | A database table (one row = one file): Supabase, PostgreSQL, MySQL, MariaDB, SQLite, MSSQL, Oracle | A split column (`type`, `status`, …) |
| `CSV` | A csv listing the files (one row = one file) | A split column (`type`, `status`, …) |

- **Type values:** `DB` and `CSV` are read in any case (`csv` works too). An empty `Type` shows
  `[Data] Type is not set` in the status bar.
- **How much is read:** up to 200,000 rows (files), whatever the source.
- **Where the ground truth comes from:** always `[Label]`. A label column in a prediction result file is never
  used as the ground truth.
- **Remote files:** a file path can be on a server, e.g. `ssh:/data/img/0001.jpg`
  ([Data on a remote server](#data-on-a-remote-server-ssh)).
- **Required columns and label formats:** see [Data format: required columns and label values](#data-format-required-columns-and-label-values).

### Task: single / multi

`[Project] Task` names one task, or several separated by commas.

```toml
Task = "classification"                                            # a single task
Task = "classification, instance segmentation, object detection"   # several tasks
```

- **Tasks:** `classification`, `object detection` (or `detection`), `instance segmentation`,
  `semantic segmentation`, `panoptic segmentation`, `anomaly detection`, `pose-estimation` (or `keypoints`). Case,
  spaces, `_` and `-` don't matter (`Object_detection` works). An unknown name is noted and skipped.
- **One raw data source:** `[Data]` is shared by every task; what differs per task is the ground truth
  (`[Label]`) and the predictions (`[Prediction]`).
- **Folders:** with a folder per task under `[Path]` Models / Hyperparameter / Results, each task is kept apart.

  ```text
  test_projects/
  ├── Data/semiconductor_AD_df.csv     # the raw data (one)
  ├── Models/classification/<model>/
  ├── Runs/classification/<model>/      # [Path] Hyperparameter
  └── Results/
      ├── classification/<model>/inference.csv
      ├── instance segmentation/
      ├── object detection/
      ├── anomaly detection/
      └── pose-estimation/
  ```

  - The Model page and Home count `Models/<task>/<model>` as one model.
  - CSV predictions are looked for under `Results/<task>/`.
- **Data page:** with several tasks, a **Task** drop-down in the viewer header picks whose ground truth and
  predictions are shown. File info lists every task's ground truth as `Label · <task>`.
- **Home:** the task name lists every task (e.g. *Classification · Instance segmentation · Object detection*).

### Changing the settings

**On the Setting page (recommended)**

1. In **Setting → Load project file**, pick the toml and click **Load**.
2. In the **Fields** list below, click **Edit** next to `[Data]` → `Type`.
3. Pick `CSV` / `DB` in the popup's drop-down and click **Save**.
4. Fill in the keys that Type needs (table below) the same way. For a path, the folder icon in the box
   opens a file / folder picker.

- **Applied at once:** Save reloads the project, so the Data page shows the change right away.
- **The file is left alone:** the toml on disk isn't changed. To keep the change, use **Save Changed** to write
  a new toml. Clicking **Load** again goes back to what the file says.
- **Rows that depend on Type:**
  - `Table` is shown only for `Type = "DB"`, `File_path` only when it isn't DB.
  - The `[DB]` section is shown only while `[Project] DB = True`.
- **Descriptions:** hover a key or its value to see what to put in it.

**Editing the toml file**

Edit the toml in any editor, then click **Load** in Setting. To start one, use **New** in Setting or copy
`template.toml` at the repository root, which lists every key. Section and key names are read in any case (`[Path]` and
`[paths]` are the same).

### `[Data]` keys at a glance

| Key | `DB` | `CSV` | Meaning |
| --- | --- | --- | --- |
| `Type` | required | required | `DB` / `CSV` |
| `Table` | required | – | Table name, `table` or `schema.table` |
| `File_path` | – | required | The csv listing the files |
| `Raw` | optional | optional | Column with each raw file's path (e.g. `file_path`). Empty: found automatically (table below) |

Paths such as `File_path` are absolute, or relative to the folder that holds the toml.

### Type = DB

Each row of a database table is one data file. Supabase, PostgreSQL, MySQL, MariaDB, SQLite, MSSQL and Oracle
work (read through SQLAlchemy).

```toml
[Project]
DB = True                          # True to use a database

[DB]                               # the connection
DB = "supabase"
DB_ip = "http://127.0.0.1:54322/"  # a Supabase URL → its Postgres on port 54322

[Data]
Type = "DB"
Table = "semiconductor"
Raw = "file_path"
```

- **Connection (`[DB] DB_ip`):**
  - A Supabase URL (such as `http://127.0.0.1:54323/`) connects to the Postgres on that host. The defaults are
    port `54322` and `postgres` for the user, password and database; when they don't fit, add `Port`, `User`,
    `Password` or `Database` to `[DB]`.
  - Any other database takes its address (URL). Its driver is installed separately
    (`pip install "laboard[mysql]"`, …).

    | Database | `DB_ip` | extra |
    | --- | --- | --- |
    | PostgreSQL | `postgresql://user:pw@host:5432/db` | `postgres` |
    | MySQL | `mysql://user:pw@host:3306/db` | `mysql` |
    | MariaDB | `mariadb://user:pw@host:3306/db` | `mysql` |
    | SQLite | `sqlite:///data.db` (relative to the toml) / `sqlite:////abs/path/data.db` | none |
    | MSSQL | `mssql://user:pw@host:1433/db` | `mssql` |
    | Oracle | `oracle://user:pw@host:1521/?service_name=XEPDB1` | `oracle` |

  - To pick another driver, write the SQLAlchemy URL as is, e.g. `mysql+mysqldb://…` or
    `mssql+pyodbc://…?driver=ODBC+Driver+18+for+SQL+Server`, and install that driver yourself.
  - URL-encode a password holding `@`, `/` or `:` (`@` → `%40`).
- **`Table`:** `table` or `schema.table` (MSSQL `dbo.voc`, Oracle `OWNER.voc`, MySQL `db.voc`). A mixed-case name
  is quoted, so it must match exactly.
- **Column names:** the columns named in `Raw`, `Label` and `Predict` are found in any case (Oracle stores them
  upper case).
- **How much is read:** at most `Limit` rows (default 200,000), ordered by the first column.
- **`[Project] DB`:** when it is `False`, the database isn't read and the note
  `[Data] Type = DB, but [Project] DB = False` appears.
- **Columns the table needs:**

  | Column | Required | Content |
  | --- | --- | --- |
  | File path | yes | The raw file's path: the column named in `[Data] Raw`, else see [Columns](#columns) |
  | Split | no | `type`, `status`, `split`, … Without it every file is Unused |
  | Created | no | `create_date`, … Used for File info's Created, the files-per-month chart and past-commit views |
  | Trained | no | `trained` / `used` (true / false). Home shows how many files were used in training |
  | Task | no | `object` / `task`. Home's task name |
  | id | no | File info's Row |

- **Example (`semiconductor` table):** `id`, `file_path`, `object`, `type`, `extension`, `label`,
  `create_date`, `trained`, `predict`
  - `file_path` is the path, `label` the ground truth and `type` the split.
  - The table's `predict` column isn't used as the prediction for Type = DB data; predictions come from
    `[Prediction]`.
- **Past commits:** when "Show project as of" shows an older commit, rows created after it (by the created
  column) are hidden.
- **Connection status:** see Setting → Detected (`Database · Connected` / `Unreachable`).

### Type = CSV

Each row of a csv is one data file. tsv, jsonl and parquet files are read the same way.

```toml
[Data]
Type = "CSV"
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Raw = "file_path"
```

- **Columns the csv needs:** the same as a Type = DB table. A file-path column is required; ground-truth
  (`label`) and split columns are used when present.

  ```csv
  data_path,label,status
  /mnt/data/Dataset/wafer/test/Normal/image_001.jpg,Normal,test
  /mnt/data/Dataset/wafer/train/Scratch/image_002.jpg,Scratch,train
  ```

- **Relative paths:** paths in the csv are read relative to the csv's folder.
- **Wrong path:** when `File_path` isn't a file, the note `[Data] File_path … is not a file` appears.
- **No path column found:** name it in `[Data] Raw`.

### Data on a remote server (`ssh:`)

A file path in the csv or DB table can start with `ssh:`. Laboard then logs in to the server with the `[ssh]`
section of the project file and reads the file there.

```csv
file_path,type,label
ssh:/data/wafer/train/Normal/0001.jpg,train,Normal
ssh:~/wafer/valid/Scratch/0102.jpg,valid,Scratch
ssh:~/wafer/test/Donut/0203.jpg,test,Donut
```

```toml
# the project file (e.g. my_project.toml)
[ssh]                    # logs in with: ssh -i ~/.ssh/my-key ubuntu@1.2.3.4
key_name = "my-key"
user_name = "ubuntu"
ip = "1.2.3.4"
```

- **Paths:** `ssh:/…` is an absolute path on the server, and `ssh:~/…` a path under the login user's home folder.
- **What is read:** loading reads only each remote file's size and time, in one ssh call. The Data page copies the
  file it shows, and its thumbnails, when it shows them, and keeps them until Laboard exits.
- **A csv on the server:** `File_path = "ssh:~/wafer/data.csv"` copies the csv at load. Relative paths inside it
  are read under its folder on the server.
- **Other servers:** `gcloud:`, `az:`, `aws:` and any `abc:` prefix log in with the section of the same name. See
  [Setting · Files on a remote server](setting.md#files-on-a-remote-server) for every login and its keys.
- **When the server can't be reached:** the files are still listed with their split and label, but can't be shown.
  The status bar says why, and Detected shows *Remote data files · Unreachable*.

### Columns

Each meaning's column is found by name (any case; the first match wins).

| Meaning | Names recognised |
| --- | --- |
| File path | The column named in `[Data] Raw`, else `file_path`, `data_path`, `path`, `filepath`, `file`, `image`, `image_path`, `img`, `filename` |
| Split | `type`, `status`, `split`, `subset`, `set` |
| Task | `object`, `task` |
| Created | `create_date`, `created_at`, `created`, `date`, `timestamp` |
| Trained | `trained`, `used` |
| id | `id` |

- **Path column check:** a column with a matching name whose values don't look like paths (no extension
  or `/`) isn't used; another column whose values do look like paths is used instead.
- **Split column guess:** without a matching name, a column whose values are all split values is used.

### Split values

These are read as follows (any case). Anything else becomes **Unused**.

| Value in the data | Read as |
| --- | --- |
| `train`, `training` | Train |
| `val`, `valid`, `validation`, `eval`, `dev` | Valid |
| `test`, `testing` | Test |

### Folder grouping

The sidebar's folders group files by their directory without the split part, so `train/cat/` and
`valid/cat/` both show as the folder `cat`.

## Label setup (`[Label]`)

The ground truth picks its source with `Type` (`CSV` / `DB`) too, and `Label` names its one column, shared by every task.

| Key | `CSV` | `DB` | Meaning |
| --- | --- | --- | --- |
| `Type` | required | required | `CSV` / `DB` |
| `File_path` | optional | – | The labels csv (empty: `[Data]`'s) |
| `Table` | – | optional | The labels table (empty: `[Data]`'s) |
| `Label` | column | column | The ground-truth column (e.g. `label`) |

- **Columns:** rows are matched to the data files by the raw-file path column (`Raw`, empty: `[Data] Raw`).
  Labels in the `[Data]` csv or table are read from there.
- **Several tasks:** give the csv / table a task column (`task` or `object`) and list a file once per task. Each
  task reads `Label` from the row whose task matches, and `[Data]` lists each file once
  ([Table shape](#table-shape-one-row-per-file--one-row-per-task)).
- **Json labels** (coco format, as made by `Data_prep/raw_to_csv`) are drawn over the image on the Data page:
  `["cat", "dog"]` (class names), `[{"category", "bbox": [x, y, w, h]}]` (boxes),
  `[{"category", "segmentation"}]` (polygons or RLE), `[{"category", "bbox", "keypoints"}]` (keypoints, with the
  coco skeleton for 17 points) and `{"mask_path", "segments_info"}` (a coco panoptic png). Text shows a summary
  such as `20 objects · chair ×5, vase ×4`. A json prediction is drawn on the Predict pane the same way.
- **No ground truth:** with no `Label`, the note `[Label] no Label` appears and nothing has ground truth. With a
  task column but no rows for a task, only that task has none.

```toml
[Label]                                 # a single task, CSV
Type = "CSV"
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Label = "label"

[Label]                                 # several tasks, DB (task + json label columns)
Type = "DB"
Table = "voc"
Label = "label"

[Label]                                 # several tasks, CSV (task + json label columns)
Type = "CSV"
File_path = "/mnt/data/Dataset/COCO/COCO_2017_dataset.csv"
Label = "label"
```

## Data format: required columns and label values

The columns a csv / table needs, and how to store values in the label column.

### Required and optional columns

| Column | Needed | Name (any case) | Value |
| --- | --- | --- | --- |
| File path | **required** | the one named in `[Data] Raw`, else `file_path`, `data_path`, `path`, `image`, `filename`, … ([Columns](#columns)) | The raw file's path. DB: an **absolute path** · CSV: absolute, or relative to the csv file's folder. Either can be on a server: `ssh:/…` ([remote data](#data-on-a-remote-server-ssh)) |
| Label | required to see the ground truth | the one named in `[Label] Label` (e.g. `label`) | See [Label values](#label-values) below |
| Task | **required** when a file has one row per task | `task`, `object` | A task name from `[Project] Task` (e.g. `classification`, `detection`) |
| Split | optional (recommended) | `type`, `status`, `split`, `subset`, `set` | `train` / `valid` (`val`, `validation`) / `test`. Missing or anything else: Unused |
| Created | optional | `create_date`, `created_at`, `created`, `date`, `timestamp` | ISO format `2024-01-05 10:00:00`, or a DB timestamp. Missing: the file's modified time |
| Trained | optional | `trained`, `used` | `true` / `false` (`1`, `yes` work too) |
| id | optional | `id` | Shown in File info |

- **No file-path column, or values that don't look like paths:** nothing is read and the note
  `no file-path column found` appears.
- **Rows with an empty path** are skipped.
- **No label column:** the files show up without ground truth and the note `[Label] Label: no column …` appears.

### Table shape: one row per file / one row per task

There is always one label column (`[Label] Label`); with several tasks, a task column splits the rows.

| Shape | A row is | Label column | Use it for |
| --- | --- | --- | --- |
| One row per file | one file | one column (e.g. `label`) | a single task (with several, every task gets the same value) |
| One row per task | one file × one task | one column (e.g. `label`) + the task column | several tasks |

- **When it counts as one row per task:** the table has a task column and the same file path appears in more than
  one row. Each task then reads its label from the row with its task value, and `[Data]` lists the file once.
- **Task values:** must match the names in `[Project] Task`. Case, spaces, `_` and `-` don't matter
  (`instance_segmentation` = `instance segmentation`); `detection` reads as `object detection` and `keypoints` as
  `pose-estimation`.
- **Split and created date:** taken from the file's first row. Store the same values in every row of a file.

### Label values

A label is a **plain string** such as a class name, or **json in coco format**. Json is drawn over the image on the
Data page and summarised in text, e.g. `20 objects · chair ×5, vase ×4`. Predictions (`[Prediction] Predict`) in
the same format are drawn on the Predict pane the same way.

| Task | Format | Example |
| --- | --- | --- |
| classification | a string, or a list of class names | `cat` · `["cat", "dog"]` |
| object detection | `[{"category", "bbox"}]` | `[{"category": "cat", "bbox": [10, 20, 100, 80]}]` |
| instance segmentation | `[{"category", "segmentation"}]`, one object per instance | `[{"category": "cat", "segmentation": [[10, 20, 110, 20, 60, 100]]}]` |
| semantic segmentation | `[{"category", "segmentation"}]`, one object per category covering all of its area | `[{"category": "cat", "segmentation": [[10, 20, 110, 20, 60, 100], [200, 30, 260, 30, 230, 90]]}]` |
| pose-estimation | `[{"category", "bbox", "keypoints"}]` | `[{"category": "person", "bbox": [5, 5, 50, 120], "keypoints": [30, 12, 2, 0, 0, 0, …]}]` |
| panoptic segmentation | `{"mask_path", "segments_info"}` | `{"mask_path": "/data/panoptic/0001.png", "segments_info": [{"id": 3226956, "category": "person", "bbox": [413, 158, 53, 138]}]}` |

- **Coordinates:** image pixels, origin at the top left, x to the right, y down.
- **bbox:** `[x, y, w, h]` (top-left corner, width, height), not `[x1, y1, x2, y2]`.
- **instance / semantic segmentation:** the same format, drawn the same way; they differ only in what one object
  covers. `segmentation` is a list of polygons `[[x1, y1, x2, y2, …], …]` (an object may have several, each with 3+ points),
  or uncompressed RLE `{"counts": [...], "size": [h, w]}` (column-major, starting with a run of 0s). Compressed RLE
  (a string `counts`) isn't drawn.
- **keypoints:** `[x, y, v]` repeated for each keypoint. Points with `v = 0` aren't drawn; with 17 points the coco
  person skeleton is drawn too.
- **panoptic:** `mask_path` is the **absolute path** of a coco panoptic png. A pixel's value `R + 256·G + 256²·B` is
  its segment `id`; each `segments_info` entry needs `id` and `category` for its area to be filled in the category's
  colour, and a `bbox` puts the name at its centre.
- **category:** any string. A name always gets the same colour. The Data page's class list is every category in
  the labels.
- **Values that aren't json:** anything that doesn't start with `[` or `{`, or doesn't parse as json, is shown as
  text only.

### When saving

- **Save real json:** `str(list)` in Python writes `['cat', 'dog']` with single quotes, which isn't json, so it is
  shown as text and not drawn. Convert with `json.dumps(label)` first.
- **CSV:** json holds `"` and `,`, so the value must be quoted with `"` doubled to `""`. pandas `to_csv` and Python's
  `csv` module do this for you.
- **DB:** make the label column `JSONB` (recommended) or `TEXT`. With `JSONB` the database checks the json and can
  query inside it, e.g. `label->0->'bbox'`.

### Examples

A one-row-per-task csv and its settings (the format `Data_prep/raw_to_csv` writes):

```csv
file_path,label,task,type,create_date
/data/img/0001.jpg,"[""cat"", ""dog""]",classification,train,2024-01-05 10:00:00
/data/img/0001.jpg,"[{""category"": ""cat"", ""bbox"": [10, 20, 100, 80]}]",detection,train,2024-01-05 10:00:00
/data/img/0002.jpg,"[""dog""]",classification,valid,2024-01-06 09:30:00
```

```toml
[Project]
Task = "classification, detection"

[Data]
Type = "CSV"
File_path = "/data/dataset.csv"
Raw = "file_path"

[Label]
Type = "CSV"
File_path = "/data/dataset.csv"
Label = "label"
```

## Prediction setup (`[Prediction]`)

Predictions pick their source with `Type` too, independently of the data (e.g. data from DB, predictions
from CSV).

- **Per task:** every key applies to every task. To set one for a single task, write `<Task>_<Key>`, e.g.
  `Instance_segmentation_File_path`, `Instance_segmentation_Predict`, `Object_detection_Type`.
- **Source names:** with several tasks, a source's name in the Results drop-down starts with its task, and only
  the picked task's sources are listed.

| Key | `CSV` | `DB` | Meaning |
| --- | --- | --- | --- |
| `Type` | required | required | `CSV` / `DB` |
| `File_path` | required | – | Result file name / glob |
| `Table` | – | required | Table holding the predictions |
| `Predict` | required | required | Predicted-class column |
| `Predict_score` | optional | optional | Score column |

In Setting, `Table` is shown only for `Type = "DB"`, and `File_path` only when it isn't DB.

### Prediction Type = CSV

```toml
[Prediction]
Type = "CSV"
File_path = "inference.csv"
Predict = "classification"
Predict_score = "AD_score"
```

- **Finding result files:** `File_path` is a file name or glob looked for under `[Path] Results/<task>/`
  (all of `[Path] Results` when it has no task folders), or an absolute path.
  - Every match is one source. With one `inference.csv` per model folder, for example, a **Results**
    drop-down appears in the viewer header to pick the model.
- **Matching the data:** rows are matched to data files by the result file's path column (same names as
  [Columns](#columns)); by file name when the full paths differ.
- **Missing columns:** when a column named in `Predict` / `Predict_score` isn't there, a `… no column …`
  note appears and that line shows `—`.

### Prediction Type = DB

```toml
[Prediction]
Type = "DB"
Table = "semiconductor"
Predict = "predict"
Predict_score = "AD_score"
```

- **Connection:** needs the `[DB]` connection and `[Project] DB = True`. When `[Data]` reads the same table,
  it is queried once.
- **Matching the data:** by the table's file-path column.

## Common notes

Notes shown in the status bar and Setting's Detected card, and what to do about them.

| Note | Cause / fix |
| --- | --- |
| `[Data] Type is not set` | Set `[Data] Type` to `DB` or `CSV` |
| `[Data] Type = DB, but [Project] DB = False` | Set `[Project] DB` to `True` |
| `DB … unavailable (…)` | The database can't be reached. Check `[DB] DB_ip`, that the server runs, and the table name |
| `DB … unavailable (No module named …; install it with: pip install "laboard[…]")` | The database's driver isn't installed. Install the extra it names (e.g. `pip install ".[mysql]"`) |
| `[Data] File_path … is not a file` | The CSV path is wrong. Pick the file again |
| `… no file-path column found` | No path column found. Name it in `[Data] Raw` |
| `[Label] Label: no column …` | The labels csv / table has no such column. Check its name |
| `[Label] no Label: …` | `[Label] Label` is not set |
| `[Project] Task: unknown task …` | Not a task name. Use one from [Task](#task-single--multi) |
| `[Prediction] … no column …` | A column named in `Predict` / `Predict_score` isn't in the results |
| `[Prediction] <task> File_path … not found under Path.Results/<task>` | The task's results folder has no result file |
| `Path.Data … is not a table file` | Older format: `[Path] Data` is a folder. Point it at a csv / tsv / jsonl / parquet |
| `the project file has no [<host>] section` | Add a section named like the path's prefix to the project file, e.g. `[ssh]` for `ssh:…` |
| `[<host>] in the project file: no …` | A required key is missing or empty, e.g. `ip` in `[ssh]` |
| *Remote data files · Unreachable* (Detected) | The server can't be reached. Check the login section in the project file (`[ssh]`, `[gcloud]`, …), and that the server is on |
| `No data rows found` | Nothing could be read because of one of the above |

## Older format (Task is empty)

When `[Project] Task` is empty, the older format is used. Laboard uses
the first of these sources that works:

1. **A database table:** `[DB] Table`. If the database can't be reached, the status bar says so and the
   next source is tried. `[Path] Data = "DB"` (a section name) reads only that database.
2. **A table file:** the csv / tsv / jsonl / parquet that `[Path] Data` points at. A folder isn't read; the note
   `Path.Data … is not a table file` appears.

- **Predictions:** come from the `[Labels]` section (`Result_file`, …).
- **Without `[Labels]`:** the data's own `predict` column is used as the prediction.

## Left sidebar

### Folders card

This card lists each data folder and how many files it has. Click a folder to show it; its first file
is selected. When there are more than 9 folders, the list scrolls.

### Files list

- **All / Train / Valid / Test** limits the list, the viewer and the thumbnails to one split.
- Each row shows a split colour dot, the file extension, the file name and the split name.
- The count at the top reads like `120 of 3,400 · cat/`.

## Viewer (centre)

### Header

- The file name and its split.
- **Raw / Predict / Both**, which chooses what the viewer shows:
  - **Raw:** the file with its label.
  - **Predict:** the file with the prediction chips (see below).
  - **Both:** Raw and Predict side by side.
- **Task** drop-down. This appears only with several tasks. It picks whose ground truth and predictions are shown.
- **Results** drop-down. This appears only when there is more than one prediction result file (the
  `File_path` of `[Prediction] Type = "CSV"` matches several, e.g. one `inference.csv` per model). It picks which
  result file the predictions come from.

### Image

Only images (png, jpg, jpeg, bmp, gif, webp, tif, tiff) are drawn. Other formats show a striped
placeholder.

| Action | Effect |
| --- | --- |
| Scroll | Zoom in/out around the cursor (up to 40× the fitted size) |
| Shift+scroll, or drag | Pan |
| Double-click | Fit the image to the pane |
| **Reset** | Fit and centre every pane |

In **Both**, each pane keeps its own zoom and position. The zoom lasts until you show another file.

### Navigation

- `12 of 3,400` shows where you are in the folder.
- **Previous / Next** move through the files in the current split filter, wrapping around at the ends.
- The thumbnail strip shows up to 30 files on each side of the current one. Each thumbnail carries the
  last 6 characters of the file name and a split dot. Click one to show it.

### Prediction colours

The label is always the data's own ground truth (`[Label]`, or the `label` column in the older format).

Predictions come from `[Prediction]` (`[Labels]` in the older format). Rows are matched by path, or by
file name when the paths differ. The prediction box has one line each for `Predict` and `Predict_score`
(`predict : Normal`, `predict_score : 7.80`), each with a dot:

| Mark | Meaning |
| --- | --- |
| Green dot | The value equals the label |
| Red dot | The value is a different class |
| No dot | Anything else (a score, text, …) |
| `—` | The value is empty |

If the file isn't in the prediction source, the box says `not in <source>`. Without a prediction setup, or
when it can't be read, it says `none · predict column is empty`.

## Right panel

### Data splits

- The source, and a line such as `3,400 rows from <where> · root <folder>`.
- A stacked bar of the splits.
- One row per split with its count, percentage, and how the split was decided. For example:
  - `type = 'train'` (from a split column)
  - `no split column`
- Click a split row to filter to that split, which is the same as the sidebar buttons. Click it again
  to show all splits.
- **Overlap check (file name):** *No overlap*, or a warning such as *3 shared* when the same file name
  appears in more than one split.

### File info

These rows are always shown:

| Row | Shows |
| --- | --- |
| Path | Full path to the file |
| Split | The file's split |
| Dimensions | Image width × height |
| Format | File extension |
| Label | The file's ground truth. With several tasks, one `Label · <task>` row per task |
| Size | File size, or `missing` if the file isn't on disk |
| Modified | The file's modification time |

Some rows appear only when the source has the data for them:

| Row | Appears when |
| --- | --- |
| Created | The data has a `created`-type column |
| Trained | The data has a `trained`/`used` column |
| Row | The data comes from the database; the row's `id` |

With predictions, each one is also listed as `key · column` (e.g. `predict · classification`), plus the
**Result file** the values came from (or `no row` when the file isn't in it).

### Folder summary

- **Files** and **Size** of the current folder.
- Where the folder was read from.
- How many directories its files sit in on disk.
