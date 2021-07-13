

class OslotsFeature(object):
    def __init__(self, api, metaData, data):
        self.api = api
        self.meta = metaData

        self.data = data[0]
        self.maxSlot = data[1]
        self.maxNode = data[2]

    def items(self):

        maxSlot = self.maxSlot
        data = self.data
        maxNode = self.maxNode

        shift = maxSlot + 1

        for n in range(maxSlot + 1, maxNode + 1):
            yield (n, data[n - shift])

    def s(self, n):

        if n == 0:
            return ()
        if n < self.maxSlot + 1:
            return (n,)
        m = n - self.maxSlot
        if m <= len(self.data):
            return self.data[m - 1]
        return ()
