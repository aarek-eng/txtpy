
from collections import namedtuple
from itertools import chain
from ..core.helpers import rangesFromList, console
from ..core.text import DEFAULT_FORMAT
from .settings import ORIG
from .highlight import getHlAtt
from .helpers import QUAD


__pdoc__ = {}


class OuterSettings:

    pass


OuterSettings = namedtuple(  # noqa: F811
    "OuterSettings",
    """
    slotType
    ltr
    fmt
    textClsDefault
    textMethod
    getText
    upMethod
    slotsMethod
    lookupMethod
    browsing
    webLink
    getGraphics
""".strip().split(),
)


class NodeProps:

    pass


NodeProps = namedtuple(  # noqa: F811
    "NodeProps",
    """
    nType
    isSlot
    isSlotOrDescend
    descend
    isBaseNonSlot
    isLexType
    lexType
    lineNumberFeature
    featuresBare
    features
    textCls
    hlCls
    hlStyle
    cls
    hasGraphics
    after
    plainCustom
""".strip().split(),
)


class TreeInfo:

    def __init__(self, **specs):
        self.update(**specs)

    def update(self, **specs):
        for (k, v) in specs.items():
            setattr(self, k, v)

    def get(self, k, v):
        return getattr(self, k, v)


def unravel(app, n, isPlain=True, _inTuple=False, explain=False, **options):

    display = app.display
    dContext = display.distill(options)
    return _unravel(app, not isPlain, dContext, n, _inTuple=_inTuple, explain=explain)


