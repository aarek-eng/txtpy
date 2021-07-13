
import functools


class Nodes:
    def __init__(self, api):
        self.api = api
        C = api.C
        Crank = C.rank.data

        self.otypeRank = {d[0]: i for (i, d) in enumerate(reversed(C.levels.data))}

        self.sortKey = lambda n: Crank[n - 1]

        self.sortKeyTuple = lambda tup: tuple(Crank[n - 1] for n in tup)

        (sortKeyChunk, sortKeyChunkLength) = self.makeSortKeyChunk()

        self.sortKeyChunk = sortKeyChunk

        self.sortKeyChunkLength = sortKeyChunkLength

    def makeSortKeyChunk(self):
        api = self.api

        fOtype = api.F.otype
        otypeRank = self.otypeRank
        fOtypev = fOtype.v

        def beforePosition(chunk1, chunk2):
            (n1, (b1, e1)) = chunk1
            (n2, (b2, e2)) = chunk2
            if b1 < b2:
                return -1
            elif b1 > b2:
                return 1

            r1 = otypeRank[fOtypev(n1)]
            r2 = otypeRank[fOtypev(n2)]

            if r1 > r2:
                return -1
            elif r1 < r2:
                return 1

            return (
                -1
                if e1 > e2
                else 1
                if e1 < e2
                else -1
                if n1 < n2
                else 1
                if n1 > n2
                else 0
            )

        def beforeLength(chunk1, chunk2):
            (n1, (b1, e1)) = chunk1
            (n2, (b2, e2)) = chunk2

            size1 = e1 - b1
            size2 = e2 - b2

            if size1 > size2:
                return -1
            elif size2 > size1:
                return 1
            elif b1 < b2:
                return -1
            elif b1 > b2:
                return 1

            r1 = otypeRank[fOtypev(n1)]
            r2 = otypeRank[fOtypev(n2)]

            if r2 > r1:
                return -1
            elif r1 > r2:
                return 1

            return (
                -1
                if n1 < n2
                else 1
                if n1 > n2
                else 0
            )

        return (
            functools.cmp_to_key(beforePosition),
            functools.cmp_to_key(beforeLength),
        )

    def sortNodes(self, nodeSet):

        api = self.api

        Crank = api.C.rank.data
        return sorted(nodeSet, key=lambda n: Crank[n - 1])

    def walk(self):

        api = self.api

        for n in api.C.order.data:
            yield n
