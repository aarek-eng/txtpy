import os

from IPython.display import display, Markdown, HTML

from ..parameters import EXPRESS_BASE, GH_BASE, TEMP_DIR
from ..core.helpers import mdEsc, htmlEsc, unexpanduser, QUAD


RESULT = "result"
NB = "\u00a0"
EM = "*empty*"

SEQ_TYPES1 = {tuple, list}
SEQ_TYPES2 = {tuple, list, set, frozenset}


def dm(md):

    display(Markdown(unexpanduser(md)))


def dh(html):

    display(HTML(unexpanduser(html)))


# COLLECT CONFIG SETTINGS IN A DICT


def getLocalDir(cfg, local, version):
    provenanceSpec = cfg.get("provenanceSpec", {})
    org = provenanceSpec.get("org", None)
    repo = provenanceSpec.get("repo", None)
    relative = provenanceSpec.get("relative", "tf")
    version = provenanceSpec.get("version", None) if version is None else version
    base = hasData(local, org, repo, version, relative)

    if not base:
        base = EXPRESS_BASE

    return os.path.expanduser(f"{base}/{org}/{repo}/{TEMP_DIR}")


def hasData(local, org, repo, version, relative):
    versionRep = f"/{version}" if version else ""
    if local == "clone":
        ghBase = os.path.expanduser(GH_BASE)
        ghTarget = f"{ghBase}/{org}/{repo}/{relative}{versionRep}"
        if os.path.exists(ghTarget):
            return ghBase

    expressBase = os.path.expanduser(EXPRESS_BASE)
    expressTarget = f"{expressBase}/{org}/{repo}/{relative}{versionRep}"
    if os.path.exists(expressTarget):
        return expressBase
    return False


def tupleEnum(tuples, start, end, limit, item):
    if start is None:
        start = 1
    i = -1
    if not hasattr(tuples, "__len__"):
        if end is None or end - start + 1 > limit:
            end = start - 1 + limit
        for tup in tuples:
            i += 1
            if i < start - 1:
                continue
            if i >= end:
                break
            yield (i + 1, tup)
    else:
        if end is None or end > len(tuples):
            end = len(tuples)
        rest = 0
        if end - (start - 1) > limit:
            rest = end - (start - 1) - limit
            end = start - 1 + limit
        for i in range(start - 1, end):
            yield (i + 1, tuples[i])
        if rest:
            dh(
                f"<b>{rest} more {item}s skipped</b> because we show a maximum of"
                f" {limit} {item}s at a time"
            )


def parseFeatures(features):
    if (
        type(features) in SEQ_TYPES1
        and len(features) == 2
        and type(features[0]) in SEQ_TYPES2
        and type(features[1]) is dict
    ):
        return features

    bare = []
    indirect = {}
    feats = (
        ()
        if not features
        else features.split()
        if type(features) is str
        else tuple(features)
    )
    for feat in feats:
        if not feat:
            continue
        parts = feat.split(":", 1)
        feat = parts[-1]
        bare.append(feat)
        if len(parts) > 1:
            indirect[feat] = parts[0]
    return (bare, indirect)


def transitiveClosure(relation, reflexiveExceptions):

    descendants = {parent: set(children) for (parent, children) in relation.items()}

    changed = True
    while changed:
        changed = False
        for (parent, children) in relation.items():
            for child in children:
                if child in descendants:
                    for grandChild in descendants[child]:
                        if grandChild not in descendants[parent]:
                            descendants[parent].add(grandChild)
                            changed = True
    for parent in relation:
        if parent not in reflexiveExceptions:
            descendants[parent].add(parent)
    return descendants


def htmlSafe(text, isHtml):
    return text if isHtml else htmlEsc(text)


