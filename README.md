# 🧪 Laboard


<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Docs/assets/LABOARD_LOGO_DARK.png"/>
    <img src="Docs/assets/LABOARD_LOGO.png" alt="Laboard" width="136"/>
  </picture>
</p>

<p align="center">
  <a href="README.ko.md"><img src="https://img.shields.io/badge/%F0%9F%87%B0%F0%9F%87%B7_%ED%95%9C%EA%B5%AD%EC%96%B4-9fe870?style=for-the-badge" alt="한국어"/></a>
  <a href="README.md"><img src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8_English-e8ebe6?style=for-the-badge" alt="English"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge" alt="Version 1.0.0"/>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"/></a>
  <a href="https://pypi.org/project/PyQt6/"><img src="https://img.shields.io/badge/PyQt6-6.7%2B-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6 6.7+"/></a>
  <a href="https://www.sqlalchemy.org/"><img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.0+"/></a>
  <a href="https://github.com/lutzroeder/netron"><img src="https://img.shields.io/badge/Netron-8.0%2B-555555?style=for-the-badge" alt="Netron 8.0+"/></a>
  <a href="https://onnx.ai/"><img src="https://img.shields.io/badge/ONNX-1.15%2B-005CED?style=for-the-badge&logo=onnx&logoColor=white" alt="ONNX 1.15+"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License: MIT"/></a>
</p>


<br></br>

<table>
  <tr>
    <td align="center" width="50%"><img src="Docs/assets/LABOARD_HOME.png" alt="Home (light)"/><br/><sub>Light</sub></td>
    <td align="center" width="50%"><img src="Docs/assets/LABOARD_HOME_DARK.png" alt="Home (dark)"/><br/><sub>Dark</sub></td>
  </tr>
</table>


<br></br>

A PyQt6 desktop experiment tracker for machine-learning projects. Point it at one project file (`.toml`)
that says where your data, models, training runs and results live and which git repository to follow,
and Laboard shows all of them in one window.

Laboard only reads: it never edits your files, your database or your repository. The one exception is
the **Fetch** button in the git log popup, which runs `git fetch` and so updates only the
remote-tracking branches.

</br>

---

## 🚀 Features

