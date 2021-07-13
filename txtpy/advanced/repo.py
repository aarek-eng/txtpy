
import os
import io
import re
from shutil import rmtree
import requests
import base64
from zipfile import ZipFile

from github import Github, GithubException, UnknownObjectException

from ..parameters import (
    URL_GH,
    URL_TFDOC,
    GH_BASE,
    EXPRESS_BASE,
    EXPRESS_SYNC,
    EXPRESS_SYNC_LEGACY,
    DOWNLOADS,
)
from ..core.helpers import console, htmlEsc
from .helpers import dh
from .zipdata import zipData


class Repo:
    def __init__(
        self,
        org,
        repo,
        folder,
        version,
        increase,
        source=GH_BASE,
        dest=DOWNLOADS,
    ):
        self.org = org
        self.repo = repo
        self.folder = folder
        self.version = version
        self.increase = increase
        self.source = os.path.expanduser(source)
        self.dest = os.path.expanduser(dest)

        self.repoOnline = None
        self.ghConn = None

    def newRelease(self):
        if not self.makeZip():
            return False

        self.connect()
        if not self.ghConn:
            return False

        if not self.fetchInfo():
            return False

        if not self.bumpRelease():
            return False

        if not self.makeRelease():
            return False

        if not self.uploadZip():
            return False

        return True

    def makeZip(self):
        source = self.source
        dest = self.dest
        org = self.org
        repo = self.repo
        folder = self.folder
        version = self.version

        dataIn = f"{source}/{org}/{repo}/{folder}/{version}"

        if not os.path.exists(dataIn):
            console(f"No data found in {dataIn}", error=True)
            return False

        zipData(org, repo, version=version, relative=folder, source=source, dest=dest)
        return True

    def connect(self):
        warning = self.warning

        if not self.ghConn:
            ghPerson = os.environ.get("GHPERS", None)
            if ghPerson:
                self.ghConn = Github(ghPerson)
            else:
                ghClient = os.environ.get("GHCLIENT", None)
                ghSecret = os.environ.get("GHSECRET", None)
                if ghClient and ghSecret:
                    self.ghConn = Github(client_id=ghClient, client_secret=ghSecret)
                else:
                    self.ghConn = Github()
        try:
            rate = self.ghConn.get_rate_limit().core
            self.log(
                f"rate limit is {rate.limit} requests per hour,"
                f" with {rate.remaining} left for this hour"
            )
            if rate.limit < 100:
                warning(f"To increase the rate," f"see {URL_TFDOC}/advanced/repo.html/")

            self.log(
                f"\tconnecting to online GitHub repo {self.org}/{self.repo} ... ",
                newline=False,
            )
            self.repoOnline = self.ghConn.get_repo(f"{self.org}/{self.repo}")
            self.log("connected")
        except GithubException as why:
            warning("failed")
            warning(f"GitHub says: {why}")
        except IOError:
            warning("no internet")

    def fetchInfo(self):
        g = self.repoOnline
        if not g:
            return False
        self.commitOn = None
        self.releaseOn = None
        self.releaseCommitOn = None
        result = self.getRelease()
        if result:
            self.releaseOn = result
        result = self.getCommit()
        if result:
            self.commitOn = result
        return True

    def bumpRelease(self):
        increase = self.increase

        latestR = self.releaseOn
        if latestR:
            console(f"Latest release = {latestR}")
        else:
            latestR = "v0.0.0"
            console("No releases yet")

        # bump the release version

        v = ""
        if latestR.startswith("v"):
            v = "v"
            r = latestR[1:] if latestR.startswith("v") else latestR
        parts = [int(p) for p in r.split(".")]
        nParts = len(parts)
        if nParts < increase:
            for i in range(nParts, increase):
                parts.append(0)
        parts[increase - 1] += 1
        parts[increase:] = []
        newTag = f"{v}{'.'.join(str(p) for p in parts)}"
        console(f"New release = {newTag}")
        self.newTag = newTag
        return True

    def makeRelease(self):
        commit = self.commitOn
        newTag = self.newTag

        g = self.repoOnline
        if not g:
            return False

        tag_message = "data update"
        release_name = "data update"
        release_message = "data update"

        try:
            newReleaseObj = g.create_git_tag_and_release(
                newTag,
                tag_message,
                release_name,
                release_message,
                commit,
                "commit",
            )
        except Exception as e:
            self.error("\tcannot create release", newline=True)
            console(str(e), error=True)
            return False

        self.newReleaseObj = newReleaseObj
        return True

    def uploadZip(self):
        newTag = self.newTag
        newReleaseObj = self.newReleaseObj
        dest = self.dest
        org = self.org
        repo = self.repo
        folder = self.folder
        version = self.version
        dataFile = f"{folder}-{version}.zip"
        dataDir = f"{dest}/{org}-release/{repo}"
        dataPath = f"{dataDir}/{dataFile}"

        if not os.path.exists(dataPath):
            console(f"No release data found: {dataPath}", error=True)
            return False

        try:
            newReleaseObj.upload_asset(dataPath, label='', content_type="application/zip", name=dataFile)
            console(f"{dataFile} attached to release {newTag}")
        except Exception as e:
            self.error("\tcannot attach zipfile to release", newline=True)
            console(str(e), error=True)
            return False

        return True

    def getRelease(self):
        r = self.getReleaseObj()
        if not r:
            return None
        return r.tag_name

    def getReleaseObj(self):
        g = self.repoOnline
        if not g:
            return None

        r = None

        try:
            r = g.get_latest_release()
        except UnknownObjectException:
            self.error("\tno releases", newline=True)
        except Exception:
            self.error("\tcannot find releases", newline=True)
        return r

    def getCommit(self):
        c = self.getCommitObj()
        if not c:
            return None
        return c.sha

    def getCommitObj(self):
        error = self.error

        g = self.repoOnline
        if not g:
            return None

        c = None

        try:
            cs = g.get_commits()
            if cs.totalCount:
                c = cs[0]
            else:
                error("\tno commits")
        except Exception:
            error("\tcannot find commits")
        return c

    def log(self, msg, newline=True):
        console(msg, newline=newline)

    def warning(self, msg, newline=True):
        console(msg, newline=newline)

    def error(self, msg, newline=True):
        console(msg, error=True, newline=newline)


