

import os
import types

from ..parameters import DOWNLOADS, SERVER_DISPLAY, SERVER_DISPLAY_BASE
from ..core.helpers import mdEsc
from .helpers import getRowsX, tupleEnum, RESULT, dh, showDict
from .condense import condense, condenseSet
from .highlight import getTupleHighlights
from .options import Options
from .render import render
from .unravel import unravel, _getLtr

LIMIT_SHOW = 100
LIMIT_TABLE = 2000


def displayApi(app, silent):

    app.export = types.MethodType(export, app)
    app.table = types.MethodType(table, app)
    app.plainTuple = types.MethodType(plainTuple, app)
    app.plain = types.MethodType(plain, app)
    app.show = types.MethodType(show, app)
    app.prettyTuple = types.MethodType(prettyTuple, app)
    app.pretty = types.MethodType(pretty, app)
    app.unravel = types.MethodType(unravel, app)
    app.loadCss = types.MethodType(loadCss, app)
    app.getCss = types.MethodType(getCss, app)
    app.displayShow = types.MethodType(displayShow, app)
    app.displaySetup = types.MethodType(displaySetup, app)
    app.displayReset = types.MethodType(displayReset, app)

    app.display = Options(app)
    if not app._browse:
        app.loadCss()


def displayShow(app, *options):

    display = app.display
    display.setup()
    data = display.current
    showDict("<b>current display options</b>", data, *options)


def displaySetup(app, **options):

    display = app.display

    display.setup(**options)


def displayReset(app, *options):

    display = app.display

    display.reset(*options)


def loadCss(app):

    _browse = app._browse
    aContext = app.context
    appCss = aContext.css

    if _browse:
        return appCss

    css = getCss(app)
    dh(css)


def getCss(app):

    aContext = app.context
    appCss = aContext.css

    cssPath = (
        f"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}"
        f"{SERVER_DISPLAY_BASE}"
    )
    genericCss = ""
    for cssFile in SERVER_DISPLAY:
        with open(f"{cssPath}/{cssFile}", encoding="utf8") as fh:
            genericCss += fh.read()

    tableCss = (
        "tr.tf.ltr, td.tf.ltr, th.tf.ltr { text-align: left ! important;}\n"
        "tr.tf.rtl, td.tf.rtl, th.tf.rtl { text-align: right ! important;}\n"
    )
    return f"<style>{tableCss}{genericCss}{appCss}</style>"


def export(app, tuples, toDir=None, toFile="results.tsv", **options):

    display = app.display

    if not display.check("table", options):
        return ""

    dContext = display.distill(options)
    fmt = dContext.fmt
    condenseType = dContext.condenseType
    tupleFeatures = dContext.tupleFeatures

    if toDir is None:
        toDir = os.path.expanduser(DOWNLOADS)
        if not os.path.exists(toDir):
            os.makedirs(toDir, exist_ok=True)
    toPath = f"{toDir}/{toFile}"

    resultsX = getRowsX(app, tuples, tupleFeatures, condenseType, fmt=fmt)

    with open(toPath, "w", encoding="utf_16_le") as fh:
        fh.write(
            "\ufeff"
            + "".join(
                ("\t".join("" if t is None else str(t) for t in tup) + "\n")
                for tup in resultsX
            )
        )


# PLAIN and FRIENDS


def table(app, tuples, _asString=False, **options):

    display = app.display

    if not display.check("table", options):
        return ""

    api = app.api
    F = api.F
    fOtypev = F.otype.v

    dContext = display.distill(options)
    end = dContext.end
    start = dContext.start
    withPassage = dContext.withPassage
    condensed = dContext.condensed
    condenseType = dContext.condenseType
    skipCols = dContext.skipCols

    ltr = _getLtr(app, dContext) or "ltr"

    if skipCols:
        tuples = tuple(
            tuple(x for (i, x) in enumerate(tup) if i + 1 not in skipCols)
            for tup in tuples
        )

    item = condenseType if condensed else RESULT

    if condensed:
        tuples = condense(api, tuples, condenseType, multiple=True)

    passageHead = f'</th><th class="tf {ltr}">p' if withPassage is True else ""

    html = []
    one = True

    newOptions = display.consume(options, "skipCols")

    for (i, tup) in tupleEnum(tuples, start, end, LIMIT_TABLE, item):
        if one:
            heads = '</th><th class="tf">'.join(fOtypev(n) for n in tup)
            html.append(
                f'<tr class="tf {ltr}">'
                f'<th class="tf {ltr}">n{passageHead}</th>'
                f'<th class="tf {ltr}">{heads}</th>'
                f"</tr>"
            )
            one = False
        html.append(
            plainTuple(
                app,
                tup,
                i,
                item=item,
                position=None,
                opened=False,
                _asString=True,
                skipCols=set(),
                **newOptions,
            )
        )
    html = "<table>" + "\n".join(html) + "</table>"
    if _asString:
        return html
    dh(html)


