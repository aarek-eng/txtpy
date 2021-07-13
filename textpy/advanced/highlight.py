from itertools import chain

from .search import runSearch


def getHlAtt(app, n, highlights, isSlot):

    noResult = ({True: "", False: ""}, {True: "", False: ""})

    if highlights is None:
        return noResult

    color = (
        highlights.get(n, None)
        if type(highlights) is dict
        else ""
        if n in highlights
        else None
    )

    if color is None:
        return noResult

    hlCls = {True: "hl", False: "hl" if isSlot else "hlbx"}
    hlObject = {True: "background", False: "background" if isSlot else "border"}
    hlCls = {b: hlCls[b] for b in (True, False)}
    hlStyle = {
        b: f' style="{hlObject[b]}-color: {color};" ' if color != "" else ""
        for b in (True, False)
    }

    return (hlCls, hlStyle)


def getTupleHighlights(api, tup, highlights, colorMap, condenseType):

    F = api.F
    N = api.N
    fOtype = F.otype.v
    otypeRank = N.otypeRank

    condenseRank = otypeRank[condenseType]
    if highlights is None:
        highlights = {}
    elif type(highlights) is set:
        highlights = {m: "" for m in highlights}
    newHighlights = {n: h for (n, h) in highlights.items()}

    for (i, n) in enumerate(tup):
        nType = fOtype(n)
        if newHighlights.get(n, None):
            continue
        if otypeRank[nType] < condenseRank:
            newHighlights[n] = (
                highlights[n]
                if n in highlights
                else colorMap[i + 1]
                if colorMap is not None and i + 1 in colorMap
                else ""
            )
    return newHighlights


def getPassageHighlights(app, node, query, cache):

    if not query:
        return None

    (queryResults, messages, features) = runSearch(app, query, cache)
    if messages:
        return None

    api = app.api
    L = api.L
    passageNodes = L.d(node)

    resultSet = set(chain.from_iterable(queryResults))
    passageSet = set(passageNodes)
    return resultSet & passageSet
