"""Files and folders on another machine, read over ssh: a value written ``host:path`` (``gcloud:~/laboard/Runs``,
``gcloud:/data/img/0001.jpg``), in the project file or in the file-path column of a data table (csv or db).

How to log in to ``host``, first found:

* ``[SSH] host = "SSH/gcp.key"`` in the project file: a file holding the login command (e.g.
  ``gcloud compute ssh my-vm --zone us-west1-b`` or ``ssh -i ~/.ssh/key user@1.2.3.4``) or a private key
  (``ssh -i <file> host``); a value that isn't a file is the command itself;
* ``SSH/<host>.*`` next to the project file, or the only file in that folder, read the same way;
* ``ssh host`` (a Host of ~/.ssh/config).

A ``gcloud compute ssh`` login is replaced by the plain ssh it runs (``--dry-run``), and the calls to one host share
one connection (ControlMaster), so a call after the first takes milliseconds instead of gcloud's seconds.

* ``copy``: a remote file or folder into a temp folder, read like a local one (Path folders, csv files, label and
  prediction files);
* ``listing`` / ``stat``: the names, sizes and times of remote data files, without copying them;
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

_project = dict(base=Path.cwd(), ssh={})
_logins = {}  # host → (kind "ssh" | "gcloud", argv, the gcloud login an ssh came from or None)
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
    for kind, argv, _ in _logins.values():
        if kind == "ssh":  # close the shared connection
            try:
                subprocess.run(argv[:1] + ["-O", "exit"] + argv[1:], capture_output=True, timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass
    if _root:
        shutil.rmtree(_root, ignore_errors=True)


def use(base, ssh_cfg):
    """The project being loaded: ``base``, its file's folder (where SSH/ is); ``ssh_cfg``, its [SSH] table."""
    if (base, ssh_cfg) != (_project["base"], _project["ssh"]):
        _logins.clear()
    _project.update(base=base, ssh=dict(ssh_cfg))
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
def _from_file(f, host):
    text = f.read_text(errors="replace")
    return ["ssh", "-i", str(f), host] if "PRIVATE KEY" in text else shlex.split(text, comments=True)


def _login(host):
    """argv that logs in to ``host``, from the project's [SSH] table / SSH folder (see the module doc)."""
    base, ref = _project["base"], _project["ssh"].get(host.lower())
    if ref:
        f = Path(str(ref)).expanduser()
        f = f if f.is_absolute() else base / f
        return _from_file(f, host) if f.is_file() else shlex.split(str(ref))
    keys = sorted(p for p in (base / "SSH").glob("*") if p.is_file())
    f = next((p for p in keys if p.stem.lower() == host.lower()), keys[0] if len(keys) == 1 else None)
    return _from_file(f, host) if f else ["ssh", host]


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
        argv = _login(host)
        if not argv:
            raise OSError(f"no login command for {host}")
        if Path(argv[0]).name != "gcloud":
            _logins[host] = ("ssh", _shared(argv), None)
        else:
            try:
                r = subprocess.run(_gcloud(argv, "--dry-run", "--command", "true"), stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True, timeout=60)
                dry = shlex.split(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else []
            except (OSError, subprocess.SubprocessError):
                dry = []
            if dry[-2:] == ["--", "true"] and Path(dry[0]).name == "ssh":
                _logins[host] = ("ssh", _shared(dry[:-2]), argv)
            else:  # no dry run: every call goes through gcloud
                _logins[host] = ("gcloud", argv, None)
    return _logins[host]


def _last(err):
    lines = [ln for ln in err.decode(errors="replace").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def _call(host, cmd, data=None, out=None):
    """Run the shell command ``cmd`` on ``host`` (``data`` on its stdin). Returns the CompletedProcess, its stdout
    written to the file ``out`` when given. OSError when the host can't be reached."""
    while True:
        kind, argv, came_from = _connection(host)
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
            _logins[host] = ("gcloud", came_from, None)
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


def listing(value, limit):
    """[relative path] of the files under the remote folder ``value`` (hidden folders skipped), sorted, at most
    ``limit``; their sizes and times are kept for ``stat``. Raises OSError like ``copy``."""
    host, path = split(value)
    where = shlex.quote(_where(path))
    cmd = (f"cd {where} 2>/dev/null || {{ echo {shlex.quote('no folder ' + path)} >&2; exit 2; }}; "
           f"find . -type f -not -path '*/.*' -printf '%P\\t%s\\t%T@\\0' | sort -z | head -z -n {int(limit)}")
    r = _call(host, cmd)
    if r.returncode != 0:
        raise OSError(_last(r.stderr) or f"listing {value} failed ({r.returncode})")
    out = []
    for entry in r.stdout.decode(errors="replace").split("\0"):
        rel, _, rest = entry.rpartition("\t")
        rel, _, size = rel.rpartition("\t")
        if rel:
            _stats[join(value, rel)] = (int(size), float(rest))
            out.append(rel)
    return out


def stat(paths):
    """{remote file: (size, mtime)} of the remote ``paths`` that exist (others are skipped): one ssh call per
    host, and none for files ``listing`` or an earlier call of this load saw. Raises OSError like ``copy``."""
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