def _unravel(app, isPretty, options, n, _inTuple=False, explain=False):

    _browse = app._browse
    webLink = app.webLink
    getText = app.getText
    getGraphics = getattr(app, "getGraphics", None)

    api = app.api
    N = api.N
    E = api.E
    F = api.F
    Fs = api.Fs
    L = api.L
    T = api.T

    eOslots = E.oslots.s
    fOtype = F.otype
    fOtypeV = fOtype.v
    fOtypeAll = fOtype.all
    slotType = fOtype.slotType
    nType = fOtypeV(n)

    aContext = app.context
    lexTypes = aContext.lexTypes
    lexMap = aContext.lexMap
    lineNumberFeature = aContext.lineNumberFeature
    featuresBare = aContext.featuresBare
    features = aContext.features
    descendantType = aContext.descendantType
    levelCls = aContext.levelCls
    styles = aContext.styles
    formatHtml = aContext.formatHtml
    hasGraphics = aContext.hasGraphics

    customMethods = app.customMethods
    afterChild = customMethods.afterChild
    plainCustom = customMethods.plainCustom
    prettyCustom = customMethods.prettyCustom

    baseTypes = options.baseTypes
    highlights = options.highlights
    fmt = options.fmt
    options.set("isHtml", fmt in formatHtml)
    ltr = _getLtr(app, options)
    textClsDefault = _getTextCls(app, fmt)
    descendType = T.formats.get(fmt, slotType)
    textMethod = T.text
    upMethod = L.u

    subBaseTypes = set()

    if baseTypes and baseTypes != {slotType}:
        for bt in baseTypes:
            if bt in descendantType:
                subBaseTypes |= descendantType[bt]

    settings = OuterSettings(
        slotType,
        ltr,
        fmt,
        textClsDefault,
        textMethod,
        getText,
        upMethod,
        eOslots,
        Fs,
        _browse,
        webLink,
        getGraphics,
    )

    nodeInfo = {}

    def distillChunkInfo(m, chunkInfo):

        mType = fOtypeV(m)
        isSlot = mType == slotType
        isBaseNonSlot = not isSlot and (mType in baseTypes or mType in subBaseTypes)
        (hlCls, hlStyle) = getHlAtt(app, m, highlights, isSlot)
        cls = {}
        if mType in levelCls:
            cls.update(levelCls[mType])
        if mType in prettyCustom:
            prettyCustom[mType](m, mType, cls)
        textCls = styles.get(mType, settings.textClsDefault)
        nodeInfoM = nodeInfo.setdefault(
            m,
            NodeProps(
                mType,
                isSlot,
                isSlot or mType == descendType,
                False if descendType == mType or mType in lexTypes else None,
                isBaseNonSlot,
                mType in lexTypes,
                lexMap.get(mType, None),
                lineNumberFeature.get(mType, None),
                featuresBare.get(mType, ((), {})),
                features.get(mType, ((), {})),
                textCls,
                hlCls,
                hlStyle,
                cls,
                mType in hasGraphics,
                afterChild.get(mType, None),
                plainCustom.get(mType, None) if plainCustom else None,
            ),
        )
        chunkInfo.update(
            options=options,
            settings=settings,
            props=nodeInfoM,
            boundaryCls=chunkBoundaries[chunk],
        )

    # determine intersecting nodes

    hideTypes = options.hideTypes
    hiddenTypes = options.hiddenTypes
    verseTypes = aContext.verseTypes
    showVerseInTuple = aContext.showVerseInTuple
    full = options.full

    isBigType = (
        _inTuple
        if not isPretty and nType in verseTypes and not showVerseInTuple
        else _getBigType(app, isPretty, options, nType)
    )

    if isBigType and not full:
        iNodes = set()
    elif nType in descendantType:
        myDescendantType = descendantType[nType]
        iNodes = set(L.i(n, otype=myDescendantType))
    elif nType in lexTypes:
        iNodes = {n}
    else:
        iNodes = set(L.i(n))

    if hideTypes:
        iNodes -= set(m for m in iNodes if fOtypeV(m) in hiddenTypes)

    iNodes.add(n)

    # chunkify all nodes and determine all true boundaries:
    # of nodes and of their maximal contiguous chunks

    exclusions = aContext.exclusions
    nSlots = eOslots(n)
    if nType in lexTypes:
        nSlots = (nSlots[0],)
    nSlots = set(nSlots)

    chunks = {}
    boundaries = {}

    for m in iNodes:
        mType = fOtypeV(m)
        if mType in exclusions:
            skip = False
            conditions = exclusions[mType]
            for (feat, value) in conditions.items():
                if Fs(feat).v(m) == value:
                    skip = True
                    break
            if skip:
                continue

        slots = eOslots(m)
        if nType in lexTypes:
            slots = (slots[0],)
        if m != n and mType == nType and nSlots <= set(slots):
            continue
        ranges = rangesFromList(slots)
        bounds = {}
        minSlot = min(slots)
        maxSlot = max(slots)

        # for each node m the boundaries value is a dict keyed by slots
        # and valued by a tuple: (left bound, right bound)
        # where bound is:
        # None if there is no left resp. right boundary there
        # True if the left resp. right node boundary is there
        # False if a left resp. right inner chunk boundary is there

        for r in ranges:
            (b, e) = r
            chunks.setdefault(mType, set()).add((m, r))
            bounds[b] = ((b == minSlot), (None if b != e else e == maxSlot))
            bounds[e] = ((b == minSlot if b == e else None), (e == maxSlot))
        boundaries[m] = bounds

    # fragmentize all chunks

    sortKeyChunk = N.sortKeyChunk
    sortKeyChunkLength = N.sortKeyChunkLength

    typeLen = len(fOtypeAll) - 1  # exclude the slot type

    for (p, pType) in enumerate(fOtypeAll):
        pChunks = chunks.get(pType, ())
        if not pChunks:
            continue

        # fragmentize nodes of the same type, largest first

        splits = {}

        pChunksLen = len(pChunks)
        pSortedChunks = sorted(pChunks, key=sortKeyChunkLength)
        for (i, pChunk) in enumerate(pSortedChunks):
            for j in range(i + 1, pChunksLen):
                p2Chunk = pSortedChunks[j]
                splits.setdefault(p2Chunk, set()).update(
                    _getSplitPoints(pChunk, p2Chunk)
                )

        # apply the splits for nodes of this type

        _applySplits(pChunks, splits)

        # fragmentize nodes of other types

        for q in range(p + 1, typeLen):
            qType = fOtypeAll[q]
            qChunks = chunks.get(qType, ())
            if not qChunks:
                continue
            splits = {}
            for qChunk in qChunks:
                for pChunk in pChunks:
                    splits.setdefault(qChunk, set()).update(
                        _getSplitPoints(pChunk, qChunk)
                    )
            _applySplits(qChunks, splits)

    # collect all fragments for all types in one list, ordered canonically
    # theorem: each fragment is either contained in the top node or completely
    # outside the top node.
    # We leave out the fragments that are outside the top node.
    # In order to test that, it is sufficient to test only one slot of
    # the fragment. We take the begin slot/

    chunks = sorted(
        (c for c in chain.from_iterable(chunks.values()) if c[1][0] in nSlots),
        key=sortKeyChunk,
    )

    # determine boundary classes

    startCls = "r" if ltr == "rtl" else "l"
    endCls = "l" if ltr == "rtl" else "r"

    chunkBoundaries = {}

    for (m, (b, e)) in chunks:
        bounds = boundaries[m]
        css = []
        code = bounds[b][0] if b in bounds else None
        cls = f"{startCls}no" if code is None else "" if code else startCls
        if cls:
            css.append(cls)
        code = bounds[e][1] if e in bounds else None
        cls = f"{endCls}no" if code is None else "" if code else endCls
        if cls:
            css.append(cls)

        chunkBoundaries[(m, (b, e))] = " ".join(css)

    # stack the chunks hierarchically

    tree = (None, TreeInfo(options=options, settings=settings), [])
    parent = {}
    rightmost = tree

    for chunk in chunks:
        rightnode = rightmost
        added = False
        m = chunk[0]
        e = chunk[1][1]
        chunkInfo = TreeInfo()

        while rightnode is not tree:
            (br, er) = rightnode[0][1]
            cr = rightnode[2]
            if e <= er:
                rightmost = (chunk, chunkInfo, [])
                cr.append(rightmost)
                parent[chunk] = rightnode
                added = True
                break

            rightnode = parent[rightnode[0]]

        if not added:
            rightmost = (chunk, chunkInfo, [])
            tree[2].append(rightmost)
            parent[chunk] = tree

        distillChunkInfo(m, chunkInfo)

    if explain:
        details = False if explain is True else True if explain == "details" else None
        if details is None:
            console(
                "Illegal value for parameter explain: `{explain}`.\n"
                "Must be `True` or `'details'`",
                error=True,
            )
        _showTree(tree, 0, details=details)
    return tree


