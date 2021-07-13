import os
import types
import traceback

from ..parameters import ORG, APP_CODE
from ..fabric import Fabric
from ..parameters import APIREF, TEMP_DIR
from ..lib import readSets
from ..core.helpers import console, setDir, mergeDict
from .find import findAppConfig, findAppClass
from .helpers import getText, dm, dh
from .settings import setAppSpecs, setAppSpecsApi
from .links import linksApi, outLink
from .text import textApi
from .sections import sectionsApi
from .display import displayApi
from .search import searchApi
from .data import getModulesData
from .repo import checkoutRepo


# SET UP A TF API FOR AN APP


FROM_TF_METHODS = """
    banner
    silentOn
    silentOff
    isSilent
    setSilent
    info
    warning
    error
    indent
""".strip().split()


class App:
    def __init__(
        self,
        cfg,
        appName,
        appPath,
        commit,
        release,
        local,
        _browse,
        hoist=False,
        version=None,
        checkout="",
        mod=None,
        locations=None,
        modules=None,
        api=None,
        setFile="",
        silent=False,
        **configOverrides,
    ):

        self.context = None

        mergeDict(cfg, configOverrides)

        for (key, value) in dict(
            isCompatible=cfg.get("isCompatible", None),
            appName=appName,
            api=api,
            version=version,
            silent=silent,
            _browse=_browse,
        ).items():
            setattr(self, key, value)

        setattr(self, "dm", dm)
        setattr(self, "dh", dh)

        setAppSpecs(self, cfg)
        aContext = self.context
        version = aContext.version

        setDir(self)

        if not self.api:
            self.sets = None
            if setFile:
                sets = readSets(setFile)
                if sets:
                    self.sets = sets
                    console(f'Sets from {setFile}: {", ".join(sets)}')
            specs = getModulesData(
                self, mod, locations, modules, version, checkout, silent
            )
            if specs:
                (locations, modules) = specs
                self.tempDir = f"{self.repoLocation}/{TEMP_DIR}"
                TF = Fabric(locations=locations, modules=modules, silent=silent or True)
                api = TF.load("", silent=silent or True)
                if api:
                    self.api = api
                    excludedFeatures = aContext.excludedFeatures
                    allFeatures = TF.explore(silent=silent or True, show=True)
                    loadableFeatures = allFeatures["nodes"] + allFeatures["edges"]
                    useFeatures = [
                        f for f in loadableFeatures if f not in excludedFeatures
                    ]
                    result = TF.load(useFeatures, add=True, silent=silent or True)
                    if result is False:
                        self.api = None
            else:
                self.api = None

        if self.api:
            self.TF = self.api.TF
            for m in FROM_TF_METHODS:
                setattr(self, m, getattr(self.TF, m))
            self.getText = types.MethodType(getText, self)
            linksApi(self, silent)
            searchApi(self)
            sectionsApi(self)
            setAppSpecsApi(self, cfg)
            displayApi(self, silent)
            textApi(self)
            if hoist:
                # docs = self.api.makeAvailableIn(hoist)
                self.api.makeAvailableIn(hoist)
                if not silent:
                    dh(
                        "<div><b>Text-Fabric API:</b> names "
                        + outLink("N F E L T S C TF", APIREF, title="doc",)
                        + " directly usable</div><hr>"
                    )

            silentOff = self.silentOff
            silentOff()
        else:
            if not _browse:
                console(
                    f"""
There were problems with loading data.
The Text-Fabric API has not been loaded!
The app "{appName}" will not work!
""",
                    error=True,
                )

    def reinit(self):

        pass

    def reuse(self, hoist=False):

        aContext = self.context
        appPath = aContext.appPath
        appName = aContext.appName
        local = aContext.local
        commit = aContext.commit
        release = aContext.release
        version = aContext.version
        api = self.api

        cfg = findAppConfig(appName, appPath, commit, release, local, version=version)
        findAppClass(appName, appPath)

        setAppSpecs(self, cfg, reset=True)

        if api:
            TF = self.TF
            TF._makeApi()
            api = TF.api
            self.api = api
            self.reinit()  # may be used by custom TF apps
            linksApi(self, True)
            searchApi(self)
            sectionsApi(self)
            setAppSpecsApi(self, cfg)
            displayApi(self, True)
            textApi(self)
            if hoist:
                api.makeAvailableIn(hoist)


def findApp(appName, checkoutApp, _browse, *args, silent=False, version=None, **kwargs):

    (commit, release, local) = (None, None, None)
    extraMod = None

    if not appName or ("/" in appName and checkoutApp == ""):
        appPath = os.path.expanduser(appName) if appName else ""
        absPath = os.path.abspath(appPath)

        if os.path.isdir(absPath):
            (appDir, appName) = os.path.split(absPath)
            codePath = f"{absPath}/{APP_CODE}"
            if os.path.isdir(codePath):
                appDir = codePath
            appBase = ""
        else:
            console(f"{absPath} is not an existing directory", error=True)
            appBase = False
            appDir = None
        appPath = appDir
    elif "/" in appName and checkoutApp != "":
        appBase = ""
        appDir = ""
        appPath = appDir
        extraMod = f"{appName}:{checkoutApp}"
    else:
        (commit, release, local, appBase, appDir) = checkoutRepo(
            _browse=_browse,
            org=ORG,
            repo=f"app-{appName}",
            folder=APP_CODE,
            checkout=checkoutApp,
            withPaths=True,
            keep=False,
            silent=silent,
            label="TF-app",
        )
        appBaseRep = f"{appBase}/" if appBase else ""
        appPath = f"{appBaseRep}{appDir}"

    if appPath is None:
        return None

    cfg = findAppConfig(appName, appPath, commit, release, local, version=version)
    version = cfg["provenanceSpec"].get("version", None)
    isCompatible = cfg["isCompatible"]
    if isCompatible is None:
        appClass = App
    elif not isCompatible:
        return None
    else:
        appBaseRep = f"{appBase}/" if appBase else ""
        appPath = f"{appBaseRep}{appDir}"

        appClass = findAppClass(appName, appPath) or App
    if extraMod:
        if kwargs.get("mod", None):
            kwargs["mod"] = f"{extraMod},{kwargs['mod']}"
        else:
            kwargs["mod"] = extraMod
    try:
        app = appClass(
            cfg,
            appName,
            appPath,
            commit,
            release,
            local,
            _browse,
            *args,
            version=version,
            silent=silent,
            **kwargs,
        )
    except Exception as e:
        if appClass is not App:
            console(
                f"There was an error loading TF-app {appName} from {appPath}", error=True
            )
            console(repr(e), error=True)
        traceback.print_exc()
        console("Text-Fabric is not loaded", error=True)
        return None
    return app
