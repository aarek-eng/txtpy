

import re
import types

from ..parameters import URL_GH, URL_NB, URL_TFDOC
from ..core.helpers import console, mergeDictOfSets
from .options import INTERFACE_OPTIONS
from .helpers import parseFeatures, transitiveClosure, showDict


VAR_PATTERN = re.compile(r"\{([^}]+)\}")

WRITING_DEFAULTS = dict(
    akk=dict(language="akkadian", direction="ltr",),
    hbo=dict(language="hebrew", direction="rtl",),
    syc=dict(language="syriac", direction="rtl",),
    ara=dict(language="arabic", direction="rtl",),
    grc=dict(language="greek", direction="ltr",),
    cld=dict(language="aramaic", direction="ltr",),
)
WRITING_DEFAULTS[""] = dict(language="", direction="ltr",)

FONT_BASE = (
    "https://github.com/annotation/text-fabric/blob/master/tf/server/static/fonts"
)

METHOD = "method"
STYLE = "style"
DESCEND = "descend"

FMT_KEYS = {METHOD, STYLE}

DEFAULT_CLS = "txtn"
DEFAULT_CLS_SRC = "txto"
DEFAULT_CLS_ORIG = "txtu"
DEFAULT_CLS_TRANS = "txtt"
DEFAULT_CLS_PHONO = "txtp"

NORMAL = "normal"
ORIG = "orig"

FORMAT_CLS = (
    (NORMAL, DEFAULT_CLS),
    (ORIG, DEFAULT_CLS_ORIG),
    ("trans", DEFAULT_CLS_TRANS),
    ("source", DEFAULT_CLS_SRC),
    ("phono", DEFAULT_CLS_PHONO),
)

LEVEL_DEFAULTS = dict(
    level={
        4: dict(flow="hor"),
        3: dict(flow="hor"),
        2: dict(flow="hor"),
        1: dict(flow="hor"),
        0: dict(flow="ver"),
    },
    flow=dict(ver=dict(wrap=False, stretch=False), hor=dict(wrap=True, stretch=True)),
    wrap=None,
    stretch=None,
)

RELATIVE_DEFAULT = "tf"

MSPEC_KEYS = set(
    """
    org
    repo
    relative
    corpus
    docUrl
    doi
""".strip().split()
)

PROVENANCE_DEFAULTS = (
    ("org", None),
    ("repo", None),
    ("relative", RELATIVE_DEFAULT),
    ("graphicsRelative", None),
    ("version", None),
    ("moduleSpecs", ()),
    ("zip", None),
    ("corpus", "TF dataset (unspecified)"),
    ("doi", None),
    ("webBase", None),
    ("webHint", None),
    ("webLang", None),
    ("webLexId", None),
    ("webOffset", None),
    ("webUrl", None),
    ("webUrlLex", None),
    ("webLexId", None),
    ("webHint", None),
)

DOC_DEFAULTS = (
    ("docRoot", "{urlGh}"),
    ("docExt", ".md"),
    ("docBase", "{docRoot}/{org}/{repo}/blob/master/docs"),
    ("docPage", "home"),
    ("docUrl", "{docBase}/{docPage}{docExt}"),
    ("featureBase", "{docBase}/features/<feature>{docExt}"),
    ("featurePage", "home"),
    ("charUrl", "{tfDoc}/writing/{language}.html"),
    ("charText", "How TF features represent text"),
)

DATA_DISPLAY_DEFAULTS = (
    ("excludedFeatures", set(), False),
    ("noneValues", {None}, False),
    ("sectionSep1", " ", False),
    ("sectionSep2", ":", False),
    ("textFormats", {}, True),
    ("browseNavLevel", None, True),
    ("browseContentPretty", False, False),
    ("showVerseInTuple", False, False),
    ("exampleSection", None, True),
    ("exampleSectionHtml", None, True),
)