def _getSplitPoints(pChunk, qChunk):

    (b1, e1) = pChunk[1]
    (b2, e2) = qChunk[1]
    if b2 == e2 or (b1 <= b2 and e1 >= e2):
        return []
    splitPoints = set()
    if b2 < b1 <= e2:
        splitPoints.add(b1)
    if b2 <= e1 < e2:
        splitPoints.add(e1 + 1)
    return splitPoints


def _applySplits(chunks, splits):

    if not splits:
        return

    for (target, splitPoints) in splits.items():
        if not splitPoints:
            continue
        chunks.remove(target)
        (m, (b, e)) = target
        prevB = b
        # invariant: sp > prevB
        # initially true because it is the result of _getSPlitPoint
        # after each iteration: the new split point cannot be the old one
        # and the new start is the old split point.
        for sp in sorted(splitPoints):
            chunks.add((m, (prevB, sp - 1)))
            prevB = sp
        chunks.add((m, (prevB, e)))


def _getTextCls(app, fmt):
    aContext = app.context
    formatCls = aContext.formatCls
    defaultClsOrig = aContext.defaultClsOrig

    return formatCls.get(fmt or DEFAULT_FORMAT, defaultClsOrig)


def _getLtr(app, options):
    aContext = app.context
    direction = aContext.direction

    fmt = options.fmt or DEFAULT_FORMAT

    return (
        "rtl"
        if direction == "rtl" and (f"{ORIG}-" in fmt or f"-{ORIG}" in fmt)
        else ("" if direction == "ltr" else "ltr")
    )


def _getBigType(app, isPretty, options, nType):
    api = app.api
    T = api.T
    N = api.N

    sectionTypeSet = T.sectionTypeSet
    structureTypeSet = T.structureTypeSet
    otypeRank = N.otypeRank

    aContext = app.context
    bigTypes = aContext.bigTypes
    isBigOverride = nType in bigTypes

    full = options.full
    condenseType = options.condenseType

    isBig = False
    if not full:
        if not isPretty and isBigOverride:
            isBig = True
        elif sectionTypeSet and nType in sectionTypeSet | structureTypeSet:
            if condenseType is None or otypeRank[nType] > otypeRank[condenseType]:
                isBig = True
        elif condenseType is not None and otypeRank[nType] > otypeRank[condenseType]:
            isBig = True
    return isBig


def _showTree(tree, level, details=False):
    indent = QUAD * level
    (chunk, info, subTrees) = tree
    if chunk is None:
        console(f"{indent}<{level}> TOP")
        settings = info.settings
        options = info.options
        if details:
            _showItems(
                indent,
                settings._asdict().items(),
                ((k, options.get(k)) for k in options.allKeys),
            )
    else:
        (n, (b, e)) = chunk
        rangeRep = "{" + (str(b) if b == e else f"{b}-{e}") + "}"
        props = info.props
        nType = props.nType
        isBaseNonSlot = props.isBaseNonSlot
        base = "*" if isBaseNonSlot else ""
        boundaryCls = info.boundaryCls
        console(f"{indent}<{level}> {nType}{base} {n} {rangeRep} {boundaryCls}")
        if details:
            _showItems(indent, props._asdict().items())
    for subTree in subTrees:
        _showTree(subTree, level + 1, details=details)


def _showItems(indent, *iterables):
    for (k, v) in sorted(chain(*iterables), key=lambda x: x[0],):
        if (
            k == "nType"
            or v is None
            or v == []
            or v == ""
            or v == {}
            or v == ()
            or v == set()
        ):
            continue
        console(f"{indent}{QUAD * 4}{k:<20} = {v}")