def releaseData(org, repo, folder, version, increase, source=GH_BASE, dest=DOWNLOADS):
    R = Repo(org, repo, folder, version, increase, source=source, dest=dest)
    return R.newRelease()


class Checkout(object):
    @staticmethod
    def fromString(string):
        commit = None
        release = None
        local = None
        if not string:
            commit = ""
            release = ""
        elif string == "latest":
            commit = None
            release = ""
        elif string == "hot":
            commit = ""
            release = None
        elif string in {"local", "clone"}:
            commit = None
            release = None
            local = string
        elif "." in string or len(string) < 12:
            commit = None
            release = string
        else:
            commit = string
            release = None
        return (commit, release, local)

    @staticmethod
    def toString(commit, release, local, source=GH_BASE, dest=EXPRESS_BASE):
        extra = ""
        if local:
            baseRep = source if local == "clone" else dest
            extra = f" offline under {baseRep}"
        if local == "clone":
            result = "repo clone"
        elif commit and release:
            result = f"r{release}=#{commit}"
        elif commit:
            result = f"#{commit}"
        elif release:
            result = f"r{release}"
        elif commit is None and release is None:
            result = "unknown release or commit"
        elif commit is None:
            result = "latest release"
        elif release is None:
            result = "latest commit"
        else:
            result = "latest release or commit"
        return f"{result}{extra}"

    def isClone(self):
        return self.local == "clone"

    def isOffline(self):
        return self.local in {"clone", "local"}

    def __init__(
        self,
        org,
        repo,
        relative,
        checkout,
        source,
        dest,
        keep,
        withPaths,
        silent,
        _browse,
        version=None,
        label="data",
    ):
        self._browse = _browse
        self.label = label
        self.org = org
        self.repo = repo
        self.source = source
        self.dest = dest
        (self.commitChk, self.releaseChk, self.local) = self.fromString(checkout)
        clone = self.isClone()
        offline = self.isOffline()

        self.relative = relative
        self.version = version
        versionRep = f"/{version}" if version else ""
        self.versionRep = versionRep
        relativeRep = f"/{relative}" if relative else ""
        relativeGh = f"/tree/master/{relative}" if relative else ""
        self.baseGh = f"{URL_GH}/{org}/{repo}{relativeGh}{versionRep}"
        self.dataDir = f"{relative}{versionRep}"

        self.baseLocal = os.path.expanduser(self.dest)
        self.dataRelLocal = f"{org}/{repo}{relativeRep}"
        self.dirPathSaveLocal = f"{self.baseLocal}/{org}/{repo}"
        self.dirPathLocal = f"{self.baseLocal}/{self.dataRelLocal}{versionRep}"
        self.dataPathLocal = f"{self.dataRelLocal}{versionRep}"
        self.filePathLocal = f"{self.dirPathLocal}/{EXPRESS_SYNC}"

        self.baseClone = os.path.expanduser(self.source)
        self.dataRelClone = f"{org}/{repo}{relativeRep}"
        self.dirPathClone = f"{self.baseClone}/{self.dataRelClone}{versionRep}"
        self.dataPathClone = f"{self.dataRelClone}{versionRep}"

        self.dataPath = self.dataRelClone if clone else self.dataRelLocal

        self.keep = keep
        self.withPaths = withPaths
        self.ghConn = None

        self.commitOff = None
        self.releaseOff = None
        self.commitOn = None
        self.releaseOn = None
        self.releaseCommitOn = None

        self.silent = silent

        self.repoOnline = None
        self.localBase = False
        self.localDir = None

        if clone:
            self.commitOff = None
            self.releaseOff = None
        else:
            self.fixInfo()
            self.readInfo()

        if not offline:
            self.connect()
            self.fetchInfo()

    def log(self, msg, newline=True):
        silent = self.silent
        if not silent:
            console(msg, newline=newline)

    def warning(self, msg, newline=True):
        silent = self.silent
        if not silent == "deep":
            console(msg, newline=newline)

    def error(self, msg, newline=True):
        console(msg, error=True, newline=newline)

    def possibleError(self, msg, showErrors, again=False, indent="\t", newline=False):
        error = self.error
        warning = self.warning

        if showErrors:
            error(msg, newline=newline)
        else:
            warning(msg, newline=newline)
            if again:
                warning(f"{indent}Will try something else")

    def makeSureLocal(self, attempt=False):
        _browse = self._browse
        label = self.label
        offline = self.isOffline()
        clone = self.isClone()

        error = self.error
        warning = self.warning

        cOff = self.commitOff
        rOff = self.releaseOff
        cChk = self.commitChk
        rChk = self.releaseChk
        cOn = self.commitOn
        rOn = self.releaseOn
        rcOn = self.releaseCommitOn

        askExact = rChk or cChk
        askExactRelease = rChk
        askExactCommit = cChk
        askLatest = not askExact and (rChk == "" or cChk == "")
        askLatestAny = rChk == "" and cChk == ""
        askLatestRelease = rChk == "" and cChk is None
        askLatestCommit = cChk == "" and rChk is None

        isExactReleaseOff = rChk and rChk == rOff
        isExactCommitOff = cChk and cChk == cOff
        isExactReleaseOn = rChk and rChk == rOn
        isExactCommitOn = cChk and cChk == cOn
        isLatestRelease = rOff and rOff == rOn or cOff and cOff == rcOn
        isLatestCommit = cOff and cOff == cOn

        isLocal = (
            askExactRelease
            and isExactReleaseOff
            or askExactCommit
            and isExactCommitOff
            or askLatestAny
            and (isLatestRelease or isLatestCommit)
            or askLatestRelease
            and isLatestRelease
            or askLatestCommit
            and isLatestCommit
        )
        mayLocal = (
            askLatestAny
            and (rOff or cOff)
            or askLatestRelease
            and rOff
            or askLatestCommit
            and cOff
        )
        canOnline = self.repoOnline
        isOnline = canOnline and (
            askExactRelease
            and isExactReleaseOn
            or askExactCommit
            and isExactCommitOn
            or askLatestAny
            or askLatestRelease
            or askLatestCommit
        )

        if offline:
            if clone:
                dirPath = self.dirPathClone
                self.localBase = self.baseClone if os.path.exists(dirPath) else False
            else:
                self.localBase = (
                    self.baseLocal
                    if (
                        cChk
                        and cChk == cOff
                        or cChk is None
                        and cOff
                        or rChk
                        and rChk == rOff
                        or rChk is None
                        and rOff
                    )
                    else False
                )
            if not self.localBase:
                method = self.warning if attempt else self.error
                method(f"The requested {label} is not available offline")
                base = self.baseClone if clone else self.baseLocal
                method(f"\t{base}/{self.dataPath} not found")
        else:
            if isLocal:
                self.localBase = self.baseLocal
            else:
                if not canOnline:
                    if askLatest:
                        if mayLocal:
                            warning(f"The offline {label} may not be the latest")
                            self.localBase = self.baseLocal
                        else:
                            error(f"The requested {label} is not available offline")
                    else:
                        warning(f"The requested {label} is not available offline")
                        error("No online connection")
                elif not isOnline:
                    error(f"The requested {label} is not available online")
                else:
                    self.localBase = self.baseLocal if self.download() else False

        if self.localBase:
            self.localDir = self.dataPath
            state = (
                "requested"
                if askExact
                else "latest release"
                if rChk == "" and canOnline and self.releaseOff
                else "latest? release"
                if rChk == "" and not canOnline and self.releaseOff
                else "latest commit"
                if cChk == "" and canOnline and self.commitOff
                else "latest? commit"
                if cChk == "" and not canOnline and self.commitOff
                else "local release"
                if self.local == "local" and self.releaseOff
                else "local commit"
                if self.local == "local" and self.commitOff
                else "local github"
                if self.local == "clone"
                else "for whatever reason"
            )
            offString = self.toString(
                self.commitOff,
                self.releaseOff,
                self.local,
                dest=self.dest,
                source=self.source,
            )
            labelEsc = htmlEsc(label)
            stateEsc = htmlEsc(state)
            offEsc = htmlEsc(offString)
            locEsc = htmlEsc(f"{self.localBase}/{self.localDir}{self.versionRep}")
            if _browse:
                self.log(
                    f"Using {label} in {self.localBase}/{self.localDir}{self.versionRep}:"
                )
                self.log(f"\t{offString} ({state})")
            else:
                dh(
                    f'<b title="{stateEsc}">{labelEsc}:</b>'
                    f' <span title="{offEsc}">{locEsc}</span>'
                )

    def download(self):
        cChk = self.commitChk
        rChk = self.releaseChk

        fetched = False
        if rChk is not None:
            fetched = self.downloadRelease(rChk, showErrors=cChk is None)
        if not fetched and cChk is not None:
            fetched = self.downloadCommit(cChk, showErrors=True)

        if fetched:
            self.writeInfo()
        return fetched

    def downloadRelease(self, release, showErrors=True):
        cChk = self.commitChk
        r = self.getReleaseObj(release, showErrors=showErrors)
        if not r:
            return False
        (commit, release) = self.getReleaseFromObj(r)

        assets = None
        try:
            assets = r.get_assets()
        except Exception:
            pass
        assetUrl = None
        versionRep3 = f"-{self.version}" if self.version else ""
        relativeFlat = self.relative.replace("/", "-")
        dataFile = f"{relativeFlat}{versionRep3}.zip"
        if assets and assets.totalCount > 0:
            for asset in assets:
                if asset.name == dataFile:
                    assetUrl = asset.browser_download_url
                    break
        fetched = False
        if assetUrl:
            fetched = self.downloadZip(assetUrl, showErrors=False)
        if not fetched:
            thisShowErrors = not cChk == ""
            fetched = self.downloadCommit(commit, showErrors=thisShowErrors)
        if fetched:
            self.commitOff = commit
            self.releaseOff = release
        return fetched

    def downloadCommit(self, commit, showErrors=True):
        c = self.getCommitObj(commit)
        if not c:
            return False
        commit = self.getCommitFromObj(c)
        fetched = self.downloadDir(commit, exclude=r"\.tfx", showErrors=showErrors)
        if fetched:
            self.commitOff = commit
            self.releaseOff = None
        return fetched

    def downloadZip(self, dataUrl, showErrors=True):
        label = self.label
        self.log(f"\tdownloading {dataUrl} ... ")
        try:
            r = requests.get(dataUrl, allow_redirects=True)
            self.log("\tunzipping ... ")
            zf = io.BytesIO(r.content)
        except Exception as e:
            msg = f"\t{str(e)}\n\tcould not download {dataUrl}"
            self.possibleError(msg, showErrors, again=True)
            return False

        self.log(f"\tsaving {label}")

        cwd = os.getcwd()
        destZip = self.dirPathLocal
        try:
            z = ZipFile(zf)
            if not self.keep:
                if os.path.exists(destZip):
                    rmtree(destZip)
            os.makedirs(destZip, exist_ok=True)
            os.chdir(destZip)
            if self.withPaths:
                z.extractall()
                if os.path.exists("__MACOSX"):
                    rmtree("__MACOSX")
            else:
                for zInfo in z.infolist():
                    if zInfo.filename[-1] == "/":
                        continue
                    if zInfo.filename.startswith("__MACOS"):
                        continue
                    zInfo.filename = os.path.basename(zInfo.filename)
                    z.extract(zInfo)
        except Exception:
            msg = f"\tcould not save {label} to {destZip}"
            self.possibleError(msg, showErrors, again=True)
            os.chdir(cwd)
            return False
        os.chdir(cwd)
        return True

    def downloadDir(self, commit, exclude=None, showErrors=False):
        g = self.repoOnline
        if not g:
            return None

        destDir = f"{self.dirPathLocal}"
        destSave = f"{self.dirPathSaveLocal}"
        if not self.keep:
            if os.path.exists(destDir):
                rmtree(destDir)
        os.makedirs(destDir, exist_ok=True)

        excludeRe = re.compile(exclude) if exclude else None

        good = True

        def _downloadDir(subPath, level=0):
            nonlocal good
            if not good:
                return
            lead = "\t" * level
            try:
                contents = g.get_contents(subPath, ref=commit)
            except UnknownObjectException:
                msg = f"{lead}No directory {subPath} in {self.toString(commit, None, False)}"
                self.possibleError(msg, showErrors, again=True, indent=lead)
                good = False
                return
            for content in contents:
                thisPath = content.path
                self.log(f"\t{lead}{thisPath}...", newline=False)
                if exclude and excludeRe.search(thisPath):
                    self.log("excluded")
                    continue
                if content.type == "dir":
                    self.log("directory")
                    os.makedirs(f"{destSave}/{thisPath}", exist_ok=True)
                    _downloadDir(thisPath, level + 1)
                else:
                    try:
                        fileContent = g.get_git_blob(content.sha)
                        fileData = base64.b64decode(fileContent.content)
                        fileDest = f"{destSave}/{thisPath}"
                        with open(fileDest, "wb") as fd:
                            fd.write(fileData)
                        self.log("downloaded")
                    except (GithubException, IOError):
                        msg = "error"
                        self.possibleError(msg, showErrors, again=True, indent=lead)
                        good = False

        _downloadDir(self.dataDir, 0)

        if good:
            self.log("\tOK")
        else:
            msg = "\tFailed"
            self.possibleError(msg, showErrors)

        return good

    def getRelease(self, release, showErrors=True):
        r = self.getReleaseObj(release, showErrors=showErrors)
        if not r:
            return None
        return self.getReleaseFromObj(r)

    def getCommit(self, commit):
        c = self.getCommitObj(commit)
        if not c:
            return None
        return self.getCommitFromObj(c)

    def getReleaseObj(self, release, showErrors=True):
        g = self.repoOnline
        if not g:
            return None

        r = None
        msg = f' tagged "{release}"' if release else "s"

        try:
            r = g.get_release(release) if release else g.get_latest_release()
        except UnknownObjectException:
            self.possibleError(f"\tno release{msg}", showErrors, newline=True)
        except Exception:
            self.possibleError(f"\tcannot find release{msg}", showErrors, newline=True)
        return r

    def getCommitObj(self, commit):
        error = self.error

        g = self.repoOnline
        if not g:
            return None

        c = None
        msg = f' with hash "{commit}"' if commit else "s"

        try:
            cs = g.get_commits(sha=commit) if commit else g.get_commits()
            if cs.totalCount:
                c = cs[0]
            else:
                error(f"\tno commit{msg}")
        except Exception:
            error(f"\tcannot find commit{msg}")
        return c

    def getReleaseFromObj(self, r):
        g = self.repoOnline
        if not g:
            return None
        release = r.tag_name
        ref = g.get_git_ref(f"tags/{release}")
        commit = ref.object.sha
        return (commit, release)

    def getCommitFromObj(self, c):
        g = self.repoOnline
        if not g:
            return None
        return c.sha

    def fetchInfo(self):
        g = self.repoOnline
        if not g:
            return
        self.commitOn = None
        self.releaseOn = None
        self.releaseCommitOn = None
        if self.releaseChk is not None:
            result = self.getRelease(self.releaseChk, showErrors=self.commitChk is None)
            if result:
                (self.releaseCommitOn, self.releaseOn) = result
        if self.commitChk is not None:
            result = self.getCommit(self.commitChk)
            if result:
                self.commitOn = result

    def fixInfo(self):
        sDir = self.dirPathLocal
        if not os.path.exists(sDir):
            return
        for sFile in EXPRESS_SYNC_LEGACY:
            sPath = f"{sDir}/{sFile}"
            if os.path.exists(sPath):
                goodPath = f"{sDir}/{EXPRESS_SYNC}"
                if os.path.exists(goodPath):
                    os.remove(sPath)
                else:
                    os.rename(sPath, goodPath)

    def readInfo(self):
        if os.path.exists(self.filePathLocal):
            with open(self.filePathLocal, encoding="utf8") as f:
                for line in f:
                    string = line.strip()
                    (commit, release, local) = self.fromString(string)
                    if commit:
                        self.commitOff = commit
                    if release:
                        self.releaseOff = release

    def writeInfo(self):
        if not os.path.exists(self.dirPathLocal):
            os.makedirs(self.dirPathLocal, exist_ok=True)
        with open(self.filePathLocal, "w", encoding="utf8") as f:
            if self.releaseOff:
                f.write(f"{self.releaseOff}\n")
            if self.commitOff:
                f.write(f"{self.commitOff}\n")

    def connect(self):
        warning = self.warning

        if not self.ghConn:
            ghPerson = os.environ.get("GHPERS", None)
            if ghPerson:
                self.ghConn = Github(ghPerson)
            else:
                ghClient = os.environ.get("GHCLIENT", None)
                ghSecret = os.environ.get("GHSECRET", None)
                if ghClient and ghSecret:
                    self.ghConn = Github(client_id=ghClient, client_secret=ghSecret)
                else:
                    self.ghConn = Github()
        try:
            rate = self.ghConn.get_rate_limit().core
            self.log(
                f"rate limit is {rate.limit} requests per hour,"
                f" with {rate.remaining} left for this hour"
            )
            if rate.limit < 100:
                warning(f"To increase the rate," f"see {URL_TFDOC}/advanced/repo.html/")

            self.log(
                f"\tconnecting to online GitHub repo {self.org}/{self.repo} ... ",
                newline=False,
            )
            self.repoOnline = self.ghConn.get_repo(f"{self.org}/{self.repo}")
            self.log("connected")
        except GithubException as why:
            warning("failed")
            warning(f"GitHub says: {why}")
        except IOError:
            warning("no internet")


def checkoutRepo(
    _browse=False,
    org="annotation",
    repo="tutorials",
    folder="text-fabric/examples/banks/tf",
    version="",
    checkout="",
    source=GH_BASE,
    dest=EXPRESS_BASE,
    withPaths=True,
    keep=True,
    silent=False,
    label="data",
):
    def resolve(chkout, attempt=False):
        rData = Checkout(
            org,
            repo,
            folder,
            chkout,
            source,
            dest,
            keep,
            withPaths,
            silent,
            _browse,
            version=version,
            label=label,
        )
        rData.makeSureLocal(attempt=attempt)
        return (
            (
                rData.commitOff,
                rData.releaseOff,
                rData.local,
                rData.localBase,
                rData.localDir,
            )
            if rData.localBase
            else (None, None, False, False, None)
        )

    if checkout == "":
        rData = resolve("local", attempt=True)
        if rData[3]:
            return rData

    return resolve(checkout)