TYPE_KEYS = set(
    """
    base
    children
    condense
    features
    featuresBare
    flow
    graphics
    hidden
    isBig
    label
    level
    lexOcc
    lineNumber
    stretch
    template
    transform
    verselike
    wrap
""".strip().split()
)

HOOKS = """
    transform
    afterChild
    plainCustom
    prettyCustom
""".strip().split()


class AppCurrent:
    def __init__(self, specs):
        self.allKeys = set()
        self.update(specs)

    def update(self, specs):
        allKeys = self.allKeys
        for (k, v) in specs.items():
            allKeys.add(k)
            setattr(self, k, v)

    def get(self, k, v):
        return getattr(self, k, v)

    def set(self, k, v):
        self.allKeys.add(k)
        setattr(self, k, v)


class Check:
    def __init__(self, app, withApi):
        self.app = app
        self.withApi = withApi
        self.errors = []

    def checkSetting(self, k, v, extra=None):
        app = self.app
        withApi = self.withApi
        errors = self.errors
        dKey = self.dKey
        specs = app.specs
        interfaceDefaults = {inf[0]: inf[1] for inf in INTERFACE_OPTIONS}

        if withApi:
            customMethods = app.customMethods
            api = app.api
            F = api.F
            T = api.T
            Fall = api.Fall
            allNodeFeatures = set(Fall())
            nTypes = F.otype.all
            sectionTypes = T.sectionTypes

            if k in {"template", "label"}:
                (template, feats) = extra
                if template is not True and type(template) is not str:
                    errors.append(f"{k} must be `true` or a string")
                for feat in feats:
                    if feat not in allNodeFeatures:
                        if feat not in customMethods.transform.get(dKey, {}):
                            errors.append(f"{k}: feature {feat} not loaded")
            elif k in {"featuresBare", "features"}:
                feats = extra[0]
                tps = extra[1].values()
                for feat in feats:
                    if feat not in allNodeFeatures:
                        errors.append(f"{k}: feature {feat} not loaded")
                for tp in tps:
                    if tp not in nTypes:
                        errors.append(f"{k}: node type {tp} not present")
            elif k == "exclude":
                if type(v) is not dict():
                    errors.append(f"{k}: must be a dict of features and values")
                    for feat in v:
                        if feat not in allNodeFeatures:
                            errors.append(f"{k}: feature {feat} not loaded")
            elif k == "base":
                pass
            elif k == "lineNumber":
                if v not in allNodeFeatures:
                    errors.append(f"{k}: feature {v} not loaded")
            elif k == "browseNavLevel":
                legalValues = set(range(len(sectionTypes)))
                if v not in legalValues:
                    allowed = ",".join(sorted(legalValues))
                    errors.append(f"{k} must be an integer in {allowed}")
            elif k == "children":
                if type(v) is not str and type(v) is not list:
                    errors.append(f"{k} must be a (list of) node types")
                else:
                    v = {v} if type(v) is str else set(v)
                    for tp in v:
                        if tp not in nTypes:
                            errors.append(f"{k}: node type {tp} not present")
            elif k in {"lexOcc"}:
                if type(v) is not str or v not in nTypes:
                    errors.append(f"{k}: node type {v} not present")
            elif k == "transform":
                for (feat, method) in extra.items():
                    if type(method) is str:
                        errors.append(f"{k}:{feat}: {method}() not implemented in app")
            elif k == "style":
                if type(v) is not str or v.lower() != v:
                    errors.append(f"{k} must be an all lowercase string")
            elif k in interfaceDefaults:
                allowed = self.extra[k]
                if not allowed and v is not None:
                    errors.append(
                        f"{k}={v} is not useful (dataset lacks relevant features)"
                    )
            elif k == "textFormats":
                formatStyle = specs["formatStyle"]
                if type(v) is dict:
                    for (fmt, fmtInfo) in v.items():
                        for (fk, fv) in fmtInfo.items():
                            if fk not in FMT_KEYS:
                                errors.append(f"{k}: {fmt}: illegal key {fk}")
                                continue
                            if fk == METHOD:
                                (descendType, func) = T.splitFormat(fv)
                                func = f"fmt_{func}"
                                if not hasattr(app, func):
                                    errors.append(
                                        f"{k}: {fmt} needs unimplemented method {func}"
                                    )
                            elif fk == STYLE:
                                if fv not in formatStyle:
                                    if fv.lower() != fv:
                                        errors.append(
                                            f"{k}: {fmt}: style {fv}"
                                            f" must be all lowercase"
                                        )
                else:
                    errors.append(f"{k} must be a dictionary")
        else:
            if k in {"excludedFeatures", "noneValues"}:
                if type(v) is not list:
                    errors.append(f"{k} must be a list")
            elif k in {
                "sectionSep1",
                "sectionSep2",
                "exampleSection",
                "exampleSectionHtml",
            }:
                if type(v) is not str:
                    errors.append(f"{k} must be a string")
            elif k == "writing":
                legalValues = set(WRITING_DEFAULTS)
                if v not in legalValues:
                    allowed = ",".join(legalValues - {""})
                    errors.append(f"{k} must be the empty string or one of {allowed}")
            elif k in {"direction", "language"}:
                legalValues = {w[k] for w in WRITING_DEFAULTS}
                if v not in legalValues:
                    allowed = ",".join(legalValues)
                    errors.append(f"{k} must be one of {allowed}")
            elif k in {
                "browseContentPretty",
                "base",
                "condense",
                "graphics",
                "hidden",
                "isBig",
                "showVerseInTuple",
                "stretch",
                "verselike",
                "wrap",
            }:
                legalValues = {True, False}
                if v not in legalValues:
                    allowed = "true,false"
                    errors.append(f"{k} must be a boolean in {allowed}")
            elif k == "flow":
                legalValues = {"hor", "ver"}
                if v not in legalValues:
                    allowed = ",".join(legalValues)
                    errors.append(f"{k} must be a value in {allowed}")
            elif k == "level":
                legalValues = set(range(len(4)))
                if v not in legalValues:
                    allowed = ",".join(sorted(legalValues))
                    errors.append(f"{k} must be an integer in {allowed}")

    def checkGroup(self, cfg, defaults, dKey, postpone=set(), extra=None):
        self.cfg = cfg
        self.defaults = defaults
        self.dKey = dKey
        self.extra = extra
        errors = []

        errors.clear()
        dSource = cfg.get(dKey, {})

        for (k, v) in dSource.items():
            if k in defaults:
                if k not in postpone:
                    self.checkSetting(k, v)
            else:
                errors.append(f"Illegal parameter `{k}` with value {v}")

    def checkItem(self, cfg, dKey):
        self.cfg = cfg
        self.dKey = dKey
        errors = self.errors

        errors.clear()
        if dKey in cfg:
            self.checkSetting(dKey, cfg[dKey])

    def report(self):
        errors = self.errors
        dKey = self.dKey

        if errors:
            console(f"App config error(s) in {dKey}:", error=True)
            for msg in errors:
                console(f"\t{msg}", error=True)

        self.errors = []


