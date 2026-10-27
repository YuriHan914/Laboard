import json
import math
import pickle
import re
import struct
import zipfile
from collections import Counter, OrderedDict
from pathlib import Path

MAX_LAYERS = 12
_cache = {}


class Tensor:
    __slots__ = ("shape", "dtype")

    def __init__(self, shape, dtype):
        self.shape, self.dtype = tuple(int(d) for d in shape), str(dtype)

    @property
    def size(self):
        return math.prod(self.shape)


def count(n):
    return f"{n / 1e9:.2f}B" if n >= 1e9 else f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.1f}K" if n >= 1e3 else str(n)


def _onnx(p):
    import onnx

    m = onnx.load(str(p), load_external_data=False)
    g = m.graph
    dtype = onnx.TensorProto.DataType.Name
    tensors = {t.name: Tensor(t.dims, dtype(t.data_type).lower()) for t in g.initializer}
    for n in g.node:
        if n.op_type == "Constant":
            for a in n.attribute:
                if a.name == "value" and a.t.dims:
                    tensors.setdefault(n.output[0], Tensor(a.t.dims, dtype(a.t.data_type).lower()))
    init = set(tensors)
    users = {}
    for n in g.node:
        for i in n.input:
            if i in init and i not in users:
                users[i] = n.name.strip("/").rsplit("/", 1)[0] if "/" in n.name.strip("/") else n.op_type
    tensors = {f"{users.get(k, 'unused')}:{k}": t for k, t in tensors.items()}

    def shape(v):
        dims = [d.dim_value or d.dim_param or "?" for d in v.type.tensor_type.shape.dim]
        return f"{dtype(v.type.tensor_type.elem_type).lower()}[{','.join(map(str, dims))}]"

    ops = Counter(n.op_type for n in g.node)
    props = [("Format", f"ONNX IR v{m.ir_version}"), ("Producer", f"{m.producer_name} {m.producer_version}".strip() or "—"),
             ("Opset", ", ".join(f"{o.domain or 'ai.onnx'} {o.version}" for o in m.opset_import)),
             *[("Input", f"{v.name}: {shape(v)}") for v in g.input if v.name not in init],
             *[("Output", f"{v.name}: {shape(v)}") for v in g.output],
             ("Nodes", f"{len(g.node):,}"), ("Top ops", ", ".join(f"{k} {n}" for k, n in ops.most_common(4)))]
    if any(t.data_location == onnx.TensorProto.EXTERNAL for t in g.initializer):
        props.append(("Weights", "external data file (not loaded)"))
    return tensors, props


