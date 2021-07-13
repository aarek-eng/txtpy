import sys
import os
from importlib import util
import yaml

from ..parameters import (
    APP_CONFIG,
    APP_CONFIG_OLD,
    APP_DISPLAY,
    API_VERSION as avTf,
)
from ..core.helpers import console
from .helpers import getLocalDir


def findAppConfig(appName, appPath, commit, release, local, version=None):

    configPath = f"{appPath}/{APP_CONFIG}"
    configPathOld = f"{appPath}/{APP_CONFIG_OLD}"
    cssPath = f"{appPath}/{APP_DISPLAY}"

    checkApiVersion = True

    isCompatible = None

    if os.path.exists(configPath):
        with open(configPath) as fh:
            cfg = yaml.load(fh, Loader=yaml.FullLoader)
    else:
        cfg = {}
        checkApiVersion = False
        if os.path.exists(configPathOld):
            isCompatible = False
    cfg.update(
        appName=appName, appPath=appPath, commit=commit, release=release, local=local
    )

    if version is None:
        version = cfg.setdefault("provenanceSpec", {}).get("version", None)
    else:
        cfg.setdefault("provenanceSpec", {})["version"] = version

    if os.path.exists(cssPath):
        with open(cssPath, encoding="utf8") as fh:
            cfg["css"] = fh.read()
    else:
        cfg["css"] = ""

    cfg["local"] = local
    cfg["localDir"] = getLocalDir(cfg, local, version)

    avA = cfg.get("apiVersion", None)
    if isCompatible is None and checkApiVersion:
        isCompatible = (
            avA is not None and avA == avTf
        )
    if not isCompatible:
        if isCompatible is None:
            pass
        elif avA is None or avA < avTf:
            console(
                f"""
App `{appName}` requires API version {avA or 0} but Text-Fabric provides {avTf}.
Your copy of the TF app `{appName}` is outdated for this version of TF.
Recommendation: obtain a newer version of `{appName}`.
Hint: load the app in one of the following ways:

    {appName}
    {appName}:latest
    {appName}:hot

    For example:

    The Text-Fabric browser:

        text-fabric {appName}:latest

    In a program/notebook:

        A = use('{appName}:latest', hoist=globals())

""",
                error=True,
            )
        else:
            console(
                f"""
App `{appName}` requires API version {avA or 0} but Text-Fabric provides {avTf}.
Your Text-Fabric is outdated and cannot use this version of the TF app `{appName}`.
Recommendation: upgrade Text-Fabric.
Hint:

    pip3 install --upgrade text-fabric

""",
                error=True,
            )

    cfg["isCompatible"] = isCompatible
    return cfg


def findAppClass(appName, appPath):

    appClass = None
    moduleName = f"textpy.apps.{appName}.app"
    filePath = f"{appPath}/app.py"
    if not os.path.exists(filePath):
        return None

    try:
        spec = util.spec_from_file_location(moduleName, f"{appPath}/app.py")
        code = util.module_from_spec(spec)
        sys.path.insert(0, appPath)
        spec.loader.exec_module(code)
        sys.path.pop(0)
        appClass = code.TfApp
    except Exception as e:
        console(f"findAppClass: {str(e)}", error=True)
        console(f'findAppClass: Api for "{appName}" not loaded')
        appClass = None
    return appClass


def loadModule(moduleName, *args):

    (appName, appPath) = args[1:3]
    try:
        spec = util.spec_from_file_location(
            f"textpy.apps.{appName}.{moduleName}", f"{appPath}/{moduleName}.py",
        )
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        console(f"loadModule: {str(e)}", error=True)
        console(f'loadModule: {moduleName} in "{appName}" not found')
    return module