def _fillInDefined(template, data):
    val = template.format(**data)
    return None if "None" in val else val


def setAppSpecs(app, cfg, reset=False):
    if not reset:
        app.customMethods = AppCurrent({hook: {} for hook in HOOKS})
    specs = dict(urlGh=URL_GH, urlNb=URL_NB, tfDoc=URL_TFDOC,)
    app.specs = specs
    specs.update(cfg)
    if "apiVersion" not in specs:
        specs["apiVersion"] = None
    checker = Check(app, False)

    dKey = "writing"
    checker.checkItem(cfg, dKey)
    checker.report()
    value = cfg.get(dKey, "")
    specs[dKey] = value
    for (k, v) in WRITING_DEFAULTS[value].items():
        specs[k] = v
    extension = f" {value}" if value else ""
    defaultClsOrig = f"{DEFAULT_CLS_ORIG}{extension}"
    specs.update(extension=extension, defaultClsOrig=defaultClsOrig)

    for (dKey, defaults) in (
        ("provenanceSpec", PROVENANCE_DEFAULTS),
        ("docs", DOC_DEFAULTS),
    ):
        checker.checkGroup(cfg, {d[0] for d in defaults}, dKey)
        checker.report()
        dSource = cfg.get(dKey, {})
        for (k, v) in defaults:
            val = dSource.get(k, v)
            val = (
                None
                if val is None
                else _fillInDefined(val, specs)
                # else val.format(**specs)
                if type(val) is str
                else val
            )
            specs[k] = val

        if dKey == "provenanceSpec":
            moduleSpecs = specs["moduleSpecs"] or []
            for moduleSpec in moduleSpecs:
                for k in MSPEC_KEYS:
                    if k in moduleSpec:
                        v = moduleSpec[k]
                        if k == "docUrl" and v is not None:
                            # v = v.format(**specs)
                            v = _fillInDefined(v, specs)
                            moduleSpec[k] = v
                    else:
                        moduleSpec[k] = (
                            specs.get(k, None)
                            if k in {"org", "repo"}
                            else RELATIVE_DEFAULT
                            if k == "relative"
                            else None
                        )

        specs[dKey] = {k[0]: specs[k[0]] for k in defaults}

    if specs["zip"] is None:
        org = specs["org"]
        repo = specs["repo"]
        graphicsRelative = specs["graphicsRelative"]
        graphicsModule = [(org, repo, graphicsRelative)] if graphicsRelative else []
        specs["zip"] = (
            [repo]
            + [(m["org"], m["repo"], m["relative"],) for m in moduleSpecs]
            + graphicsModule
        )

    for (dKey, method) in (
        ("dataDisplay", getDataDefaults),
        ("typeDisplay", getTypeDefaults),
    ):
        method(app, cfg, dKey, False)

    app.context = AppCurrent(specs)


