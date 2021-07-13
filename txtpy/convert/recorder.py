

import os
from itertools import chain

from txtpy.core.helpers import specFromRangesLogical, specFromRanges, rangesFromSet

ZWJ = "\u200d"  # zero width joiner


class Recorder:
    def __init__(self, api=None):
        self.api = api

        self.material = []

        self.nodesByPos = []

        self.context = set()

    def start(self, n):
        self.context.add(n)

    def end(self, n):
        self.context.discard(n)

    def add(self, string, empty=ZWJ):

        if string is None:
            string = empty
        self.material.append(string)
        self.nodesByPos.extend([frozenset(self.context)] * len(string))

    def text(self):
        return "".join(self.material)

    def positions(self, byType=False, simple=False):

        if not byType:
            if simple:
                return tuple(list(x)[0] if x else None for x in self.nodesByPos)
            return self.nodesByPos

        api = self.api
        if api is None:
            print(
                """\
Cannot determine node types without a TF api.
You have to call Recorder(`api`) instead of Recorder()
where `api` is the result of
    txtpy.app.use(corpus)
    or
    txtpy.Fabric(locations, modules).load(features)
"""
            )
            return None

        F = api.F
        Fotypev = F.otype.v
        info = api.TF.info
        indent = api.TF.indent

        indent(level=True, reset=True)
        info("gathering nodes ...")

        allNodes = set(chain.from_iterable(self.nodesByPos))
        allTypes = {Fotypev(n) for n in allNodes}
        info(f"found {len(allNodes)} nodes in {len(allTypes)} types")

        nodesByPosByType = {nodeType: [] for nodeType in allTypes}

        info("partitioning nodes over types ...")

        for nodeSet in self.nodesByPos:
            typed = {}
            for node in nodeSet:
                nodeType = Fotypev(node)
                typed.setdefault(nodeType, set()).add(node)
            for nodeType in allTypes:
                thisSet = (
                    frozenset(typed[nodeType]) if nodeType in typed else frozenset()
                )
                value = (list(thisSet)[0] if thisSet else None) if simple else thisSet
                nodesByPosByType[nodeType].append(value)

        info("done")
        indent(level=False)
        return nodesByPosByType

    def iPositions(self, byType=False, logical=True, asEntries=False):

        method = specFromRangesLogical if logical else specFromRanges
        posByNode = {}
        for (i, nodeSet) in enumerate(self.nodesByPos):
            for node in nodeSet:
                posByNode.setdefault(node, set()).add(i)
        for (n, nodeSet) in posByNode.items():
            posByNode[n] = method(rangesFromSet(nodeSet))

        if asEntries:
            posByNode = tuple(posByNode.items())
        if not byType:
            return posByNode

        api = self.api
        if api is None:
            print(
                """\
Cannot determine node types without a TF api.
You have to call Recorder(`api`) instead of Recorder()
where `api` is the result of
    txtpy.app.use(corpus)
    or
    txtpy.Fabric(locations, modules).load(features)
"""
            )
            return None

        F = api.F
        Fotypev = F.otype.v

        posByNodeType = {}
        if asEntries:
            for (n, spec) in posByNode:
                nType = Fotypev(n)
                posByNodeType.setdefault(nType, []).append(n, spec)
        else:
            for (n, spec) in posByNode.items():
                nType = Fotypev(n)
                posByNodeType.setdefault(nType, {})[n] = spec

        return posByNodeType

    def rPositions(self, acceptMaterialOutsideNodes=False):

        good = True
        multipleNodes = 0
        multipleFirst = 0
        noNodes = 0
        noFirst = 0
        nonConsecutive = 0
        nonConsecutiveFirst = 0

        posByNode = {}
        for (i, nodeSet) in enumerate(self.nodesByPos):
            if (not acceptMaterialOutsideNodes and len(nodeSet) == 0) or len(
                nodeSet
            ) > 1:
                good = False
                if len(nodeSet) == 0:
                    if noNodes == 0:
                        noFirst = i
                    noNodes += 1
                else:
                    if multipleNodes == 0:
                        multipleFirst = i
                    multipleNodes += 1
                continue
            for node in nodeSet:
                if node in posByNode:
                    continue
                posByNode[node] = i

        lastI = i

        if not good:
            msg = ""
            if noNodes:
                msg += (
                    f"{noNodes} positions without node, "
                    f"of which the first one is {noFirst}\n"
                )
            if multipleNodes:
                msg += (
                    f"{multipleNodes} positions with multiple nodes, "
                    f"of which the first one is {multipleFirst}\n"
                )
            return msg

        sortedPosByNode = sorted(posByNode.items())
        offset = sortedPosByNode[0][0] - 1
        posList = [offset]
        prevNode = offset
        for (node, i) in sortedPosByNode:
            if prevNode + 1 != node:
                good = False
                if nonConsecutive == 0:
                    nonConsecutiveFirst = f"{prevNode} => {node}"
                nonConsecutive += 1
            else:
                posList.append(i)
            prevNode = node
        posList.append(lastI)

        if not good:
            return (
                f"{nonConsecutive} nonConsecutive nodes, "
                f"of which the first one is {nonConsecutiveFirst}"
            )
        return posList

    def write(self, textPath, posPath=None, byType=False, optimize=True):

        posPath = posPath or f"{textPath}.pos"

        with open(textPath, "w", encoding="utf8") as fh:
            fh.write(self.text())

        if not byType:
            with open(posPath, "w", encoding="utf8") as fh:
                fh.write(
                    "\n".join(
                        "\t".join(str(i) for i in nodes) for nodes in self.nodesByPos
                    )
                )
            return

        nodesByPosByType = self.positions(byType=True)
        if nodesByPosByType is None:
            print("No position files written")
            return

        (base, ext) = os.path.splitext(posPath)

        # if we reach this, there is a TF api

        api = self.api
        info = api.TF.info
        indent = api.TF.indent

        indent(level=True, reset=True)

        for (nodeType, nodesByPos) in nodesByPosByType.items():
            fileName = f"{base}-{nodeType}{ext}"
            info(f"{nodeType:<20} => {fileName}")
            with open(fileName, "w", encoding="utf8") as fh:
                if not optimize:
                    fh.write(
                        "\n".join(
                            "\t".join(str(i) for i in nodes) for nodes in nodesByPos
                        )
                    )
                else:
                    repetition = 1
                    previous = None

                    for nodes in nodesByPos:
                        if nodes == previous:
                            repetition += 1
                            continue
                        else:
                            if previous is not None:
                                prefix = f"{repetition}*" if repetition > 1 else ""
                                value = "\t".join(str(i) for i in previous)
                                fh.write(f"{prefix}{value}\n")
                            repetition = 1
                            previous = nodes
                    if previous is not None:
                        prefix = f"{repetition + 1}*" if repetition else ""
                        value = "\t".join(str(i) for i in previous)
                        fh.write(f"{prefix}{value}\n")

        indent(level=False)

    def read(self, textPath, posPath=None):

        posPath = posPath or f"{textPath}.pos"
        self.context = {}

        with open(textPath, encoding="utf8") as fh:
            self.material = list(fh)

        with open(posPath, encoding="utf8") as fh:
            self.nodesByPos = [
                {int(n) for n in line.rstrip("\n").split("\t")} for line in fh
            ]

    def makeFeatures(self, featurePath, headers=True):

        nodesByPos = self.nodesByPos

        features = {}

        with open(featurePath, encoding="utf8") as fh:
            if headers is True:
                names = next(fh).rstrip("\n").split("\t")[2:]
            elif headers is not None:
                names = headers
            else:
                names = None

            for line in fh:
                (start, end, *data) = line.rstrip("\n").split("\t")
                if names is None:
                    names = tuple(f"f{i}" for i in range(1, len(data) + 1))
                nodes = set(
                    chain.from_iterable(
                        nodesByPos[i] for i in range(int(start), int(end) + 1)
                    )
                )
                for n in nodes:
                    for i in range(len(names)):
                        val = data[i]
                        if not val:
                            continue
                        name = names[i]
                        features.setdefault(name, {})[n] = val

        return features
