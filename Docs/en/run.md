<p align="center">
  <img src="../assets/LABOARD_RUN.png" alt="Run" width="900"/>
</p>

# Run

**English** | [한국어](../ko/run.md)

The Run page shows one training run:

- where it lives and which commit last touched it
- how far training has got
- every hyperparameter in its config files, with the file each value came from
- the state of the GPU

## What counts as a run

- **A run** is any folder under `paths.runs`, up to 3 levels deep, that holds config files
  (`.json`, `.yaml`, `.yml`, `.toml`, each under 2 MB).
- **Nesting:** runs don't nest. Once a folder counts as a run, the folders inside it are not separate runs.
- **Limit:** up to 500 runs are read.
- **YAML:** configs are read only if PyYAML is installed; otherwise they are skipped.
- **Order:** the most recently modified run comes first.
- **Name:** a run's name is its path relative to `paths.runs`. If `paths.runs` is itself a run, its name
  comes from `exp_name`, `run_name` or `name` in its config, otherwise the folder name.

## Left sidebar

**Runs** is a folder tree. Next to each run is:

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
- **Show source / Values only** shows or hides the column that names each value's file.
- **Re-read** loads the project file again. Use it to pick up changes to configs or to the GPU state.

### Sections

There is one card per config file (`trainer_state.json` is only used for progress). The cards sit in
two columns, or one when the page is narrow.

- **Title:** the file name in sentence case. For example, `training_args.json` becomes *Training args*.
- **Keys:** nested keys are flattened with dots, such as `optimizer.lr`.
- **Long values:** lists longer than 8 items are shown as `[N items]`, and values longer than 90
  characters are cut with `…`.
- **Row limit:** each card shows up to 40 rows.

## GPU

This card reads GPU 0 from `nvidia-smi`:

- **Utilization:** a percentage, with a bar.
- **Memory:** used / total in GB, with a bar.
- **Temperature:** in °C, with a bar.

The GPU is read when the project loads, not continuously; click **Re-read** to refresh it. Without
`nvidia-smi` the card says *No GPU detected*.
