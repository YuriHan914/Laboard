<p align="center">
  <img src="../assets/LABOARD_HOME.png" alt="Home (light)" width="900"/>
  <img src="../assets/LABOARD_HOME_DARK.png" alt="Home (dark)" width="900"/>
</p>

# Home

**English** | [한국어](../ko/home.md)

Home is the project at a glance. The centre has four summary cards: Data, Model, Latest run and Result.
The right side shows the project's git history. Each card has an **Open** link that jumps to its page.

If no project is loaded, Home shows *No project loaded* and points you to Setting.

## Left sidebar

### Project card

| Row | Shows |
| --- | --- |
| Name | `[project] name` (or the root folder's name), with the task as a pill (see the Data card) |
| Remote | The `origin` URL |
| Branch | The current branch and how it compares with its upstream (e.g. `ahead 1`, `up to date with origin/main`). While viewing an older commit: `detached at <hash> · read-only snapshot` |
| Commits | The number of commits and of contributors |
| Runs linked | How many runs were found under `paths.runs` |

### Root folders

This list has one row for the project root and one for each `[paths]` entry (`data`, `models`, `runs`,
`results`), with its path relative to the root. **Open** shows the folder in your file manager. If the
folder doesn't exist, a message appears in the status bar.

## Summary cards

The cards sit in two columns. When the centre is narrow they drop to one column and scroll.
When a card has nothing to show, it says what is missing, for example *No model files found in paths.models.*

### Data

| Part | Shows |
| --- | --- |
| Task pill | The most common value of the data's `task`/`object` column. With no such column: *Classification* if the files have labels, otherwise *Unlabeled* |
| Note | Where the data was read from, the number of classes and the file extensions |
| Tiles | If the data has a `trained`/`used` column: **Total files · Used in training · Not yet trained**. Otherwise: **Total files · Classes · Folders** |
| Files added per month | Bars for the last 8 months. The date comes from the data's `created` column when there is one, otherwise from each file's modification time |
| Legend | The number of files in each split (Train / Valid / Test / Unused) |

### Model

| Part | Shows |
| --- | --- |
| Tiles | **Models** (top-level entries under `paths.models`), **Files** (model files), **Last updated** (the newest file's age) |
| Format | A stacked bar and legend of the file formats (PyTorch, ONNX, safetensors, …), with a count and extensions for each |
| Table | Up to 8 models, most recently changed first: **Model · Formats · Files · Size** |

### Latest run

This card shows the run that was changed most recently.

- A note gives the run's name, the last commit that touched its folder, when it was modified and the
  config files it was read from.
- Below that are the first 12 hyperparameters, in two columns.

### Result

This card looks for a file named `accuracy.csv` anywhere under `paths.results`.

**When `accuracy.csv` exists**, the card shows:

- A chart with **train loss** and **valid loss** as lines (left axis) and **inference ms / image** as
  bars (right axis), one point per row.
- Three tiles: **Best valid loss** (with its commit), **Fastest** (with its model) and **Rows in csv**.

The file has no required header; rows that don't fit the layout (such as a header line) are skipped.
Expected columns:

```
commit, model, train_loss, valid_loss, ms_per_image
```

**When there is no `accuracy.csv`**, the card shows how many result files there are and the two most
common file types.

## Git history (right panel)

This panel lists up to 100 commits from the current branch and its upstream. It starts at the commit
being shown, so older snapshots don't list newer commits.

Each commit shows:

- the commit message
- ref pills: the current branch is dark, other branches are grey, tags are green
- *Local · not pushed* or *Remote · not pulled* when the commit is only on one side (only when the
  branch has an upstream)
- hash · author · date · number of files changed

**Opening a commit.** Click a commit to open it and list its files: green for added / modified /
renamed / copied, red for deleted. Click it again to close it. The newest commit starts open.

**All / This file.** *This file* keeps only the commits that touched the project's most frequently
changed file (counted over the last 100 commits). On the timeline, a filled dot marks the latest commit
that touched that file.

If the project root isn't a git repository, the panel says so.