def _safetensors(p):
    with open(p, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
    meta = header.pop("__metadata__", None) or {}
    tensors = {k: Tensor(v["shape"], v["dtype"].lower()) for k, v in header.items()}
    props = [("Format", "safetensors"), ("Tensors", f"{len(tensors):,}"),
             ("Dtypes", ", ".join(sorted({t.dtype for t in tensors.values()})))]
    props += [(f"meta · {k}", str(v)[:60]) for k, v in list(meta.items())[:4]]
    return tensors, props


def _msgpack(p):
    import msgpack

    def ext(code, data):
        if code == 1:
            shape, dtype, _ = msgpack.unpackb(data, raw=False)
            return Tensor(shape, dtype)
        if code == 3:
            return Tensor((), msgpack.unpackb(data, raw=False)[0])
        return msgpack.ExtType(code, data)

    with open(p, "rb") as f:
        tree = msgpack.unpackb(f.read(), ext_hook=ext, raw=False, strict_map_key=False)
    tensors = dict(_leaves(tree))
    return tensors, [("Format", "Flax msgpack"), ("Tensors", f"{len(tensors):,}"),
                     ("Dtypes", ", ".join(sorted({t.dtype for t in tensors.values()})))]


class _Obj:
    def __new__(cls, *a, **k):
        return object.__new__(cls)

    def __init__(self, *a, **k):
        self.args = a

    def __setstate__(self, state):
        self.state = state


class _Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "collections" and name == "OrderedDict":
            return OrderedDict
        if module == "torch._utils" and name.startswith("_rebuild_tensor"):
            return lambda storage, offset, size, *a, **k: Tensor(size, storage)
        if module == "torch._utils" and name == "_rebuild_parameter":
            return lambda data, *a, **k: data
        if module == "torch" and name.endswith("Storage"):
            return name[:-len("Storage")].lower() or "untyped"
        if module == "torch" and name in ("float32", "float16", "bfloat16", "int64", "int32", "uint8", "bool"):
            return name
        return type(name, (_Obj,), {"__module__": "stub." + module})

    def persistent_load(self, pid):
        return pid[1] if isinstance(pid[1], str) else "untyped"


CHECKPOINT_SKIP = re.compile(r"optim|sched|scaler|rng|history|ema_|swa_", re.I)


def model_tensors(obj):
    if isinstance(obj, dict) and not all(isinstance(v, Tensor) for v in obj.values()):
        parts = {k: OrderedDict(_leaves(v)) for k, v in obj.items()
                 if not CHECKPOINT_SKIP.search(str(k)) and not isinstance(v, Tensor)}
        parts = {k: v for k, v in parts.items() if v}
        if parts:
            return max(parts.values(), key=len)
    return OrderedDict(_leaves(obj))


def _torch(p):
    if not zipfile.is_zipfile(p):
        raise ValueError("legacy (non-zip) torch file; re-save with torch>=1.6 to inspect")
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        obj = _Unpickler(z.open(next(n for n in names if n.endswith("data.pkl")))).load()
    tensors = model_tensors(obj)
    kind = "state_dict" if isinstance(obj, dict) and all(isinstance(v, Tensor) for v in obj.values()) else \
        "checkpoint dict" if isinstance(obj, dict) else type(obj).__name__
    if any("/code/" in n for n in names):
        kind = "TorchScript"
    props = [("Format", f"PyTorch zip · {kind}"), ("Tensors", f"{len(tensors):,}")]
    if isinstance(obj, dict):
        extra = [k for k, v in obj.items() if not isinstance(v, Tensor)][:6]
        if extra:
            props.append(("Keys", ", ".join(map(str, extra))))
    return tensors, props


def _engine(p):
    with open(p, "rb") as f:
        head = f.read(32)
    magic = head[:4].decode("latin-1")
    props = [("Format", "TensorRT engine" if magic == "ftrt" else "TensorRT plan"),
             ("Note", "built for one TensorRT/GPU combination; layers need that runtime")]
    return {}, props


_SKIP = {"_modules", "_parameters", "_buffers", "state", "args", "params"}


def _leaves(obj, prefix=""):
    if isinstance(obj, Tensor):
        yield prefix.rstrip("."), obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, prefix if str(k) in _SKIP else f"{prefix}{k}.")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{prefix}{i}.")
    elif isinstance(obj, _Obj):
        yield from _leaves(getattr(obj, "state", None) or getattr(obj, "args", ()), prefix)


def _layers(tensors):
    parts = {k: [s for s in re.split(r"[./:]", k) if s] for k in tensors}
    best = []
    top = Counter()
    for k, t in tensors.items():
        top[parts[k][0] if parts[k] else k] += t.size
    if len(top) > MAX_LAYERS:
        head = top.most_common(MAX_LAYERS - 1)
        return head + [("other", sum(top.values()) - sum(n for _, n in head))]
    for depth in range(1, 8):
        groups = OrderedDict()
        for k, t in tensors.items():
            key = ".".join(parts[k][:depth]) or k
            groups[key] = groups.get(key, 0) + t.size
        if len(groups) > MAX_LAYERS:
            break
        best = list(groups.items())
        if all(len(p) <= depth for p in parts.values()):
            break
    return best


READERS = {".onnx": _onnx, ".safetensors": _safetensors, ".msgpack": _msgpack, ".pt": _torch, ".pth": _torch,
           ".ckpt": _torch, ".bin": _torch, ".engine": _engine, ".plan": _engine, ".trt": _engine}


def inspect(path):
    p = Path(path)
    key = (str(p), p.stat().st_mtime)
    if key not in _cache:
        reader = READERS.get(p.suffix.lower())
        try:
            tensors, props = reader(p) if reader else ({}, [("Format", p.suffix[1:].upper() or "file")])
        except Exception as e:
            tensors, props = {}, [("Could not read", f"{type(e).__name__}: {str(e)[:80]}")]
        total = sum(t.size for t in tensors.values())
        stats = [("Parameters", count(total))] if tensors else []
        _cache[key] = dict(stats=stats, props=props, layers=_layers(tensors))
    return _cache[key]