def getText(
    app, isPretty, n, nType, outer, first, last, level, passage, descend, options=None
):
    T = app.api.T
    sectionTypeSet = T.sectionTypeSet
    structureTypeSet = T.structureTypeSet

    aContext = app.context
    templates = aContext.labels if isPretty else aContext.templates

    fmt = None if options is None else options.fmt
    standardFeatures = True if options is None else options.standardFeatures
    isHtml = False if options is None else options.isHtml
    suppress = set() if options is None else options.suppress

    (tpl, feats) = templates[nType]

    tplFilled = (
        (
            (
                '<span class="tfsechead">'
                + (NB if passage else app.sectionStrFromNode(n))
                + "</span>"
            )
            if nType in sectionTypeSet
            else f'<span class="structure">{app.structureStrFromNode(n)}</span>'
            if nType in structureTypeSet
            else htmlSafe(
                T.text(
                    n,
                    fmt=fmt,
                    descend=descend,
                    outer=outer,
                    first=first,
                    last=last,
                    level=level,
                ),
                isHtml,
            )
        )
        if tpl is True
        else (
            tpl.format(
                **{feat: getValue(app, n, nType, feat, suppress) for feat in feats}
            )
            if standardFeatures
            else ""
        )
    )
    return tplFilled


def getValue(app, n, nType, feat, suppress):
    F = app.api.F
    Fs = app.api.Fs

    customMethods = app.customMethods
    transform = customMethods.transform
    if feat in suppress:
        val = ""
    else:
        featObj = Fs(feat) if hasattr(F, feat) else None
        val = htmlEsc(featObj.v(n)) if featObj else None
        modifier = transform.get(nType, {}).get(feat, None)
        if modifier:
            val = modifier(n, val)
    return f'<span title="{feat}">{val}</span>'


# COMPOSE TABLES FOR CSV EXPORT


def isUniform(app, tuples):
    api = app.api
    F = api.F
    fOtype = F.otype.v

    uniform = True
    fixedLength = None
    fixedTypes = None

    for tup in tuples:
        thisLength = len(tup)
        theseTypes = tuple(fOtype(n) for n in tup)

        if fixedLength is None:
            fixedLength = thisLength
        if fixedTypes is None:
            fixedTypes = theseTypes

        if thisLength != fixedLength or theseTypes != fixedTypes:
            uniform = False
            break

    return uniform


def getRowsX(app, tuples, features, condenseType, fmt=None):

    return (
        getResultsX(app, tuples, features, condenseType, fmt=fmt)
        if isUniform(app, tuples)
        else getTuplesX(app, tuples, condenseType, fmt=fmt)
    )


def getResultsX(app, results, features, condenseType, fmt=None):

    api = app.api
    F = api.F
    Fs = api.Fs
    T = api.T
    N = api.N
    fOtype = F.otype.v
    otypeRank = N.otypeRank
    sectionTypeSet = T.sectionTypeSet

    aContext = app.context
    noDescendTypes = aContext.noDescendTypes

    sectionDepth = len(sectionTypeSet)
    if len(results) == 0:
        return ()
    firstResult = results[0]
    nTuple = len(firstResult)
    refColumns = [
        i for (i, n) in enumerate(firstResult) if fOtype(n) not in sectionTypeSet
    ]
    refColumn = refColumns[0] if refColumns else nTuple - 1
    header = ["R"] + [f"S{i}" for i in range(1, sectionDepth + 1)]
    emptyA = []

    featureDict = {i: tuple(f.split()) if type(f) is str else f for (i, f) in features}

    def withText(nodeType):
        return (
            condenseType is None
            and nodeType not in sectionTypeSet
            or otypeRank[nodeType] <= otypeRank[condenseType]
        )

    noDescendTypes = noDescendTypes

    for j in range(nTuple):
        i = j + 1
        n = firstResult[j]
        nType = fOtype(n)
        header.extend([f"NODE{i}", f"TYPE{i}"])
        if withText(nType):
            header.append(f"TEXT{i}")
        header.extend(f"{feature}{i}" for feature in featureDict.get(j, emptyA))
    rows = [tuple(header)]
    for (rm, r) in enumerate(results):
        rn = rm + 1
        row = [rn]
        refN = r[refColumn]
        sparts = T.sectionFromNode(refN)
        nParts = len(sparts)
        section = sparts + ((None,) * (sectionDepth - nParts))
        row.extend(section)
        for j in range(nTuple):
            n = r[j]
            nType = fOtype(n)
            row.extend((n, nType))
            if withText(nType):
                text = T.text(n, fmt=fmt, descend=nType not in noDescendTypes)
                row.append(text)
            row.extend(Fs(feature).v(n) for feature in featureDict.get(j, emptyA))
        rows.append(tuple(row))
    return tuple(rows)


