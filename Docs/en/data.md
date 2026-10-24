<p align="center">
  <img src="../assets/LABOARD_DATA.png" alt="Data" width="900"/>
</p>

# Data

**English** | [한국어](../ko/data.md)

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
| `[Label]` | Each file's ground truth | One `<Task>_Label` per task ([Label setup](#label-setup-label)) |
| `[Prediction]` | Each file's model prediction | Read for each task ([Prediction setup](#prediction-setup-prediction)) |

This format applies when `[Project] Task` names one or more of the tasks below ([Task: single / multi](#task-single--multi)).
With an empty Task, the [older format](#older-format-task-is-empty) is used.

| `[Data] Type` | Where the file list comes from | Split |
| --- | --- | --- |
| `DB` | A database table (one row = one file) | A split column (`type`, `status`, …) |
| `CSV` | A csv listing the files (one row = one file) | A split column (`type`, `status`, …) |
| `Folder` | A scan of a dataset folder | The split folder in the path |

- **Type values:** `DB`, `CSV` and `Folder` are read in any case (`csv` works too). An empty `Type` shows
  `[Data] Type is not set` in the status bar.
- **How much is read:** up to 200,000 rows (files), whatever the source.
- **Where the ground truth comes from:** always `[Label]`. A label column in a prediction result file is never
  used as the ground truth.

### Task: single / multi

`[Project] Task` names one task, or several separated by commas.

```toml
Task = "classification"                                   # a single task
Task = "classification, segmentation, object detection"   # several tasks
```

- **Tasks:** `classification`, `object detection`, `segmentation`, `anomaly detection`, `pose-estimation`. Case,
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
      ├── segmentation/
      ├── object detection/
      ├── anomaly detection/
      └── pose-estimation/
  ```

  - The Model page and Home count `Models/<task>/<model>` as one model.
  - CSV predictions are looked for under `Results/<task>/`.
- **Data page:** with several tasks, a **Task** drop-down in the viewer header picks whose ground truth and
  predictions are shown. File info lists every task's ground truth as `Label · <task>`.
- **Home:** the task name lists every task (e.g. *Classification · Segmentation · Object detection*).

### Changing the settings

**On the Setting page (recommended)**

1. In **Setting → Load project file**, pick the toml and click **Load**.
2. In the **Fields** list below, click **Edit** next to `[Data]` → `Type`.
3. Pick `CSV` / `DB` / `Folder` in the popup's drop-down and click **Save**.
4. Fill in the keys that Type needs (table below) the same way. For a path, the folder icon in the box
   opens a file / folder picker.

- **Applied at once:** Save reloads the project, so the Data page shows the change right away.
- **The file is left alone:** the toml on disk isn't changed. To keep the change, use **Save as…** to write
  a new toml. Clicking **Load** again goes back to what the file says.
- **Rows that depend on Type:**
  - `Table` is shown only for `Type = "DB"`, `File_path` only when it isn't DB, `[Data] Raw` only when it isn't Folder.
  - `[Label]` gets a `<Task>_Label` row for each task of `[Project] Task`.
  - The `[DB]` section is shown only while `[Project] DB = True`.
- **Descriptions:** hover a key or its value to see what to put in it.

**Editing the toml file**

Edit the toml in any editor, then click **Load** in Setting. `template.toml` at the repository root lists
every key with empty values; copy it to start. Section and key names are read in any case (`[Path]` and
`[paths]` are the same).

### `[Data]` keys at a glance

| Key | `DB` | `CSV` | `Folder` | Meaning |
| --- | --- | --- | --- | --- |
| `Type` | required | required | required | `DB` / `CSV` / `Folder` |
| `Table` | required | – | – | Table name, `table` or `schema.table` |
| `File_path` | – | required | required | CSV: the file list · Folder: the dataset folder |
| `Raw` | optional | optional | – | Column with each raw file's path (e.g. `file_path`). Empty: found automatically (table below) |

Paths such as `File_path` are absolute, or relative to the folder that holds the toml.

### Type = DB

Each row of a database table is one data file. A local Supabase or any Postgres works.

```toml
[Project]
DB = True                          # True to use a database

[DB]                               # the connection
DB = "supabase"
DB_ip = "http://127.0.0.1:54323/"  # a Supabase URL → its Postgres on port 54322

[Data]
Type = "DB"
Table = "semiconductor"
Raw = "file_path"
```

- **Connection (`[DB] DB_ip`):**
  - A Supabase URL (such as `http://127.0.0.1:54323/`) connects to the Postgres on that host. The defaults are
    port `54322` and `postgres` for the user, password and database.
  - A `postgresql://user:password@host:5432/dbname` address works too.
  - When the defaults don't fit, add `Port`, `User`, `Password` or `Database` to `[DB]`. `Limit` sets the
    most rows read.
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

### Type = Folder

The dataset folder is scanned, one row per file. The split and the ground truth come from the folders.

```toml
[Data]
Type = "Folder"
File_path = "/mnt/data/Dataset/semiconductor_waifer_defect_classification"
```

- **Folder layout:** `<split>/<label>/<file>`.

  ```text
  semiconductor_waifer_defect_classification/
  ├── train/
  │   ├── Normal/   image_001.jpg …
  │   └── Scratch/  image_101.jpg …
  ├── valid/
  │   └── …
  └── test/
      └── …
  ```

- **Finding the split folder:** the first folder in the path named like a split (`train`, `valid`, `test`, …,
  see split values below). The **folder right after it** is the ground truth.
  - More folders above are fine: `root/2024/train/Normal/x.jpg` → split `train`, label `Normal`.
  - More folders below are fine too: `train/Normal/sub/x.jpg` still has the label `Normal`.
- **No ground truth when:**
  - there is no split folder, as in `Normal/x.jpg`: the split is Unused and there is no label;
  - the order is reversed (`Normal/train/x.jpg`) or there is no label folder (`train/x.jpg`).
- **`[Data] Raw`:** not used. Classification ground truth comes from this layout with `[Label] Type = "Folder"`.
- **Files left out:**
  - code, notebooks and markdown: `.py`, `.pyc`, `.ipynb`, `.sh`, `.md`
  - table files: `.csv`, `.tsv`, `.jsonl`, `.parquet`
  - hidden files and `__pycache__`
  - with `[Prediction] Type = "Folder"`, the prediction format (`.txt` / `.json`), so prediction files kept
    next to the data aren't taken for data

### Columns

For Type = DB / CSV, each meaning's column is found by name (any case; the first match wins).

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

The ground truth picks its source with `Type` (`CSV` / `DB` / `Folder`) too, with one `<Task>_Label` key per task.

| Key | `CSV` | `DB` | `Folder` | Meaning |
| --- | --- | --- | --- | --- |
| `Type` | required | required | required | `CSV` / `DB` / `Folder` |
| `File_path` | optional | – | optional | CSV: the labels csv (empty: `[Data]`'s) · Folder: the folder the label folders are in (empty: the data folder) |
| `Table` | – | optional | – | The labels table (empty: `[Data]`'s) |
| `<Task>_Label` | column | column | see below | `Classification_Label`, `Segmentation_Label`, `Object_detection_Label`, `Anomaly_detection_Label`, `Pose_estimation_Label` |

- **CSV / DB:** `<Task>_Label` is the column with that task's ground truth. Rows are matched to the data files by
  the raw-file path column (`Raw`, empty: `[Data] Raw`). Labels in the `[Data]` csv or table are read from there.
- **Folder:**
  - classification takes the ground truth from the `split/<class>/file` layout of `[Data] Type = "Folder"`; the
    value can be anything.
  - another task's `<Task>_Label` is a folder of label files (relative to `File_path`, or absolute). Each data file
    gets the label file with the same name (without the extension), and its file name is shown as the ground truth.
- **A task without one:** with no `<Task>_Label`, the note `[Label] no <Task>_Label` appears and that task has no
  ground truth.

```toml
[Label]                                 # a single task, CSV
Type = "CSV"
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Classification_Label = "label"

[Label]                                 # several tasks, DB
Type = "DB"
Table = "semiconductor"
Classification_Label = "label"
Segmentation_Label = "seg_label"
Object_detection_Label = "obj_label"

[Label]                                 # several tasks, Folder
Type = "Folder"
File_path = "/mnt/data/Dataset/semiconductor_waifer_defect_classification"
Classification_Label = "label"          # the class folders
Segmentation_Label = "seg_label"        # label files under File_path/seg_label/
```

## Prediction setup (`[Prediction]`)

Predictions pick their source with `Type` too, independently of the data (e.g. data from DB, predictions
from CSV).

- **Per task:** every key applies to every task. To set one for a single task, write `<Task>_<Key>`, e.g.
  `Segmentation_File_path`, `Segmentation_Predict`, `Object_detection_Type`.
- **Source names:** with several tasks, a source's name in the Results drop-down starts with its task, and only
  the picked task's sources are listed.

| Key | `CSV` | `DB` | `Folder` | Meaning |
| --- | --- | --- | --- | --- |
| `Type` | required | required | required | `CSV` / `DB` / `Folder` |
| `File_path` | required | – | required | CSV: result file name / glob · Folder: folder of prediction files |
| `Table` | – | required | – | Table holding the predictions |
| `Format` | – | – | optional | `txt` (default) / `json` |
| `Predict` | required | required | optional (json) | Predicted-class column (json: key) |
| `Predict_score` | optional | optional | optional (json) | Score column (json: key) |

In Setting, `Table` is shown only for `Type = "DB"`, `File_path` only when it isn't DB, and `Format` only for
`Type = "Folder"`.

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

### Prediction Type = Folder

```toml
[Prediction]
Type = "Folder"
File_path = "/mnt/data/predictions"
Format = "txt"
```

- **Where prediction files go:** one per data file, looked up in this order:
  1. under `File_path`, at the **same place with the same name** as in the data folder
     (`test/Normal/x.jpg` → `test/Normal/x.txt`);
  2. otherwise anywhere under `File_path` with the **same file name** (without the extension).
- **`Format = "txt"`:** the first line holds `<class> [score]`, separated by spaces or a comma.

  ```text
  Normal 0.93
  ```

- **`Format = "json"`:** an object, or the first object of a list.

  ```json
  {"class": "Normal", "score": 0.93}
  ```

  - `Predict` / `Predict_score` can name the keys.
  - Left empty, the class is the first of `predict`, `prediction`, `class`, `label`, `pred`, and the score the
    first of `predict_score`, `score`, `confidence`, `prob`, `probability`.
- **No files:** when there are no prediction files at all, the note `[Prediction] no .txt files under …`
  appears.

## Common notes

Notes shown in the status bar and Setting's Detected card, and what to do about them.

| Note | Cause / fix |
| --- | --- |
| `[Data] Type is not set` | Set `[Data] Type` to `DB`, `CSV` or `Folder` |
| `[Data] Type = DB, but [Project] DB = False` | Set `[Project] DB` to `True` |
| `DB … unavailable (…)` | The database can't be reached. Check `[DB] DB_ip`, that the server runs, and the table name |
| `[Data] File_path … is not a file` | The CSV path is wrong. Pick the file again |
| `… no file-path column found` | No path column found. Name it in `[Data] Raw` |
| `[Label] <Task>_Label: no column …` | The labels csv / table has no such column. Check its name |
| `[Label] <Task>_Label: no folder …` / `no label files in …` | The Folder label folder is missing or empty |
| `[Label] no <Task>_Label: …` | That task has no `<Task>_Label` |
| `[Project] Task: unknown task …` | Not a task name. Use one from [Task](#task-single--multi) |
| `[Prediction] … no column …` | A column named in `Predict` / `Predict_score` isn't in the results |
| `[Prediction] no .txt files under …` | The prediction folder has no prediction files. Check `File_path` and `Format` |
| `[Prediction] <task> File_path … not found under Path.Results/<task>` | The task's results folder has no result file |
| `No data rows found` | Nothing could be read because of one of the above |

## Older format (Task is empty)

When `[Project] Task` is empty, the older format is used. Laboard uses
the first of these sources that works:

1. **A database table:** `[DB] Table`. If the database can't be reached, the status bar says so and the
   next source is tried. `[Path] Data = "DB"` (a section name) reads only that database.
2. **A table file:** the csv / tsv / jsonl / parquet that `[Path] Data` points at, or one inside that folder.
   A file found automatically in a folder must point at real files.
3. **A folder scan:** the `[Path] Data` folder, read like [Type = Folder](#type--folder).

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

The label is always the data's own ground truth (the `label` column, or the folder name for a scan).

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
  - `split from folder name` (from a folder scan)
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
