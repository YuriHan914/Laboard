import json
import re
import tomllib
from datetime import date, datetime, time

TASKS = ("classification", "object detection", "instance segmentation", "semantic segmentation", "panoptic segmentation",
         "anomaly detection", "pose-estimation")
TASK_ALIASES = {"detection": "objectdetection", "keypoint": "poseestimation", "keypoints": "poseestimation"}
SCHEMA = (("project", ("name", "root", "task", "db")),
          ("db", ("db", "db_ip")),
          ("git", ("remote", "branch")),
          ("paths", ("models", "hyperparameter", "results")),
          ("data", ("type", "file_path", "table", "raw")),
          ("label", ("type", "file_path", "table", "label")),
          ("prediction", ("type", "file_path", "table", "predict", "predict_score")))
ENUMS = {("project", "db"): (True, False),
         ("data", "type"): ("CSV", "DB"),
         ("label", "type"): ("CSV", "DB"),
         ("prediction", "type"): ("CSV", "DB")}
BARE_VALUE = re.compile(r"^(\s*[\w.-]+\s*=\s*)(?!(?:true|false|inf|nan)\b)([A-Za-z_][\w-]*)(\s*(?:#.*)?)$", re.M)
HEADER = re.compile(r"^\s*\[([^\[\]]+)\]\s*(#.*)?$")
ALIASES = {"path": "paths", "lables": "labels"}


def task_id(name):
    tid = re.sub(r"[^a-z]", "", str(name).lower())
    return TASK_ALIASES.get(tid, tid)


def title(name):
    if "." in name:
        return ".".join(map(title, name.split(".")))
    low = name.lower()
    if low == "paths":
        return "Path"
    if low == "db" or low.startswith("db_"):
        return "DB" + name[2:]
    return name[:1].upper() + name[1:]


def canon(section):
    low = section.lower()
    return ALIASES.get(low, low)


def normalize(cfg):
    def low(d):
        return {k.lower(): low(v) if isinstance(v, dict) else v for k, v in d.items()}
    out = {}
    for k, v in low(cfg).items():
        out.setdefault(ALIASES.get(k, k), v)
    return out


class Raw(str):
    pass


def _bare(m):
    word = m.group(2)
    value = word.lower() if word in ("True", "False") else f'"{word}"'
    return m.group(1) + value + m.group(3)


def parse(text):
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        fixed = BARE_VALUE.sub(_bare, text)
        if fixed == text:
            raise
        try:
            return tomllib.loads(fixed)
        except tomllib.TOMLDecodeError:
            raise e from None


def written(v):
    return ("True" if v else "False") if isinstance(v, bool) else literal(v)


def literal(v):
    if isinstance(v, Raw):
        tomllib.loads(f"x = {v}")
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (datetime, date, time)):
        return v.isoformat()
    if isinstance(v, list):
        return "[" + ", ".join(map(literal, v)) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {literal(x)}" for k, x in v.items()) + " }" if v else "{}"
    return repr(v)


