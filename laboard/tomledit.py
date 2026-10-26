"""A project toml as editable fields: read it section by section and write single values back,
keeping the file's comments, order and layout.

Section and key names are written as ``title`` spells them ([Project] Name, [DB] DB_ip, [Path] Models)
and read in any case; internally (``SCHEMA``, ``ENUMS``, ``HELP``, ``normalize``) they are lower case."""
import json
import re
import tomllib
from datetime import date, datetime, time

TASKS = ("classification", "object detection", "segmentation", "instance segmentation", "semantic segmentation",
         "panoptic segmentation", "anomaly detection", "pose-estimation")
TASK_ALIASES = {"detection": "objectdetection", "keypoint": "poseestimation", "keypoints": "poseestimation"}  # by task_id
# every key of a task project file, in the order the Setting page always lists them (see template.toml); lower case,
# written as ``title`` spells them. [Label] also gets a <Task>_Label key per task of [Project] Task (``fields``).
SCHEMA = (("project", ("name", "root", "task", "db")),
          ("db", ("db", "db_ip")),
          ("git", ("remote", "branch")),
          ("paths", ("models", "hyperparameter", "results")),
          ("data", ("type", "file_path", "table", "raw")),
          ("label", ("type", "file_path", "table")),
          ("prediction", ("type", "file_path", "table", "format", "predict", "predict_score")))
# keys with a fixed set of values, shown as drop-downs (section names match in any case)
ENUMS = {("project", "db"): (True, False),
         ("data", "type"): ("CSV", "DB", "Folder"),  # read in any case
         ("label", "type"): ("CSV", "DB", "Folder"),
         ("prediction", "type"): ("CSV", "DB", "Folder"),
         ("prediction", "format"): ("txt", "json")}
BARE_VALUE = re.compile(r"^(\s*[\w.-]+\s*=\s*)(?!(?:true|false|inf|nan)\b)([A-Za-z_][\w-]*)(\s*(?:#.*)?)$", re.M)
HEADER = re.compile(r"^\s*\[([^\[\]]+)\]\s*(#.*)?$")
ALIASES = {"path": "paths", "lables": "labels"}  # section names read as another


def task_id(name):
    """A task name compared loosely: case, spaces, "_" and "-" don't matter ("Object_detection" = "object detection"),
    and an alias is its task ("detection" = "object detection", "keypoints" = "pose-estimation")."""
    tid = re.sub(r"[^a-z]", "", str(name).lower())
    return TASK_ALIASES.get(tid, tid)


def label_key(task):
    """[Label]'s key for ``task``: "object detection" → "Object_detection_Label"."""
    return title(re.sub(r"[\s-]+", "_", task)) + "_Label"


def tasks_of(value):
    """The known tasks named in ``[Project] Task`` (one, or a comma-separated list), in order."""
    ids = {task_id(t): t for t in TASKS}
    return list(dict.fromkeys(ids[task_id(p)] for p in str(value or "").split(",") if task_id(p) in ids))


def title(name):
    """How a section or key name is written: first letter upper case, db → DB (db_ip → DB_ip), paths → Path."""
    if "." in name:
        return ".".join(map(title, name.split(".")))
    low = name.lower()
    if low == "paths":
        return "Path"
    if low == "db" or low.startswith("db_"):
        return "DB" + name[2:]
    return name[:1].upper() + name[1:]


def canon(section):
    """The lower-case name a section is read as: [Path] → paths, [DB] → db."""
    low = section.lower()
    return ALIASES.get(low, low)


def normalize(cfg):
    """``cfg`` with every key lower case and section aliases resolved, as the loader reads it."""
    def low(d):
        return {k.lower(): low(v) if isinstance(v, dict) else v for k, v in d.items()}
    out = {}
    for k, v in low(cfg).items():
        out.setdefault(ALIASES.get(k, k), v)
    return out


class Raw(str):
    """A value typed as a toml literal (number, list, inline table, date), checked when saved."""


def _bare(m):
    word = m.group(2)
    value = word.lower() if word in ("True", "False") else f'"{word}"'  # Python-style booleans are booleans
    return m.group(1) + value + m.group(3)


def parse(text):
    """dict from toml text; a bare word value (``data = DB``) is read as a string, ``True`` / ``False`` as booleans."""
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
    """toml text for a key's value as Laboard writes it: booleans as True / False (read back by ``parse``),
    anything else as ``literal``."""
    return ("True" if v else "False") if isinstance(v, bool) else literal(v)


def literal(v):
    """toml text for a value (booleans inside lists and inline tables stay true / false)."""
    if isinstance(v, Raw):
        tomllib.loads(f"x = {v}")  # raises with the reason when it isn't a toml value
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


