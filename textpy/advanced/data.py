from ..core.helpers import itemize, splitModRef, expandDir
from .repo import checkoutRepo
from .links import provenanceLink


# GET DATA FOR MAIN SOURCE AND ALL MODULES


class AppData(object):
    def __init__(self, app, moduleRefs, locations, modules, version, checkout, silent):
        self.app = app
        self.moduleRefs = moduleRefs
        self.locationsArg = locations
        self.modulesArg = modules
        self.version = version
        self.checkout = checkout
        self.silent = silent

    def getMain(self):

        app = self.app
        aContext = app.context
        org = aContext.org
        repo = aContext.repo
        relative = aContext.relative
        appPath = aContext.appPath
        appName = aContext.appName

        if org is None or repo is None:
            appPathRep = f"{appPath}/" if appPath else ""
            relative = f"{appPathRep}{appName}"
            self.checkout = "local"

        if not self.getModule(org, repo, relative, self.checkout, isBase=True):
            self.good = False

    def getStandard(self):

        app = self.app
        aContext = app.context
        moduleSpecs = aContext.moduleSpecs

        for m in moduleSpecs or []:
            if not self.getModule(
                m["org"],
                m["repo"],
                m["relative"],
                m.get("checkout", self.checkout),
                specs=m,
            ):
                self.good = False

    def getRefs(self):

        refs = self.moduleRefs
        for ref in refs.split(",") if refs else []:
            if ref in self.seen:
                continue

            parts = splitModRef(ref)
            if not parts:
                self.good = False
                continue

            (org, repo, relative, thisCheckoutData) = parts

            if not self.getModule(*parts):
                self.good = False

    def getModules(self):

        self.provenance = []
        provenance = self.provenance
        self.mLocations = []
        mLocations = self.mLocations

        self.locations = None
        self.modules = None

        self.good = True
        self.seen = set()

        self.getMain()
        self.getStandard()
        self.getRefs()

        version = self.version
        good = self.good
        app = self.app

        if good:
            app.mLocations = mLocations
            app.provenance = provenance
        else:
            return

        mModules = []
        if mLocations:
            mModules.append(version or "")

        locations = self.locationsArg
        modules = self.modulesArg

        givenLocations = (
            []
            if locations is None
            else [expandDir(app, x.strip()) for x in itemize(locations, "\n")]
            if type(locations) is str
            else locations
        )
        givenModules = (
            []
            if modules is None
            else [x.strip() for x in itemize(modules, "\n")]
            if type(modules) is str
            else modules
        )

        self.locations = mLocations + givenLocations
        self.modules = mModules + givenModules

    def getModule(self, org, repo, relative, checkout, isBase=False, specs=None):

        version = self.version
        silent = self.silent
        mLocations = self.mLocations
        provenance = self.provenance
        seen = self.seen
        app = self.app
        _browse = app._browse
        aContext = app.context

        moduleRef = f"{org}/{repo}/{relative}"
        if moduleRef in self.seen:
            return True

        if org is None or repo is None:
            repoLocation = relative
            mLocations.append(relative)
            (commit, local, release) = (None, None, None)
        else:
            (commit, release, local, localBase, localDir) = checkoutRepo(
                _browse=_browse,
                org=org,
                repo=repo,
                folder=relative,
                version=version,
                checkout=checkout,
                withPaths=False,
                keep=False,
                silent=silent,
            )
            if not localBase:
                return False

            repoLocation = f"{localBase}/{org}/{repo}"
            mLocations.append(f"{localBase}/{localDir}")

        seen.add(moduleRef)
        if isBase:
            app.repoLocation = repoLocation

        info = {}
        for item in (
            ("doi", None),
            ("corpus", f"{org}/{repo}/{relative}"),
        ):
            (key, default) = item
            info[key] = (
                getattr(aContext, key)
                if isBase
                else specs[key]
                if specs and key in specs
                else default
            )
        provenance.append(
            (
                ("corpus", info["corpus"]),
                ("version", version),
                ("commit", commit or "??"),
                ("release", release or "none"),
                (
                    "live",
                    provenanceLink(org, repo, version, commit, local, release, relative),
                ),
                ("doi", info["doi"]),
            )
        )
        return True


def getModulesData(*args):

    mData = AppData(*args)
    mData.getModules()
    if mData.locations is None:
        return None
    return (mData.locations, mData.modules)
