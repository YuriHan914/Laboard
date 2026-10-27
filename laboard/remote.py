"""Files and folders on another machine, read over ssh: a value written ``host:path`` (``gcloud:~/laboard/Runs``,
``gcloud:/data/img/0001.jpg``), in the project file or in the file-path column of a data table (csv or db).

How to log in to ``host``: the ``[host]`` section of ``key/ssh.key`` next to the project file. A section holds
``key = value`` lines or one login command line, and its type is its ``type`` key, else its name:

* ``[gcloud]`` instance_name, zone: ``gcloud compute ssh <instance_name> --zone <zone>``;
* ``[az]`` vm_name, resource-group: ``az ssh vm --name <vm_name> --resource-group <resource-group>``;
* ``[aws]`` instance-id, instance-os-user, ssh-public-key, availability-zone: the public key is sent with
  ``aws ec2-instance-connect send-ssh-public-key``, then ``ssh -i <its private key> <instance-os-user>@<public ip>``;
* ``[ssh]`` key_name, user_name, ip: ``ssh -i ~/.ssh/<key_name> <user_name>@<ip>``;
* a command line (``ssh -i ~/.ssh/key user@1.2.3.4``, ``gcloud compute ssh my-vm --zone us-west1-b``, …) is the
  login itself, in a section of any name.

Any other key is passed on as ``--key value`` (``true``: the bare flag), and ``_`` / ``-`` in key names are the same.

A ``gcloud compute ssh`` login is replaced by the plain ssh it runs (``--dry-run``), and the calls to one host share
one connection (ControlMaster), so a call after the first takes milliseconds instead of gcloud's seconds.

* ``copy``: a remote file or folder into a temp folder, read like a local one (Path folders, csv files);
* ``stat``: the sizes and times of remote data files, without copying them;
* ``fetch`` / ``local``: local copies of remote data files, made when a page shows them and kept until Laboard exits.

Nothing on the remote side is changed. ``use`` (on every project load) says which project the hosts are read from.
"""
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

REMOTE = re.compile(r"^([\w.@-]{2,}):(?!//)(.+)$")  # host:path; a single letter would be a Windows drive
TIMEOUT = 180
TAR = "tar cf - --dereference --hard-dereference"  # file contents only: a link entry can't be unpacked from a stream

KEY_FILE = Path("key", "ssh.key")  # login sections, next to the project file
SECTION = re.compile(r"^\[([^\[\]]+)\]\s*(#.*)?$")
OPTION = re.compile(r"^([\w.-]+)\s*=\s*(.*)$")

_project = dict(base=Path.cwd())
_logins = {}  # host → (kind "ssh" | "gcloud" | "cli", argv, the gcloud login an ssh came from, prepare argv)
_copies = {}  # (value, options) → local copy, this load
_origin = {}  # str(local copy) → the host:path it was copied from
_stats = {}  # remote file → (size, mtime), this load
_absent = set()  # remote files a fetch didn't bring, this load
_root = None


def _cache():
    global _root
    if _root is None:
        _root = Path(tempfile.mkdtemp(prefix="laboard-remote-"))
    return _root


