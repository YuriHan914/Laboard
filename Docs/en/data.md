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

## Where the data comes from

Laboard uses the first of these sources that works:

1. **A database table:** `[db]`, either a local Supabase or any Postgres. If the database can't be
   reached, the status bar says so and Laboard falls back to the next source.
2. **A table file** under `paths.data` (csv / tsv / jsonl / parquet), or the file set by
   `[data] table`. Its path column must point at files that exist.
3. **A folder scan:** every file under `paths.data`, skipping code, notebooks, markdown and table files.
   The split and label are taken from ImageFolder-style paths such as `train/<label>/x.jpg`.

Up to 200,000 rows or files are read.

**Columns.** For tables and databases, Laboard finds the columns by their usual names. You can set any
of them yourself with `columns = {…}`.

| Meaning | Names recognised (first match wins) |
| --- | --- |
| path | `file_path`, `data_path`, `path`, `filepath`, `file`, `image`, `image_path`, `img`, `filename` |
| label | `class`, `labels`, `label`, `cls`, `class_name`, `category`, `target` |
| split | `type`, `status`, `split`, `subset`, `set` |
| task | `object`, `task` |
| created | `create_date`, `created_at`, `created`, `date`, `timestamp` |
| trained | `trained`, `used` |
| predict | `predict`, `prediction`, `pred`, `predicted` |
| id | `id` |

**Split values.** These are read as follows (case-insensitive). Anything else becomes **Unused**.

| Value in the data | Read as |
| --- | --- |
| `train`, `training` | Train |
| `val`, `valid`, `validation`, `eval`, `dev` | Valid |
| `test`, `testing` | Test |

**Folders.** Files are grouped into folders by their directory, with the split part removed. So
`train/cat/` and `valid/cat/` are both shown in the folder `cat`.

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
- **Results** drop-down. This appears only when `[labels] result_file` matches more than one file, for
  example one `inference.csv` per model. It picks which result file the labels and predictions come from.

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

**With a `[labels]` section**, the label and the predictions come from the chosen result file. Rows are
matched by path, or by file name when the paths differ. Every column named in `[labels]` becomes a chip:

| Chip | Meaning |
| --- | --- |
| Green | The value equals the label |
| Red | The value is a different class |
| Grey | Anything else (a score, text, …) |
| `—` | The value is empty |

If the file isn't in the result file, the chip says `not in <file>`.

**Without `[labels]`**, the prediction comes from the data's own `predict` column. It is green when it
matches the label and red when it doesn't. If the column is empty, the chip says
`none · predict column is empty`.

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

With `[labels]`, each configured column is also listed as `key · column`, plus the **Result file** the
values came from (or `no row` when the file isn't in it).

### Folder summary

- **Files** and **Size** of the current folder.
- Where the folder was read from.
- How many directories its files sit in on disk.