def getTuplesX(app, results, condenseType, fmt=None):

    api = app.api
    F = api.F
    T = api.T
    N = api.N
    fOtype = F.otype.v
    otypeRank = N.otypeRank
    sectionTypeSet = T.sectionTypeSet

    aContext = app.context
    noDescendTypes = aContext.noDescendTypes

    sectionDepth = len(sectionTypeSet)
    if len(results) == 0:
        return ()

    def withText(nodeType):
        return (
            condenseType is None
            and nodeType not in sectionTypeSet
            or otypeRank[nodeType] <= otypeRank[condenseType]
        )

    noDescendTypes = noDescendTypes

    rows = []

    for (tm, tup) in enumerate(results):
        tn = tm + 1
        row = [tn]
        for n in tup:
            sparts = T.sectionFromNode(n)
            nParts = len(sparts)
            section = sparts + ((None,) * (sectionDepth - nParts))
            row.extend(section)
            nType = fOtype(n)
            row.extend((n, nType))
            if withText(nType):
                text = T.text(n, fmt=fmt, descend=nType not in noDescendTypes)
                row.append(text)
        rows.append(tuple(row))
    return tuple(rows)


def eScalar(x, level):
    if type(x) is str and "\n" in x:
        indent = QUAD * level
        return (
            f"\n{indent}```\n{indent}"
            + f"\n{indent}".join(x.split("\n"))
            + f"\n{indent}```\n"
        )
    return f"`{mdEsc(str(x))}`" if x else EM


def eEmpty(x):
    return EM if type(x) is str else str(x)


def eList(x, level):
    tpv = type(x)
    indent = QUAD * level
    md = "\n"
    for (i, v) in enumerate(sorted(x, key=lambda y: str(y)) if tpv is set else x):
        item = f"{i + 1}." if level == 0 else "*"
        md += f"{indent}{item:<4}{eData(v, level + 1)}"
    return md


def eDict(x, level):
    indent = QUAD * level
    md = "\n"
    for (k, v) in sorted(x.items(), key=lambda y: str(y)):
        item = "*"
        md += f"{indent}{item:<4}**{eScalar(k, level)}**:" f" {eData(v, level + 1)}"
    return md


def eRest(x, level):
    indent = QUAD * level
    return "\n" + indent + eScalar(x, level) + "\n"


def eData(x, level):
    if not x:
        return eEmpty(x) + "\n"
    tpv = type(x)
    if tpv is str or tpv is float or tpv is int or tpv is bool:
        return eScalar(x, level) + "\n"
    if tpv is list or tpv is tuple or tpv is set:
        return eList(x, level)
    if tpv is dict:
        return eDict(x, level)
    return eRest(x, level)


def showDict(title, data, *keys):

    keys = set(keys)

    openRep1 = "open" if len(keys) else ""
    openRep2 = "open" if len(keys) == 1 else ""
    md = [f"<details {openRep1}>" f"<summary>{title}</summary>\n\n"]
    for (i, (k, v)) in enumerate(sorted(data.items(), key=lambda y: str(y))):
        if len(keys) and k not in keys:
            continue
        md.append(
            f"<details {openRep2}>"
            f"<summary>{i + 1}. {k}</summary>\n\n{eData(v, 0)}\n</details>\n"
        )
    md.append("</details>\n")
    dm("".join(md))
