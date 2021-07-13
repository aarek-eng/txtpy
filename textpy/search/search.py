
from ..core.helpers import console, wrapMessages
from .searchexe import SearchExe
from ..parameters import YARN_RATIO, TRY_LIMIT_FROM, TRY_LIMIT_TO


class Search(object):

    def __init__(self, api, silent):
        self.api = api
        self.silent = silent
        self.exe = None
        self.perfDefaults = dict(
            yarnRatio=YARN_RATIO, tryLimitFrom=TRY_LIMIT_FROM, tryLimitTo=TRY_LIMIT_TO,
        )
        self.perfParams = {}
        self.perfParams.update(self.perfDefaults)
        SearchExe.setPerfParams(self.perfParams)

    def tweakPerformance(self, silent=False, **kwargs):

        api = self.api
        TF = api.TF
        error = TF.error
        info = TF.info
        isSilent = TF.isSilent
        setSilent = TF.setSilent
        defaults = self.perfDefaults

        wasSilent = isSilent()
        setSilent(silent)
        for (k, v) in kwargs.items():
            if k not in defaults:
                error(f'No such performance parameter: "{k}"', tm=False)
                continue
            if v is None:
                v = defaults[k]
            elif type(v) is not int and k != "yarnRatio":
                error(
                    f'Performance parameter "{k}" must be set to an integer, not to "{v}"',
                    tm=False,
                )
                continue
            self.perfParams[k] = v
        info("Performance parameters, current values:", tm=False)
        for (k, v) in sorted(self.perfParams.items()):
            info(f"\t{k:<20} = {v:>7}", tm=False)
        SearchExe.setPerfParams(self.perfParams)
        setSilent(wasSilent)

    def search(
        self,
        searchTemplate,
        limit=None,
        sets=None,
        shallow=False,
        silent=True,
        here=True,
        _msgCache=False,
    ):

        exe = SearchExe(
            self.api,
            searchTemplate,
            outerTemplate=searchTemplate,
            quKind=None,
            offset=0,
            sets=sets,
            shallow=shallow,
            silent=silent,
            _msgCache=_msgCache,
            setInfo={},
        )
        if here:
            self.exe = exe
        queryResults = exe.search(limit=limit)
        if type(_msgCache) is list:
            messages = wrapMessages(_msgCache)
            return (queryResults, messages) if here else (queryResults, messages, exe)
        return queryResults

    def study(
        self, searchTemplate, strategy=None, sets=None, shallow=False, here=True,
    ):

        exe = SearchExe(
            self.api,
            searchTemplate,
            outerTemplate=searchTemplate,
            quKind=None,
            offset=0,
            sets=sets,
            shallow=shallow,
            silent=False,
            showQuantifiers=True,
            setInfo={},
        )
        if here:
            self.exe = exe
        return exe.study(strategy=strategy)

    def fetch(self, limit=None, _msgCache=False):

        exe = self.exe
        TF = self.api.TF

        if exe is None:
            error = TF.error
            error('Cannot fetch if there is no previous "study()"')
        else:
            queryResults = exe.fetch(limit=limit)
            if type(_msgCache) is list:
                messages = TF.cache(_asString=True)
                return (queryResults, messages)
            return queryResults

    def count(self, progress=None, limit=None):

        exe = self.exe
        if exe is None:
            error = self.api.TF.error
            error('Cannot count if there is no previous "study()"')
        else:
            exe.count(progress=progress, limit=limit)

    def showPlan(self, details=False):

        exe = self.exe
        if exe is None:
            error = self.api.TF.error
            error('Cannot show plan if there is no previous "study()"')
        else:
            exe.showPlan(details=details)

    def relationsLegend(self):

        exe = self.exe
        if exe is None:
            exe = SearchExe(self.api, "")
        console(exe.relationLegend)

    def glean(self, tup):

        T = self.api.T
        F = self.api.F
        E = self.api.E
        fOtype = F.otype.v
        slotType = F.otype.slotType
        maxSlot = F.otype.maxSlot
        eoslots = E.oslots.data

        lR = len(tup)
        if lR == 0:
            return ""
        fields = []
        for (i, n) in enumerate(tup):
            otype = fOtype(n)
            words = [n] if otype == slotType else eoslots[n - maxSlot - 1]
            if otype == T.sectionTypes[2]:
                field = "{} {}:{}".format(*T.sectionFromNode(n))
            elif otype == slotType:
                field = T.text(words)
            elif otype in T.sectionTypes[0:2]:
                field = ""
            else:
                field = "{}[{}{}]".format(
                    otype, T.text(words[0:5]), "..." if len(words) > 5 else "",
                )
            fields.append(field)
        return " ".join(fields)
