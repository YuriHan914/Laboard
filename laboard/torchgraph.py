import hashlib
import tempfile
import zipfile
from collections import OrderedDict
from pathlib import Path

from . import modelinfo

CACHE = Path(tempfile.gettempdir()) / "laboard-graphs"
PARAM_NAMES = ("weight", "bias", "running_mean", "running_var", "num_batches_tracked", "kernel", "scale")


def is_pickle(path):
    if not zipfile.is_zipfile(path):
        return False
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    return any(n.endswith("data.pkl") for n in names) and not any("/code/" in n or n.endswith("constants.pkl") for n in names)


ONNX_OPS = {"Conv1d": ("Conv", ("weight", "bias")), "Conv2d": ("Conv", ("weight", "bias")), "Conv3d": ("Conv", ("weight", "bias")),
            "Linear": ("Gemm", ("weight", "bias")), "BatchNorm": ("BatchNormalization", ("weight", "bias", "running_mean", "running_var")),
            "Norm": ("LayerNormalization", ("weight", "bias")), "Embedding": ("Gather", ("weight",))}


def _kind(module, params):
    w = params.get("weight", params.get("kernel"))
    if "running_mean" in params:
        return "BatchNorm", {"num_features": params["running_mean"].shape[0] if params["running_mean"].shape else 0}
    if "in_proj_weight" in params:
        return "MultiheadAttention", {"embed_dim": params["in_proj_weight"].shape[1]}
    if w is None:
        return "Parameters", {}
    nd = len(w.shape)
    if nd in (3, 4, 5):
        return f"Conv{nd - 2}d", {"out_channels": w.shape[0], "in_channels": w.shape[1], "kernel_shape": list(w.shape[2:])}
    if nd == 2:
        if "embed" in module.lower() and "bias" not in params:
            return "Embedding", {"num_embeddings": w.shape[0], "embedding_dim": w.shape[1]}
        return "Linear", {"in_features": w.shape[1], "out_features": w.shape[0]}
    if nd == 1 and "bias" in params:
        return "Norm", {"features": w.shape[0]}
    return "Parameters", {}


def build(path):
    import onnx
    from onnx import TensorProto, helper

    p = Path(path)
    key = hashlib.sha1(f"{p.resolve()}:{p.stat().st_mtime}".encode()).hexdigest()[:16]
    out = CACHE / f"{p.stem}-{key}.onnx"
    if out.exists():
        return out
    with zipfile.ZipFile(p) as z:
        obj = modelinfo._Unpickler(z.open(next(n for n in z.namelist() if n.endswith("data.pkl")))).load()
    tensors = modelinfo.model_tensors(obj)
    if not tensors:
        return None
    modules = OrderedDict()
    for name, t in tensors.items():
        mod, _, param = name.rpartition(".")
        if param not in PARAM_NAMES and not mod:
            mod, param = name, "value"
        modules.setdefault(mod or name, OrderedDict())[param] = t

    dtypes = {"float16": TensorProto.FLOAT16, "bfloat16": TensorProto.BFLOAT16, "int64": TensorProto.INT64,
              "long": TensorProto.INT64, "int32": TensorProto.INT32, "int": TensorProto.INT32, "uint8": TensorProto.UINT8,
              "bool": TensorProto.BOOL, "double": TensorProto.DOUBLE, "float64": TensorProto.DOUBLE}
    nodes, inits, prev = [], [], "input"
    for mod, params in modules.items():
        kind, attrs = _kind(mod, params)
        op, order = ONNX_OPS.get(kind, (kind, ()))
        if op == "Gemm":
            attrs = {"transB": 1}
        elif op == "Conv":
            attrs = {"kernel_shape": attrs["kernel_shape"]}
        elif op != kind:
            attrs = {}
        if op in ("BatchNormalization",) and not all(k in params for k in order):
            op, order = kind, ()
        names = {}
        for param, t in params.items():
            init = TensorProto(name=f"{mod}.{param}", data_type=dtypes.get(t.dtype, TensorProto.FLOAT), dims=t.shape)
            inits.append(init)
            names[param] = init.name
        if order:
            args = [names[k] for k in order if k in names]
            ins = [args[0], prev] if op == "Gather" else [prev, *args]
        else:
            ins = [prev, *names.values()]
        node = helper.make_node(op, ins, [mod], name=mod, domain="" if op != kind else "laboard.inferred", **attrs)
        node.doc_string = f"{kind} (inferred from tensor shapes)"
        nodes.append(node)
        prev = mod
    graph = helper.make_graph(nodes, p.stem, [helper.make_tensor_value_info("input", TensorProto.FLOAT, None)],
                              [helper.make_tensor_value_info(prev, TensorProto.FLOAT, None)], initializer=inits)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17), helper.make_opsetid("laboard.inferred", 1)],
                              producer_name="laboard (inferred from checkpoint tensor names)")
    CACHE.mkdir(parents=True, exist_ok=True)
    onnx.save(model, out)
    return out
