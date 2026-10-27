PROJECT = {}
COMMITS = []
ROOT_FOLDERS = []

DASH = {}

DATA_FOLDERS = {}
CLASSES = []
SPLITS = {"train": ("Train", "ink"), "valid": ("Valid", "c2"), "test": ("Test", "c3"), "unused": ("Unused", "mute")}
SPLIT_TOTALS = []
SPLIT_SOURCE = ("", "")
SPLIT_OVERLAP = None


def split_of(folder, i):
    fd = DATA_FOLDERS.get(folder)
    return fd["splits"][i] if fd else "unused"


MODEL_FILES = []
MODEL_INFO = {}


RUNS = []
RUN_DETAILS = {}

RESULT_FILES = []
RESULT_PATHS = {}
RESULT_ROOT = ""
INFERENCE = {}
TABLE_ROWS, TABLE_ROWS_DEFAULT = (20, 30, 40, 50, 100), 30
TASKS = []

RECENT_PROJECTS = []
TOML = []
DETECTED = []

STATUS = dict(watching="", left=[], right=[])
