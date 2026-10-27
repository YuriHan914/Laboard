import csv
import itertools
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

MAX_RECORDS = 20000
MAX_TEXT_BYTES = 256 * 1024
X_KEYS = ("step", "global_step", "_step", "epoch", "iteration", "iter")


def _num(v):
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _series(records):
    keys = list(dict.fromkeys(k for r in records[:50] for k in r))
    out = {}
    for k in keys:
        vals = [v for v in (_num(r.get(k)) for r in records) if v is not None]
        if len(vals) >= 2 and len(vals) >= len(records) * 0.5 and len(set(vals)) > 1:
            out[k] = vals
    return out


def table(path):
    ext = path.suffix.lower()
    with open(path, newline="") as f:
        if ext == ".jsonl":
            recs = []
            for line in itertools.islice(f, MAX_RECORDS):
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    recs.append({k: v for k, v in d.items() if not isinstance(v, (dict, list))})
            cols = list(dict.fromkeys(k for r in recs[:50] for k in r))
        else:
            reader = csv.DictReader(f, delimiter="\t" if ext == ".tsv" else ",")
            recs = list(itertools.islice(reader, MAX_RECORDS))
            cols = list(reader.fieldnames or [])
        more = f.readline() != ""
    return cols, recs, more


def numeric(records):
    series = _series(records)
    x_key = next((k for k in X_KEYS if k in series), None)
    xs = series.pop(x_key) if x_key else list(range(len(records)))
    return x_key, xs, series


def _varint(b, i):
    n = shift = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << shift
        if c < 0x80:
            return n, i
        shift += 7


def _fields(b):
    i = 0
    while i < len(b):
        key, i = _varint(b, i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 1:
            v, i = b[i:i + 8], i + 8
        elif wt == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif wt == 5:
            v, i = b[i:i + 4], i + 4
        else:
            return
        yield f, wt, v


def _tensor_value(b):
    dtype = 1
    for f, wt, v in _fields(b):
        if f == 1 and wt == 0:
            dtype = v
        elif f == 4 and wt == 2 and v:
            return struct.unpack_from("<f" if dtype == 1 else "<d", v)[0] if dtype in (1, 2) else None
        elif f == 5:
            return struct.unpack_from("<f", v)[0]
        elif f == 6:
            return struct.unpack_from("<d", v)[0]
    return None


def tfevents(path):
    out = defaultdict(lambda: ([], []))
    data = Path(path).read_bytes()
    i = 0
    try:
        while i + 12 <= len(data):
            n = struct.unpack_from("<Q", data, i)[0]
            ev = data[i + 12:i + 12 + n]
            i += 12 + n + 4
            step = 0
            for f, wt, v in _fields(ev):
                if f == 2 and wt == 0:
                    step = v
                elif f == 5 and wt == 2:
                    for f2, wt2, val in _fields(v):
                        if f2 != 1 or wt2 != 2:
                            continue
                        tag, x = None, None
                        for f3, wt3, v3 in _fields(val):
                            if f3 == 1 and wt3 == 2:
                                tag = v3.decode(errors="replace")
                            elif f3 == 2 and wt3 == 5:
                                x = struct.unpack("<f", v3)[0]
                            elif f3 == 8 and wt3 == 2:
                                x = _tensor_value(v3)
                        if tag and x is not None and math.isfinite(x):
                            out[tag][0].append(step)
                            out[tag][1].append(x)
    except (IndexError, struct.error):
        pass
    return dict(out)


def text(path):
    p = Path(path)
    size = p.stat().st_size
    with open(p, "rb") as f:
        if b"\0" in f.read(8192):
            return [], f"binary file · {size:,} bytes · no preview"
    if p.suffix.lower() == ".json" and size <= MAX_TEXT_BYTES:
        try:
            return json.dumps(json.loads(p.read_text()), indent=2, ensure_ascii=False).splitlines(), ""
        except ValueError:
            pass
    with open(p, "rb") as f:
        if size > MAX_TEXT_BYTES:
            f.seek(size - MAX_TEXT_BYTES)
            f.readline()
        lines = f.read().decode(errors="replace").splitlines()
    note = f"last {len(lines):,} lines" if size > MAX_TEXT_BYTES else f"{len(lines):,} lines"
    return lines[-500:], note if len(lines) <= 500 else f"last 500 of {note}"
