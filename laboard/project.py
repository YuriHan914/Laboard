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
* Runs are folders under ``paths.runs`` holding json / yaml / toml configs.
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

from . import store, tomledit

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
SNAPSHOT_ROOT = Path(tempfile.gettempdir()) / "laboard-snapshots"
PRED_JSON_KEYS = dict(predict=("predict", "prediction", "class", "label", "pred"),
                      predict_score=("predict_score", "score", "confidence", "prob", "probability"))
RESERVED = {"project", "git", "paths", "data", "models", "labels", "lables", "prediction"}  # toml tables that aren't a database

_PATCHED = ("PROJECT", "COMMITS", "ROOT_FOLDERS", "DASH", "DATA_FOLDERS", "CLASSES", "SPLIT_TOTALS", "SPLIT_SOURCE",
            "SPLIT_OVERLAP", "MODEL_FILES", "MODEL_INFO", "RUNS", "RUN_DETAILS", "GPU", "RESULT_FILES",
            "RESULT_PATHS", "RESULT_ROOT", "INFERENCE", "RECENT_PROJECTS", "TOML", "DETECTED", "STATUS")
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
            return rows, dict(kind="file", name=f.name, where=str(f), label=f"{f.suffix[1:]} · {f.name}", base=f.parent)
    return None


def _abs(p, base):
    p = str(p)
    return p if os.path.isabs(p) or not base else str(Path(base, p))


def _rows_from_scan(data_dir, skip=()):
    """One row per file under ``paths.data`` (but ``skip`` extensions); split and label from an
    ImageFolder-style path."""
    if not data_dir or not data_dir.is_dir():
        return None
    rows = []
    for dp, files in _walk(data_dir):
        for f in files:
            if Path(f).suffix.lower() in SKIP_DATA_EXT or Path(f).suffix.lower() in TABLE_EXT or Path(f).suffix.lower() in skip:
                continue
            parts = [p.lower() for p in Path(_rel(dp, data_dir)).parts]
            at = next((i for i, p in enumerate(parts) if p in SPLIT_WORDS), None)
            split = SPLIT_WORDS[parts[at]] if at is not None else None
            label = Path(_rel(dp, data_dir)).parts[at + 1] if at is not None and at + 1 < len(parts) else None
            rows.append(dict(path=str(dp / f), split=split or "unused", label=label, task=None, created=None, trained=None,
                             predict=None, id=None))
            if len(rows) >= MAX_DATA_FILES:
                break
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
    for r in rows:
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

    classes = sorted({r["label"] for r in rows if r["label"] is not None})
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
                           f"{_size(sum(r['bytes'] for r in rows))}", "positive", "Found")])



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
        src = _rows_from_table(paths["data"], data_cfg, base) or _rows_from_scan(paths["data"])
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
    """``_data`` from raw table / db rows. ``as_of`` (a commit's time) hides db rows created after it."""
    rows = _normalize(src[0], cols, src[1].get("base") or base)
    if as_of and src[1]["kind"] == "db":  # db rows aren't versioned in git; their created column dates them
        dated = [r for r in rows if r["created"] is None or r["created"] <= as_of]
        if any(r["created"] for r in rows):
            if len(dated) < len(rows):
                notes.append(f"{len(rows) - len(dated):,} db rows created after {as_of:%b %d, %H:%M} hidden")
        else:
            notes.append("db rows have no created column; showing all of them")
        rows = dated
    return _data(rows, src[1], cols) if rows else None


# ---------------------------------------------------------------- task = "classification": [data] / [prediction]
def _db_rows(cfg, table, section, detected, notes, cache):
    """(rows, src) of ``table`` through the [db] connection, or None (noted). ``cache``: table → result,
    so [data] and [prediction] on one table query it once."""
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