HELP = {
    ("project", "name"): "Project name shown in the title bar and on Home. Any text. "
                         "Left out: the name of the root folder.",
    ("project", "root"): "Folder of the project's git repository; the git history, branch and remote come from it. "
                         "Absolute, or relative to this toml. Left out: the first of Path.*, or this toml's folder.",
    ("project", "task"): "What the model does: one task, or several separated by commas, e.g. \"classification, "
                         "instance segmentation\". Tasks: classification, object detection (detection), instance "
                         "segmentation, semantic segmentation, panoptic segmentation, anomaly detection, pose-estimation "
                         "(keypoints) (case, spaces, _ and - don't matter). The data ([Data]) and labels ([Label]) are "
                         "shared; each task has its own predictions ([Prediction]).",
    ("project", "db"): "True when [Data], [Label] or [Prediction] uses Type = \"DB\"; the connection comes from [DB]. "
                       "False: no database is used.",
    ("git", "remote"): "Remote shown when the repository has no origin remote, e.g. "
                       "\"github.com:user/repo.git\". Only a fallback; git's own remote wins.",
    ("git", "branch"): "Branch shown when HEAD is detached or root is not a git repository, e.g. \"main\". "
                       "Only a fallback; git's own branch wins.",
    ("paths", "data"): "Older format, not used when Task = \"classification\" (use [Data]). A csv / tsv / "
                       "jsonl / parquet listing the files, or the name of a database section such as \"DB\".",
    ("paths", "models"): "Folder with model checkpoints (.pt, .pth, .onnx, .safetensors, .ckpt, …), "
                         "listed on the Model page. Sub-folders are included.",
    ("paths", "hyperparameter"): "Folder with one sub-folder per training run, each holding json / yaml / toml "
                                 "configs (and trainer_state.json); shown on the Hyperparameter page. "
                                 "\"host:path\" (e.g. \"gcloud:~/laboard/Runs\") reads it over ssh, logging in "
                                 "with the [host] section of this file (e.g. [gcloud] instance_name, zone).",
    ("paths", "results"): "Folder with result files (csv, logs, images, TensorBoard events, …) shown on the Result "
                          "page. [Prediction] Type = \"CSV\" looks for its path here.",
    ("db", "db"): "Database kind, shown only: \"supabase\", \"postgresql\", \"mysql\", \"mariadb\", \"sqlite\", "
                  "\"mssql\" or \"oracle\". DB_ip's address decides what is connected to.",
    ("db", "db_ip"): "Database address: a Supabase URL such as \"http://127.0.0.1:54323/\" (its Postgres on port "
                     "54322 is used), or a database URL: \"postgresql://user:pw@host:5432/db\", "
                     "\"mysql://user:pw@host:3306/db\", \"mariadb://user:pw@host:3306/db\", \"sqlite:///data.db\" "
                     "(relative to this toml), \"mssql://user:pw@host:1433/db\", "
                     "\"oracle://user:pw@host:1521/?service_name=XEPDB1\". Each needs its driver: "
                     "pip install \"laboard[postgres]\" (mysql, mssql, oracle; SQLite needs none).",
    ("db", "supabase"): "Older name of DB_ip: a Supabase URL such as \"http://127.0.0.1:54323/\".",
    ("db", "dsn"): "A database URL such as \"mysql://user:pw@host:3306/db\" (see DB_ip); used instead of DB_ip.",
    ("db", "table"): "Older format: the table to read data rows from, \"table\" or \"schema.table\".",
    ("db", "port"): "With a Supabase URL: its Postgres port. Default 54322 (local Supabase).",
    ("db", "user"): "With a Supabase URL: the Postgres user. Default \"postgres\".",
    ("db", "password"): "With a Supabase URL: the Postgres password. Default \"postgres\".",
    ("db", "database"): "With a Supabase URL: the Postgres database name. Default \"postgres\".",
    ("db", "limit"): "Most rows read from a table. Default 200000.",
    ("db", "columns"): "Older format: column names as an inline table, e.g. { Path = \"file_path\", Split = \"type\" }.",
    ("data", "type"): "Where the raw data files are listed (one list for every task). \"CSV\": a csv with one row "
                      "per file (File_path). \"DB\": a database table (Table).",
    ("data", "file_path"): "Type = \"CSV\": path of the csv listing the data files. Not used for Type = \"DB\".",
    ("data", "table"): "Type = \"DB\": the table with one row per data file, \"table\" or \"schema.table\".",
    ("data", "raw"): "Type = \"CSV\" / \"DB\": column holding each raw data file's path, e.g. \"file_path\". "
                     "Left out: guessed (file_path, data_path, path, …).",
    ("label", "type"): "Where the ground truth is. \"CSV\" / \"DB\": columns of a csv (File_path) or table (Table), "
                       "matched to the data by the raw-file path column.",
    ("label", "file_path"): "Type = \"CSV\": the csv with the labels (may be the [Data] csv). Not used for DB.",
    ("label", "table"): "Type = \"DB\": the table with the labels (may be the [Data] table).",
    ("label", "label"): "Type = \"CSV\" / \"DB\": the column with the ground truth, e.g. \"label\". When the csv / table lists a file once per task (a "
                        "task column), each task's label is read from its own row. A json value (a list of "
                        "{\"category\", \"bbox\"} / {\"category\", \"segmentation\"} / keypoints, coco format) is drawn "
                        "on the image.",
    ("data", "columns"): "Older format: column names as an inline table, e.g. { Path = \"img\", Split = \"subset\" }.",
    ("prediction", "type"): "Where predictions come from. \"CSV\": result csv files under Path.Results (File_path). "
                            "\"DB\": a database table (Table). Any key can be set for one task as <Task>_<Key>, "
                            "e.g. Instance_segmentation_Predict.",
    ("prediction", "file_path"): "Type = \"CSV\": result file name or glob, e.g. \"inference.csv\", looked for under "
                            "Path.Results/<task> (or Path.Results); each match (e.g. one per model folder) is one source.",
    ("prediction", "table"): "Type = \"DB\": the table with predictions; its rows are matched to data files by "
                             "their file-path column.",
    ("prediction", "predict"): "Column (csv / db) holding the predicted class. Shown green when it "
                               "equals the label, red when it is another class.",
    ("prediction", "predict_score"): "Column (csv / db) holding a score for the prediction, "
                                     "e.g. \"AD_score\". Shown as is.",
    ("labels", "result_file"): "Older format: result file name or glob under Path.Results, e.g. \"inference.csv\".",
    ("labels", "path"): "Older format: column of the result file matching rows to data files. Left out: guessed.",
    ("labels", "*"): "Older format: a column of the result file to show on the Data page; the key is the chip's "
                     "name, the value the column, e.g. Infer = \"classification\".",
    ("models", "extensions"): "Checkpoint extensions to list on the Model page, e.g. [\".pt\", \".onnx\"]. "
                              "Left out: every known model format.",
}


