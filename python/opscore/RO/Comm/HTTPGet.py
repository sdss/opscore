#!/usr/bin/env python

"""Retrieve a remote file via http to a local file.

Note: at exit attempts to abort all outstanding transfers and delete the output files.

To do: try polling while connected instead of using a progress callback.
The advantages are:
- fewer calls (except over a slow connection)
- can implement a "stalled" time limit that only kicks in
  if the given time elapses with no new bytes read.
To do this you will have to get the full size from the token:
self._tkApp.eval("set [set token](totalsize)")
and should probably get the current size as well
(rather than using the convenience function)
because it's not clear the convenience function exists in older tcl.
note: I doubt this tcl code can be executed with _tkApp.call --
at least nothing I tried with call worked.

Loosely based on opscore.RO.Wdg.FTPLogWdg.

History:
2005-07-08 ROwen
2005-07-11 ROwen    Modified to call stateFunc less often during download.
2005-09-15 ROwen    Documented the arguments for callback functions.
2008-04-29 ROwen    Fixed reporting of exceptions that contain unicode arguments.
2010-05-26 ROwen    Tweaked to use _removeAllCallbacks() instead of nulling _callbacks.
2010-11-12 ROwen    Bug fix: timeLim was mishandled.
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
2012-08-01 ROwen    Changed isDone()->isDone, getStateStr()->state, getErrMsg()->errMsg,
                    getBytes()->readBytes, totBytes;
                    Deleted getState() (use state, but returns a string, not an int);
                    Added didFail, isAbortable.
                    State constants are now strings, not integers.
2014-04-01 ROwen    Bug fix: "unknown state" message used an undefined variable.
2014-09-16 ROwen    Modified to use opscore.RO.AddCallback.safeCall2.
                    Modified _cleanup to deregister tcl callbacks before cleaning up the connection.
                    Modified to print warnings to stderr instead of stdout.
2014-09-18 ROwen    Fixed a bug in the unit test.
2015-09-24 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
"""

from __future__ import print_function


__all__ = ['HTTPGet']

import atexit
import os
import sys
import time
from six.moves import tkinter
import opscore.RO.AddCallback
import opscore.RO.StringUtil
import opscore.RO.TkUtil

_Debug = False
_DebugExit = False

_ProgressInterval = 0.1 # minimum time between progress callbacks (sec)

class _ExitClass:
    """Class to keep track of outstanding nework transfers
    and abort them at exit.
    """
    def __init__(self, timeLim = 2.0, dtime = 0.1):
        self.transferDict = {}
        self.timeLim = timeLim
        self.dtime = max(dtime, 0.01)
        self.didRegisterExit = False

    def addTransfer(self, httpGetter):
        """Add one httpGetter.
        """
        if _DebugExit:
            print("HTTPGet._Exit.addTransfer(%s)" % (httpGetter,))
        httpGetter.addDoneCallback(self.removeTransfer)
        self.transferDict[httpGetter] = None
        if not self.didRegisterExit:
            atexit.register(self.abortAll)
            self.didRegisterExit = True

    def removeTransfer(self, httpGetter):
        """Remove one httpGetter.
        Does not verify that the getter is finished.
        """
        if _DebugExit:
            print("HTTPGet._Exit.removeTransfer(%s)" % (httpGetter,))
        self.transferDict.pop(httpGetter)

    def abortAll(self):
        """Abort all outsanding transfers.
        Meant to be registered with atexit.
        """
        if _DebugExit:
            print("HTTPGet._Exit.abortAll()")
        if not self.transferDict:
            return

        transferList = list(self.transferDict.keys())
        for xfer in transferList:
            if _DebugExit:
                print("HTTGet._Exit: aborting %s" % (xfer,))
            xfer.abort()

        # wait a few seconds for all to end
        maxWaits = self.timeLim / self.dtime
        nWaits = 0
        while self.transferDict:
            time.sleep(self.dtime)
            nWaits += 1
            if nWaits > maxWaits:
                if _DebugExit:
                    print("HTTGet._Exit: timed out while waiting for aborts to finish")
                break
        else:
            if _DebugExit:
                print("HTTGet._Exit: all aborts finished")
_ExitObj = _ExitClass()


