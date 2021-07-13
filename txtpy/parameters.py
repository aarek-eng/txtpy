
import sys
from zipfile import ZIP_DEFLATED


VERSION = '1.0.0'

NAME = "Text-Fabric"

PACK_VERSION = "2"

API_VERSION = 3

GZIP_LEVEL = 2

PICKLE_PROTOCOL = 4

ORG = "annotation"

REPO = "txtpy"

RELATIVE = "tf"

URL_GH_API = "https://api.github.com/repos"

URL_GH = "https://github.com"

URL_NB = "https://nbviewer.jupyter.org/github"

DOWNLOADS = "~/Downloads"

GH_BASE = "~/github"

EXPRESS_BASE = "~/text-fabric-data"

EXPRESS_SYNC = "__checkout__.txt"

EXPRESS_SYNC_LEGACY = [
    "__release.txt",
    "__commit.txt",
]

URL_TFDOC = f"https://{ORG}.github.io/{REPO}/tf"

DOI_DEFAULT = "no DOI"
DOI_URL_PREFIX = "https://doi.org"

DOI_TF = "10.5281/zenodo.592193"

APIREF = f"https://{ORG}.github.io/{REPO}/tf/cheatsheet.html"

SEARCHREF = f"https://{ORG}.github.io/{REPO}/tf/about/searchusage.html"

APP_URL = f"{URL_GH}/{ORG}"

APP_NB_URL = f"{URL_NB}/{ORG}/tutorials/blob/master"

APP_GITHUB = f"{GH_BASE}/annotation"

APP_CONFIG = "config.yaml"

APP_CONFIG_OLD = "config.py"

APP_CODE = "code"

APP_DISPLAY = "static/display.css"

SERVER_DISPLAY_BASE = "/server/static"

SERVER_DISPLAY = ("fonts.css", "display.css", "highlight.css")

TEMP_DIR = "_temp"

LOCATIONS = [
    "~/Downloads/text-fabric-data",
    "~/text-fabric-data",
    "~/github/text-fabric-data",
    "~/Dropbox/text-fabric-data",
    "/mnt/shared/text-fabric-data",
]

ZIP_OPTIONS = dict(compression=ZIP_DEFLATED)

if sys.version_info[1] >= 7:
    ZIP_OPTIONS["compresslevel"] = 6

YARN_RATIO = 1.25

TRY_LIMIT_FROM = 40

TRY_LIMIT_TO = 40
