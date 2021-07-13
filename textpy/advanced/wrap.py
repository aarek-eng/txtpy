
import time
import datetime

from ..parameters import NAME, VERSION, DOI_URL_PREFIX, DOI_DEFAULT, DOI_TF, APP_URL

# PROVENANCE


def wrapProvenance(form, provenance, setNames):
    utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
    utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
    now = (
        datetime.datetime.now()
        .replace(microsecond=0, tzinfo=datetime.timezone(offset=utc_offset))
        .isoformat()
    )
    job = form["jobName"]
    author = form["author"]

    (appProvenance, dataProvenance) = provenance

    appHtml = ""
    appMd = ""
    sep = ""

    for d in appProvenance:
        d = dict(d)
        name = d["name"]
        commit = d["commit"]
        url = f"{APP_URL}/app-{name}/tree/{commit}"
        liveHtml = f'<a href="{url}">{commit}</a>'
        liveMd = f"[{commit}]({url})"
        appHtml += f"""\
    <div class="pline">
      <div class="pname">TF App:</div>
      <div class="pval">{name}</div>
    </div>
    <div class="p2line">
      <div class="pname">commit</div>
      <div class="pval">{liveHtml}</div>
    </div>\
"""
        appMd += f"""{sep}TF app | {name}
commit | {liveMd}"""
        sep = "\n"

    dataHtml = ""
    dataMd = ""
    sep = ""

    for d in dataProvenance:
        d = dict(d)
        corpus = d["corpus"]
        version = d["version"]
        release = d["release"]
        (liveText, liveUrl) = d["live"]
        liveHtml = f'<a href="{liveUrl}">{liveText}</a>'
        liveMd = f"[{liveText}]({liveUrl})"
        doi = d["doi"]
        doiUrl = f"{DOI_URL_PREFIX}/{doi}"
        doiHtml = f'<a href="{doiUrl}">{doi}</a>' if doi else DOI_DEFAULT
        doiMd = f"[{doi}]({doiUrl})" if doi else DOI_DEFAULT
        dataHtml += f"""\
    <div class="pline">
      <div class="pname">Data:</div>
      <div class="pval">{corpus}</div>
    </div>
    <div class="p2line">
      <div class="pname">version</div>
      <div class="pval">{version}</div>
    </div>
    <div class="p2line">
      <div class="pname">release</div>
      <div class="pval">{release}</div>
    </div>
    <div class="p2line">
      <div class="pname">download</div>
      <div class="pval">{liveHtml}</div>
    </div>
    <div class="p2line">
      <div class="pname">DOI</div>
      <div class="pval">{doiHtml}</div>
    </div>\
"""
        dataMd += f"""{sep}Data source | {corpus}
version | {version}
release | {release}
download   | {liveMd}
DOI | {doiMd}"""
        sep = "\n"

    setHtml = ""
    setMd = ""

    if setNames:
        setNamesRep = ", ".join(setNames)
        setHtml += f"""\
    <div class="psline">
      <div class="pname">Sets:</div>
      <div class="pval">{setNamesRep} (<b>not exported</b>)</div>
    </div>\
"""
        setMd += f"""Sets | {setNamesRep} (**not exported**)"""

    tool = f"{NAME} {VERSION}"
    toolDoiUrl = f"{DOI_URL_PREFIX}/{DOI_TF}"
    toolDoiHtml = f'<a href="{toolDoiUrl}">{DOI_TF}</a>'
    toolDoiMd = f"[{DOI_TF}]({toolDoiUrl})"

    html = f"""
    <div class="pline">\
      <div class="pname">Job:</div><div class="pval">{job}</div>
    </div>
    <div class="pline">
      <div class="pname">Author:</div><div class="pval">{author}</div>
    </div>
    <div class="pline">
      <div class="pname">Created:</div><div class="pval">{now}</div>
    </div>
    {dataHtml}
    {setHtml}
    <div class="pline">
      <div class="pname">Tool:</div>
      <div class="pval">{tool} {toolDoiHtml}</div>
    </div>
    {appHtml}\
  """

    md = f"""
meta | data
--- | ---
Job | {job}
Author | {author}
Created | {now}
{dataMd}
{setMd}
Tool | {tool} {toolDoiMd}
{appMd}
"""

    return (html, md)
