

class OtypeFeature(object):
    def __init__(self, api, metaData, data):
        self.api = api
        self.meta = metaData

        self.data = data[0]
        self.maxSlot = data[1]

        self.maxNode = data[2]

        self.slotType = data[3]

        self.all = None

    def items(self):

        slotType = self.slotType
        maxSlot = self.maxSlot
        data = self.data

        for n in range(1, maxSlot + 1):
            yield (n, slotType)

        maxNode = self.maxNode

        shift = maxSlot + 1

        for n in range(maxSlot + 1, maxNode + 1):
            yield (n, data[n - shift])

    def v(self, n):

        if n == 0:
            return None
        if n < self.maxSlot + 1:
            return self.slotType
        m = n - self.maxSlot
        if m <= len(self.data):
            return self.data[m - 1]
        return None

    def s(self, val):

        # NB: the support attribute has been added by precomputing __levels__
        if val in self.support:
            (b, e) = self.support[val]
            return range(b, e + 1)
        else:
            return ()

    def sInterval(self, val):

        # NB: the support attribute has been added by precomputing __levels__
        if val in self.support:
            return self.support[val]
        else:
            return ()
