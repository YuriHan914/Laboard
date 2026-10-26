"""Load a laboard .toml project into ``store``, which the UI reads.

Nothing here assumes particular file names, counts or formats:

* Data rows come from one of three sources, picked by ``paths.data``:

  - ``data = "DB"`` (the name of a toml table, any case, quotes optional): rows from that
    table's database, e.g. ``[DB] supabase = "http://127.0.0.1:54323/"  table = "semiconductor"``;
  - a table file (csv / tsv / jsonl / parquet) listing one data file per row;
  - a folder: the first table file under it that points at real files, else a scan of the folder
    (ImageFolder-style ``split/label/file``).

  A ``[db]`` table next to a path is tried first and falls back to that path. The ground truth
  of a db table or table file is always its ``label`` column. Path / split columns are matched
  by common names, then detected from the values; ``[db.columns]`` or ``[data.columns]``
  override them.
* Models are files with a known checkpoint extension (``[models] extensions`` overrides);
  when none match, every file under ``paths.models`` is listed.
* Runs (the Hyperparameter page) are folders under ``[Path] Hyperparameter`` holding json / yaml / toml configs.
* A value written ``host:path`` is on another machine, read over ssh (``remote``): Models / Hyperparameter / Results
  folders and [Data] / [Label] / [Prediction] files are copied into a temp folder on every load (``REMOTE_COPY``,
  ``_copy_remote``); a data folder and the data files a table lists as ``host:path`` stay remote, their sizes read
  over ssh and each file fetched when the Data page shows it.
* Results are every file under ``paths.results``.

File names that repeat in different folders are shown by their relative path, so each
sidebar entry stays unique. Sections that find nothing stay empty, and ``DETECTED`` says
what was found.
"""
import atexit
import copy
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from . import labels as label_values, remote, store, tomledit

# column name aliases, first match wins (db: file_path/label/type, csv: data_path/label/status).
# The ground truth of a db table / table file is always its "label" column; [*.columns] can't move it.
COLS = dict(path=("file_path", "data_path", "path", "filepath", "file", "image", "image_path", "img", "filename"),
            label=("label",), split=("type", "status", "split", "subset", "set"),
            task=("object", "task"), created=("create_date", "created_at", "created", "date", "timestamp"),
            trained=("trained", "used"), predict=("predict", "prediction", "pred", "predicted"), id=("id",))
SPLIT_WORDS = {"train": "train", "training": "train", "val": "valid", "valid": "valid", "validation": "valid",
               "eval": "valid", "dev": "valid", "test": "test", "testing": "test", "unused": "unused"}
SPLIT_ORDER = list(store.SPLITS)
MODEL_EXT = {".pt": "PyTorch", ".pth": "PyTorch", ".ckpt": "PyTorch", ".bin": "PyTorch", ".onnx": "ONNX",
             ".msgpack": "JAX", ".safetensors": "safetensors", ".engine": "TensorRT", ".trt": "TensorRT", ".plan": "TensorRT",
             ".h5": "Keras", ".keras": "Keras", ".pb": "TensorFlow", ".tflite": "TFLite", ".gguf": "GGUF",
             ".pkl": "Pickle", ".joblib": "Pickle", ".mlmodel": "CoreML", ".xml": "OpenVINO"}
TABLE_EXT = (".csv", ".tsv", ".jsonl", ".parquet")
CONFIG_EXT = (".json", ".yaml", ".yml", ".toml")
SKIP_DATA_EXT = {".py", ".pyc", ".ipynb", ".sh", ".md"}
IMAGE_EXT = {"png", "jpg", "jpeg", "bmp", "gif", "webp", "tif", "tiff"}
FORMAT_COLORS = ["ink", "c2", "c3", "mute", "grid", "body"]
MAX_DATA_FILES = 200_000  # rows read from a table / files from a data scan
MAX_RESULT_FILES = 20_000
MAX_RUNS, RUN_DEPTH = 500, 3
PATH_LABELS = dict(data="Data", models="Models", runs="Hyperparameter", results="Results")  # paths keys as the toml names them
MAX_CONFIG_ROWS = 2_000  # rows read from one run config (the Hyperparameter page shows them 20 per page)
SNAPSHOT_ROOT = Path(tempfile.gettempdir()) / "laboard-snapshots"
TASKS = tomledit.TASKS
PRED_JSON_KEYS = dict(predict=("predict", "prediction", "class", "label", "pred"),
                      predict_score=("predict_score", "score", "confidence", "prob", "probability"))
RESERVED = {"project", "git", "paths", "data", "models", "labels", "lables", "prediction", "ssh"}  # toml tables that aren't a database
# a host:path [Path] value: which files of it are copied over ssh (see remote.py), by paths key
REMOTE_COPY = dict(models=dict(max_size=500_000_000), runs=dict(exts=CONFIG_EXT, depth=RUN_DEPTH + 1, max_size=2_000_000),
                   results=dict(max_size=50_000_000))
REMOTE_FILE_MAX = 50_000_000  # per file of a remote label / prediction folder

_PATCHED = ("PROJECT", "COMMITS", "ROOT_FOLDERS", "DASH", "DATA_FOLDERS", "CLASSES", "SPLIT_TOTALS", "SPLIT_SOURCE",
            "SPLIT_OVERLAP", "MODEL_FILES", "MODEL_INFO", "RUNS", "RUN_DETAILS", "RESULT_FILES",
            "RESULT_PATHS", "RESULT_ROOT", "INFERENCE", "TASKS", "RECENT_PROJECTS", "TOML", "DETECTED", "STATUS")
_original = None


