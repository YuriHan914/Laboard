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

The `[Data]` section of the project file (toml) decides which files the Data page lists, and the
`[Prediction]` section where each file's model prediction comes from. This format applies when
`[Project] Task = "classification"`; other tasks use the [older format](#older-format-task-is-not-classification).

| `[Data] Type` | Where the file list comes from | Ground truth (label) | Split |
| --- | --- | --- | --- |
| `DB` | A database table (one row = one file) | The `Label` column | A split column (`type`, `status`, …) |
| `CSV` | A csv listing the files (one row = one file) | The `Label` column | A split column (`type`, `status`, …) |
| `Folder` | A scan of a dataset folder | The folder name right after the split folder | The split folder in the path |

- **Type values:** `DB`, `CSV` and `Folder` are read in any case (`csv` works too). An empty `Type` shows
  `[Data] Type is not set` in the status bar.
- **How much is read:** up to 200,000 rows (files), whatever the source.
- **Where the ground truth comes from:** always the data. A label column in a prediction result file is never
  used as the ground truth.

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
  - `Table` is shown only for `Type = "DB"`.
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
| `Label` | optional | optional | – | Ground-truth column. Empty: `"label"` |
| `Path` | optional | optional | – | File-path column. Empty: found automatically (table below) |

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
Label = "label"
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
  | File path | yes | The data file's path. See [Columns](#columns) for the names (e.g. `file_path`) |
  | Ground truth | recommended | The column named in `[Data] Label` (default `label`). Without it files have no label |
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
Label = "label"
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
- **No path column found:** name it in `[Data] Path`.

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
- **`[Data] Label`:** not used.
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
| File path | The column named in `[Data] Path`, else `file_path`, `data_path`, `path`, `filepath`, `file`, `image`, `image_path`, `img`, `filename` |
| Ground truth | The column named in `[Data] Label` (default `label`) |
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

## Prediction setup (`[Prediction]`)

Predictions pick their source with `Type` too, independently of the data (e.g. data from DB, predictions
from CSV).

| Key | `CSV` | `DB` | `Folder` | Meaning |
| --- | --- | --- | --- | --- |
| `Type` | required | required | required | `CSV` / `DB` / `Folder` |
| `Path` | required | – | required | CSV: result file name / glob · Folder: folder of prediction files |
| `Table` | – | required | – | Table holding the predictions |
| `Format` | – | – | optional | `txt` (default) / `json` |
| `Predict` | required | required | optional (json) | Predicted-class column (json: key) |
| `Predict_score` | optional | optional | optional (json) | Score column (json: key) |

In Setting, `Table` is shown only for `Type = "DB"` and `Format` only for `Type = "Folder"`.

### Prediction Type = CSV

```toml
[Prediction]
Type = "CSV"
Path = "inference.csv"
Predict = "classification"
Predict_score = "AD_score"
```

- **Finding result files:** `Path` is a file name or glob looked for under `[Path] Results`, or an absolute
  path.
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
Path = "/mnt/data/predictions"
Format = "txt"
```

- **Where prediction files go:** one per data file, looked up in this order:
  1. under `Path`, at the **same place with the same name** as in the data folder
     (`test/Normal/x.jpg` → `test/Normal/x.txt`);
  2. otherwise anywhere under `Path` with the **same file name** (without the extension).
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
| `… no file-path column found` | No path column found. Name it in `[Data] Path` |
| `… no 'label' column; files have no ground truth` | No ground-truth column. Name it in `[Data] Label` |
| `[Prediction] … no column …` | A column named in `Predict` / `Predict_score` isn't in the results |
| `[Prediction] no .txt files under …` | The prediction folder has no prediction files. Check `Path` and `Format` |
| `No data rows found` | Nothing could be read because of one of the above |

## Older format (Task is not classification)

When `[Project] Task` is empty, `object detection` or `segmentation`, the older format is used. Laboard uses
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
- **Results** drop-down. This appears only when there is more than one prediction result file (the
  `Path` of `[Prediction] Type = "CSV"` matches several, e.g. one `inference.csv` per model). It picks which
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
| Label | The file's label |
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