# what to put in each key, shown as the Setting page's tooltip and in its Edit popup
HELP = {
    ("project", "name"): "Project name shown in the title bar and on Home. Any text. "
                         "Left out: the name of the root folder.",
    ("project", "root"): "Folder of the project's git repository; the git history, branch and remote come from it. "
                         "Absolute, or relative to this toml. Left out: the first of Path.*, or this toml's folder.",
    ("project", "task"): "What the model does: one task, or several separated by commas, e.g. \"classification, "
                         "segmentation\". Tasks: classification, object detection (detection), segmentation, instance "
                         "segmentation, semantic segmentation, panoptic segmentation, anomaly detection, pose-estimation "
                         "(keypoints) (case, spaces, _ and - don't matter). The data ([Data]) is shared; each task "
                         "has its own labels ([Label] <Task>_Label) and predictions ([Prediction]).",
    ("project", "db"): "True when [Data] or [Prediction] uses Type = \"DB\"; the connection comes from [DB]. "
                       "False: no database is used.",
    ("git", "remote"): "Remote shown when the repository has no origin remote, e.g. "
                       "\"github.com:user/repo.git\". Only a fallback; git's own remote wins.",
    ("git", "branch"): "Branch shown when HEAD is detached or root is not a git repository, e.g. \"main\". "
                       "Only a fallback; git's own branch wins.",
    ("paths", "data"): "Older format, not used when Task = \"classification\" (use [Data]). A dataset folder "
                       "(split/label/file), a csv / tsv / jsonl / parquet listing the files, or the name of a "
                       "database section such as \"DB\".",
    ("paths", "models"): "Folder with model checkpoints (.pt, .pth, .onnx, .safetensors, .ckpt, …), "
                         "listed on the Model page. Sub-folders are included.",
    ("paths", "hyperparameter"): "Folder with one sub-folder per training run, each holding json / yaml / toml "
                                 "configs (and trainer_state.json); shown on the Hyperparameter page. "
                                 "\"host:path\" (e.g. \"gcloud:~/laboard/Runs\") reads it over ssh, logging in "
                                 "with the command in [SSH] host or the SSH/ folder next to this file.",
    ("paths", "results"): "Folder with result files (csv, logs, images, TensorBoard events, …) shown on the Result "
                          "page. [Prediction] Type = \"CSV\" looks for its path here.",
    ("db", "db"): "Database kind: \"supabase\" (a local Supabase stack, whose Postgres runs on port 54322).",
    ("db", "db_ip"): "Database address: a Supabase URL such as \"http://127.0.0.1:54323/\" (its Postgres on port "
                     "54322 is used), or \"postgresql://user:password@host:5432/dbname\".",
    ("db", "supabase"): "Older name of DB_ip: a Supabase URL such as \"http://127.0.0.1:54323/\".",
    ("db", "dsn"): "Any Postgres as \"postgresql://user:password@host:5432/dbname\"; used instead of a Supabase URL.",
    ("db", "table"): "Older format: the table to read data rows from, \"table\" or \"schema.table\".",
    ("db", "port"): "Postgres port. Default 54322 (local Supabase).",
    ("db", "user"): "Postgres user. Default \"postgres\".",
    ("db", "password"): "Postgres password. Default \"postgres\".",
    ("db", "database"): "Postgres database name. Default \"postgres\".",
    ("db", "limit"): "Most rows read from a table. Default 200000.",
    ("db", "columns"): "Older format: column names as an inline table, e.g. { Path = \"file_path\", Split = \"type\" }.",
    ("data", "type"): "Where the raw data files are listed (one list for every task). \"CSV\": a csv with one row "
                      "per file (File_path). \"DB\": a database table (Table). \"Folder\": a dataset folder laid "
                      "out as split/label/file, e.g. train/Normal/x.jpg (File_path).",
    ("data", "file_path"): "Type = \"CSV\": path of the csv listing the data files. Type = \"Folder\": the dataset "
                           "folder holding train/, valid/, test/ with one folder per class inside. "
                           "Not used for Type = \"DB\".",
    ("data", "table"): "Type = \"DB\": the table with one row per data file, \"table\" or \"schema.table\".",
    ("data", "raw"): "Type = \"CSV\" / \"DB\": column holding each raw data file's path, e.g. \"file_path\". "
                     "Left out: guessed (file_path, data_path, path, …).",
    ("label", "type"): "Where the ground truth is. \"CSV\" / \"DB\": columns of a csv (File_path) or table (Table), "
                       "matched to the data by the raw-file path column. \"Folder\": classification takes the class "
                       "folder of a Folder data layout; other tasks have a folder of label files.",
    ("label", "file_path"): "Type = \"CSV\": the csv with the labels (may be the [Data] csv). Type = \"Folder\": the "
                            "folder the <Task>_Label folders are in (default: the data folder). Not used for DB.",
    ("label", "table"): "Type = \"DB\": the table with the labels (may be the [Data] table).",
    ("label", "label"): "Type = \"CSV\" / \"DB\": the column with the ground truth of every task that has no "
                        "<Task>_Label of its own, e.g. \"label\". When the csv / table lists a file once per task (a "
                        "task column), each task's label is read from its own row. A json value (a list of "
                        "{\"category\", \"bbox\"} / {\"category\", \"segmentation\"} / keypoints, coco format) is drawn "
                        "on the image.",
    ("label", "*"): "A task's ground truth. Type = \"CSV\" / \"DB\": the column holding it, e.g. \"label\". "
                    "Type = \"Folder\": classification uses the class folders (any value); other tasks name a "
                    "folder of label files under File_path, one per data file with the same name.",
    ("data", "columns"): "Older format: column names as an inline table, e.g. { Path = \"img\", Split = \"subset\" }.",
    ("prediction", "type"): "Where predictions come from. \"CSV\": result csv files under Path.Results (File_path). "
                            "\"DB\": a database table (Table). \"Folder\": one prediction file per data file "
                            "(File_path). Any key can be set for one task as <Task>_<Key>, e.g. Segmentation_Predict.",
    ("prediction", "file_path"): "Type = \"CSV\": result file name or glob, e.g. \"inference.csv\", looked for under "
                            "Path.Results/<task> (or Path.Results); each match (e.g. one per model folder) is one source. "
                            "Type = \"Folder\": the folder holding the prediction files, laid out like the data "
                            "folder or flat, named after each data file (x.jpg → x.txt).",
    ("prediction", "table"): "Type = \"DB\": the table with predictions; its rows are matched to data files by "
                             "their file-path column.",
    ("prediction", "format"): "Type = \"Folder\": file format of the predictions. \"txt\": first line is "
                              "\"<class> [score]\", e.g. \"Normal 0.93\". \"json\": an object such as "
                              "{\"class\": \"Normal\", \"score\": 0.93}.",
    ("prediction", "predict"): "Column (csv / db) or json key holding the predicted class. Shown green when it "
                               "equals the label, red when it is another class.",
    ("prediction", "predict_score"): "Column (csv / db) or json key holding a score for the prediction, "
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
    """What to put in ``section.key``, for people editing it."""
    s, key = canon(section), key.lower()
    text = HELP.get((s, key)) or (HELP[("labels", "*")] if s == "labels" else None)
    if text is None and s == "label" and key.endswith("_label"):
        text = HELP[("label", "*")]
    if text is None and s.endswith(".columns"):
        text = "Column name in the table / file for this meaning."
    return text or ("No description for this key. Text is saved in quotes; numbers, true / false and lists "
                    "such as [1, 2] are saved as typed.")


def _name(header):
    return ".".join(p.strip().strip('"') for p in header.split("."))


def _headers(lines):
    """[(section name, line index)] in file order."""
    return [(_name(m.group(1)), i) for i, line in enumerate(lines) if (m := HEADER.match(line))]


def fields(text):
    """[(section, [(key, value)])]: every ``SCHEMA`` section and key in its order, whatever the file holds (value
    None when the file leaves a key out), then any other keys the file has, in file order. Names are the file's
    spelling, or ``title``'s for what the file leaves out."""
    cfg = parse(text)
    names = [n for n, _ in _headers(text.splitlines())]
    in_file = {}
    for sec in [""] + names:
        d = cfg
        for part in sec.split(".") if sec else []:
            d = d.get(part, {}) if isinstance(d, dict) else {}
        # sub-tables with their own [a.b] header are listed as sections of their own
        items = [(k, v) for k, v in d.items() if not (isinstance(v, dict) and (f"{sec}.{k}" if sec else k) in names)]
        if items or sec:
            in_file[sec] = items
    project = next((v for k, v in cfg.items() if canon(k) == "project" and isinstance(v, dict)), {})
    task = next((v for k, v in project.items() if k.lower() == "task"), "")
    out = []
    for sec, keys in SCHEMA:
        if sec == "label":
            keys = keys + tuple(label_key(t) for t in tasks_of(task))
        name = next((n for n in in_file if canon(n) == sec), title(sec))  # the file's spelling, e.g. [paths]
        have = {k.lower(): (k, v) for k, v in in_file.pop(name, [])}
        out.append((name, [have.pop(k.lower(), (title(k), None)) for k in keys] + list(have.values())))
    return out + [(s, items) for s, items in in_file.items() if items]


def _comment(line):
    """The trailing ``# …`` of a ``key = value`` line, or ""."""
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
    if span:  # after the section's last non-blank line
        at = max((i for i in range(*span) if lines[i].strip()), default=span[0] - 1) + 1
        lines.insert(at, entry)
    else:
        lines += ["", f"[{section}]", entry]
    return lines


def save(text, edits):
    """``text`` with ``edits`` ({(section, key): value, None removes the key}) applied; raises when the
    result isn't valid toml."""
    lines = text.splitlines()
    for (section, key), value in edits.items():
        lines = _set(lines, section, key, value)
    out = "\n".join(lines) + "\n"
    parse(out)
    return out
