import atexit
import hashlib
import posixpath
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from collections import defaultdict
from pathlib import Path

REMOTE = re.compile(r"^([\w.@-]{2,}):(?!//)(.+)$")
TIMEOUT = 180
TAR = "tar cf - --dereference --hard-dereference"

WHERE = "the project file"

_project = dict(base=Path.cwd(), cfg={})
_logins = {}
_logged_with = {}
_copies = {}
_origin = {}
_stats = {}
_absent = set()
_root = None


def _cache():
    global _root
    if _root is None:
        _root = Path(tempfile.mkdtemp(prefix="laboard-remote-"))
    return _root


@atexit.register
def _cleanup():
    for kind, argv, _, _ in _logins.values():
        if kind == "ssh":
            try:
                subprocess.run(argv[:1] + ["-O", "exit"] + argv[1:], capture_output=True, timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass
    if _root:
        shutil.rmtree(_root, ignore_errors=True)


def use(base, cfg):
    if base != _project["base"]:
        _logins.clear()
    _project.update(base=base, cfg=cfg)
    for host in [h for h in _logins if _section(h) != _logged_with.get(h)]:
        del _logins[host]
    _copies.clear()
    _stats.clear()
    _absent.clear()


def split(value):
    m = REMOTE.match(value) if isinstance(value, str) else None
    return m.groups() if m else None


def join(folder, rel):
    return f"{str(folder).rstrip('/')}/{rel}"


def origin(p):
    return _origin.get(str(p))


def parent(p):
    o = origin(p)
    if not o:
        return None
    host, path = split(o)
    return f"{host}:{posixpath.dirname(path.rstrip('/')) or '.'}"


def _where(path):
    if path == "~" or path == "~/":
        return "."
    return path[2:] if path.startswith("~/") else path


def _local(p):
    host, path = split(p)
    w = _where(path)
    parts = [q for q in w.split("/") if q not in ("", ".", "..")]
    return _cache().joinpath("files", host, "root" if w.startswith("/") else "home", *parts)


def _section(host):
    sec = _project["cfg"].get(host.lower())
    if not isinstance(sec, dict):
        return None
    options = {k.lower().replace("_", "-"): v if isinstance(v, bool) else str(v) for k, v in sec.items()
               if not isinstance(v, dict) and k.lower() != "command"}
    command = next((v for k, v in sec.items() if k.lower() == "command"), "")
    return options, shlex.split(str(command))


def _flags(options, skip=()):
    out = []
    for k, v in options.items():
        if k not in skip and v is not False:
            out += [f"--{k}"] if v is True else [f"--{k}", str(v)]
    return out


def _need(name, options, *keys):
    missing = [k for k in keys if not options.get(k)]
    if missing:
        raise OSError(f"[{name}] in {WHERE}: no {', '.join(missing)}")
    return [str(options[k]) for k in keys]


def _gcloud_login(name, o):
    (vm,) = _need(name, o, "instance-name")
    return "gcloud", ["gcloud", "compute", "ssh", vm] + _flags(o, ("type", "instance-name")), None


def _az_login(name, o):
    o = {("name" if k == "vm-name" else k): v for k, v in o.items()}
    return "cli", ["az", "ssh", "vm"] + _flags(o, ("type",)), None


def _aws_login(name, o):
    vm, user, pub = _need(name, o, "instance-id", "instance-os-user", "ssh-public-key")
    pub = pub.removeprefix("file://")
    key = str(o.get("private-key") or pub.removesuffix(".pub"))
    region = ["--region", str(o["region"])] if o.get("region") else \
        ["--region", o["availability-zone"].rstrip("abcdefghijklmnopqrstuvwxyz")] if o.get("availability-zone") else []
    ip = o.get("host") or o.get("public-ip")
    if not ip:
        try:
            r = subprocess.run(["aws", "ec2", "describe-instances", "--instance-ids", vm, "--output", "text", "--query",
                                "Reservations[0].Instances[0].PublicIpAddress", *region],
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            raise OSError(f"can't run aws ({e})") from None
        ip = r.stdout.decode().strip()
        if r.returncode or ip in ("", "None"):
            raise OSError(_last(r.stderr) or f"[{name}] {vm} has no public ip")
    send = {**o, "ssh-public-key": "file://" + str(Path(pub).expanduser())}
    prepare = ["aws", "ec2-instance-connect", "send-ssh-public-key"] + \
        _flags(send, ("type", "private-key", "host", "public-ip", "region")) + region
    return "ssh", ["ssh", "-i", str(Path(key).expanduser()), f"{user}@{ip}"], prepare


def _ssh_login(name, o):
    (ip,) = _need(name, o, "ip")
    key = str(o.get("key-name") or "")
    key = ["-i", str(Path(key).expanduser() if "/" in key else Path.home() / ".ssh" / key)] if key else []
    return "ssh", ["ssh", *key, f"{o['user-name']}@{ip}" if o.get("user-name") else str(ip)], None


LOGINS = dict(gcloud=_gcloud_login, az=_az_login, aws=_aws_login, ssh=_ssh_login)


def _login(host):
    section = _section(host)
    if section is None:
        raise OSError(f"{WHERE} has no [{host}] section")
    options, command = section
    if command:
        tool = Path(command[0]).name
        return ("gcloud" if tool == "gcloud" else "ssh" if tool == "ssh" else "cli"), command, None
    kind = str(options.get("type") or host).lower()
    if kind not in LOGINS:
        raise OSError(f"[{host}] in {WHERE}: no login command, and type {kind!r} isn't {' / '.join(LOGINS)}")
    return LOGINS[kind](host, options)


def _prepare(host, argv):
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise OSError(f"can't run {argv[0]} ({e})") from None
    if r.returncode:
        raise OSError(_last(r.stderr) or f"can't prepare the login to {host}")


def _gcloud(argv, *extra):
    cut = argv.index("--") if "--" in argv else len(argv)
    return argv[:cut] + ["--quiet", *extra] + argv[cut:]


def _shared(argv):
    return argv[:1] + ["-o", "BatchMode=yes", "-o", "ControlMaster=auto", "-o", f"ControlPath={_cache()}/%C",
                       "-o", "ControlPersist=600"] + argv[1:]


def _connection(host):
    if host not in _logins:
        _logged_with[host] = _section(host)
        kind, argv, prepare = _login(host)
        if prepare:
            _prepare(host, prepare)
        if kind != "gcloud":
            _logins[host] = (kind, _shared(argv) if kind == "ssh" else argv, None, prepare)
        else:
            try:
                r = subprocess.run(_gcloud(argv, "--dry-run", "--command", "true"), stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True, timeout=60)
                dry = shlex.split(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else []
            except (OSError, subprocess.SubprocessError):
                dry = []
            if dry[-2:] == ["--", "true"] and Path(dry[0]).name == "ssh":
                _logins[host] = ("ssh", _shared(dry[:-2]), argv, None)
            else:
                _logins[host] = ("gcloud", argv, None, None)
    return _logins[host]


def _last(err):
    lines = [ln for ln in err.decode(errors="replace").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def _call(host, cmd, data=None, out=None):
    prepared = False
    while True:
        kind, argv, came_from, prepare = _connection(host)
        full = _gcloud(argv, "--command", cmd) if kind == "gcloud" else argv + ["--", cmd]
        if out:
            out.seek(0)
            out.truncate()
        feed = dict(input=data) if data is not None else dict(stdin=subprocess.DEVNULL)
        try:
            r = subprocess.run(full, stdout=out or subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT, **feed)
        except subprocess.TimeoutExpired:
            raise OSError(f"no answer from {host} in {TIMEOUT}s") from None
        except OSError as e:
            raise OSError(f"can't run {full[0]} ({e.strerror})") from None
        if r.returncode == 255 and came_from:
            _logins[host] = ("gcloud", came_from, None, None)
            continue
        if r.returncode == 255 and prepare and not prepared:
            _prepare(host, prepare)
            prepared = True
            continue
        if r.returncode == 255:
            raise OSError(_last(r.stderr) or f"can't log in to {host}")
        return r


def _find(exts, depth, max_size):
    find = ["find", ".", "-mindepth", "1"] + (["-maxdepth", str(depth)] if depth else []) + \
           ["-type", "f", "-not", "-path", "'*/.*'"] + (["-size", f"-{max_size}c"] if max_size else [])
    if exts:
        find += ["\\("] + " -o ".join(f"-iname '*{e}'" for e in exts).split() + ["\\)"]
    return " ".join(find)


def copy(value, exts=None, depth=None, max_size=None):
    key = (value, tuple(exts) if exts else None, depth, max_size)
    if key in _copies:
        return _copies[key]
    host, path = split(value)
    where = shlex.quote(_where(path))
    cmd = (f"if [ -d {where} ]; then printf D; cd {where} && {_find(exts, depth, max_size)} -print0 | {TAR} --null -T -; "
           f"elif [ -f {where} ]; then printf F; cd \"$(dirname {where})\" && {TAR} \"$(basename {where})\"; "
           f"else echo {shlex.quote('no file or folder ' + path)} >&2; exit 2; fi")
    dest = _cache() / "copies" / hashlib.sha1(repr(key).encode()).hexdigest()[:12]
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    name = posixpath.basename(path.rstrip("/")) or host
    with tempfile.TemporaryFile() as fh:
        r = _call(host, cmd, out=fh)
        if r.returncode != 0:
            raise OSError(_last(r.stderr) or f"reading {value} failed ({r.returncode})")
        fh.seek(0)
        kind = fh.read(1)
        if kind not in (b"D", b"F"):
            raise OSError(f"unexpected answer from {host}")
        into = dest / name if kind == b"D" else dest
        into.mkdir(exist_ok=True)
        try:
            with tarfile.open(fileobj=fh, mode="r|") as tar:
                tar.extractall(into, filter="data")
        except tarfile.ReadError:
            pass
    _copies[key] = dest / name
    _origin[str(dest / name)] = value
    return dest / name


def stat(paths):
    out, todo = {}, defaultdict(dict)
    for p in paths:
        s = split(p)
        if not s:
            continue
        if p in _stats:
            out[p] = _stats[p]
        else:
            todo[s[0]][_where(s[1])] = p
    for host, names in todo.items():
        r = _call(host, "xargs -0 -r stat --printf '%s\\t%Y\\t%n\\0' --", data="\0".join(names).encode())
        for entry in r.stdout.decode(errors="replace").split("\0"):
            size, _, rest = entry.partition("\t")
            mtime, _, name = rest.partition("\t")
            if name in names:
                out[names[name]] = _stats[names[name]] = (int(size), float(mtime))
    return out


def fetch(paths):
    todo = defaultdict(list)
    for p in dict.fromkeys(paths):
        s = split(p)
        if s and p not in _absent and not _local(p).exists():
            todo[s[0]].append(p)
    for host, ps in todo.items():
        for top in ("home", "root"):
            group = [p for p in ps if _where(split(p)[1]).startswith("/") == (top == "root")]
            if not group:
                continue
            dest = _cache() / "files" / host / top
            dest.mkdir(parents=True, exist_ok=True)
            names = [_where(split(p)[1]).lstrip("/") for p in group]
            try:
                with tempfile.TemporaryFile() as fh:
                    _call(host, ("cd / && " if top == "root" else "") + f"{TAR} --null -T - 2>/dev/null",
                          data="\0".join(names).encode(), out=fh)
                    fh.seek(0)
                    with tarfile.open(fileobj=fh, mode="r|") as tar:
                        for member in tar:
                            try:
                                tar.extract(member, dest, filter="data")
                            except (OSError, tarfile.TarError):
                                pass
            except (OSError, tarfile.TarError):
                pass
            _absent.update(p for p in group if not _local(p).exists())


def local(path):
    if not split(path):
        return path
    fetch([path])
    return str(_local(path))