* Data viewer with train / valid / test splits, labels and model predictions side by side
* Model graphs in an embedded [Netron](https://netron.app) view, with parameter counts (no GPU or torch needed)
* Training runs: progress and every hyperparameter from the config files
* Result charts from csv / jsonl / TensorBoard files, with smoothing and multi-curve comparison
* Git history, and the whole project viewed as of any earlier commit
* Data from a database table (Supabase, PostgreSQL, MySQL, MariaDB, SQLite, MSSQL, Oracle) or a table file (csv / tsv / jsonl / parquet)
* Files on another machine, read over gcloud / az / aws / ssh
* Light and dark themes
* Text on screen (table values, hyperparameters, settings, …) can be selected by dragging the mouse and copied with Ctrl+C or the right-click menu

---

## 🛠️ Installation

- Recommend Python 3.11+

1. Download from git repository
```bash
git clone https://github.com/YuriHan914/Laboard.git
cd Laboard
pip install -e .                        # no database (csv / tsv / jsonl files, SQLite)
pip install -e ".[postgres]"            # PostgreSQL, Supabase
pip install -e ".[mysql,oracle]"        # several
pip install -r requirements.txt         # all (= pip install -e ".[all]")

```

2. pip install 
```bash
pip install laboard                    # no database (csv / tsv / jsonl files, SQLite)
pip install "laboard[postgres]"        # with the driver of the database you use
pip install "laboard[mysql,oracle]"    # several
pip install "laboard[all]"             # every database driver + parquet
```

| extra | Database | Driver installed |
| --- | --- | --- |
| `postgres` | PostgreSQL, Supabase | `psycopg2-binary` |
| `mysql` | MySQL, MariaDB | `PyMySQL` |
| `mssql` | Microsoft SQL Server | `pymssql` |
| `oracle` | Oracle | `oracledb` |
| `sqlite` | SQLite | none (comes with Python) |
| `parquet` | `.parquet` data files | `pandas` |

Using a database without its driver names the extra to install in the `DB … unavailable` note, e.g.
`install it with: pip install "laboard[mysql]"`. For development, install with `pip install -e ".[all]"` (or
`pip install -r requirements.txt`).

### Cloud CLIs for remote files (optional)

Only needed when a path in the project file is on another machine, written `gcloud:…`, `az:…` or `aws:…`
([Accessing files on remote machines](#accessing-files-on-remote-machines)). Laboard logs in by running these
command-line tools, which pip doesn't install. Install the one you use, make sure it is on your `PATH`, and log in
once yourself.

| Path prefix | CLI | Install | Log in once |
| --- | --- | --- | --- |
| `gcloud:` | Google Cloud CLI | [Install the gcloud CLI](https://docs.cloud.google.com/sdk/docs/install-sdk) | `gcloud auth login`, then `gcloud config set project <project-id>` |
| `az:` | Azure CLI | [Install the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) | `az login`, then `az extension add --name ssh` (for `az ssh vm`) |
| `aws:` | AWS CLI | [Install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | `aws configure` (or `aws configure sso`) |
| `ssh:` | OpenSSH | comes with Linux / macOS / Windows 10+ | – |

- **No prompts:** Laboard runs them in the background, so the login must work without a password prompt. Connect
  to the server once by hand so its host key is known.
- **Login details** (instance name, zone, user, ip, …) go in the project file's `[gcloud]`, `[az]`, `[aws]` or
  `[ssh]` section; [`template.toml`](template.toml) lists the keys of each.

---

## ▶️ Quick Start

```bash
python -m laboard                             # runs without a toml; create one in the app
python -m laboard  --project my_project.toml  # runs with the given toml
```

### Command-line options

| Option | Effect |
| --- | --- |
| `--project TOML` | Load this project file at start and open on Home |
| `--tab home\|data\|model\|hyperparameter\|result\|setting` | Start on this tab. The default is `home`, or `setting` when no project is given |
| `--theme light\|dark` | Start in the light or dark theme (default: light) |
| `--frameless` | Draw Laboard's own dark title bar instead of the system one |
| `--screenshot out.png` | Render the window once, save it as a PNG and exit. Works headless with `QT_QPA_PLATFORM=offscreen` |


### Making a project toml file

Fill in only the parts you need and leave the rest empty.
1. Start Laboard, click **New** in **Setting**, fill in the form of each section and save
2. Or copy [`template.toml`](template.toml) below, fill it in and save
    <details>
    <summary>template.toml</summary>

      ```toml
      # Laboard project file.
      # One raw data source ([Data]) is shared by every task; each task has its own labels ([Label]) and predictions
      # ([Prediction]). Fill in the keys your data uses and leave the others empty (""). Paths are absolute, or relative
      # to this file. Settings shows every key below with a description of what to put in it. Names are read in any case.

      [Project]
      Name = ""                                       # project name; empty: the root folder's name
      Root = ""                                       # folder of the project's git repository
      Task = "classification,object detection,..."    # one task or several, comma-separated: classification, object detection,
                                                      # instance segmentation, semantic segmentation, panoptic segmentation,
                                                      # anomaly detection, pose-estimation
      DB = False                                      # True when [Data], [Label] or [Prediction] uses Type = "DB"

      [DB]                                            # database connection, shown and used when [Project] DB = True
      DB = ""                                         # supabase
      DB_ip = ""                                      # e.g. "http://127.0.0.1:54323/" or "postgresql://user:password@host:5432/db"

      [Git]                                           # fallbacks when git can't tell
      Remote = ""                                     # e.g. "github.com:user/repo.git"
      Branch = ""                                     # e.g. "main"

      [Path]                                          # each may hold one folder per task, e.g. Results/classification/<model>/
      Models = ""                                     # folder with model checkpoints
      Hyperparameter = ""                             # folder with one sub-folder per training run
      Results = ""                                    # folder with result files

      [Data]                                          # the raw data files, one list for every task
      Type = ""                                       # CSV | DB
      File_path = ""                                  # CSV: the csv listing the files
      Table = ""                                      # DB: table with one row per file
      Raw = ""                                        # CSV / DB: column with each raw file's path, e.g. "file_path"

      [Label]                                         # ground truth, one column for every task
      Type = ""                                       # CSV | DB
      File_path = ""                                  # CSV: the labels csv
      Table = ""                                      # DB: table with the labels
      Label = ""                                      # its column; a task column picks each task's row

      [Prediction]                                    # any key can be set for one task as <Task>_<Key>, e.g. Instance_segmentation_Predict
      Type = ""                                       # CSV | DB
      File_path = ""                                  # CSV: result file name / glob under Path.Results/<task>
      Table = ""                                      # DB: table with the predictions
      Predict = ""                                    # predicted-class column
      Predict_score = ""                              # score column


      [gcloud]                                        # gcloud compute ssh <instance_name> --zone <zone>
      instance_name="instance name"                   # required: the VM instance's name
      zone="instance zone"                            # e.g. "us-west1-b"

      [az]                                            # az ssh vm --name <vm_name> --resource-group <resource-group>
      vm_name="VM name"                               # the Azure VM's name
      resource-group="resource group"                 # its resource group

      [aws]                                           # sends the public key (EC2 Instance Connect), then ssh -i <private key> <user>@<public ip>
      instance-id="instance ID"                       # required: e.g. "i-0123456789abcdef0"
      instance-os-user="ec2-user"                     # required: the login user, e.g. "ec2-user", "ubuntu"
      ssh-public-key="file://~/.ssh/id_ed25519.pub"   # required: public key; the private key is this file without .pub
      availability-zone="AZ(zone)"                    # e.g. "us-east-1a"; its region finds the instance's public ip

      [ssh]                                           # ssh -i ~/.ssh/<key_name> <user_name>@<ip>
      key_name=""                                     # a key under ~/.ssh, or the key file's own path when it has a "/"
      user_name=""                                    # login user; empty: ssh's default
      ip=""                                           # required: server address (ip or host name)


      ```
    </details>

    <details>
    <summary>Project file reference</summary>

      <br>

      - Section and key names can be written in any case (`[Path]` = `[paths]`).
      - Paths are absolute, or relative to the folder that holds the project file.
      - An empty value (`""`) counts as not set.
      - Any path can be on another machine, written `<host>:<path>` (see [below](#accessing-files-on-remote-machines)).

      **`template.toml`** (as in the repository; Setting's **New** asks for the same sections and keys in a form):

      Laboard project file. One raw data source ([Data]) is shared by every task; each task has its own labels ([Label]) and predictions ([Prediction]). Fill in the keys your data uses and leave the others empty (""). Paths are absolute, or relative to this file. Settings shows every key below with a description of what to put in it. Names are read in any case.

      | Section | Needed | Key | Value | Comment |
      | --- | --- | --- | --- | --- |
      | **`[Project]`** |  |  |  |  |
      |  | optional | `Name` | `""` | project name; empty: the root folder's name |
      |  | optional | `Root` | `""` | folder of the project's git repository |
      |  | **required** | `Task` | `"classification,object detection,..."` | one task or several, comma-separated: classification, object detection, instance segmentation, semantic segmentation, panoptic segmentation, anomaly detection, pose-estimation |
      |  | with `Type = "DB"` | `DB` | `False` | True when [Data], [Label] or [Prediction] uses Type = "DB" |
      | **`[DB]`** |  |  |  | database connection, shown and used only when [Project] DB = True |
      |  | with DB | `DB` | `""` | supabase |
      |  | with DB | `DB_ip` | `""` | e.g. "http://127.0.0.1:54323/" or "postgresql://user:password@host:5432/db" |
      | **`[Git]`** |  |  |  | fallbacks used only when git can't tell |
      |  | optional | `Remote` | `""` | e.g. "github.com:user/repo.git" |
      |  | optional | `Branch` | `""` | e.g. "main" |
      | **`[Path]`** |  |  |  | each may hold one folder per task, e.g. Results/classification/&lt;model&gt;/ |
      |  | optional | `Models` | `""` | folder with model checkpoints |
      |  | optional | `Hyperparameter` | `""` | folder with one sub-folder per training run |
      |  | optional | `Results` | `""` | folder with result files |
      | **`[Data]`** |  |  |  | the raw data files, one list for every task |
      |  | required | `Type` | `""` | CSV \| DB |
      |  | CSV: required | `File_path` | `""` | CSV: the csv listing the files |
      |  | DB: required | `Table` | `""` | DB: table with one row per file |
      |  | optional | `Raw` | `""` | CSV / DB: column with each raw file's path, e.g. "file_path" |
      | **`[Label]`** |  |  |  | ground truth, one column for every task |
      |  | required | `Type` | `""` | CSV \| DB |
      |  | CSV: optional | `File_path` | `""` | CSV: the labels csv |
      |  | DB: optional | `Table` | `""` | DB: table with the labels |
      |  | to show labels | `Label` | `""` | its column; a task column picks each task's row |
      | **`[Prediction]`** |  |  |  | any key can be set for one task as &lt;Task&gt;_&lt;Key&gt;, e.g. Instance_segmentation_Predict |
      |  | required | `Type` | `""` | CSV \| DB |
      |  | CSV: required | `File_path` | `""` | CSV: result file name / glob under Path.Results/&lt;task&gt; |
      |  | DB: required | `Table` | `""` | DB: table with the predictions |
      |  | required | `Predict` | `""` | predicted-class column |
      |  | optional | `Predict_score` | `""` | score column |
      | **`[gcloud]`** |  |  |  | gcloud compute ssh &lt;instance_name&gt; --zone &lt;zone&gt; |
      |  | **required** | `instance_name` | `"instance name"` | required: the VM instance's name |
      |  | optional | `zone` | `"instance zone"` | e.g. "us-west1-b" |
      | **`[az]`** |  |  |  | az ssh vm --name &lt;vm_name&gt; --resource-group &lt;resource-group&gt; |
      |  | optional | `vm_name` | `"VM name"` | the Azure VM's name |
      |  | optional | `resource-group` | `"resource group"` | its resource group |
      | **`[aws]`** |  |  |  | sends the public key (EC2 Instance Connect), then ssh -i &lt;private key&gt; &lt;user&gt;@&lt;public ip&gt; |
      |  | **required** | `instance-id` | `"instance ID"` | required: e.g. "i-0123456789abcdef0" |
      |  | **required** | `instance-os-user` | `"ec2-user"` | required: the login user, e.g. "ec2-user", "ubuntu" |
      |  | **required** | `ssh-public-key` | `"file://~/.ssh/id_ed25519.pub"` | required: public key; the private key is this file without .pub |
      |  | optional | `availability-zone` | `"AZ(zone)"` | e.g. "us-east-1a"; its region finds the instance's public ip |
      | **`[ssh]`** |  |  |  | ssh -i ~/.ssh/&lt;key_name&gt; &lt;user_name&gt;@&lt;ip&gt; |
      |  | optional | `key_name` | `""` | a key under ~/.ssh, or the key file's own path when it has a "/" |
      |  | optional | `user_name` | `""` | login user; empty: ssh's default |
      |  | **required** | `ip` | `""` | required: server address (ip or host name) |


    </details>



### Accessing files on remote machines

- With the sections below in the toml file, files can also be read from a remote machine.
- Remote login: register the keys for ssh or cloud login yourself beforehand. **Laboard does not register keys.**
- To read a file on a remote machine, start its path with the remote's name followed by `:`.

  | Remote name | How it logs in |
  | ------------ | --- |
  | `ssh:` | ssh, as above |
  | `gcloud:` | gcloud compute ssh |
  | `az:` | az ssh vm |
  | `aws:` | aws ec2-instance-connect |

  - Examples
    - **Folder** : ```"gcloud:/home/Runs"```
    - **File** : ```"gcloud:/home/img.png"```

- Other logins can be added at the end of the toml file

  | Prefix | Section | How it logs in |
  | --- | --- | --- |
  | `abc:` | `[abc]` | other cloud login |

  ```toml
  [train-vm]               # for train-vm:… paths
  type = "ssh"
  key_name = "train-key"
  user_name = "ubuntu"
  ip = "10.0.0.5"
  ```


## 🗂️ Data Format

The columns a csv / table needs when data is read with `[Data] Type = "CSV"` / `"DB"`, and how labels are stored.
The full description is in [Data · Data format](Docs/en/data.md#data-format-required-columns-and-label-values).

- **One row per file:** one label column, named with `Label = "label"`. Fits a single task.
- **One row per task:** a task column + the same one label column, for several tasks. A table where the same file
  path appears in several rows is read this way.


| Column | Needed | Value |
| --- | --- | --- |
| File path (`file_path`, …, set with `[Data] Raw`) | **required** | The raw file's path. DB: absolute · CSV: absolute, or relative to the csv's folder |
| Label (set with `[Label] Label`) | required to see the ground truth | See the label format below |
| Task (`task` / `object`) | **required** when a file has one row per task | A task name from `[Project] Task` |
| Split (`type`, `split`, …) | optional (recommended) | `train` / `valid` / `test` |
| Created (`create_date`, …) | optional | `2024-01-05 10:00:00` |



**Label format**: a plain string, or json in coco format. Json is drawn over the image on the Data page.

| Task | Format |
| --- | --- |
| classification | `cat` or `["cat", "dog"]` |
| object detection | `[{"category": "cat", "bbox": [x, y, w, h]}]` |
| instance segmentation | `[{"category": "cat", "segmentation": [[x1, y1, x2, y2, …]]}]`, one object per instance (polygons, or RLE `{"counts", "size"}`) |
| semantic segmentation | `[{"category": "cat", "segmentation": [[x1, y1, x2, y2, …], …]]}]`, one object per category covering all of its area (polygons, or RLE `{"counts", "size"}`) |
| pose-estimation | `[{"category": "person", "bbox": [x, y, w, h], "keypoints": [x, y, v, …]}]` |
| panoptic segmentation | `{"mask_path": "<absolute png path>", "segments_info": [{"id", "category", "bbox"}]}` |

- Instance and semantic segmentation use the same format and are drawn the same way; they differ only in what one
  object covers.
- Coordinates are image pixels (origin at the top left); a bbox is `[x, y, w, h]`.
- Save with `json.dumps`. `['cat']` written by `str(list)` (single quotes) isn't json and isn't drawn.
- Make a DB label column `JSONB` (recommended) or `TEXT`.

---

## 📚 Documentation

Each page has a detailed guide in [Docs](Docs/README.md).

| Page | What it is for |
| --- | --- |
| [Home](Docs/en/home.md) | Data / model / latest run / result summaries, next to the git history |
| [Data](Docs/en/data.md) | Browse every data file, its split and label, and compare it with model predictions |
| [Model](Docs/en/model.md) | A model file's graph in Netron, its properties and parameters by layer |
| [Hyperparameter](Docs/en/hyperparameter.md) | A training run's progress and all of its hyperparameters |
| [Result](Docs/en/result.md) | Charts from csv / jsonl / TensorBoard, curve comparison, tables, logs and images |
| [Setting](Docs/en/setting.md) | Load a project file, see what was detected, switch the theme, set Result and Hyperparameter table rows per page; the project file reference |
