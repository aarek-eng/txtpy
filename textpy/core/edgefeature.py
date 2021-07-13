
import collections

from .helpers import makeInverse, makeInverseVal


class EdgeFeatures(object):
    pass


class EdgeFeature(object):

    def __init__(self, api, metaData, data, doValues):
        self.api = api
        self.meta = metaData

        self.doValues = doValues
        if type(data) is tuple:
            self.data = data[0]
            self.dataInv = data[1]
        else:
            self.data = data
            self.dataInv = (
                makeInverseVal(self.data) if doValues else makeInverse(self.data)
            )

    def items(self):

        return self.data.items()

    def f(self, n):

        if n not in self.data:
            return ()
        Crank = self.api.C.rank.data
        if self.doValues:
            return tuple(sorted(self.data[n].items(), key=lambda mv: Crank[mv[0] - 1]))
        else:
            return tuple(sorted(self.data[n], key=lambda m: Crank[m - 1]))

    def t(self, n):

        if n not in self.dataInv:
            return ()
        Crank = self.api.C.rank.data
        if self.doValues:
            return tuple(
                sorted(self.dataInv[n].items(), key=lambda mv: Crank[mv[0] - 1])
            )
        else:
            return tuple(sorted(self.dataInv[n], key=lambda m: Crank[m - 1]))

    def b(self, n):

        if n not in self.data and n not in self.dataInv:
            return ()
        Crank = self.api.C.rank.data
        if self.doValues:
            result = {}
            if n in self.dataInv:
                result.update(self.dataInv[n].items())
            if n in self.data:
                result.update(self.data[n].items())
            return tuple(sorted(result.items(), key=lambda mv: Crank[mv[0] - 1]))
        else:
            result = set()
            if n in self.dataInv:
                result |= self.dataInv[n]
            if n in self.data:
                result |= self.data[n]
            return tuple(sorted(result, key=lambda m: Crank[m - 1]))

    def freqList(self, nodeTypesFrom=None, nodeTypesTo=None):

        if nodeTypesFrom is None and nodeTypesTo is None:
            if self.doValues:
                fql = collections.Counter()
                for (n, vals) in self.data.items():
                    for val in vals.values():
                        fql[val] += 1
                return tuple(sorted(fql.items(), key=lambda x: (-x[1], x[0])))
            else:
                fql = 0
                for (n, ms) in self.data.items():
                    fql += len(ms)
                return fql
        else:
            fOtype = self.api.F.otype.v
            if self.doValues:
                fql = collections.Counter()
                for (n, vals) in self.data.items():
                    if nodeTypesFrom is None or fOtype(n) in nodeTypesFrom:
                        for (m, val) in vals.items():
                            if nodeTypesTo is None or fOtype(m) in nodeTypesTo:
                                fql[val] += 1
                return tuple(sorted(fql.items(), key=lambda x: (-x[1], x[0])))
            else:
                fql = 0
                for (n, ms) in self.data.items():
                    if nodeTypesFrom is None or fOtype(n) in nodeTypesFrom:
                        for m in ms:
                            if nodeTypesTo is None or fOtype(m) in nodeTypesTo:
                                fql += len(ms)
                return fql