def _classification_data(cfg, paths, detected, notes, as_of, cache):
    """[data] ``type`` = "db" (``table``) | "csv" (``file_path``) | "folder" (``file_path``, split/label/file).

    For db / csv the ground truth is the ``label`` column (default "label") and the file-path column is
    guessed, or set with ``path``. Predictions never come from the data; they're read from [prediction].
    """
    dcfg = cfg.get("data", {})
    kind = str(dcfg.get("type", "")).lower()
    if kind == "folder":
        pcfg = cfg.get("prediction", {})
        skip = {"." + str(pcfg.get("format") or "txt").lower().lstrip(".")} if str(pcfg.get("type", "")).lower() == "folder" else set()
        src = _rows_from_scan(paths["data"], skip)  # prediction files kept next to the data aren't data
        return _data(src[0], src[1], dict.fromkeys(COLS)) if src else None
    if kind == "db":
        src = _db_rows(cfg, dcfg.get("table"), "data", detected, notes, cache)
    elif kind == "csv":
        f = paths["data"]
        if not f or not f.is_file():
            notes.append(f"[Data] File_path {dcfg.get('file_path')} is not a file")
            return None
        try:
            src = _read_table(f), dict(kind="file", name=f.name, where=str(f), label=f"{f.suffix[1:]} · {f.name}", base=f.parent)
        except (OSError, ValueError, ImportError) as e:
            notes.append(f"{f.name}: {e}")
            return None
    else:
        notes.append(f"[Data] Type must be DB, CSV or Folder, not {dcfg.get('type')!r}" if kind else "[Data] Type is not set")
        return None
    if not src or not src[0]:
        return None
    gt = dcfg.get("label") or "label"
    cols = _columns(src[0], {"path": dcfg["path"]} if dcfg.get("path") else {})
    cols.update(label=gt if any(gt in r for r in src[0][:50]) else None, predict=None)
    if not cols["path"]:
        notes.append(f"{src[1]['label']}: no file-path column found (set [Data] Path)")
        return None
    if not cols["label"]:
        notes.append(f"{src[1]['label']}: no '{gt}' column; files have no ground truth")
    return _to_data(src, cols, paths["data"], notes, as_of)


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


def _classification_predictions(cfg, paths, base, rows, detected, notes, cache):
    """[prediction] ``type`` = "csv" | "db" | "folder", as {source: dict} like ``store.INFERENCE``.

    * csv: ``path`` is a result file name / glob under paths.results (or an absolute path); one source per match.
    * db: ``table``; rows match data files by their file-path column.
    * folder: ``path`` holds one ``<file stem>.<format>`` per data file, at the data file's place in the data
      tree or anywhere by stem: a txt holding "<class> [score]", or a json object.

    ``predict`` / ``predict_score`` name the class / score columns of csv and db, and the keys of a json
    (guessed from PRED_JSON_KEYS when left out).
    """
    pcfg = cfg.get("prediction", {})
    kind = str(pcfg.get("type", "")).lower()
    shows = {k: pcfg[k] for k in ("predict", "predict_score") if pcfg.get(k)}
    if kind == "csv":
        sources, inotes = _inference(pcfg.get("path"), shows, paths["results"], what="[Prediction] Path")
        notes += inotes
        return sources
    if kind == "db":
        table = pcfg.get("table")
        src = _db_rows(cfg, table, "prediction", detected, notes, cache)
        if not src or not src[0]:
            return {}
        col = _columns(src[0], {})["path"]
        if not col:
            notes.append(f"[Prediction] {table}: no file-path column")
            return {}
        lost = [c for c in shows.values() if c not in src[0][0]]
        if lost:
            notes.append(f"[Prediction] {table}: no column {', '.join(lost)}")
        by_path, by_name = _index(src[0], col, shows, None)
        return {f"db · {table}": dict(file=src[1]["where"], rel=f"db · {table}", shows=shows, by_path=by_path, by_name=by_name)}
    if kind == "folder":
        fmt = str(pcfg.get("format") or "txt").lower().lstrip(".")
        pdir = _resolve(pcfg.get("path"), base)
        if fmt not in ("txt", "json"):
            notes.append(f"[Prediction] Format {fmt} isn't supported (txt, json)")
            return {}
        if not pdir or not pdir.is_dir():
            notes.append(f"[Prediction] Path {pcfg.get('path')} is not a folder")
            return {}
        by_rel, by_stem = {}, {}
        for dp, fs in _walk(pdir):
            for f in fs:
                if f.lower().endswith("." + fmt):
                    by_rel[os.path.splitext(_rel(dp / f, pdir))[0]] = dp / f
                    by_stem.setdefault(Path(f).stem, dp / f)
        if not by_rel:
            notes.append(f"[Prediction] no .{fmt} files under {pdir}")
            return {}
        root = os.path.commonpath([os.path.dirname(r["path"]) for r in rows]) if rows else str(pdir)
        keys = {k: pcfg.get(k) for k in ("predict", "predict_score")}
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
    notes.append(f"[Prediction] Type must be CSV, DB or Folder, not {pcfg.get('type')!r}" if kind else "[Prediction] Type is not set")
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
                          mtime=st.st_mtime, folder=_rel(dp, models_dir), group=Path(_rel(p, models_dir)).parts[0]))
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
            sections.append((f.stem.replace("_", " ").capitalize(), f.name, rows[:40], False))
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
                detected=[("Runs", f"{runs_dir.name}/ · {len(out)} run{'s' if len(out) != 1 else ''}", "positive", "Found")])


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
        rec = dict(values={k: r.get(c) for k, c in shows.items()})
        p = os.path.normpath(_abs(p, base))
        by_path[p] = rec
        by_name.setdefault(os.path.basename(p), rec)
    return by_path, by_name