def setAppSpecsApi(app, cfg):
    api = app.api
    T = api.T

    specs = app.specs

    for (dKey, method) in (
        ("dataDisplay", getDataDefaults),
        ("typeDisplay", getTypeDefaults),
    ):
        method(app, cfg, dKey, True)

    specs["textFormat"] = T.defaultFormat

    dKey = "interfaceDefaults"
    interfaceDefaults = {inf[0]: inf[1] for inf in INTERFACE_OPTIONS}
    dSource = cfg.get(dKey, {})
    specific = {"lineNumbers", "showGraphics"}

    allowed = {}
    for (k, v) in interfaceDefaults.items():
        allow = (
            (
                k == "lineNumbers"
                and specs["lineNumberFeature"]
                or k == "showGraphics"
                and specs["hasGraphics"]
            )
            if k in specific
            else True
        )
        if k in dSource:
            val = dSource[k]
            default = val if allow else None
        else:
            default = v if allow else None
        interfaceDefaults[k] = default
        allowed[k] = allow
    checker = Check(app, True)
    checker.checkGroup(cfg, interfaceDefaults, dKey, extra=allowed)
    checker.report()
    specs[dKey] = interfaceDefaults

    app.context.update(specs)
    app.showContext = types.MethodType(showContext, app)


def getDataDefaults(app, cfg, dKey, withApi):
    checker = Check(app, withApi)

    if withApi:
        api = app.api
        F = api.F
        T = api.T
        sectionTypes = T.sectionTypes

    specs = app.specs

    givenInfo = cfg.get(dKey, {})

    if withApi:
        formatStyle = {f[0]: f[1] for f in FORMAT_CLS}
        formatStyle[ORIG] = specs["defaultClsOrig"]
        specs["formatStyle"] = formatStyle

    legalKeys = {d[0] for d in DATA_DISPLAY_DEFAULTS}
    checker.checkGroup(cfg, legalKeys, dKey)
    checker.report()

    for (attr, default, needsApi) in DATA_DISPLAY_DEFAULTS:
        if needsApi and not withApi or not needsApi and withApi:
            continue

        if attr == "browseNavLevel":
            default = len(sectionTypes) - 1 if sectionTypes else 1

        value = givenInfo.get(attr, specs.get(attr, default))
        if attr in specs and attr not in givenInfo:
            continue
        elif attr == "exampleSection":
            if not value:
                if sectionTypes:
                    verseType = sectionTypes[-1]
                    firstVerse = F.otype.s(verseType)[0]
                    value = app.sectionStrFromNode(firstVerse)
                else:
                    value = "passage"
            specs["exampleSection"] = value
            specs["exampleSectionHtml"] = f"<code>{value}</code>"
        if attr == "textFormats":
            methods = {fmt: v[METHOD] for (fmt, v) in value.items() if METHOD in v}
            styles = {fmt: v.get(STYLE, None) for (fmt, v) in value.items()}
            specs["formatMethod"] = methods
            specs["formatHtml"] = {T.splitFormat(fmt)[1] for fmt in methods}
            compileFormatCls(app, specs, styles)

        else:
            specs[attr] = value


