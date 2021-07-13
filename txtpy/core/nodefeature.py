

import collections


class NodeFeatures(object):
    pass


class NodeFeature(object):

    def __init__(self, api, metaData, data):
        self.api = api
        self.meta = metaData

        self.data = data

    def items(self):

        return self.data.items()

    def v(self, n):

        if n in self.data:
            return self.data[n]
        return None

    def s(self, val):

        Crank = self.api.C.rank.data
        return tuple(
            sorted(
                [n for n in self.data if self.data[n] == val],
                key=lambda n: Crank[n - 1],
            )
        )

    def freqList(self, nodeTypes=None):

        fql = collections.Counter()
        if nodeTypes is None:
            for n in self.data:
                fql[self.data[n]] += 1
        else:
            fOtype = self.api.F.otype.v
            for n in self.data:
                if fOtype(n) in nodeTypes:
                    fql[self.data[n]] += 1
        return tuple(sorted(fql.items(), key=lambda x: (-x[1], x[0])))