def enum(section, key):
    return ENUMS.get((canon(section), key.lower()))


def describe(section, key):
    s, key = canon(section), key.lower()
    text = HELP.get((s, key)) or (HELP[("labels", "*")] if s == "labels" else None)
    if text is None and s.endswith(".columns"):
        text = "Column name in the table / file for this meaning."
    return text or ("No description for this key. Text is saved in quotes; numbers, true / false and lists "
                    "such as [1, 2] are saved as typed.")


def _name(header):
    return ".".join(p.strip().strip('"') for p in header.split("."))


def _headers(lines):
    return [(_name(m.group(1)), i) for i, line in enumerate(lines) if (m := HEADER.match(line))]


def fields(text):
    cfg = parse(text)
    names = [n for n, _ in _headers(text.splitlines())]
    in_file = {}
    for sec in [""] + names:
        d = cfg
        for part in sec.split(".") if sec else []:
            d = d.get(part, {}) if isinstance(d, dict) else {}
        items = [(k, v) for k, v in d.items() if not (isinstance(v, dict) and (f"{sec}.{k}" if sec else k) in names)]
        if items or sec:
            in_file[sec] = items
    out = []
    for sec, keys in SCHEMA:
        name = next((n for n in in_file if canon(n) == sec), title(sec))
        have = {k.lower(): (k, v) for k, v in in_file.pop(name, [])}
        out.append((name, [have.pop(k.lower(), (title(k), None)) for k in keys] + list(have.values())))
    return out + [(s, items) for s, items in in_file.items() if items]


def _comment(line):
    for i, c in enumerate(line):
        if c == "#":
            try:
                tomllib.loads(line[:i])
                return line[i:]
            except tomllib.TOMLDecodeError:
                continue
    return ""


def _set(lines, section, key, value):
    heads = _headers(lines)
    span = next(((i + 1, heads[j + 1][1] if j + 1 < len(heads) else len(lines))
                 for j, (n, i) in enumerate(heads) if canon(n) == canon(section)), None)
    if section == "":
        span = (0, heads[0][1] if heads else len(lines))
    pat = re.compile(rf'^(\s*(["\']?){re.escape(key)}\2\s*=\s*)', re.IGNORECASE)
    if span:
        for i in range(*span):
            m = pat.match(lines[i])
            if m:
                if value is None:
                    del lines[i]
                else:
                    comment = _comment(lines[i])
                    lines[i] = m.group(1) + written(value) + (" " + comment if comment else "")
                return lines
    if value is None:
        return lines
    entry = f"{key} = {written(value)}"
    if span:
        at = max((i for i in range(*span) if lines[i].strip()), default=span[0] - 1) + 1
        lines.insert(at, entry)
    else:
        lines += ["", f"[{section}]", entry]
    return lines


def save(text, edits):
    lines = text.splitlines()
    for (section, key), value in edits.items():
        lines = _set(lines, section, key, value)
    out = "\n".join(lines) + "\n"
    parse(out)
    return out