def getTypeDefaults(app, cfg, dKey, withApi):
    if not withApi:
        return

    checker = Check(app, withApi)
    givenInfo = cfg.get(dKey, {})

    customMethods = app.customMethods

    api = app.api
    F = api.F
    T = api.T
    N = api.N
    otypeRank = N.otypeRank
    slotType = F.otype.slotType
    nTypes = F.otype.all
    structureTypes = T.structureTypes
    structureTypeSet = T.structureTypeSet
    sectionTypes = T.sectionTypes
    sectionTypeSet = T.sectionTypeSet

    sectionalTypeSet = sectionTypeSet | structureTypeSet

    specs = app.specs

    featuresBare = {}
    features = {}
    lineNumberFeature = {}
    hasGraphics = set()
    verseTypes = {sectionTypes[-1]} if sectionTypes else set()
    bigTypes = set()
    verseRank = otypeRank[sectionTypes[-1]] if sectionTypes else None
    lexMap = {}
    baseTypes = set()
    hiddenTypes = set()
    condenseType = None
    templates = {}
    labels = {}
    styles = {}
    givenLevels = {}
    levels = {}
    children = {}
    childType = {}
    exclusions = {}
    transform = {}

    customMethods.set("transform", transform)
    formatStyle = specs["formatStyle"]

    for nType in nTypes:
        template = (
            True if nType == slotType or nType in sectionalTypeSet - verseTypes else ""
        )
        for dest in (templates, labels):
            dest[nType] = (template, ())

    unknownTypes = {nType for nType in givenInfo if nType not in nTypes}
    if unknownTypes:
        unknownTypesRep = ",".join(sorted(unknownTypes))
        console(f"App config error(s) in typeDisplay: {unknownTypesRep}", error=True)

    for (nType, info) in givenInfo.items():
        checker.checkGroup(
            givenInfo,
            TYPE_KEYS,
            nType,
            postpone={
                "base",
                "label",
                "template",
                "features",
                "featuresBare",
                "transform",
            },
        )
        checker.report()

        if info.get("verselike", False):
            verseTypes.add(nType)

        lOcc = info.get("lexOcc", None)
        if lOcc is not None:
            lexMap[lOcc] = nType

        if "base" in info:
            base = info["base"]
            checker.checkSetting("base", base)
            baseTypes.add(nType)

        if "condense" in info:
            condenseType = nType

        trans = info.get("transform", None)
        if trans is not None:
            resolvedTrans = {}
            for (feat, func) in trans.items():
                methodName = f"transform_{func}"
                resolvedTrans[feat] = getattr(app, methodName, methodName)
            v = resolvedTrans
            checker.checkSetting("transform", trans, extra=v)
            transform[nType] = v

        for (k, dest) in (("template", templates), ("label", labels)):
            if k in info:
                template = info[k]
                templateFeatures = (
                    VAR_PATTERN.findall(template) if type(template) is str else ()
                )
                dest[nType] = (template, templateFeatures)
                checker.checkSetting(
                    k, template, extra=(template, templateFeatures),
                )

        if "style" in info:
            style = info["style"]
            styles[nType] = formatStyle.get(style, style)

        for k in ("featuresBare", "features"):
            v = info.get(k, "")
            parsedV = parseFeatures(v)
            checker.checkSetting(k, v, extra=parsedV)
            if k == "features":
                features[nType] = parsedV
            else:
                featuresBare[nType] = parsedV

        lineNumber = info.get("lineNumber", None)
        if lineNumber is not None:
            lineNumberFeature[nType] = lineNumber

        graphics = info.get("graphics", False)
        if graphics:
            hasGraphics.add(nType)

        hidden = info.get("hidden", None)
        if hidden:
            hiddenTypes.add(nType)

        verselike = info.get("verselike", False)
        if verselike:
            verseTypes.add(nType)

        if "children" in info:
            childs = info["children"] or ()
            if type(childs) is str:
                childs = {childs}
            else:
                childs = set(childs)
            children[nType] = set(childs or ())

        isBig = info.get("isBig", False)
        if isBig:
            bigTypes.add(nType)

        if "level" in info or "flow" in info or "wrap" in info or "stretch" in info:
            givenLevels[nType] = {
                k: v for (k, v) in info.items() if k in LEVEL_DEFAULTS
            }

        if "exclude" in info:
            exclusions[nType] = info["exclude"] or {}

        checker.report()

    lexTypes = set(lexMap.values())
    nTypesNoLex = [n for n in nTypes if n not in lexTypes]

    specs["allowedValues"] = dict(
        baseTypes=tuple(e for e in nTypesNoLex if e not in sectionTypeSet),
        condenseType=tuple(nTypesNoLex[0:-1]),
        hiddenTypes=tuple(e for e in nTypesNoLex[0:-1] if e not in sectionTypeSet),
    )

    levelTypes = [set(), set(), set(), set(), set()]
    levelTypes[4] = sectionalTypeSet - verseTypes
    levelTypes[3] = verseTypes
    levelTypes[0] = {slotType} | lexTypes

    remainingTypeSet = set(nTypes) - levelTypes[4] - levelTypes[3] - levelTypes[0]
    remainingTypes = tuple(x for x in nTypes if x in remainingTypeSet)
    nRemaining = len(remainingTypes)

    if nRemaining == 0:
        midType = slotType
    elif nRemaining == 1:
        midType = remainingTypes[0]
        levelTypes[1] = {midType}
    else:
        mid = len(remainingTypes) // 2
        midType = remainingTypes[mid]
        levelTypes[2] = set(remainingTypes[0:mid])
        levelTypes[1] = set(remainingTypes[mid:])

    childType = {
        nType: {nTypesNoLex[i + 1]}
        for (i, nType) in enumerate(nTypesNoLex)
        if i < len(nTypesNoLex) - 1
        # if nType in levelTypes[2] | levelTypes[1]
    }
    mergeDictOfSets(
        childType,
        {
            nType: {structureTypes[i + 1]}
            for (i, nType) in enumerate(structureTypes)
            if i < len(structureTypes) - 1
        },
    )
    mergeDictOfSets(
        childType,
        {
            nType: {sectionTypes[i + 1]}
            for (i, nType) in enumerate(sectionTypes)
            if i < len(sectionTypes) - 1
        },
    )

    # here we override from the chlidren information in the app-config

    for (nType, childInfo) in children.items():
        childType[nType] = childInfo

    lowestSectionalTypes = set() | verseTypes
    if sectionTypes:
        lowestSectionalTypes.add(sectionTypes[-1])
    if structureTypes:
        lowestSectionalTypes.add(structureTypes[-1])

    biggestOtherType = slotType
    for rt in remainingTypes:
        if verseRank is None or otypeRank[rt] < verseRank:
            biggestOtherType = rt
            break
    smallestOtherType = remainingTypes[-1] if remainingTypes else None

    for lexType in lexTypes:
        if lexType in childType:
            del childType[lexType]

    for lowestSectionalType in lowestSectionalTypes:
        if lowestSectionalType not in childType:
            childType[lowestSectionalType] = {biggestOtherType}
        else:
            childType[lowestSectionalType].add(biggestOtherType)

    if smallestOtherType is not None and smallestOtherType != slotType:
        if smallestOtherType not in childType:
            childType[smallestOtherType] = {slotType}
        else:
            childType[smallestOtherType].add(slotType)

    if condenseType is None:
        condenseType = sectionTypes[-1] if sectionTypes else midType

    for (i, nTypes) in enumerate(levelTypes):
        for nType in nTypes:
            levels[nType] = getLevel(i, givenLevels.get(nType, {}), nType in verseTypes)

    levelCls = {}

    for (nType, nTypeInfo) in levels.items():
        level = nTypeInfo["level"]
        flow = nTypeInfo["flow"]
        wrap = nTypeInfo["wrap"]

        containerCls = f"contnr c{level}"
        labelCls = f"lbl c{level}"
        childrenCls = (
            f"children {flow} {'wrap' if wrap else ''}"
            if childType.get(nType, None)
            else ""
        )

        levelCls[nType] = dict(
            container=containerCls, label=labelCls, children=childrenCls,
        )

    descendantType = transitiveClosure(childType, {slotType})

    specs.update(
        baseTypes=baseTypes if baseTypes else {slotType},
        bigTypes=bigTypes,
        childType=childType,
        condenseType=condenseType,
        descendantType=descendantType,
        exclusions=exclusions,
        features=features,
        featuresBare=featuresBare,
        hasGraphics=hasGraphics,
        hiddenTypes=hiddenTypes,
        labels=labels,
        levels=levels,
        levelCls=levelCls,
        lexMap=lexMap,
        lexTypes=lexTypes,
        lineNumberFeature=lineNumberFeature,
        noDescendTypes=lexTypes,
        styles=styles,
        templates=templates,
        verseTypes=verseTypes,
    )