def _inference(name, shows, results_dir, path_col=None, what="[Labels] Result_file"):
    """Inference columns from result files: ``[labels]`` (also read when spelled ``[lables]``) and
    ``[prediction] type = "csv"``.

    ``name`` is a file name, relative path or glob under paths.results (or an absolute path); every
    match is one source, e.g. one ``inference.csv`` per model folder. ``shows`` maps a key to the column
    shown for it, e.g. ``{"infer": "classification"}``; ``path_col`` names the file-path column (guessed
    when None). Rows match data files by path, or by file name when paths differ. The ground truth stays
    the data's own label; a label column in the result file isn't read. Returns ({source: dict}, notes).
    """
    if not name:
        return {}, [f"{what} not set"]
    if Path(name).is_absolute():
        files = [Path(name)] if Path(name).is_file() else []
    else:
        files = sorted(f for f in results_dir.rglob(name) if f.is_file()) if results_dir and results_dir.is_dir() else []
    if not files:
        return {}, [f"{what} {name} not found under Path.Results"]
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
        by_path, by_name = _index(rows, cols["path"], shows, f.parent)
        src = _rel(f.parent, results_dir) if f.parent != results_dir else f.name
        sources[src] = dict(file=str(f), rel=_rel(f, results_dir.parent if results_dir else f.parent),
                            shows=shows, by_path=by_path, by_name=by_name)
    return sources, notes


# ---------------------------------------------------------------- environment
def _gpu():
    out = _run("nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
               "--format=csv,noheader,nounits", timeout=3).strip().splitlines()
    try:
        name, util, used, total, temp = [x.strip() for x in out[0].split(",")]
        util, used, total, temp = int(util), int(used), int(total), int(temp)
    except (IndexError, ValueError):
        return dict(name="No GPU detected", rows=[]), None
    return (dict(name=f"GPU 0 · {name.replace('NVIDIA ', '').replace('GeForce ', '')}",
                 rows=[("Utilization", f"{util}%", util), ("Memory", f"{used / 1024:.1f} / {total / 1024:.0f} GB",
                                                            round(used / total * 100)), ("Temperature", f"{temp} °C", temp)]),
            f"GPU 0 · {util}%")


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


