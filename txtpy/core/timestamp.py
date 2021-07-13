
import sys
import time

from .helpers import unexpanduser as ux


class Timestamp(object):
    def __init__(self, level=None):
        indent = self.indent

        self.oneLevelRep = "   |   "
        self.timestamp = {}
        self.level = 0
        indent(level=level, reset=True)
        self.log = []
        self.verbose = -2  # regulates all messages
        self.silent = False  # regulates informational messages only

    def raw_msg(self, msg, tm=True, nl=True, cache=0, error=False):
        # cache is a list: append to cache, do not output anything
        # cache = -1: only to cache
        # cache =  1: to cache and to console
        # cache =  0: only to console
        if self.verbose != -2 and self.level >= self.verbose:
            return
        if type(msg) is not str:
            msg = repr(msg)
        msg = ux(msg)
        if tm:
            msgRep = f"{self.levelRep}{self._elapsed():>7} {msg}".replace(
                "\n", "\n" + self.levelRep
            )
        else:
            msgRep = f"{self.levelRep}{msg}".replace("\n", "\n" + self.levelRep)
        if type(cache) is list:
            cache.append((error, nl, msgRep))
        else:
            if cache:
                self.log.append((error, nl, msgRep))
            if cache >= 0:
                channel = sys.stderr if error else sys.stdout
                channel.write("{}{}".format(msgRep, "\n" if nl else ""))
                channel.flush()

    def reset(self):
        self.log = []

    def cache(self, _asString=False):
        if _asString:
            lines = []
            for (error, nl, msgRep) in self.log:
                lines.append("{}{}".format(msgRep, "\n" if nl else ""))
            result = "".join(lines)
        else:
            for (error, nl, msgRep) in self.log:
                channel = sys.stderr if error else sys.stdout
                channel.write("{}{}".format(msgRep, "\n" if nl else ""))
            sys.stderr.flush()
            sys.stdout.flush()
        self.log = []
        if _asString:
            return result

    def info(self, msg, tm=True, nl=True, cache=0, force=False):

        if force or not self.silent:
            self.raw_msg(msg, tm=tm, nl=nl, cache=cache)

    def warning(self, msg, tm=True, nl=True, cache=0, force=False):

        if force or self.silent != "deep":
            self.raw_msg(msg, tm=tm, nl=nl, cache=cache)

    def error(self, msg, tm=True, nl=True, cache=0):

        self.raw_msg(msg, tm=tm, nl=nl, cache=cache, error=True)

    def indent(self, level=None, reset=False, _verbose=None):

        self.level = (
            0
            if level is None
            else level
            if type(level) is int
            else self.level + 1
            if level
            else self.level - 1
        )
        if self.level < 0:
            self.level = 0
        self.levelRep = self.oneLevelRep * self.level
        if reset:
            self.timestamp[self.level] = time.time()
        if _verbose is not None:
            self.verbose = _verbose

    def isSilent(self):
        return self.silent

    def setSilent(self, silent):

        self.silent = silent

    def silentOn(self, deep=False):

        self.silent = True if not deep else "deep"

    def silentOff(self):

        self.silent = False

    def _elapsed(self):
        interval = time.time() - self.timestamp.setdefault(self.level, time.time())
        if interval < 10:
            return f"{interval: 2.2f}s"
        interval = int(round(interval))
        if interval < 60:
            return f"{interval:>2d}s"
        if interval < 3600:
            return f"{interval // 60:>2d}m {interval % 60:>02d}s"
        return (
            f"{interval // 3600:>2d}h {(interval % 3600) // 60:>02d}m"
            f" {interval % 60:>02d}s"
        )
