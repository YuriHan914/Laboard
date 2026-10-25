<p align="center">
  <img src="../assets/LABOARD_RUN.png" alt="Hyperparameter" width="900"/>
</p>

# Hyperparameter

**English** | [한국어](../ko/run.md)

The Hyperparameter page shows one training run's hyperparameter set:

- where it lives and which commit last touched it
- how far training has got
- every hyperparameter in its config files, with the file each value came from

## What counts as a hyperparameter set

- **A set (a training run)** is any folder under `[Path] Hyperparameter`, up to 3 levels deep, that holds config files
  (`.json`, `.yaml`, `.yml`, `.toml`, each under 2 MB).
- **Nesting:** runs don't nest. Once a folder counts as a run, the folders inside it are not separate runs.
- **Limit:** up to 500 runs are read.
- **YAML:** configs are read only if PyYAML is installed; otherwise they are skipped.
- **Order:** the most recently modified run comes first.
- **Name:** a set's name is its path relative to `[Path] Hyperparameter`. If `[Path] Hyperparameter` is itself a run, its name
  comes from `exp_name`, `run_name` or `name` in its config, otherwise the folder name.

## Left sidebar

**Hyperparameter** is a folder tree (*N sets*). Next to each set is:

- its best metric as a percentage, when `trainer_state.json` has a `best_metric` between 0 and 1
- otherwise, the date it was last modified

## Header card

| Part | Shows |
| --- | --- |
| Title | The run's name |
| Subtitle | The run folder's path · the last commit that touched it · when it was last modified |
| **Open folder** | Opens the run folder in your file manager |
| Progress bar | `epoch / total epochs` from `trainer_state.json` |
| Epoch text | e.g. `Epoch 12 / 50`. Without `trainer_state.json` it says `50 epochs configured` or `No trainer_state.json` |
| Best | `best 0.9132` when `trainer_state.json` has a `best_metric` |

The total number of epochs is read from the first of these that is set:

1. `num_train_epochs` in `trainer_state.json`
2. `epochs` in the config
3. `num_train_epochs` in the config
4. `max_epochs` in the config

The config here means files whose names contain `config`, `args` or `hparams`.

## Hyperparameters

### Header

- **Read from source at launch** lists the config files that were read: the first four, then `+N more`.
- **Re-read** loads the project file again. Use it to pick up changes to configs.

### Sections

There is one card per config file (`trainer_state.json` is only used for progress). The cards sit one
per row, as wide as the column.

- **Open / close:** click a card's header (▸ title · row count · file name) to open its table, and again to close
  it. Every card starts closed and stays as you left it until you leave the Hyperparameter page; opening and
  closing keep the page's scroll position.
- **Title:** the file name in sentence case. For example, `training_args.json` becomes *Training args*.
- **Keys:** nested keys are flattened with dots, such as `optimizer.lr`.
- **Long values:** lists longer than 8 items are shown as `[N items]`, and values longer than 90
  characters are cut with `…`.
- **Pages:** a card with more than 20 rows shows them 20 at a time. **Rows 1–20 of N** and **Previous / Next**
  sit under the table; turning a page keeps the page's scroll position, and each card keeps its page until you
  leave the Hyperparameter page. Up to 2,000 rows are read from one file.