def plainTuple(
    app, tup, seq, item=RESULT, position=None, opened=False, _asString=False, **options
):

    display = app.display

    if not display.check("plainTuple", options):
        return ""

    api = app.api
    F = api.F
    T = api.T
    N = api.N
    otypeRank = N.otypeRank
    fOtypev = F.otype.v
    _browse = app._browse

    dContext = display.distill(options)
    condenseType = dContext.condenseType
    colorMap = dContext.colorMap
    highlights = dContext.highlights
    withPassage = dContext.withPassage
    skipCols = dContext.skipCols

    ltr = _getLtr(app, dContext) or "ltr"

    if skipCols:
        tup = tuple(x for (i, x) in enumerate(tup) if i + 1 not in skipCols)

    if withPassage is True:
        passageNode = _getRefMember(otypeRank, fOtypev, tup, dContext)
        passageRef = (
            ""
            if passageNode is None
            else app._sectionLink(passageNode)
            if _browse
            else app.webLink(passageNode, _asString=True)
        )
        passageRef = f'<span class="tfsechead ltr">{passageRef}</span>'
    else:
        passageRef = ""

    newOptions = display.consume(options, "withPassage")
    newOptionsH = display.consume(options, "withPassage", "highlights")

    highlights = getTupleHighlights(api, tup, highlights, colorMap, condenseType)

    if _browse:
        prettyRep = (
            prettyTuple(app, tup, seq, withPassage=False, **newOptions)
            if opened
            else ""
        )
        current = "focus" if seq == position else ""
        attOpen = "open " if opened else ""
        tupSeq = ",".join(str(n) for n in tup)
        if withPassage is True:
            sparts = T.sectionFromNode(passageNode, fillup=True)
            passageAtt = " ".join(
                f'sec{i}="{sparts[i] if i < len(sparts) else ""}"' for i in range(3)
            )
        else:
            passageAtt = ""

        plainRep = "".join(
            '<span class="col">'
            + mdEsc(
                app.plain(
                    n,
                    _inTuple=True,
                    withPassage=_doPassage(dContext, i),
                    highlights=highlights,
                    **newOptionsH,
                )
            )
            + "</span>"
            for (i, n) in enumerate(tup)
        )
        html = (
            f'<details class="pretty dtrow {current}" seq="{seq}" {attOpen}>'
            f"<summary>"
            f'<a href="#" class="pq fa fa-solar-panel fa-xs"'
            f' title="show in context" {passageAtt}></a>'
            f'<a href="#" class="sq" tup="{tupSeq}">{seq}</a>'
            f" {passageRef} {plainRep}"
            f"</summary>"
            f'<div class="pretty">{prettyRep}</div>'
            f"</details>"
        )
        return html

    html = [str(seq)]
    if withPassage is True:
        html.append(passageRef)
    for (i, n) in enumerate(tup):
        html.append(
            app.plain(
                n,
                _inTuple=True,
                _asString=True,
                withPassage=_doPassage(dContext, i),
                highlights=highlights,
                **newOptionsH,
            )
        )
    html = (
        f'<tr class="tf {ltr}"><td class="tf {ltr}">'
        + f'</td><td class="tf {ltr}">'.join(html)
        + "</td></tr>"
    )
    if _asString:
        return html

    passageHead = f'</th><th class="tf {ltr}">p' if withPassage is True else ""
    head = (
        (
            f'<tr class="tf {ltr}"><th class="tf {ltr}">n{passageHead}</th>'
            f'<th class="tf {ltr}">'
        )
        + f'</th><th class="tf {ltr}">'.join(fOtypev(n) for n in tup)
        + "</th></tr>"
    )
    html = "<table>" + head + "".join(html) + "</table>"

    dh(html)


def plain(app, n, _inTuple=False, _asString=False, explain=False, **options):

    return render(app, False, n, _inTuple, _asString, explain, **options)


# PRETTY and FRIENDS


def show(app, tuples, **options):

    display = app.display

    if not display.check("show", options):
        return ""

    dContext = display.distill(options)
    end = dContext.end
    start = dContext.start
    condensed = dContext.condensed
    condenseType = dContext.condenseType
    skipCols = dContext.skipCols

    if skipCols:
        tuples = tuple(
            tuple(x for (i, x) in enumerate(tup) if i + 1 not in skipCols)
            for tup in tuples
        )

    api = app.api
    F = api.F

    item = condenseType if condensed else RESULT

    if condensed:
        tuples = condense(api, tuples, condenseType, multiple=True)

    newOptions = display.consume(options, "skipCols")

    for (i, tup) in tupleEnum(tuples, start, end, LIMIT_SHOW, item):
        item = F.otype.v(tup[0]) if condensed and condenseType else RESULT
        prettyTuple(app, tup, i, item=item, skipCols=set(), **newOptions)


def prettyTuple(app, tup, seq, item=RESULT, **options):

    display = app.display

    if not display.check("prettyTuple", options):
        return ""

    dContext = display.distill(options)
    colorMap = dContext.colorMap
    highlights = dContext.highlights
    condenseType = dContext.condenseType
    condensed = dContext.condensed
    skipCols = dContext.skipCols

    _browse = app._browse

    if skipCols:
        tup = tuple(x for (i, x) in enumerate(tup) if i + 1 not in skipCols)

    if len(tup) == 0:
        if _browse:
            return ""
        else:
            return

    api = app.api
    N = api.N
    sortKey = N.sortKey

    containers = {tup[0]} if condensed else condenseSet(api, tup, condenseType)
    highlights = getTupleHighlights(api, tup, highlights, colorMap, condenseType)

    if not _browse:
        dh(f"<p><b>{item}</b> <i>{seq}</i></p>")
    if _browse:
        html = []
    for t in sorted(containers, key=sortKey):
        h = app.pretty(
            t,
            highlights=highlights,
            **display.consume(options, "highlights"),
        )
        if _browse:
            html.append(h)
    if _browse:
        return "".join(html)


def pretty(app, n, explain=False, **options):

    return render(app, True, n, False, False, explain, **options)


def _getRefMember(otypeRank, fOtypev, tup, dContext):
    minRank = None
    minN = None
    for n in tup:
        nType = fOtypev(n)
        rank = otypeRank[nType]
        if minRank is None or rank < minRank:
            minRank = rank
            minN = n
            if minRank == 0:
                break

    return (tup[0] if tup else None) if minN is None else minN


def _doPassage(dContext, i):
    withPassage = dContext.withPassage
    return withPassage is not True and withPassage and i + 1 in withPassage