@atexit.register
def _cleanup():
    for kind, argv, _, _ in _logins.values():
        if kind == "ssh":  # close the shared connection
            try:
                subprocess.run(argv[:1] + ["-O", "exit"] + argv[1:], capture_output=True, timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass
    if _root:
        shutil.rmtree(_root, ignore_errors=True)


def use(base):
    """The project being loaded: ``base``, its file's folder (where key/ssh.key is)."""
    if base != _project["base"]:
        _logins.clear()
    _project.update(base=base)
    _copies.clear()
    _stats.clear()
    _absent.clear()


# ---------------------------------------------------------------- remote paths
def split(value):
    """(host, path) of a ``host:path`` value, else None."""
    m = REMOTE.match(value) if isinstance(value, str) else None
    return m.groups() if m else None


def join(folder, rel):
    """``rel`` under the remote folder ``folder``."""
    return f"{str(folder).rstrip('/')}/{rel}"


def origin(p):
    """The host:path that the local copy ``p`` was made from, else None."""
    return _origin.get(str(p))


def parent(p):
    """The remote folder (host:path) of the file that the local copy ``p`` was made from, else None."""
    o = origin(p)
    if not o:
        return None
    host, path = split(o)
    return f"{host}:{posixpath.dirname(path.rstrip('/')) or '.'}"


def _where(path):
    """``path`` as the remote shell gets it: absolute, or under the login folder (home) for ``~/…`` and relative ones."""
    if path == "~" or path == "~/":
        return "."
    return path[2:] if path.startswith("~/") else path


def _local(p):
    """Where the local copy of the remote file ``p`` goes."""
    host, path = split(p)
    w = _where(path)
    parts = [q for q in w.split("/") if q not in ("", ".", "..")]
    return _cache().joinpath("files", host, "root" if w.startswith("/") else "home", *parts)


# ---------------------------------------------------------------- logging in
def _sections(f):
    """{name: (options, command argv)} of a key file's [name] sections; names and keys in lower case, "_" as "-"."""
    out, cur = {}, None
    for line in f.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if m := SECTION.match(line):
            cur = out.setdefault(m[1].strip().lower(), ({}, []))
        elif cur is not None:
            if m := OPTION.match(line):
                v = " ".join(shlex.split(m[2], comments=True))
                cur[0][m[1].lower().replace("_", "-")] = {"true": True, "false": False}.get(v.lower(), v)
            else:
                cur[1].extend(shlex.split(line, comments=True))
    return out


def _flags(options, skip=()):
    """``--key value`` of each option not in ``skip``; true is the bare flag, false is left out."""
    out = []
    for k, v in options.items():
        if k not in skip and v is not False:
            out += [f"--{k}"] if v is True else [f"--{k}", str(v)]
    return out


def _need(name, options, *keys):
    missing = [k for k in keys if not options.get(k)]
    if missing:
        raise OSError(f"[{name}] in {KEY_FILE}: no {', '.join(missing)}")
    return [str(options[k]) for k in keys]


def _gcloud_login(name, o):
    (vm,) = _need(name, o, "instance-name")
    return "gcloud", ["gcloud", "compute", "ssh", vm] + _flags(o, ("type", "instance-name")), None


def _az_login(name, o):
    o = {("name" if k == "vm-name" else k): v for k, v in o.items()}
    return "cli", ["az", "ssh", "vm"] + _flags(o, ("type",)), None


def _aws_login(name, o):
    """ssh with the instance's key, after the public key is sent (valid 60 s: sent again when a login fails)."""
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
    """``ssh -i ~/.ssh/<key_name> <user_name>@<ip>``; a key_name with a "/" is the key file's own path."""
    (ip,) = _need(name, o, "ip")
    key = str(o.get("key-name") or "")
    key = ["-i", str(Path(key).expanduser() if "/" in key else Path.home() / ".ssh" / key)] if key else []
    return "ssh", ["ssh", *key, f"{o['user-name']}@{ip}" if o.get("user-name") else str(ip)], None


LOGINS = dict(gcloud=_gcloud_login, az=_az_login, aws=_aws_login, ssh=_ssh_login)  # by a section's type


def _login(host):
    """(kind, argv, prepare argv or None) that logs in to ``host``, from its key file section (see the module doc)."""
    f = _project["base"] / KEY_FILE
    if not f.is_file():
        raise OSError(f"no {KEY_FILE} next to the project file for {host}:")
    section = _sections(f).get(host.lower())
    if section is None:
        raise OSError(f"{KEY_FILE} has no [{host}] section")
    options, command = section
    if command:
        tool = Path(command[0]).name
        return ("gcloud" if tool == "gcloud" else "ssh" if tool == "ssh" else "cli"), command, None
    kind = str(options.get("type") or host).lower()
    if kind not in LOGINS:
        raise OSError(f"[{host}] in {KEY_FILE}: no login command, and type {kind!r} isn't {' / '.join(LOGINS)}")
    return LOGINS[kind](host, options)


def _prepare(host, argv):
    """Run a login's preparing command (e.g. sending the aws public key)."""
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise OSError(f"can't run {argv[0]} ({e})") from None
    if r.returncode:
        raise OSError(_last(r.stderr) or f"can't prepare the login to {host}")


def _gcloud(argv, *extra):
    """A gcloud login with ``extra`` flags, which go before the args it hands to ssh (after "--")."""
    cut = argv.index("--") if "--" in argv else len(argv)
    return argv[:cut] + ["--quiet", *extra] + argv[cut:]


def _shared(argv):
    """A plain ssh that never prompts and shares one connection per host."""
    return argv[:1] + ["-o", "BatchMode=yes", "-o", "ControlMaster=auto", "-o", f"ControlPath={_cache()}/%C",
                       "-o", "ControlPersist=600"] + argv[1:]


def _connection(host):
    if host not in _logins:
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
            else:  # no dry run: every call goes through gcloud
                _logins[host] = ("gcloud", argv, None, None)
    return _logins[host]


def _last(err):
    lines = [ln for ln in err.decode(errors="replace").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def _call(host, cmd, data=None, out=None):
    """Run the shell command ``cmd`` on ``host`` (``data`` on its stdin). Returns the CompletedProcess, its stdout
    written to the file ``out`` when given. OSError when the host can't be reached."""
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
        if r.returncode == 255 and came_from:  # the plain ssh gcloud printed doesn't log in: use gcloud itself
            _logins[host] = ("gcloud", came_from, None, None)
            continue
        if r.returncode == 255 and prepare and not prepared:  # e.g. the aws public key expired: send it again
            _prepare(host, prepare)
            prepared = True
            continue
        if r.returncode == 255:
            raise OSError(_last(r.stderr) or f"can't log in to {host}")
        return r


# ---------------------------------------------------------------- reading
def _find(exts, depth, max_size):
    """find of the files under the current folder (hidden folders skipped), as a shell command."""
    find = ["find", ".", "-mindepth", "1"] + (["-maxdepth", str(depth)] if depth else []) + \
           ["-type", "f", "-not", "-path", "'*/.*'"] + (["-size", f"-{max_size}c"] if max_size else [])
    if exts:
        find += ["\\("] + " -o ".join(f"-iname '*{e}'" for e in exts).split() + ["\\)"]
    return " ".join(find)


def copy(value, exts=None, depth=None, max_size=None):
    """Copy the remote file or folder ``value`` (``host:path``) into a temp folder, named like it, and return the copy.

    Of a folder only files ending in one of ``exts`` (any when None), at most ``depth`` levels down and smaller than
    ``max_size`` bytes are copied. A copy is made again on every load (``use``). Raises OSError when the host can't
    be reached or has no such file or folder.
    """
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
        except tarfile.ReadError:  # nothing in it
            pass
    _copies[key] = dest / name
    _origin[str(dest / name)] = value
    return dest / name


def stat(paths):
    """{remote file: (size, mtime)} of the remote ``paths`` that exist (others are skipped): one ssh call per
    host, and none for files an earlier call of this load saw. Raises OSError like ``copy``."""
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
    """Copy the remote files among ``paths`` that have no local copy yet: one ssh call per host. Files that can't
    be had (missing, host down) are skipped; their ``local`` path doesn't exist."""
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
                            except (OSError, tarfile.TarError):  # one bad entry (e.g. an odd name) skips only itself
                                pass
            except (OSError, tarfile.TarError):
                pass
            _absent.update(p for p in group if not _local(p).exists())


def local(path):
    """A local file to read ``path`` from: ``path`` itself, or the copy of a remote file (fetched now if needed)."""
    if not split(path):
        return path
    fetch([path])
    return str(_local(path))
