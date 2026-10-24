"""Project data shown by the UI.

Everything starts empty; ``project.load(toml)`` fills it from a real project and pages show
an empty state for whatever is still missing. Only display constants have fixed values.
"""

# name, path, toml, remote, branch, branch_name, dirty, commits, runs_linked, hot_file, loaded, view,
# head (short hash), upstream ("origin/main" or ""), ahead, behind, fetched ("3 h ago")
PROJECT = {}
# hash, message, author, relative time, date ("Oct 20, 14:02"), [(path, added, deleted)], [(ref, style)],
# where: "local" (not pushed), "remote" (on the upstream, not pulled) or "both"
COMMITS = []
ROOT_FOLDERS = []  # (name, meta, path)

# ---------------------------------------------------------------- Home dashboard
DASH = {}  # summary values per card, see project.load

# ---------------------------------------------------------------- Data
DATA_FOLDERS = {}  # folder → dict(n, size, ext, files, rows, splits, labels)
CLASSES = []
SPLITS = {"train": ("Train", "ink"), "valid": ("Valid", "c2"), "test": ("Test", "c3"), "unused": ("Unused", "mute")}
SPLIT_TOTALS = []  # (split, count, description)
SPLIT_SOURCE = ("", "")  # (source label, description)
SPLIT_OVERLAP = None  # (check name, result, badge tone)


def split_of(folder, i):
    fd = DATA_FOLDERS.get(folder)
    return fd["splits"][i] if fd else "unused"


# ---------------------------------------------------------------- Model
MODEL_FILES = []  # (file label, EXT, size, folder under paths.models; "" for the top level)
MODEL_INFO = {}  # file label → dict(path, stats=[(k, v)], props=[(k, v)]) from the file system


# ---------------------------------------------------------------- Run
RUNS = []  # (name, meta)
RUN_DETAILS = {}  # run name → (dict(cmd, commit, started, progress, epoch, eta, sources), [(title, file, rows, numbered)])
GPU = dict(name="", rows=[])

# ---------------------------------------------------------------- Result
RESULT_FILES = []  # (file label, EXT, size, folder under paths.results; "" for the top level)
RESULT_PATHS = {}  # file label → absolute path
RESULT_ROOT = ""
# [labels] result files: source (folder under results) → dict(file, rel, shows={key: column},
# by_path={data path: dict(values={key: value})}, by_name={file name: same})
INFERENCE = {}  # plus task=… for a task project: the task a source's predictions are for
TASKS = []  # [Project] Task of a task project, in order (the first one's label is a row's "label")

# ---------------------------------------------------------------- Setting
RECENT_PROJECTS = []  # (name, folder)
TOML = []  # lines of the loaded project file
DETECTED = []  # (what, detail, badge tone, badge text)

STATUS = dict(watching="", left=[], right=[])
