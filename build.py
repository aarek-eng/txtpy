import sys
import os
import re
from glob import glob

from shutil import rmtree
from subprocess import run


ORG = "annotation"
REPO = "textpy"
PKG = "textpy"
PACKAGE = "textpy"
SCRIPT = "/Library/Frameworks/Python.framework/Versions/Current/bin/{PACKAGE}"

DIST = "dist"

VERSION_CONFIG = dict(
    setup=dict(
        file="setup.py",
        re=re.compile(r"""version\s*=\s*['"]([^'"]*)['"]"""),
        mask="version='{}'",
    ),
    parameters=dict(
        file="textpy/parameters.py",
        re=re.compile(r"""\bVERSION\s*=\s*['"]([^'"]*)['"]"""),
        mask="VERSION = '{}'",
    ),
)

AN_BASE = os.path.expanduser(f"~/github/{ORG}")
TF_BASE = f"{AN_BASE}/{REPO}"

currentVersion = None
newVersion = None


HELP = """
python3 build.py command

command:

-h
--help
help  : print help and exit

clean : clean local develop build
l     : local develop build
lp    : local production build
i     : local non-develop build
g     : push to github
v     : show current version
r1    : version becomes r1+1.0.0
r2    : version becomes r1.r2+1.0
r3    : version becomes r1.r2.r3+1
ship  : build for shipping

For g and ship you need to pass a commit message.
"""


def readArgs():
    args = sys.argv[1:]
    if not len(args) or args[0] in {"-h", "--help", "help"}:
        print(HELP)
        return (False, None, [])
    arg = args[0]
    if arg not in {
        "clean",
        "l",
        "lp",
        "i",
        "g",
        "ship",
        "v",
        "r1",
        "r2",
        "r3",
    }:
        print(HELP)
        return (False, None, [])
    if arg in {"g", "ship"}:
        if len(args) < 2:
            print("Provide a commit message")
            return (False, None, [])
        return (arg, args[1], args[2:])
    return (arg, None, [])


def incVersion(version, task):
    comps = [int(c) for c in version.split(".")]
    (major, minor, update) = comps
    if task == "r1":
        major += 1
        minor = 0
        update = 0
    elif task == "r2":
        minor += 1
        update = 0
    elif task == "r3":
        update += 1
    return ".".join(str(c) for c in (major, minor, update))


def replaceVersion(task, mask):
    def subVersion(match):
        global currentVersion
        global newVersion
        currentVersion = match.group(1)
        newVersion = incVersion(currentVersion, task)
        return mask.format(newVersion)

    return subVersion


def showVersion():
    global currentVersion
    versions = set()
    for (key, c) in VERSION_CONFIG.items():
        with open(c["file"]) as fh:
            text = fh.read()
        match = c["re"].search(text)
        version = match.group(1)
        print(f'{version} (according to {c["file"]})')
        versions.add(version)
    currentVersion = None
    if len(versions) == 1:
        currentVersion = list(versions)[0]


def adjustVersion(task):
    for (key, c) in VERSION_CONFIG.items():
        print(f'Adjusting version in {c["file"]}')
        with open(c["file"]) as fh:
            text = fh.read()
        text = c["re"].sub(replaceVersion(task, c["mask"]), text)
        with open(c["file"], "w") as fh:
            fh.write(text)
    if currentVersion == newVersion:
        print(f"Rebuilding version {newVersion}")
    else:
        print(f"Replacing version {currentVersion} by {newVersion}")


def makeDist(pypi=True):
    distFile = "{}-{}".format(PACKAGE, currentVersion)
    distFileCompressed = f"{distFile}.tar.gz"
    distPath = f"{DIST}/{distFileCompressed}"
    distPath = f"{DIST}/*"
    print(distPath)
    if os.path.exists(DIST):
        rmtree(DIST)
    os.makedirs(DIST, exist_ok=True)
    run(["python3", "setup.py", "sdist", "bdist_wheel"])
    if pypi:
        run(["twine", "upload", "-u", "dirkroorda", distPath])


def commit(task, msg):
    run(["git", "add", "--all", "."])
    run(["git", "commit", "-m", msg])
    run(["git", "push", "origin", "master"])
    if task in {"ship"}:
        tagVersion = f"v{currentVersion}"
        commitMessage = f"Release {currentVersion}: {msg}"
        run(["git", "tag", "-a", tagVersion, "-m", commitMessage])
        run(["git", "push", "origin", "--tags"])


def clean():
    run(["python3", "setup.py", "develop", "-u"])
    if os.path.exists(SCRIPT):
        os.unlink(SCRIPT)
    run(["pip3", "uninstall", "-y", PACKAGE])


def main():
    (task, msg, remaining) = readArgs()
    if not task:
        return
    elif task == "clean":
        clean()
    elif task == "l":
        clean()
        run(["python3", "setup.py", "develop"])
    elif task == "lp":
        clean()
        run(["python3", "setup.py", "sdist"])
        distFiles = glob(f"dist/{PACKAGE}-*.tar.gz")
        run(["pip3", "install", distFiles[0]])
    elif task == "i":
        clean
        makeDist(pypi=False)
        run(
            [
                "pip3",
                "install",
                "--upgrade",
                "--no-index",
                "--find-links",
                f'file://{TF_BASE}/dist"',
                PACKAGE,
            ]
        )
    elif task == "g":
        commit(task, msg)
    elif task == "v":
        showVersion()
    elif task in {"r", "r1", "r2", "r3"}:
        adjustVersion(task)
    elif task == "ship":
        showVersion()
        if not currentVersion:
            print("No current version")
            return

        answer = input("right version ? [yn]")
        if answer != "y":
            return
        makeDist()
        commit(task, msg)


main()