def showContext(app, *keys):

    showDict(f"<b>{(app.appName)}</b> <i>app context</i>", app.specs, *keys)


def getLevel(defaultLevel, givenInfo, isVerse):
    level = givenInfo.get("level", defaultLevel)
    defaultsFromLevel = LEVEL_DEFAULTS["level"][level]
    flow = givenInfo.get("flow", "hor" if isVerse else defaultsFromLevel["flow"])
    defaultsFromFlow = LEVEL_DEFAULTS["flow"][flow]
    wrap = givenInfo.get("wrap", defaultsFromFlow["wrap"])
    stretch = givenInfo.get("stretch", defaultsFromFlow["stretch"])
    return dict(level=level, flow=flow, wrap=wrap, stretch=stretch)


def compileFormatCls(app, specs, givenStyles):
    api = app.api
    T = api.T

    result = {}
    extraFormats = set()

    formatStyle = specs["formatStyle"]
    defaultClsOrig = specs["defaultClsOrig"]

    for fmt in givenStyles:
        fmt = T.splitFormat(fmt)[1]
        extraFormats.add(fmt)

    for fmt in set(T.formats) | set(extraFormats):
        style = givenStyles.get(fmt, None)
        if style is None:
            textCls = None
            for (key, cls) in FORMAT_CLS:
                if (
                    f"-{key}-" in fmt
                    or fmt.startswith(f"{key}-")
                    or fmt.endswith(f"-{key}")
                ):
                    textCls = defaultClsOrig if key == ORIG else cls
            if textCls is None:
                textCls = DEFAULT_CLS
        else:
            textCls = defaultClsOrig if style == ORIG else formatStyle.get(style, style)
        result[fmt] = textCls

    specs["formatCls"] = result