def _load(toml_path, cfg, commit, text=None):
    base = toml_path.parent
    proj, gcfg, pcfg = cfg.get("project", {}), cfg.get("git", {}), cfg.get("paths", {})
    # task = "classification": [data] / [prediction] say where data and predictions are (see _classification_data)
    classification = str(proj.get("task", "")).lower() == "classification"
    dcfg = cfg.get("data", {})
    if classification:
        ref, db_key = dcfg.get("file_path") if str(dcfg.get("type", "")).lower() in ("csv", "folder") else None, None
    else:
        # paths.data naming a toml table (data = "DB" → [DB]) reads rows from that database only
        ref = pcfg.get("data")
        db_key = ref.lower() if isinstance(ref, str) and ref.lower() not in RESERVED and isinstance(cfg.get(ref.lower()), dict) else None
    paths = {k: None if k == "data" and db_key else _resolve(ref if k == "data" else pcfg.get(k), base)
             for k in ("data", "models", "runs", "results")}
    root = _resolve(proj.get("root"), base) or next((p for p in paths.values() if p), base)
    name = proj.get("name") or root.name
    notes, detected, dash = [], [], {}

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
                notes.append(f"Path.{k.capitalize()} is {'not tracked at ' + sha[:7] if k in rels else 'outside the repository'}")
        view = dict(short=sha[:7], when=datetime.fromtimestamp(int(_run("git", "show", "-s", "--format=%ct", sha, cwd=top))))
        detected.insert(1, ("Snapshot", f"{sha[:7]} · {view['when']:%b %d, %H:%M} · read-only", "warning", "Past commit"))

    as_of, db_cache = view["when"] if view else None, {}
    if classification:
        d = _classification_data(cfg, paths, detected, notes, as_of, db_cache)
    else:
        d = _load_data(cfg.get(db_key or "db", {}), dcfg, paths, base, detected, notes, as_of=as_of)
    if d:
        for k in ("DATA_FOLDERS", "CLASSES", "SPLIT_TOTALS", "SPLIT_SOURCE", "SPLIT_OVERLAP"):
            _set(k, d[k])
        dash.update(d["dash"])
        detected += d["detected"]
    else:
        notes.append("No data rows found")
        if classification:
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
            notes.append(f"Nothing found in Path.{key.capitalize()}")
            detected.append((key.capitalize(), missing.get(key) or str(p or f"Path.{key.capitalize()} not set"), "warning", "Not found"))
            continue
        for k, v in part.items():
            if k not in ("dash", "detected"):
                _set(k, v)
        dash.update(part["dash"])
        detected += part["detected"]

    lcfg = cfg.get("labels") or cfg.get("lables")
    pred = cfg.get("prediction")
    if classification and pred:
        rows = [r for fd in d["DATA_FOLDERS"].values() for r in fd["rows"]] if d else []
        inference = _classification_predictions(cfg, paths, base, rows, detected, notes, db_cache)
        _set("INFERENCE", inference)
        what = f"[Prediction] Type = {pred.get('type')} · {pred.get('table') or pred.get('path') or '—'}"
        # data files with at least one prediction value in some source
        n = len({p for src in inference.values() for p, rec in src["by_path"].items()
                 if any(v not in (None, "") for v in rec["values"].values())} & {os.path.normpath(r["path"]) for r in rows})
        if n:
            cols = ", ".join(f"{tomledit.title(k)}={v}" for k, v in next(iter(inference.values()))["shows"].items())
            detected.append(("Prediction", f"{what} · {len(inference)} source(s) · {n:,} of {len(rows):,} files · {cols}",
                             "positive", "Found"))
        else:
            detected.append(("Prediction", what, "warning", "Not found"))
    elif lcfg and not classification:
        shows = {k: v for k, v in lcfg.items() if k not in ("result_file", "path")}
        inference, inotes = _inference(lcfg.get("result_file"), shows, paths["results"], lcfg.get("path"))
        _set("INFERENCE", inference)
        notes += inotes
        if inference:
            cols = ", ".join(f"{tomledit.title(k)}={v}" for k, v in next(iter(inference.values()))["shows"].items())
            detected.append(("Labels / inference", f"{lcfg['result_file']} · {len(inference)} file(s) · {cols}", "positive", "Found"))
        else:
            detected.append(("Labels / inference", f"{lcfg.get('result_file', 'result_file not set')}", "warning", "Not found"))

    gpu, gpu_text = _gpu()
    _set("GPU", gpu)
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
        runs_linked=f"{n_runs} run{'s' if n_runs != 1 else ''}", hot_file=git["hot_file"] if git else "",
        **({k: git[k] for k in ("head", "upstream", "ahead", "behind", "fetched")} if git else {})))
    _set("ROOT_FOLDERS", [(name, str(root.parent) + "/", str(root))] +
         [(k, _rel(p, root), str(p)) for k, p in paths.items() if p])
    _set("RECENT_PROJECTS", [(name, str(toml_path.parent))])
    _set("TOML", (toml_path.read_text() if text is None else text).splitlines())
    _set("DETECTED", detected)
    from PyQt6.QtCore import PYQT_VERSION_STR
    watched = [f"{p.name}/" for k, p in paths.items() if p and p.is_dir() and k != "data"]
    _set("STATUS", dict(watching="Watching " + ", ".join(watched) if watched else "",
                        left=[f"Python {sys.version.split()[0]}", f"PyQt6 {PYQT_VERSION_STR}",
                              f"Data: {store.SPLIT_SOURCE[0]}" if d else "Data: none"],
                        right=[*([gpu_text] if gpu_text else []), f"Loaded {datetime.now():%H:%M}"]))
    return notes