class HTTPGet(opscore.RO.AddCallback.BaseMixin):
    """Downloads the specified url to a file.

    Inputs:
    - fromURL   url of file to download
    - toPath    full path of destination file
    - isBinary  file is binary? (if False, EOL translation is probably performed)
    - overwrite if True, overwrites the destination file if it exists;
                otherwise raises ValueError
    - createDir if True, creates any required directories;
                otherwise raises ValueError
    - doneFunc  function to call when the transfer completes
    - stateFunc function to call when state changes, including data received
                (stateFunc will be called when the transfer ends)
    - startNow  if True, the transfer is started immediately
                otherwise callFunc is called and the transaction remains Queued
                until start is called
    - dispStr   a string to display while downloading the file;
                if omitted, fromURL is displayed
    - timeLim   time limit (sec) for the total transfer; if None then no limit

    Callbacks receive one argument: this object.
    """
    # state constants
    Queued = "Queued"
    Connecting = "Connecting"
    Running = "Running"
    Aborting = "Aborting"
    Done = "Done"
    Aborted = "Aborted"
    Failed = "Failed"

    _AllStates = set((
        Queued,
        Connecting,
        Running,
        Aborting,
        Done,
        Aborted,
        Failed,
    ))
    _AbortableStates = set((Queued, Connecting, Running))
    _DoneStates = set((Done, Aborted, Failed))
    _FailedStates = set((Aborted, Failed))

    StateStrMaxLen = 0
    for stateStr in _AllStates:
        StateStrMaxLen = max(StateStrMaxLen, len(stateStr))
    del(stateStr)
    _tkApp = None

    def __init__(self,
        fromURL,
        toPath,
        isBinary = False,
        overwrite = False,
        createDir = True,
        doneFunc = None,
        stateFunc = None,
        startNow = True,
        dispStr = None,
        timeLim = None,
    ):
        if self._tkApp is None:
            self._tkApp = tkinter.Frame().tk
        self.fromURL = fromURL
        self.toPath = toPath
        self.isBinary = isBinary
        self.overwrite = bool(overwrite)
        self.createDir = createDir
        if timeLim is not None:
            self.timeLimMS = max(1, int(round(timeLim * 1000.0)))
        else:
            self.timeLimMS = 0

        if dispStr is None:
            self.dispStr = fromURL
        else:
            self.dispStr = dispStr

        self._tclFile = None
        self._tclHTTPConn = None
        self._tclCallbacks = ()
        self._tclHTTPDoneCallback = None
        self._tclHTTPProgressCallback = None
        self._lastProgReportTime = 0

        self._readBytes = 0
        self._lastReadBytes = 0
        self._didPrintBlockSize = None # for debug output only
        self._totBytes = None
        self._state = self.Queued
        self._errMsg = None

        self._createdFile = False

        self._tkApp.eval('package require http')

        opscore.RO.AddCallback.BaseMixin.__init__(self, stateFunc, callNow=False)
        self._doneCallbacks = []

        global _ExitObj
        _ExitObj.addTransfer(self)

        if doneFunc:
            self.addDoneCallback(doneFunc)

        if startNow:
            self.start()

    def addDoneCallback(self, func):
        """Add a function that will be called when the transfer completes"""
        self._doneCallbacks.append(func)

    def removeDoneCallback(self, func):
        """Remove a done callback.
        """
        self._doneCallbacks.remove(func)

    def start(self):
        """Start the download.

        If state is not Queued, raises RuntimeError
        """
        if _Debug:
            print("%s.start()" % (self,))
        if self._state != self.Queued:
            raise RuntimeError("Cannot start; state = %r not Queued" % (self._state,))

        self._setState(self.Connecting)

        try:
            # verify output file and verify/create output directory, as appropriate
            self._toPrep()

            # open output file
            if _Debug:
                print("HTTPGet: opening output file %r" % (self.toPath,))
            try:
                self._tclFile = self._tkApp.call('open', self.toPath, "w")
                self._createdFile = True
                if self.isBinary:
                    self._tkApp.call('fconfigure', self._tclFile, "-encoding", "binary", "-translation", "binary")
            except tkinter.TclError as e:
                raise RuntimeError("Could not open %r: %s" % (self.toPath, e))

            # start http transfer
            doneCallback = opscore.RO.TkUtil.TclFunc(self._httpDoneCallback, debug=_Debug)
            progressCallback = opscore.RO.TkUtil.TclFunc(self._httpProgressCallback, debug=_Debug)
            self._tclCallbacks = (doneCallback, progressCallback)
            if _Debug:
                print("HTTPGet: creating http connection")
            self._tclHTTPConn = self._tkApp.call(
                '::http::geturl', self.fromURL,
                '-channel', self._tclFile,
                '-command', doneCallback,
                '-progress', progressCallback,
                '-binary', self.isBinary,
                '-timeout', self.timeLimMS
            )
        except Exception as e:
            self._setState(self.Failed, opscore.RO.StringUtil.strFromException(e))
            return

        self._setState(self.Running)

    def abort(self):
        """Start aborting: cancel the transaction and delete the output file.
        Silently fails if the transaction has already completed
        """
        if _Debug:
            print("%s.abort()" % (self,))
        if self.isDone:
            return
        elif self._state == self.Queued:
            self._setState(self.Aborted)
            return

        if self._tclHTTPConn is None:
            sys.stderr.write("HTTPGet cannot abort: isDone false but no http connection\n")
            return

        self._setState(self.Aborting)
        self._tkApp.call("::http::reset", self._tclHTTPConn)
        if _Debug:
            print("http connection reset")

    @property
    def errMsg(self):
        """If the transfer failed, an explanation as a string, else None
        """
        return self._errMsg

    @property
    def state(self):
        """Returns the current state as a string.
        """
        return self._state

    @property
    def isAbortable(self):
        """True if the transaction can be aborted
        """
        return self._state in self._AbortableStates

    @property
    def isDone(self):
        """Return True if the transaction is finished (succeeded, aborted or failed), False otherwise.
        """
        return self._state in self._DoneStates

    @property
    def didFail(self):
        """Return True if the transaction failed or was aborted
        """
        return self._state in self._FailedStates

    @property
    def readBytes(self):
        """Bytes read so far
        """
        return self._readBytes

    @property
    def totBytes(self):
        """Total bytes in file, if known, None otherwise.

        The value is certain to be unknown until the transfer starts;
        after that it depends on whether the server sends the info.
        """
        return self._totBytes

    def _setState(self, newState, errMsg=None):
        """Set a new state and call callbacks.
        Do nothing if already done.
        errMsg is ignored unless newState is Failed.

        Raise RuntimeError if newState unknown.
        """
        if _Debug:
            print("%s._setState(newState=%s, errmsg=%r)" % (self, newState, errMsg))
        # if state is not valid, reject
        if self.isDone:
            return

        if newState not in self._AllStates:
            raise RuntimeError("Unknown state %r" % (newState,))

        self._state = newState
        if newState == self.Failed:
            self._errMsg = errMsg

        isDone = self.isDone
        if isDone:
            self._cleanup()

        self._doCallbacks()
        if isDone:
            # call done callbacks
            # use a copy in case a callback deregisters itself
            for func in self._doneCallbacks[:]:
                opscore.RO.AddCallback.safeCall2(str(self), func, self)

            # remove all callbacks
            self._removeAllCallbacks()
            self._doneCallbacks = []
            self._tclCallbacks = ()

    def _cleanup(self):
        """Clean up everything except references to callbacks.

        Warning: this is a private method: call only from _setState!

        Close the input and output files and deregister the tcl callbacks.
        If state in (Aborted, Failed), delete the output file.
        """
        if _Debug:
            print("%s._cleanup()")
        for tclFunc in self._tclCallbacks:
            if _Debug:
                print("deregister %s" % (tclFunc,))
            tclFunc.deregister()
        if self._tclHTTPConn is not None:
            self._tkApp.call("::http::cleanup", self._tclHTTPConn)
            self._tclHTTPConn = None
            if _Debug:
                print("http connection cleaned up")
        if self._tclFile:
            self._tkApp.call("close", self._tclFile)
            self._tclFile = None
            if _Debug:
                print("output file closed")

        if self._createdFile and self._state in (self.Aborted, self.Failed):
            try:
                os.remove(self.toPath)
                if _Debug:
                    print("deleted output file")
            except OSError as e:
                if _Debug:
                    print("failed to delete output file: %s" % (e,))

    def _httpDoneCallback(self, token=None):
        """Called when the http transfer is finished.
        """
        if self._tclHTTPConn is None:
            sys.stderr.write("HTTPGet warning: _httpDoneCallback called but no http connection\n")
            return

        if _Debug:
            print("%s.httpDoneCallback()" % (self,))
            print("status=%r" % (self._tkApp.call('::http::status', self._tclHTTPConn),))
            print("code=%r" % (self._tkApp.call('::http::code', self._tclHTTPConn),))
            print("ncode=%r" % (self._tkApp.call('::http::ncode', self._tclHTTPConn),))
            print("error=%r" % (self._tkApp.call('::http::error', self._tclHTTPConn),))

        httpState = self._tkApp.call('::http::status', self._tclHTTPConn)
        errMsg = None
        if httpState == "ok":
            codeNum = int(self._tkApp.call('::http::ncode', self._tclHTTPConn))
            if codeNum == 200:
                newState = self.Done
            else:
                if _Debug:
                    print("status ok but code=%s not 200" % (codeNum,))
                newState = self.Failed
                errMsg = self._tkApp.call('::http::code', self._tclHTTPConn)
        elif httpState == "eof":
            newState = self.Failed
            errMsg = "No reply from http server"
        elif httpState == "timeout":
            newState = self.Failed
            errMsg = "Timed out"
        elif httpState == "reset":
            newState = self.Aborted
        else:
            if httpState != "error":
                sys.stderr.write("HTTPGet warning: unknown httpState=%s; assuming error\n" % (httpState,))
            newState = self.Failed
            errMsg = self._tkApp.call('::http::error', self._tclHTTPConn)
            if not errMsg:
                errMsg = httpState

        self._setState(newState, errMsg)

    def _httpProgressCallback(self, token, totBytes, readBytes):
        """http callback function.
        """
        if _Debug:
            print("%s._httpProgressCallback(totBytes=%r, readBytes=%r)" % (self, totBytes, readBytes))

        self._totBytes = int(totBytes)
        self._lastReadBytes = self._readBytes
        self._readBytes = int(readBytes)
        if _Debug and not self._didPrintBlockSize and self._readBytes:
            print("%s block size=%s" % (self, self._readBytes - self._lastReadBytes))
            self._didPrintBlockSize = True

        newTime = time.time()
        if (newTime - self._lastProgReportTime) > _ProgressInterval:
            self._doCallbacks()
            self._lastProgReportTime = newTime

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.fromURL)

    def _toPrep(self):
        """Create or verify the existence of the output directory
        and check if output file already exists.

        Raise RuntimeError or IOError if anything is wrong.
        """
        if _Debug:
            print("%s._toPrep()" % (self,))
        # if output file exists and not overwrite, complain
        if not self.overwrite and os.path.exists(self.toPath):
            raise RuntimeError("toPath %r already exists" % (self.toPath,))

        # if directory does not exist, create it or fail, depending on createDir;
        # else if "directory" exists but is a file, fail
        toDir = os.path.dirname(self.toPath)
        if toDir:
            if not os.path.exists(toDir):
                # create the directory or fail, depending on createDir
                if self.createDir:
                    if _Debug:
                        print("%s._toPrep creating directory %r" % (self, toDir))
                    os.makedirs(toDir)
                else:
                    raise RuntimeError("directory %r does not exist" % (toDir,))
            elif not os.path.isdir(toDir):
                raise RuntimeError("%r is a file, not a directory" % (toDir,))

if __name__ == "__main__":
    root = tkinter.Tk()

    testURL = "http://www.astro.washington.edu/"
    outFile = "httpget_test.html"

    _Debug = False
    _DebugExit = True

    def stateCallback(httpObj):
        print("state =", httpObj.state, end=' ')
        print("read %s of %s bytes" % (httpObj.readBytes, httpObj.totBytes))
        if httpObj.isDone:
            if httpObj.errMsg:
                print("error message =", httpObj.errMsg)
            root.quit()

    httpObj = HTTPGet(
        fromURL = testURL,
        toPath = outFile,
        isBinary = False,
        stateFunc = stateCallback,
        startNow = True,
        overwrite = True,
    )

    root.mainloop()