# ---------------------------------------------------------------- helpers
def _size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _ago(ts):
    s = max(0, datetime.now().timestamp() - ts)
    for limit, div, unit in ((3600, 60, "min"), (86400, 3600, "h"), (86400 * 30, 86400, "days")):
        if s < limit:
            n = int(s // div)
            return "just now" if unit == "min" and n == 0 else f"{n} {unit} ago"
    return datetime.fromtimestamp(ts).strftime("%b %d, %Y")


def _stamp(ts):
    return datetime.fromtimestamp(ts).strftime("%b %d, %H:%M")


def _run(*cmd, cwd=None, timeout=10):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout if r.returncode == 0 else ""


def _resolve(value, base):
    """Path from the toml: absolute, relative to the toml, or absolute with the leading '/' missing."""
    if not value:
        return None
    if remote.split(value):  # a remote folder, listed over ssh (_rows_from_scan); never a local path
        return Path(value)
    p = Path(value).expanduser()
    if p.is_absolute():
        return p
    if (base / p).exists():
        return (base / p).resolve()
    if Path("/", p).exists():
        return Path("/", p)
    return (base / p).resolve()


def _rel(p, root):
    try:
        return str(Path(p).relative_to(root))
    except ValueError:
        return str(p)


def _labels(paths, root):
    """Sidebar label per path: the file name, or its path under ``root`` when the name repeats."""
    counts = Counter(Path(p).name for p in paths)
    return [Path(p).name if counts[Path(p).name] == 1 else _rel(p, root) for p in paths]


def _walk(root, max_depth=None):
    """os.walk without hidden folders / __pycache__, sorted, optionally depth-limited."""
    for dp, dn, fn in os.walk(root):
        depth = len(Path(dp).relative_to(root).parts)
        dn[:] = sorted(d for d in dn if not d.startswith(".") and d != "__pycache__")
        if max_depth is not None and depth >= max_depth:
            dn[:] = []
        yield Path(dp), sorted(f for f in fn if not f.startswith("."))


def _ext(name):
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


# ---------------------------------------------------------------- data rows: db → table file → folder scan
def _pg_params(db):
    url = db.get("dsn") or db.get("url") or db.get("supabase") or db.get("db_ip") or ""
    if url.startswith(("postgres://", "postgresql://")):
        return dict(dsn=url, connect_timeout=3)
    # a Supabase URL (local stack: API 54321, Postgres 54322, Studio 54323) → its Postgres
    u = urlparse(url)
    return dict(host=db.get("host", u.hostname or "127.0.0.1"), port=int(db.get("port", 54322)),
                user=db.get("user", "postgres"), password=db.get("password", "postgres"),
                dbname=db.get("database", "postgres"), connect_timeout=3)


def _rows_from_db(db):
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor

    params = _pg_params(db)
    conn = psycopg2.connect(**params)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            q = sql.SQL("SELECT * FROM {} ORDER BY 1 LIMIT {}").format(sql.Identifier(*db["table"].split(".")),
                                                                        sql.Literal(int(db.get("limit", MAX_DATA_FILES))))
            cur.execute(q)
            rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    where = params.get("dsn") or f"{params['host']}:{params['port']}/{params['dbname']}"
    return rows, dict(kind="db", name=db["table"], where=where, label=f"db · {db['table']}")


def _read_table(f):
    ext = f.suffix.lower()
    if ext == ".parquet":
        import pandas  # optional; only needed for parquet
        return pandas.read_parquet(f).head(MAX_DATA_FILES).to_dict("records")
    with open(f, newline="") as fh:
        if ext == ".jsonl":
            rows = []
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    rows.append(d)
                if len(rows) >= MAX_DATA_FILES:
                    break
            return rows
        reader = csv.DictReader(fh, delimiter="\t" if ext == ".tsv" else ",")
        return [r for _, r in zip(range(MAX_DATA_FILES), reader)]


def _rows_from_table(data_dir, data_cfg, base):
    """``paths.data`` when it is a table file, else the first table file under it (or ``[data] table``)
    that has a file-path column."""
    explicit = data_cfg.get("table") or (data_dir and data_dir.is_file())
    if data_cfg.get("table"):
        candidates = [_resolve(data_cfg["table"], data_dir if data_dir and data_dir.is_dir() else base)]
    elif data_dir and data_dir.is_file():
        candidates = [data_dir] if data_dir.suffix.lower() in TABLE_EXT else []
    elif data_dir and data_dir.is_dir():
        candidates = sorted(f for ext in TABLE_EXT for pat in ("*", "*/*") for f in data_dir.glob(pat + ext))
    else:
        return None
    for f in candidates:
        try:
            rows = _read_table(f)
        except (OSError, ValueError, ImportError):
            continue
        col = _columns(rows, data_cfg.get("columns", {}))["path"] if rows else None
        if not col:
            continue
        # an auto-found table must point at real files; an explicit [data] table / paths.data file is trusted
        sample = [_abs(r.get(col), f.parent) for r in rows[:50] if r.get(col)]
        if explicit or sum(os.path.exists(p) for p in sample) >= 0.5 * len(sample):
            return rows, dict(kind="file", name=f.name, where=remote.origin(f) or str(f), label=f"{f.suffix[1:]} · {f.name}",
                              base=_folder_of(f))
    return None


def _abs(p, base):
    p = str(p)
    if os.path.isabs(p) or remote.split(p) or not base:
        return p
    return remote.join(base, p) if remote.split(str(base)) else str(Path(base, p))


def _folder_of(f):
    """The folder that relative paths in the table file ``f`` are under: its own, or a remote copy's original one."""
    return remote.parent(f) or f.parent


def _scan_files(data_dir):
    """(folder under ``data_dir``, file path) of every file under it: walked, or listed over ssh when remote."""
    if remote.split(str(data_dir)):
        return [(Path(rel).parent, remote.join(data_dir, rel)) for rel in remote.listing(str(data_dir), MAX_DATA_FILES)]
    return ((Path(_rel(dp, data_dir)), str(dp / f)) for dp, files in _walk(data_dir) for f in files)


def _rows_from_scan(data_dir, skip=(), notes=None):
    """One row per file under ``paths.data`` (but ``skip`` extensions); split and label from an
    ImageFolder-style path."""
    if not data_dir or not (data_dir.is_dir() or remote.split(str(data_dir))):
        return None
    try:
        files = _scan_files(data_dir)
    except OSError as e:  # a remote folder that can't be listed
        if notes is not None:
            notes.append(f"{data_dir}: {e}")
        return None
    rows = []
    for folder, path in files:
        if Path(path).suffix.lower() in SKIP_DATA_EXT or Path(path).suffix.lower() in TABLE_EXT or Path(path).suffix.lower() in skip:
            continue
        parts = [p.lower() for p in folder.parts]
        at = next((i for i, p in enumerate(parts) if p in SPLIT_WORDS), None)
        split = SPLIT_WORDS[parts[at]] if at is not None else None
        label = folder.parts[at + 1] if at is not None and at + 1 < len(parts) else None
        rows.append(dict(path=path, split=split or "unused", label=label, task=None, created=None, trained=None,
                         predict=None, id=None))
        if len(rows) >= MAX_DATA_FILES:
            break
    if not rows:
        return None
    return rows, dict(kind="scan", name=data_dir.name, where=str(data_dir), label=f"scan · {data_dir.name}/")


def _looks_like_path(rows, col):
    vals = [r.get(col) for r in rows[:50] if r.get(col) not in (None, "")]
    good = [v for v in vals if isinstance(v, str) and (Path(v).suffix or "/" in v or "\\" in v)]
    return bool(vals) and len(good) >= 0.8 * len(vals)


def _looks_like_split(rows, col):
    vals = {str(r.get(col)).strip().lower() for r in rows[:500] if r.get(col) not in (None, "")}
    return bool(vals) and vals <= set(SPLIT_WORDS)


def _columns(rows, override):
    """Actual column name for each logical key: toml override, then alias, then guessed from values."""
    names = list(dict.fromkeys(k for r in rows[:50] for k in r))
    lower = {n.lower(): n for n in names}
    out = {}
    for key, aliases in COLS.items():
        want = override.get(key)
        out[key] = want if want in names else next((lower[a] for a in aliases if a in lower), None)
    if out["path"] and out["path"] != override.get("path") and not _looks_like_path(rows, out["path"]):
        out["path"] = None  # e.g. a "file" column holding ids, not paths
    if not out["path"]:
        out["path"] = next((n for n in names if _looks_like_path(rows, n)), None)
    if not out["split"]:
        out["split"] = next((n for n in names if n not in out.values() and _looks_like_split(rows, n)), None)
    return out


def _normalize(raw, cols, base=None):
    def get(r, key):
        c = cols[key]
        v = r.get(c) if c else None
        return None if v in (None, "") or (isinstance(v, float) and v != v) else v

    out = []
    for r in raw:
        path = get(r, "path")
        if not path:
            continue
        split = SPLIT_WORDS.get(str(get(r, "split") or "").strip().lower(), "unused")
        created = get(r, "created")
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except ValueError:
                created = None
        elif not isinstance(created, datetime):
            created = None
        trained = get(r, "trained")
        if isinstance(trained, str):
            trained = trained.strip().lower() in ("true", "t", "1", "yes", "y")
        label = get(r, "label")
        out.append(dict(path=_abs(path, base), split=split, label=None if label is None else str(label), task=get(r, "task"),
                        created=created, trained=None if trained is None else bool(trained), predict=get(r, "predict"),
                        id=get(r, "id")))
    return out


def _data(rows, src, cols):
    """DATA_FOLDERS etc. from normalized rows. A folder is the file's directory minus its split part."""
    far, far_error = {}, None  # remote files' (size, mtime), see remote.py
    try:
        far = remote.stat([r["path"] for r in rows])
    except OSError as e:
        far_error = str(e)
    for r in rows:
        if r["path"] in far:
            r["bytes"], r["mtime"] = far[r["path"]]
            continue
        try:
            st = os.stat(r["path"])
            r["bytes"], r["mtime"] = st.st_size, st.st_mtime
        except OSError:
            r["bytes"], r["mtime"] = 0, None
    dirs = {os.path.dirname(r["path"]) for r in rows}
    root = os.path.commonpath(list(dirs)) if len(dirs) > 1 else next(iter(dirs))
    groups = defaultdict(list)
    for r in rows:
        parts = [p for p in Path(os.path.relpath(os.path.dirname(r["path"]), root)).parts
                 if p != "." and SPLIT_WORDS.get(p.lower()) != r["split"]]
        groups["/".join(parts) or Path(root).name or "/"].append(r)

    folders = {}
    for name in sorted(groups):
        rs = sorted(groups[name], key=lambda r: (SPLIT_ORDER.index(r["split"]), r["path"]))
        ext = Counter(Path(r["path"]).suffix[1:].upper() for r in rs).most_common(1)[0][0] or "FILE"
        folders[name] = dict(n=len(rs), size=_size(sum(r["bytes"] for r in rs)), ext=ext,
                             files=_labels([r["path"] for r in rs], root), rows=rs,
                             splits=[r["split"] for r in rs], labels=[r["label"] for r in rs])

    classes = sorted({c for r in rows for v in (r["labels"].values() if "labels" in r else [r["label"]])
                      for c in label_values.categories(v)})
    counts = Counter(r["split"] for r in rows)
    if cols.get("split"):
        how = lambda k: f"{src['name']} · {cols['split']} = '{k}'"
    else:
        how = lambda k: f"{src['name']} · split from folder name" if src["kind"] == "scan" else f"{src['name']} · no split column"
    totals = [(k, counts[k], how(k) if k != "unused" else "no split value") for k in SPLIT_ORDER if counts[k]]

    by_name = defaultdict(set)
    for r in rows:
        by_name[os.path.basename(r["path"])].add(r["split"])
    shared = sum(1 for s in by_name.values() if len(s - {"unused"}) > 1)

    task = Counter(str(r["task"]) for r in rows if r["task"]).most_common(1)
    task = task[0][0].replace("_", " ").title() if task else ("Classification" if classes else "Unlabeled")
    exts = " · ".join(sorted({f["ext"] for f in folders.values()})[:6])
    known = [r for r in rows if r["trained"] is not None]
    n_trained = sum(1 for r in known if r["trained"])
    if known:
        tiles = [("Total files", f"{len(rows):,}"), ("Used in training", f"{n_trained:,}", "#2ead4b"),
                 ("Not yet trained", f"{len(rows) - n_trained:,}", "mute")]
    else:
        tiles = [("Total files", f"{len(rows):,}"), ("Classes", str(len(classes))), ("Folders", str(len(folders)))]

    # files added per month, from the created column (or file mtime)
    months = Counter()
    for r in rows:
        when = r["created"] or (datetime.fromtimestamp(r["mtime"]) if r["mtime"] else None)
        if when:
            months[(when.year, when.month)] += 1
    changes = [(str(y), datetime(y, m, 1).strftime("%b"), months[(y, m)], 0) for y, m in sorted(months)[-8:]]
    date_src = f"{src['name']}.{cols['created']}" if cols.get("created") and any(r["created"] for r in rows) else "file mtime"
    label_note = f"{len(classes)} classes" if classes else "no labels"

    return dict(
        DATA_FOLDERS=folders, CLASSES=classes, SPLIT_TOTALS=totals,
        SPLIT_SOURCE=(src["label"], f"{len(rows):,} rows from {src['where']} · root {root}"),
        SPLIT_OVERLAP=("Overlap check (file name)", "No overlap" if not shared else f"{shared} shared",
                       "positive" if not shared else "warning"),
        dash=dict(task=task, task_note=f"Read from {src['label']} · {label_note} · {exts}", tiles=tiles,
                  data_changes=changes, changes_caption=("Files added per month", date_src),
                  splits=[(store.SPLITS[k][0], f"{n:,}", store.SPLITS[k][1]) for k, n, _ in totals]),
        detected=[("Data", f"{src['label']} · {len(rows):,} files · {len(folders)} folders · "
                           f"{_size(sum(r['bytes'] for r in rows))}", "positive", "Found")] +
                 ([("Remote data files", far_error, "warning", "Unreachable")] if far_error else []))



def _load_data(db, data_cfg, paths, base, detected, notes, as_of=None):
    """Rows from db / table / scan. ``db``: the toml's database table ({} for none); paths.data is the
    fallback when set. ``as_of`` (a commit's time) hides db rows created after it."""
    src = None
    if db.get("table"):
        try:
            src = _rows_from_db(db)
            detected.append(("Database", f"{src[1]['where']} · {db['table']} · {len(src[0]):,} rows", "positive", "Connected"))
        except Exception as e:  # driver missing, server down, bad table: fall back to paths.data
            msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            notes.append(f"DB {db['table']} unavailable ({msg}); " + ("using Path.Data" if paths["data"] else "no Path.Data to fall back to"))
            detected.append(("Database", f"{db['table']} · {msg}", "warning", "Unreachable"))
    elif db:
        notes.append("database table has no 'table' key")
    overrides = {k: v for k, v in (db.get("columns", {}) if src else data_cfg.get("columns", {})).items() if k != "label"}
    if src is None:
        src = _rows_from_table(paths["data"], data_cfg, base) or _rows_from_scan(paths["data"], notes=notes)
    if src is None:
        if paths["data"] and paths["data"].is_file():
            notes.append(f"{paths['data'].name}: no file-path column found (set [Data.Columns] Path)")
        return None
    if src[1]["kind"] == "scan":  # rows are built normalized
        return _data(src[0], src[1], dict.fromkeys(COLS))
    cols = _columns(src[0], overrides)
    if not cols["path"]:
        notes.append(f"{src[1]['label']}: no file-path column found (set [DB.Columns] / [Data.Columns] Path)")
        return None
    if not cols["label"]:
        notes.append(f"{src[1]['label']}: no 'label' column; files have no ground truth")
    return _to_data(src, cols, paths["data"], notes, as_of)


def _to_data(src, cols, base, notes, as_of):
    """``_data`` from raw table / db rows (``_rows``)."""
    rows = _rows(src, cols, base, notes, as_of)
    return _data(rows, src[1], cols) if rows else None


def _rows(src, cols, base, notes, as_of):
    """Normalized rows from raw table / db rows. ``as_of`` (a commit's time) hides db rows created after it."""
    rows = _normalize(src[0], cols, src[1].get("base") or base)
    if as_of and src[1]["kind"] == "db":  # db rows aren't versioned in git; their created column dates them
        dated = [r for r in rows if r["created"] is None or r["created"] <= as_of]
        if any(r["created"] for r in rows):
            if len(dated) < len(rows):
                notes.append(f"{len(rows) - len(dated):,} db rows created after {as_of:%b %d, %H:%M} hidden")
        else:
            notes.append("db rows have no created column; showing all of them")
        rows = dated
    return rows


# ---------------------------------------------------------------- task projects: [Data] / [Label] / [Prediction]
_task_id = tomledit.task_id
TASK_IDS = {_task_id(t): t for t in TASKS}


def _tasks(value, notes):
    """The tasks of ``[Project] Task``: one name or a comma-separated list, in order."""
    out = []
    for part in str(value or "").split(","):
        if not part.strip():
            continue
        task = TASK_IDS.get(_task_id(part))
        if task is None:
            notes.append(f"[Project] Task: unknown task {part.strip()!r} (one of {', '.join(TASKS)})")
        elif task not in out:
            out.append(task)
    return out


def _per_task(section, suffix):
    """{task: value} of a section's ``<task>_<suffix>`` keys (normalized), e.g. object_detection_label."""
    out = {}
    for k, v in section.items():
        if k.endswith("_" + suffix) and v not in (None, ""):
            task = TASK_IDS.get(_task_id(k[:-len(suffix) - 1]))
            if task:
                out[task] = v
    return out


def _task_dir(folder, task):
    """The sub-folder of ``folder`` named after ``task`` (in any case / spacing), or None."""
    if not folder or not folder.is_dir():
        return None
    return next((d for d in sorted(folder.iterdir()) if d.is_dir() and _task_id(d.name) == _task_id(task)), None)


def _db_rows(cfg, table, section, detected, notes, cache):
    """(rows, src) of ``table`` through the [DB] connection, or None (noted). ``cache``: table → result,
    so [Data], [Label] and [Prediction] on one table query it once."""
    if table in cache:
        return cache[table]
    cache[table] = None
    if cfg.get("project", {}).get("db") is False:  # left out or empty: allowed
        notes.append(f"[{section}] Type = DB, but [Project] DB = False")
    elif not table:
        notes.append(f"[{section}] Type = DB has no Table")
    else:
        try:
            cache[table] = _rows_from_db({**cfg.get("db", {}), "table": table})
            src = cache[table]
            detected.append(("Database", f"{src[1]['where']} · {table} · {len(src[0]):,} rows", "positive", "Connected"))
        except Exception as e:  # driver missing, server down, bad table
            msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            notes.append(f"DB {table} unavailable ({msg})")
            detected.append(("Database", f"{table} · {msg}", "warning", "Unreachable"))
    return cache[table]


def _csv_rows(f, section, notes):
    """(rows, src) of a csv / tsv / jsonl / parquet file, or None (noted)."""
    if not f or not f.is_file():
        notes.append(f"[{section}] File_path {f or '(not set)'} is not a file")
        return None
    try:
        return _read_table(f), dict(kind="file", name=f.name, where=remote.origin(f) or str(f), label=f"{f.suffix[1:]} · {f.name}",
                                    base=_folder_of(f))
    except (OSError, ValueError, ImportError) as e:
        notes.append(f"{f.name}: {e}")
        return None


def _task_data(cfg, paths, base, tasks, detected, notes, as_of, cache):
    """Data rows of a task project: the files of [Data] (one source for every task), each with its ground truth
    per task from [Label] (``_attach_labels``).

    [Data] Type = "DB" (``Table``) | "CSV" (``File_path``: the csv listing the files) | "Folder" (``File_path``: the
    dataset folder, split/label/file). For DB / CSV, ``Raw`` names the column with each raw file's path (guessed
    when left out).
    Predictions never come from the data; they're read from [Prediction].
    """
    dcfg = cfg.get("data", {})
    kind = str(dcfg.get("type") or "").lower()
    if kind == "folder":
        pcfg = cfg.get("prediction", {})
        skip = {"." + str(pcfg.get("format") or "txt").lower().lstrip(".")} if str(pcfg.get("type") or "").lower() == "folder" else set()
        src = _rows_from_scan(paths["data"], skip, notes)  # prediction files kept next to the data aren't data
        if not src:
            return None
        cols, rows = dict.fromkeys(COLS), src[0]
        for r in rows:
            r["folder_label"] = r["label"]  # the class folder; [Label] decides what each task's label is
    else:
        if kind == "db":
            src = _db_rows(cfg, dcfg.get("table"), "Data", detected, notes, cache)
        elif kind == "csv":
            src = _csv_rows(paths["data"], "Data", notes)
        else:
            notes.append(f"[Data] Type must be DB, CSV or Folder, not {dcfg.get('type')!r}" if kind else "[Data] Type is not set")
            return None
        if not src or not src[0]:
            return None
        path_col = dcfg.get("raw")
        cols = _columns(src[0], {"path": path_col} if path_col else {})
        cols.update(label=None, predict=None)
        if not cols["path"]:
            notes.append(f"{src[1]['label']}: no file-path column found (set [Data] Raw)")
            return None
        rows = _rows(src, cols, paths["data"], notes, as_of)
        seen = set()  # a table listing a file once per task (a task column) still lists it once here
        rows = [r for r in rows if not (os.path.normpath(r["path"]) in seen or seen.add(os.path.normpath(r["path"])))]
    if not rows:
        return None
    _attach_labels(cfg, paths, base, tasks, rows, kind, src, cols, detected, notes, cache)
    d = _data(rows, src[1], cols)
    d["dash"]["task"] = " · ".join(t[:1].upper() + t[1:] for t in tasks)
    return d


def _value(v):
    """A label / prediction cell as text: json for a db json column (list / dict), None when empty."""
    if v in (None, "") or (isinstance(v, float) and v != v):
        return None
    return json.dumps(v) if isinstance(v, (list, dict)) else str(v)


def _task_rows(rows, path_col, task):
    """The rows of ``task`` when ``rows`` list a file once per task (a task column, file paths repeating), else
    every row."""
    col = _columns(rows, {})["task"] if rows else None
    if not col or len({r.get(path_col) for r in rows}) == len(rows):
        return rows
    return [r for r in rows if TASK_IDS.get(_task_id(r.get(col) or "")) == task]


def _label_files(folder):
    """(by path under ``folder`` without extension, by file stem) for every file in it."""
    by_rel, by_stem = {}, {}
    for dp, fs in _walk(folder):
        for f in fs:
            by_rel[os.path.splitext(_rel(dp / f, folder))[0]] = dp / f
            by_stem.setdefault(Path(f).stem, dp / f)
    return by_rel, by_stem


def _attach_labels(cfg, paths, base, tasks, rows, data_kind, data_src, data_cols, detected, notes, cache):
    """Give each row ``labels`` ({task: ground truth or None}) and ``label`` (the first task's: the viewer's default
    uses it), from [Label].

    [Label] Type = "DB" / "CSV": ``<Task>_Label`` names the column with that task's ground truth (``Label``: the
    column of every task without one), in ``Table`` / ``File_path`` (default: [Data]'s), matched to the data by the
    raw-file path column (``Raw``, default [Data]'s). A table listing a file once per task (a task column) gives each
    task the value of its own row.
    Type = "Folder": classification reads the split/label/file layout of a Folder data source; another task's
    ``<Task>_Label`` names a folder of label files (absolute, or under ``File_path``, default the data folder), one
    per data file with the same name.
    """
    lcfg, dcfg = cfg.get("label", {}), cfg.get("data", {})
    keys = _per_task(lcfg, "label")
    if lcfg.get("label") and str(lcfg.get("type") or data_kind).lower() in ("db", "csv"):
        keys = {t: keys.get(t, lcfg["label"]) for t in tasks}  # Label: the column of every task without its own
    kind = str(lcfg.get("type") or data_kind).lower()
    for r in rows:
        r["labels"] = dict.fromkeys(tasks)
    title = lambda t: tomledit.title(t.replace(" ", "_").replace("-", "_"))

    if kind == "folder":
        root = _resolve(lcfg.get("file_path"), base) or (paths["data"] if paths["data"] and paths["data"].is_dir() else base)
        for t in tasks:
            if t == "classification":
                if data_kind != "folder":
                    notes.append("[Label] Type = Folder: classification labels come from a [Data] Type = Folder layout")
                for r in rows:
                    r["labels"][t] = r.get("folder_label")
                continue
            if t not in keys:
                continue
            folder = _resolve(keys[t], root)
            if not folder or not folder.is_dir():
                notes.append(f"[Label] {title(t)}_Label: no folder {keys[t]}")
                continue
            by_rel, by_stem = _label_files(folder)
            data_root = os.path.commonpath([os.path.dirname(r["path"]) for r in rows])
            for r in rows:
                f = by_rel.get(os.path.splitext(os.path.relpath(r["path"], data_root))[0]) or by_stem.get(Path(r["path"]).stem)
                r["labels"][t] = f.name if f else None
            if not by_rel:
                notes.append(f"[Label] {title(t)}_Label: no label files in {folder}")
    elif kind in ("db", "csv"):
        table, file = lcfg.get("table") or dcfg.get("table"), _resolve(lcfg.get("file_path"), base) or paths["data"]
        if kind == data_kind and (kind == "csv" and file == paths["data"] or kind == "db" and table == dcfg.get("table")):
            src, path_col = data_src, data_cols["path"]  # the labels sit next to the files
        else:
            src = _db_rows(cfg, table, "Label", detected, notes, cache) if kind == "db" else _csv_rows(file, "Label", notes)
            raw = lcfg.get("raw") or dcfg.get("raw")
            path_col = _columns(src[0], {"path": raw} if raw else {})["path"] if src and src[0] else None
        if src and src[0] and path_col:
            names = set(src[0][0])
            for t, c in keys.items():
                if c not in names:
                    notes.append(f"[Label] {title(t)}_Label: no column {c!r} in {src[1]['name']}")
            at = src[1].get("base")
            for t, c in keys.items():
                index = {os.path.normpath(_abs(r[path_col], at)): r for r in _task_rows(src[0], path_col, t) if r.get(path_col)}
                for r in rows:
                    raw = index.get(os.path.normpath(r["path"]))
                    r["labels"][t] = _value(raw.get(c)) if raw else None
        elif src and src[0]:
            notes.append(f"[Label] {src[1]['name']}: no file-path column")
    else:
        notes.append(f"[Label] Type must be DB, CSV or Folder, not {lcfg.get('type')!r}")
    for t in tasks:
        if t not in keys and not (kind == "folder" and t == "classification"):
            notes.append(f"[Label] no {title(t)}_Label: {t} files have no ground truth")
    for r in rows:
        r["label"] = r["labels"][tasks[0]]


def _pred_txt(f):
    """dict(predict, predict_score) from the first line of a prediction txt: "<class> [score]"."""
    try:
        line = next((l for l in f.read_text(errors="replace").splitlines() if l.strip()), "")
    except OSError:
        line = ""
    parts = line.replace(",", " ").split()
    return dict(predict=parts[0] if parts else None, predict_score=parts[1] if len(parts) > 1 else None)


def _pred_json(f, keys):
    """dict(predict, predict_score) from a prediction json object (or the first object of a list). ``keys``:
    {"predict": key or None, "predict_score": key or None}; a key left None is the first of PRED_JSON_KEYS found."""
    try:
        d = json.loads(f.read_text(errors="replace"))
    except (OSError, ValueError):
        d = None
    if isinstance(d, list):
        d = next((x for x in d if isinstance(x, dict)), None)
    if not isinstance(d, dict):
        return dict.fromkeys(keys)
    return {k: d.get(key) if key else next((d[a] for a in PRED_JSON_KEYS[k] if a in d), None) for k, key in keys.items()}


PRED_KEYS = ("type", "file_path", "table", "format", "predict", "predict_score")


def _task_predictions(cfg, paths, base, rows, tasks, detected, notes, cache):
    """{source: dict(task, file, rel, shows, by_path, by_name)} like ``store.INFERENCE``: each task's predictions.

    [Prediction] keys apply to every task; ``<Task>_<Key>`` (``Object_detection_Predict``, ``Segmentation_File_path``, …)
    overrides one for that task. With task folders under [Path] Results (Results/classification/…), CSV results
    are looked for in the task's own folder. With several tasks, a source's name starts with its task.
    """
    pcfg = cfg.get("prediction", {})
    task_dirs = any(_task_dir(paths["results"], t) for t in TASKS)
    out = {}
    for t in tasks:
        pc = {k: _per_task(pcfg, k).get(t, pcfg.get(k)) for k in PRED_KEYS} | dict(results_root=paths["results"])
        where = "[Prediction]" + (f" {t}" if len(tasks) > 1 else "")
        results = _task_dir(paths["results"], t) if task_dirs else paths["results"]
        for name, src in _predictions(pc, cfg, base, results, rows, detected, notes, cache, where, t).items():
            src["task"] = t
            out[f"{t} · {name}" if len(tasks) > 1 else name] = src
    return out


def _predictions(pc, cfg, base, results, rows, detected, notes, cache, where, task=None):
    """One task's predictions (``pc``: its [Prediction] keys). Type = "CSV": ``File_path`` is a result file name /
    glob under ``results`` (or an absolute path), one source per match. "DB": ``Table``, matched by its file-path
    column. "Folder": ``File_path`` holds one ``<file stem>.<Format>`` per data file, at the data file's place in the data tree or
    anywhere by stem: a txt holding "<class> [score]", or a json object. ``Predict`` / ``Predict_score`` name the
    class / score columns of CSV and DB, and the keys of a json (guessed from PRED_JSON_KEYS when left out). A CSV /
    table listing a file once per task (a task column) gives ``task`` the values of its own rows."""
    kind = str(pc.get("type") or "").lower()
    shows = {k: pc[k] for k in ("predict", "predict_score") if pc.get(k)}
    if kind == "csv":
        if results is None and not Path(str(pc.get("file_path") or "")).is_absolute():  # an absolute file needs no folder
            notes.append(f"{where}: no folder for it under Path.Results")
            return {}
        under = "Path.Results" + (f"/{results.name}" if results and results.parent == pc["results_root"] else "")
        sources, inotes = _inference(pc.get("file_path"), shows, results, what=f"{where} File_path", under=under, task=task)
        notes += inotes
        return sources
    if kind == "db":
        table = pc.get("table")
        src = _db_rows(cfg, table, "Prediction", detected, notes, cache)
        if not src or not src[0]:
            return {}
        col = _columns(src[0], {})["path"]
        if not col:
            notes.append(f"{where} {table}: no file-path column")
            return {}
        lost = [c for c in shows.values() if c not in src[0][0]]
        if lost:
            notes.append(f"{where} {table}: no column {', '.join(lost)}")
        by_path, by_name = _index(_task_rows(src[0], col, task) if task else src[0], col, shows, None)
        return {f"db · {table}": dict(file=src[1]["where"], rel=f"db · {table}", shows=shows, by_path=by_path, by_name=by_name)}
    if kind == "folder":
        fmt = str(pc.get("format") or "txt").lower().lstrip(".")
        pdir = _resolve(pc.get("file_path"), base)
        if fmt not in ("txt", "json"):
            notes.append(f"{where} Format {fmt} isn't supported (txt, json)")
            return {}
        if not pdir or not pdir.is_dir():
            notes.append(f"{where} File_path {pc.get('file_path')} is not a folder")
            return {}
        by_rel, by_stem = {}, {}
        for dp, fs in _walk(pdir):
            for f in fs:
                if f.lower().endswith("." + fmt):
                    by_rel[os.path.splitext(_rel(dp / f, pdir))[0]] = dp / f
                    by_stem.setdefault(Path(f).stem, dp / f)
        if not by_rel:
            notes.append(f"{where} no .{fmt} files under {pdir}")
            return {}
        root = os.path.commonpath([os.path.dirname(r["path"]) for r in rows]) if rows else str(pdir)
        keys = {k: pc.get(k) for k in ("predict", "predict_score")}
        read = (lambda f: _pred_json(f, keys)) if fmt == "json" else _pred_txt
        by_path = {}
        for r in rows:
            f = by_rel.get(os.path.splitext(os.path.relpath(r["path"], root))[0]) or by_stem.get(Path(r["path"]).stem)
            if f:
                by_path[os.path.normpath(r["path"])] = dict(values=read(f))
        if fmt == "json":
            shows = {k: f"json · {key or ' / '.join(PRED_JSON_KEYS[k][:2])}" for k, key in keys.items()}
        else:
            shows = dict(predict="txt · 1st value", predict_score="txt · 2nd value")
        return {f"{pdir.name}/": dict(file=str(pdir), rel=f"{pdir.name}/ · *.{fmt}", by_path=by_path, by_name={},
                                      shows=shows)}
    notes.append(f"{where} Type must be CSV, DB or Folder, not {pc.get('type')!r}" if kind else f"{where} Type is not set")
    return {}


# ---------------------------------------------------------------- git
def _git_info(root, cfg):
    top = _run("git", "rev-parse", "--show-toplevel", cwd=root).strip()
    if not top:
        return None
    branch = _run("git", "branch", "--show-current", cwd=top).strip() or cfg.get("branch") or "HEAD"
    head = _run("git", "status", "-sb", cwd=top).splitlines()
    track = head[0][3:] if head else ""
    dirty = len(head) - 1
    if "[" in track:
        sync = track[track.index("[") + 1:track.index("]")]
    elif "..." in track:
        sync = "up to date with " + track.split("...")[1]
    else:
        sync = "no upstream"
    remote = _run("git", "remote", "get-url", "origin", cwd=top).strip() or cfg.get("remote", "")
    n = _run("git", "rev-list", "--count", "HEAD", cwd=top).strip() or "0"
    # local vs remote: the branch's upstream as of the last fetch (Laboard doesn't fetch on its own)
    upstream = _run("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", cwd=top).strip()
    local_only = set(_run("git", "rev-list", f"{upstream}..HEAD", cwd=top).split()) if upstream else set()
    remote_only = set(_run("git", "rev-list", f"HEAD..{upstream}", cwd=top).split()) if upstream else set()
    fetch_head = Path(top, _run("git", "rev-parse", "--git-path", "FETCH_HEAD", cwd=top).strip() or ".git/FETCH_HEAD")
    fetched = _ago(fetch_head.stat().st_mtime) if fetch_head.is_file() else "never"
    head_short = _run("git", "rev-parse", "--short", "HEAD", cwd=top).strip()
    authors = len(_run("git", "shortlog", "-sn", "HEAD", cwd=top).splitlines())

    # --name-status, not --numstat: line counts diff every blob and take seconds on repos with big files
    fmt = "\x1e%h\x1f%s\x1f%an\x1f%ar\x1f%ad\x1f%D\x1f%H"
    revs = ["HEAD", upstream] if upstream else ["HEAD"]  # remote-only commits are listed too
    log = _run("git", "log", "-100", "--name-status", f"--format={fmt}", "--date=format:%b %d, %H:%M", *revs, "--",
               cwd=top, timeout=30)
    status = {"A": ("added", ""), "D": ("", "deleted"), "R": ("renamed", ""), "C": ("copied", "")}
    commits, touched = [], Counter()
    for chunk in log.split("\x1e")[1:]:
        head_line, _, body = chunk.partition("\n")
        h, subj, author, rel, date, refs, full = head_line.split("\x1f")
        files = []
        for line in body.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                p = parts[-1]
                files.append((p, *status.get(parts[0][:1], ("modified", ""))))
                touched[p] += 1
        tags = []
        for ref in (r.strip() for r in refs.split(",")):
            ref = ref.replace("HEAD -> ", "")
            if not ref or ref == "HEAD":
                continue
            if ref.startswith("tag: "):
                tags.append((ref[5:], "green"))
            else:
                tags.append((ref, "tab" if ref == branch else "soft"))
        where = "local" if full in local_only or not upstream else "remote" if full in remote_only else "both"
        commits.append((h, subj, author, rel, date, files, tags, where))
    return dict(top=top, branch=branch, sync=sync, dirty=dirty, remote=remote, n=int(n), authors=authors,
                commits=commits, hot_file=touched.most_common(1)[0][0] if touched else "", head=head_short,
                upstream=upstream, ahead=len(local_only), behind=len(remote_only), fetched=fetched)


def _last_commit(path, top, rev="HEAD"):
    return _run("git", "log", "-1", "--format=%h", rev, "--", str(path), cwd=top).strip() if top else ""


_snapshots = set()


@atexit.register
def _remove_snapshots():
    for d in _snapshots:
        shutil.rmtree(d, ignore_errors=True)


def _snapshot(top, rev, rels):
    """Extract ``rels`` (paths in the repo) as they were at ``rev`` into a temp folder.

    Only reads the repository (``git archive``); the working tree, index and HEAD are untouched.
    Returns (folder, full sha, the rels git tracked at that commit).
    """
    sha = _run("git", "rev-parse", "--verify", f"{rev}^{{commit}}", cwd=top).strip()
    if not sha:
        raise ValueError(f"unknown commit {rev}")
    tracked = [r for r in rels if _run("git", "ls-tree", "--name-only", sha, "--", r, cwd=top).strip()]
    key = hashlib.sha1("\0".join(tracked).encode()).hexdigest()[:10]
    dest = SNAPSHOT_ROOT / f"{sha[:12]}-{key}"
    _snapshots.add(dest)
    if not (dest / ".complete").exists():
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        if tracked:
            proc = subprocess.Popen(["git", "archive", "--format=tar", sha, "--", *tracked], cwd=top,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
                tar.extractall(dest, filter="data")
            if proc.wait() != 0:
                raise OSError(proc.stderr.read().decode().strip() or f"git archive {sha[:7]} failed")
        (dest / ".complete").touch()
    return dest, sha, tracked


# ---------------------------------------------------------------- models
def _model_group(rel):
    """The model a file under paths.models belongs to: its first folder, or the first two under a task folder
    (Models/classification/<model>/…)."""
    parts = Path(rel).parts
    return "/".join(parts[:2]) if len(parts) > 2 and _task_id(parts[0]) in TASK_IDS else parts[0]


def _models(models_dir, mcfg):
    exts = {e if e.startswith(".") else "." + e: MODEL_EXT.get(e, e.lstrip(".").upper())
            for e in (e.lower() for e in mcfg.get("extensions", []))} or MODEL_EXT
    files = [(dp, f) for dp, fs in _walk(models_dir) for f in fs]
    picked = [(dp, f) for dp, f in files if Path(f).suffix.lower() in exts]
    if not picked:  # no known checkpoint format: list everything
        picked = files
    if not picked:
        return None
    found = []
    for dp, f in picked:
        p = dp / f
        st = p.stat()
        ext = p.suffix.lower()
        found.append(dict(path=p, ext=ext, fmt=exts.get(ext) or (ext[1:].upper() or "FILE"), bytes=st.st_size,
                          mtime=st.st_mtime, folder=_rel(dp, models_dir), group=_model_group(_rel(p, models_dir))))
    for m, label in zip(found, _labels([m["path"] for m in found], models_dir)):
        m["label"] = label
    rows, info = [], {}
    for m in found:
        rows.append((m["label"], m["ext"][1:].upper()[:6] or "FILE", _size(m["bytes"]), "" if m["folder"] == "." else m["folder"]))
        info[m["label"]] = dict(path=str(m["path"]), stats=[("Size", _size(m["bytes"]))],
                                props=[("Path", _rel(m["path"], models_dir.parent)), ("Kind", m["fmt"]),
                                       ("Modified", _stamp(m["mtime"])), ("Folder", m["folder"])])
    fmts = defaultdict(list)
    for m in found:
        fmts[m["fmt"]].append(m["ext"])
    formats = [(f, len(e), " ".join(sorted(set(e)))[:40], FORMAT_COLORS[i % len(FORMAT_COLORS)])
               for i, (f, e) in enumerate(sorted(fmts.items(), key=lambda kv: -len(kv[1])))]
    if len(formats) > len(FORMAT_COLORS):  # fold the tail into one "Other" segment
        rest = formats[len(FORMAT_COLORS) - 1:]
        formats = formats[:len(FORMAT_COLORS) - 1] + [("Other", sum(n for _, n, _, _ in rest), "", FORMAT_COLORS[-1])]
    groups = defaultdict(list)
    for m in found:
        groups[Path(m["group"]).stem if m["group"] == m["path"].name else m["group"]].append(m)
    table = [(g, " · ".join(sorted({m["ext"][1:] or "file" for m in ms}))[:24], len(ms), _size(sum(m["bytes"] for m in ms)))
             for g, ms in sorted(groups.items(), key=lambda kv: -max(m["mtime"] for m in kv[1]))][:8]
    newest = max(m["mtime"] for m in found)
    return dict(
        MODEL_FILES=rows, MODEL_INFO=info,
        dash=dict(models_n=str(len(groups)), trained_n=str(len(found)), last_trained=_ago(newest), formats=formats,
                  models=table, model_tiles=("Models", "Files", "Last updated"), model_cols=("Model", "Formats", "Files", "Size")),
        detected=[("Models", f"{models_dir.name}/ · {len(found)} files · {_size(sum(m['bytes'] for m in found))}",
                   "positive", "Found")])


# ---------------------------------------------------------------- runs
def _flatten(d, prefix=""):
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            yield from _flatten(v, key + ".")
        elif isinstance(v, list) and len(v) > 8:
            yield key, f"[{len(v)} items]"
        else:
            s = json.dumps(v, default=str) if isinstance(v, (list, bool)) or v is None else str(v)
            yield key, s if len(s) <= 90 else s[:87] + "…"


def _read_config(p):
    """dict from a json / yaml / toml file, or None."""
    try:
        if p.suffix == ".json":
            with open(p) as f:
                d = json.load(f)
        elif p.suffix == ".toml":
            with open(p, "rb") as f:
                d = tomllib.load(f)
        else:
            import yaml  # optional; yaml configs are skipped without it
            with open(p) as f:
                d = yaml.safe_load(f)
    except Exception:  # unreadable or malformed (incl. yaml.YAMLError, no yaml installed): skip the file
        return None
    return d if isinstance(d, dict) else None


def _configs(d):
    return sorted(f for f in d.iterdir() if f.is_file() and f.suffix.lower() in CONFIG_EXT and f.stat().st_size < 2_000_000)


def _run_detail(run_dir, name, git, runs_dir):
    sections, sources, cfg = [], [], {}
    for f in _configs(run_dir):
        d = _read_config(f)
        if d is None:
            continue
        sources.append(f.name)
        if f.name == "trainer_state.json":
            continue
        rows = [(k, v, f.name) for k, v in _flatten(d)]
        if rows:
            sections.append((f.stem.replace("_", " ").capitalize(), f.name, rows[:MAX_CONFIG_ROWS], False))
        if "config" in f.stem or "args" in f.stem or "hparams" in f.stem:
            cfg.update(d)
    state = _read_config(run_dir / "trainer_state.json") or {}
    epoch = state.get("epoch")
    total = state.get("num_train_epochs") or cfg.get("epochs") or cfg.get("num_train_epochs") or cfg.get("max_epochs")
    if isinstance(epoch, (int, float)) and isinstance(total, (int, float)) and total:
        progress, ep = min(100, round(epoch / total * 100)), f"Epoch {epoch:g} / {total:g}"
    else:
        progress, ep = 0, f"{total} epochs configured" if total else "No trainer_state.json"
    best = state.get("best_metric")
    mtime = max((p.stat().st_mtime for p in run_dir.iterdir() if p.is_file()), default=run_dir.stat().st_mtime)
    info = dict(cmd=_rel(run_dir, runs_dir.parent), path=str(run_dir), commit=_last_commit(git["repo"] / _rel(run_dir, runs_dir), git["top"], git["rev"]) or "—"
                if git else "—",
                started=f"modified {_stamp(mtime)}", progress=progress, epoch=ep,
                eta=f"best {best:.4f}" if isinstance(best, float) else "", sources=sources, mtime=mtime)
    meta = f"{best * 100:.1f}%" if isinstance(best, float) and 0 <= best <= 1 else datetime.fromtimestamp(mtime).strftime("%b %d")
    return (name, meta), info, sections


def _runs(runs_dir, git):
    """``git``: dict(top, rev, repo=runs_dir's place in the repo) to look up each run's last commit, or None."""
    """Every folder (up to RUN_DEPTH deep) that holds config files is a run; runs don't nest."""
    out, run_dirs = [], []
    for dp, _ in _walk(runs_dir, RUN_DEPTH):
        if any(dp.is_relative_to(r) and dp != r for r in run_dirs if r != runs_dir):
            continue
        if _configs(dp):
            run_dirs.append(dp)
        if len(run_dirs) >= MAX_RUNS:
            break
    names = Counter()
    for d in run_dirs:
        if d == runs_dir:
            cfg = next((c for c in map(_read_config, _configs(d)) if c), {})
            name = str(cfg.get("exp_name") or cfg.get("run_name") or cfg.get("name") or d.name)
        else:
            name = _rel(d, runs_dir)
        names[name] += 1
        if names[name] > 1:
            name = f"{name} ({names[name]})"
        out.append(_run_detail(d, name, git, runs_dir))
    if not out:
        return None
    out.sort(key=lambda r: -r[1]["mtime"])
    (name, _), info, sections = out[0]
    hp = [(k, v) for _, _, rows, _ in sections for k, v, _ in rows][:12]
    return dict(RUNS=[r[0] for r in out], RUN_DETAILS={r[0][0]: (r[1], r[2]) for r in out},
                dash=dict(run_note=(name, info["commit"], f"{info['started']} · read from {', '.join(info['sources'][:4])}"),
                          hp=hp),
                detected=[("Hyperparameter", f"{runs_dir.name}/ · {len(out)} set{'s' if len(out) != 1 else ''}", "positive", "Found")])


# ---------------------------------------------------------------- results
def _results(results_dir):
    files = []
    for dp, fs in _walk(results_dir):
        files += [dp / f for f in fs]
        if len(files) >= MAX_RESULT_FILES:
            files = files[:MAX_RESULT_FILES]
            break
    if not files:
        return None
    rows, paths = [], {}
    for p, label in zip(files, _labels(files, results_dir)):
        paths[label] = p
        ext = "TB" if "tfevents" in p.name else (_ext(p.name).upper()[:6] or "FILE")
        rows.append((label, ext, _size(p.stat().st_size), "" if p.parent == results_dir else _rel(p.parent, results_dir)))

    exts = Counter("tfevents" if "tfevents" in p.name else _ext(p.name) or "no ext" for p in files)
    accuracy = next((p for p in files if p.name == "accuracy.csv"), None)
    acc = []
    if accuracy:
        with open(accuracy, newline="") as fh:
            for r in csv.reader(fh):
                try:
                    acc.append((r[0][:7], r[1], float(r[2]), float(r[3]), float(r[4])))
                except (IndexError, ValueError):
                    continue
    tb = exts.get("tfevents", 0)
    wandb = sorted(results_dir.rglob("offline-run-*"))
    detected = [("Results", f"{results_dir.name}/ · {len(files):,} files", "positive", "Found")]
    if tb:
        detected.append(("TensorBoard", f"{tb} event file{'s' if tb != 1 else ''}", "positive", "Found"))
    if wandb:
        detected.append(("Weights & Biases", f"{wandb[0].parent.name}/ · {len(wandb)} offline run(s)", "warning", "Offline"))
    top_ext = [(f".{e} files" if e not in ("tfevents", "no ext") else e, f"{n:,}") for e, n in exts.most_common(2)]
    dash = dict(accuracy_csv=acc, accuracy_path=_rel(accuracy, results_dir.parent) if accuracy else "", result_counts=[("Result files", f"{len(files):,}"), *top_ext])
    if acc:
        best = min(acc, key=lambda r: r[3])
        fast = min(acc, key=lambda r: r[4])
        dash.update(best_valid=(best[0], f"{best[3]:.3f}"), fastest=(fast[1], f"{fast[4]:.1f} ms"))
    return dict(RESULT_FILES=rows, RESULT_PATHS=paths, RESULT_ROOT=f"{results_dir.name}/", dash=dash, detected=detected)


# ---------------------------------------------------------------- labels / inference per data file
def _index(rows, path_col, shows, base):
    """(by_path, by_name): dict(values={key: row[column] for shows}) per data file path / file name."""
    by_path, by_name = {}, {}
    for r in rows:
        p = r.get(path_col)
        if not p:
            continue
        rec = dict(values={k: _value(r.get(c)) for k, c in shows.items()})
        p = os.path.normpath(_abs(p, base))
        by_path[p] = rec
        by_name.setdefault(os.path.basename(p), rec)
    return by_path, by_name


def _inference(name, shows, results_dir, path_col=None, what="[Labels] Result_file", under="Path.Results", task=None):
    """Inference columns from result files: ``[labels]`` (also read when spelled ``[lables]``) and
    ``[prediction] type = "csv"``.

    ``name`` is a file name, relative path or glob under paths.results (or an absolute path); every
    match is one source, e.g. one ``inference.csv`` per model folder. ``shows`` maps a key to the column
    shown for it, e.g. ``{"infer": "classification"}``; ``path_col`` names the file-path column (guessed
    when None). Rows match data files by path, or by file name when paths differ. The ground truth stays
    the data's own label; a label column in the result file isn't read. ``task``: a file listing a file once per
    task (a task column) gives the values of that task's rows. Returns ({source: dict}, notes).
    """
    if not name:
        return {}, [f"{what} not set"]
    if Path(name).is_absolute():
        files = [Path(name)] if Path(name).is_file() else []
    else:
        files = sorted(f for f in results_dir.rglob(name) if f.is_file()) if results_dir and results_dir.is_dir() else []
    if not files:
        return {}, [f"{what} {name} not found under {under}"]
    sources, notes = {}, []
    for f in files:
        try:
            rows = _read_table(f)
        except (OSError, ValueError, ImportError) as e:
            notes.append(f"{f.name}: {e}")
            continue
        cols = _columns(rows, {"path": path_col} if path_col else {}) if rows else {}
        if not cols.get("path"):
            notes.append(f"{_rel(f, results_dir)}: no file-path column")
            continue
        names = list(rows[0])
        lost = [c for c in shows.values() if c not in names]
        if lost:
            notes.append(f"{_rel(f, results_dir)}: no column {', '.join(lost)}")
        by_path, by_name = _index(_task_rows(rows, cols["path"], task) if task else rows, cols["path"], shows, _folder_of(f))
        inside = results_dir is not None and f.is_relative_to(results_dir)
        src = _rel(f.parent, results_dir) if inside and f.parent != results_dir else f.name  # a file given outside: its name
        sources[src] = dict(file=str(f), rel=_rel(f, results_dir.parent if results_dir else f.parent),
                            shows=shows, by_path=by_path, by_name=by_name)
    return sources, notes


# ---------------------------------------------------------------- entry point
def _restore():
    global _original
    if _original is None:
        _original = {k: copy.deepcopy(getattr(store, k)) for k in _PATCHED}
    for k, v in _original.items():
        _set(k, copy.deepcopy(v))


def _set(name, value):
    cur = getattr(store, name)
    if isinstance(cur, dict) and isinstance(value, dict):
        cur.clear()  # keep identity: pages bind e.g. ``D = store.DASH`` at import
        cur.update(value)
    else:
        setattr(store, name, value)


def _read_toml(p, text=None):
    """The project toml (``text``, else the file) with every name lower case and [Path] read as [paths]
    (``tomledit.normalize``); a bare word value (``data = DB``) is read as a string."""
    return tomledit.normalize(tomledit.parse(p.read_text() if text is None else text))


def load(toml_path, commit=None, text=None):
    """Read ``toml_path`` and fill ``store`` with the project's data. Returns a list of notes.

    ``commit``: show the project as it was at that commit (paths inside the repo are read from a
    snapshot of it, db rows are cut at its time). ``text``: the project file's content to use instead
    of what's on disk (values edited in Setting; the file itself is never written). On any error
    ``store`` keeps what it held before and the error is raised.
    """
    before = {k: copy.deepcopy(getattr(store, k)) for k in _PATCHED}
    try:
        toml_path = Path(toml_path).expanduser().resolve()
        cfg = _read_toml(toml_path, text)
        _restore()
        return _load(toml_path, cfg, commit, text)
    except Exception:
        for k, v in before.items():
            _set(k, v)
        raise


def _copy_remote(cfg, notes):
    """[Data] / [Label] / [Prediction] values written host:path → a local copy (``remote.copy``), read like a local
    file or folder. A data folder ([Data] File_path of Type = Folder, an older-format Path.Data that isn't a table
    file) stays remote: it's listed over ssh (``_rows_from_scan``) and its files are fetched when shown."""
    folder_data = str(cfg.get("data", {}).get("type") or "").lower() == "folder"
    for sec in ("data", "label", "prediction", "paths"):
        for k, v in cfg.get(sec, {}).items():
            if not remote.split(v) or sec == "paths" and k != "data":  # Models / Hyperparameter / Results: REMOTE_COPY
                continue
            if (sec, k) == ("data", "file_path") and folder_data or sec == "paths" and Path(v).suffix.lower() not in TABLE_EXT:
                continue
            opts = dict(exts=(".txt", ".json")) if sec == "prediction" else {}  # Type = Folder: its txt / json files
            try:
                cfg[sec][k] = str(remote.copy(v, max_size=REMOTE_FILE_MAX, **opts))
            except OSError as e:
                cfg[sec][k] = None
                notes.append(f"[{tomledit.title(sec)}] {tomledit.title(k)} {v}: {e}")


def _load(toml_path, cfg, commit, text=None):
    base = toml_path.parent
    notes, detected, dash = [], [], {}
    remote.use(base, cfg.get("ssh", {}))
    _copy_remote(cfg, notes)
    proj, gcfg, pcfg = cfg.get("project", {}), cfg.get("git", {}), cfg.get("paths", {})
    # [Project] Task (one task or several): [Data] / [Label] / [Prediction] say where data, labels and predictions
    # are (see _task_data); without one, the older paths.data / [db] / [labels] format
    tasks = _tasks(proj.get("task"), notes)
    task_mode = bool(tasks)
    _set("TASKS", tasks)
    dcfg = cfg.get("data", {})
    if task_mode:
        ref, db_key = dcfg.get("file_path") if str(dcfg.get("type", "")).lower() in ("csv", "folder") else None, None
    else:
        # paths.data naming a toml table (data = "DB" → [DB]) reads rows from that database only
        ref = pcfg.get("data")
        db_key = ref.lower() if isinstance(ref, str) and ref.lower() not in RESERVED and isinstance(cfg.get(ref.lower()), dict) else None
    values = {k: ref if k == "data" else pcfg.get("hyperparameter" if k == "runs" else k)
              for k in ("data", "models", "runs", "results")}  # [Path] Hyperparameter → paths["runs"]
    remotes = {k: v for k, v in values.items() if k in REMOTE_COPY and remote.split(v)}  # host:path, copied over ssh below
    paths = {k: None if (k == "data" and db_key) or k in remotes else _resolve(v, base) for k, v in values.items()}
    root = _resolve(proj.get("root"), base) or next((p for p in paths.values() if p), base)
    name = proj.get("name") or root.name

    git = _git_info(root, gcfg)
    top = git["top"] if git else None
    if git:
        _set("COMMITS", git["commits"])
        detected.append(("Git repository", f"{git['branch']} · {git['n']} commits", "positive", "Found"))
    else:
        detected.append(("Git repository", str(root), "warning", "Not found"))

    # an older commit: read paths from a snapshot of it; what git doesn't track can't be shown as of then
    repo_paths, missing, view = dict(paths), {}, None
    if commit:
        if not git:
            raise ValueError(f"{root} is not a git repository")
        rels = {k: _rel(p, top) for k, p in paths.items() if p and p.is_relative_to(top)}
        snap, sha, tracked = _snapshot(top, commit, sorted(set(rels.values())))
        for k, p in paths.items():
            if not p:
                continue
            if rels.get(k) in tracked:
                paths[k] = snap / rels[k]
            else:
                paths[k] = None
                missing[k] = f"{p} · not tracked in git at {sha[:7]}" if k in rels else f"{p} · outside the git repository"
                notes.append(f"Path.{PATH_LABELS[k]} is {'not tracked at ' + sha[:7] if k in rels else 'outside the repository'}")
        view = dict(short=sha[:7], when=datetime.fromtimestamp(int(_run("git", "show", "-s", "--format=%ct", sha, cwd=top))))
        detected.insert(1, ("Snapshot", f"{sha[:7]} · {view['when']:%b %d, %H:%M} · read-only", "warning", "Past commit"))
    for k, v in remotes.items():
        if view:
            missing[k] = f"{v} · on another machine, not in git"
            notes.append(f"Path.{PATH_LABELS[k]} is on another machine")
            continue
        try:
            paths[k] = remote.copy(v, **REMOTE_COPY[k])
        except OSError as e:
            missing[k] = f"{v} · {e}"
            notes.append(f"Path.{PATH_LABELS[k]} {v}: {e}")

    as_of, db_cache = view["when"] if view else None, {}
    if task_mode:
        d = _task_data(cfg, paths, base, tasks, detected, notes, as_of, db_cache)
    else:
        d = _load_data(cfg.get(db_key or "db", {}), dcfg, paths, base, detected, notes, as_of=as_of)
    if d:
        for k in ("DATA_FOLDERS", "CLASSES", "SPLIT_TOTALS", "SPLIT_SOURCE", "SPLIT_OVERLAP"):
            _set(k, d[k])
        dash.update(d["dash"])
        detected += d["detected"]
    else:
        notes.append("No data rows found")
        if task_mode:
            where = f"[Data] Type = {dcfg.get('type')} · {dcfg.get('table') or dcfg.get('file_path') or 'no Table / File_path'}"
        else:
            where = f"[{ref}] {cfg[db_key].get('table', 'no table')}" if db_key else str(paths["data"] or "Path.Data not set")
        detected.append(("Data", missing.get("data") or where, "warning", "Not found"))

    run_git = dict(top=top, rev=view["short"] if view else "HEAD", repo=repo_paths["runs"]) if git and repo_paths["runs"] else None
    readers = (("models", lambda p: _models(p, cfg.get("models", {}))), ("runs", lambda p: _runs(p, run_git)),
               ("results", _results))
    for key, fn in readers:
        p = paths[key]
        part = fn(p) if p and p.is_dir() else None
        if part is None:
            notes.append(f"Nothing found in Path.{PATH_LABELS[key]}")
            detected.append((PATH_LABELS[key], missing.get(key) or str(p or f"Path.{PATH_LABELS[key]} not set"), "warning", "Not found"))
            continue
        for k, v in part.items():
            if k not in ("dash", "detected"):
                _set(k, v)
        dash.update(part["dash"])
        detected += part["detected"]

    lcfg = cfg.get("labels") or cfg.get("lables")
    pred = cfg.get("prediction")
    if task_mode and pred:
        rows = [r for fd in d["DATA_FOLDERS"].values() for r in fd["rows"]] if d else []
        inference = _task_predictions(cfg, paths, base, rows, tasks, detected, notes, db_cache)
        _set("INFERENCE", inference)
        what = f"[Prediction] Type = {pred.get('type')} · {pred.get('table') or pred.get('file_path') or '—'}"
        files = {os.path.normpath(r["path"]) for r in rows}
        found = []  # (task, data files with at least one prediction value in some source of it)
        for t in tasks:
            n = len({p for src in inference.values() if src["task"] == t for p, rec in src["by_path"].items()
                     if any(v not in (None, "") for v in rec["values"].values())} & files)
            found.append((t, n))
        if any(n for _, n in found):
            cols = ", ".join(f"{tomledit.title(k)}={v}" for k, v in next(iter(inference.values()))["shows"].items())
            per = " · ".join(f"{t} {n:,}" for t, n in found) if len(tasks) > 1 else f"{found[0][1]:,} of {len(rows):,} files"
            detected.append(("Prediction", f"{what} · {len(inference)} source(s) · {per} · {cols}", "positive", "Found"))
        else:
            detected.append(("Prediction", what, "warning", "Not found"))
    elif lcfg and not task_mode:
        shows = {k: v for k, v in lcfg.items() if k not in ("result_file", "path")}
        inference, inotes = _inference(lcfg.get("result_file"), shows, paths["results"], lcfg.get("path"))
        _set("INFERENCE", inference)
        notes += inotes
        if inference:
            cols = ", ".join(f"{tomledit.title(k)}={v}" for k, v in next(iter(inference.values()))["shows"].items())
            detected.append(("Labels / inference", f"{lcfg['result_file']} · {len(inference)} file(s) · {cols}", "positive", "Found"))
        else:
            detected.append(("Labels / inference", f"{lcfg.get('result_file', 'result_file not set')}", "warning", "Not found"))

    _set("DASH", {**store.DASH, **dash})
    n_runs = len(store.RUN_DETAILS)
    _set("PROJECT", dict(
        name=name, path=str(root), toml=str(toml_path), loaded=True, edited=text is not None, view=view["short"] if view else None,
        remote=(git["remote"] if git else gcfg.get("remote", "")).removeprefix("git@").removesuffix(".git") or "—",
        branch=(f"detached at {view['short']} · read-only snapshot" if view else f"{git['branch']} · {git['sync']}")
        if git else gcfg.get("branch") or "—",
        branch_name=git["branch"] if git else gcfg.get("branch") or "—",
        dirty=(f"{git['dirty']} uncommitted" if git["dirty"] else "clean") if git else "no git",
        commits=(f"{_run('git', 'rev-list', '--count', view['short'], cwd=top).strip()} · {git['authors']} contributors"
                 if view else f"{git['n']} · {git['authors']} contributors") if git else "—",
        runs_linked=f"{n_runs} set{'s' if n_runs != 1 else ''}", hot_file=git["hot_file"] if git else "",
        **({k: git[k] for k in ("head", "upstream", "ahead", "behind", "fetched")} if git else {})))
    _set("ROOT_FOLDERS", [(name, str(root.parent) + "/", str(root))] +
         [(PATH_LABELS[k], remote.origin(p) or _rel(p, root), str(p)) for k, p in paths.items() if p])
    _set("RECENT_PROJECTS", [(name, str(toml_path.parent))])
    _set("TOML", (toml_path.read_text() if text is None else text).splitlines())
    _set("DETECTED", detected)
    from PyQt6.QtCore import PYQT_VERSION_STR
    watched = [f"{p.name}/" for k, p in paths.items() if p and p.is_dir() and k != "data"]
    _set("STATUS", dict(watching="Watching " + ", ".join(watched) if watched else "",
                        left=[f"Python {sys.version.split()[0]}", f"PyQt6 {PYQT_VERSION_STR}",
                              f"Data: {store.SPLIT_SOURCE[0]}" if d else "Data: none"],
                        right=[f"Loaded {datetime.now():%H:%M}"]))
    return notes
