
from .helpers import flattenToSet, console
from .nodes import Nodes
from .locality import Locality
from .nodefeature import NodeFeatures
from .edgefeature import EdgeFeatures
from .computed import Computeds
from .text import Text
from ..search.search import Search

API_REFS = dict(
    AllComputeds=("Computed", "computedall", "computed-data"),
    AllEdges=("Features", "edgeall", "edge-features"),
    AllFeatures=("Features", "nodeall", "node-features"),
    C=("Computed", "computed", "computed-data"),
    Call=("Computed", "computedall", "computed-data"),
    Computed=("Computed", "computed", "computed-data"),
    ComputedString=("Computed", "computedstr", "computed-data"),
    Cs=("Computed", "computedstr", "computed-data"),
    E=("Features", "edge", "edge-features"),
    Eall=("Features", "edgeall", "edge-features"),
    Edge=("Features", "edge", "edge-features"),
    EdgeString=("Features", "edgestr", "edge-features"),
    Es=("Features", "edgestr", "edge-features"),
    F=("Features", "node", "node-features"),
    Fall=("Features", "nodeall", "node-features"),
    Feature=("Features", "node", "node-features"),
    FeatureString=("Features", "nodestr", "node-features"),
    Fs=("Features", "nodestr", "node-features"),
    L=("Locality", "locality", "locality"),
    Locality=("Locality", "locality", "locality"),
    N=("Nodes", "nodes", "navigating-nodes"),
    Nodes=("Nodes", "nodes", "navigating-nodes"),
    S=("Search", "search", "search"),
    Search=("Search", "search", "search"),
    T=("Text", "text", "text"),
    TF=("Fabric", "fabric", "loading"),
    Text=("Text", "text", "text"),
)


class Api(object):
    def __init__(self, TF):
        self.TF = TF
        self.ignored = tuple(sorted(TF.featuresIgnored))
        TF.ignored = self.ignored

        self.F = NodeFeatures()
        self.Feature = self.F
        self.E = EdgeFeatures()
        self.Edge = self.E
        self.C = Computeds()
        self.Computed = self.C
        tmObj = TF.tmObj
        TF.silentOn = tmObj.silentOn
        TF.silentOff = tmObj.silentOff
        TF.isSilent = tmObj.isSilent
        TF.setSilent = tmObj.setSilent
        TF.info = tmObj.info
        TF.warning = tmObj.warning
        TF.error = tmObj.error
        TF.cache = tmObj.cache
        TF.reset = tmObj.reset
        TF.indent = tmObj.indent
        TF.loadLog = tmObj.cache

        TF.ensureLoaded = self.ensureLoaded
        TF.makeAvailableIn = self.makeAvailableIn

        setattr(self, "FeatureString", self.Fs)
        setattr(self, "EdgeString", self.Es)
        setattr(self, "ComputedString", self.Cs)
        setattr(self, "AllFeatures", self.Fall)
        setattr(self, "AllEdges", self.Eall)
        setattr(self, "AllComputeds", self.Call)

    def Fs(self, fName):

        if not hasattr(self.F, fName):
            self.TF.error(f'Node feature "{fName}" not loaded')
            return None
        return getattr(self.F, fName)

    def Es(self, fName):

        if not hasattr(self.E, fName):
            self.TF.error(f'Edge feature "{fName}" not loaded')
            return None
        return getattr(self.E, fName)

    def Cs(self, fName):

        if not hasattr(self.C, fName):
            self.TF.error(f'Computed feature "{fName}" not loaded')
            return None
        return getattr(self.C, fName)

    def Fall(self):

        return sorted(x[0] for x in self.F.__dict__.items())

    def Eall(self):

        return sorted(x[0] for x in self.E.__dict__.items())

    def Call(self):

        return sorted(x[0] for x in self.C.__dict__.items())

    def makeAvailableIn(self, scope):

        for member in dir(self):
            if "_" not in member and member[0].isupper():
                scope[member] = getattr(self, member)
                if member not in API_REFS:
                    console(f'WARNING: API member "{member}" not documented')

        grouped = {}
        for (member, (head, sub, ref)) in API_REFS.items():
            grouped.setdefault(ref, {}).setdefault((head, sub), []).append(member)

        # grouped
        # node-features=>(Features, node)=>[F, ...]

        docs = []
        for (ref, groups) in sorted(grouped.items()):
            chunks = []
            for ((head, sub), members) in sorted(groups.items()):
                chunks.append(" ".join(sorted(members, key=lambda x: (len(x), x))))
            docs.append((head, ref, tuple(chunks)))
        return docs

    # docs
    # (Features, node-features, ('F ...', ...))

    def ensureLoaded(self, features):

        F = self.F
        E = self.E
        TF = self.TF
        warning = TF.warning

        needToLoad = set()
        loadedFeatures = set()

        for fName in sorted(flattenToSet(features)):
            fObj = TF.features.get(fName, None)
            if not fObj:
                warning(f'Cannot load feature "{fName}": not in dataset')
                continue
            if fObj.dataLoaded and (hasattr(F, fName) or hasattr(E, fName)):
                loadedFeatures.add(fName)
            else:
                needToLoad.add(fName)
        if len(needToLoad):
            TF.load(
                needToLoad, add=True, silent="deep",
            )
            loadedFeatures |= needToLoad
        return loadedFeatures


def addOtype(api):
    setattr(api.F.otype, "all", tuple(o[0] for o in api.C.levels.data))
    setattr(
        api.F.otype, "support", dict(((o[0], (o[2], o[3])) for o in api.C.levels.data))
    )


def addLocality(api):
    api.L = Locality(api)
    api.Locality = api.L


def addNodes(api):
    api.N = Nodes(api)
    api.Nodes = api.N


def addText(api):
    api.T = Text(api)
    api.Text = api.T


def addSearch(api, silent):
    api.S = Search(api, silent)
    api.Search = api.S
