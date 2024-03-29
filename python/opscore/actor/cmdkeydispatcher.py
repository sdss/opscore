"""Sends commands (of type opscore.actor.CmdVar) and dispatches replies
to key variables (opscore.actor.keyvar.KeyVar and subclasses).

History:
2002-11-25 ROwen    First version with history.
                    Modified TypeDict to include meaning (in addition to category).
                    Added AllTypes.
2002-12-13 ROwen    Modified to work with the MC.
2003-03-20 ROwen    Added actor to logged commands.
2003-03-26 ROwen    Prevented infinite repeat of failed refresh requests, whether
                    cmd failed or cmd succeeded but did not refresh the keyVar;
                    added ignoreFailed flag to refreshAllVar

2003-05-08 ROwen    Modified to use RO.CnvUtil.
2003-06-09 ROwen    Modified to look up commands purely by command ID, not by actor;
                    this allows us to detect some hub rejections of commands.
2003-06-11 ROwen    Modified to make keyword dispatching case-blind;
                    bug fix in dispatch; refreshKey sometimes referenced before set.
2003-06-18 ROwen    Modified to print a full traceback for unexpected errors.
2003-06-25 ROwen    Modified to handle message data as a dict.
2003-07-10 ROwen    Added makeMsgDict and used it to improve
                    logging and reporting of errors.
2003-07-16 ROwen    Modified to use KeyVar.refreshTimeLim
2003-08-13 ROwen    Moved TypeDict and AllTypes to KeyVariable to remove
                    a circular dependency.
2003-10-10 ROwen    Modified to use new RO.Comm.HubConnection.
2003-12-17 ROwen    Modified KeyVar to support the actor "keys",
                    which is used to refresh values from a cache,
                    to save querying the original actor:
                    - keywords from keys.<actor> are treated as if from <actor>
                    - uses KeyVar.refreshInfo to handle refresh commands.
2004-01-06 ROwen    Modified to use KeyVar.hasRefreshCmd and keyVar.getRefreshInfo
                    instead of keyVar.refreshInfo.
2004-02-05 ROwen    Modified logMsg to make it easier to use; \n is automatically appended
                    and typeCategory can be derived from typeChar.
2004-06-30 ROwen    Added abortCmdByID method to KeyVarDispatcher.
                    Modified for RO.Keyvariable.KeyCommand->CmdVar.
2004-07-23 ROwen    When disconnected, all pending commands time out.
                    Improved variable refresh and command variable timeout handling
                    to better allow other tasks to run: eliminated the use of
                    update_idletasks in favor of scheduling a helper function
                    that works through an iterator and reschedules itself
                    until the iterator is exhausted, then schedules the main task.
                    If a refresh command fails, the message is now printed to the log, not stderr.
                    Added _replyToCmdVar to centralize sending messages to cmdVars
                    and handling completion of commands.
                    If a command ID is already in use, the next ID is assigned;
                    this allows a command to never finish without causing other problems later.
2004-08-13 ROwen    Bug fix: abortCmdByID could report a bug when none existed.
2004-09-08 ROwen    Made NullLogger.addOutput output to stderr instead of discarding the data.
2004-10-12 ROwen    Modified to not keep refreshing keyvars when not connected.
2005-01-05 ROwen    Improved documentation for logMsg.
2005-06-03 ROwen    Bug fix: _isConnected was not getting set properly
                    if connection was omitted. It may also have not been
                    set correctly for real connections in special cases.
                    Bug fix: the test code had a typo; it now works.
2005-06-08 ROwen    Changed KeyVarDispatcher, NullLogger and StdErrLogger to new style classes.
2005-06-16 ROwen    Modified logMsg to take severity instead of typeChar.
2006-05-01 ROwen    Bug fix: if a message could not be parsed, logging the error failed
                    (due to logging in a way that involved parsing the message again).
2006-10-25 ROwen    Overhauled logging:
                    - Replaced logger argument with logFunc.
                    - Replaced setLogger method with setLogFunc
                    - Modified logMsg method to support the new log function:
                      - Removed typeCategory and msgID arguments.
                      - Added actor and cmdr arguments.
                    Modified to log commands using the command target as the actor, not TUI.
2008-04-29 ROwen    Fixed reporting of exceptions that contain unicode arguments.
2009-01-06 ROwen    Improved some doc strings.
2009-03-24 ROwen    Moved to opscore and modified to use opscore.
2009-03-25 ROwen    Fixed a bug that made KeyVar refresh inefficient (also fixed in
                    opscore.actor.CmdKeyVarDispatcher).
2009-04-03 ROwen    Split out keyvar functionality into a very simple base class.
2009-07-18 ROwen    Overhauled keyVar refresh to be more efficient and to run each
                    refresh command only once.
2009-07-20 ROwen    Modified to not log if logFunc = None; added a convenience logging function.
2009-07-21 ROwen    Added support for including commander info in command strings.
2009-07-23 ROwen    Added delayCallbacks argument and sendAllKeyVarCallbacks method.
2009-08-24 ROwen    Test for valid name at creation time.
                    Improved error reporting in makeReply.
                    If timing out a command fails, don't try to time it out again.
2009-08-25 ROwen    Bug fix: failed to dispatch replies to cmdVars with forUserCmd set, because it
                    ignored replies with a prefix on the cmdr.
                    Added replyIsMine method.
2010-02-18 ROwen    Added NullConnection to avoid using RO.Comm.HubConnect's Tk-based version;
                    it may be a bit minimal, but it's enough for the dispatcher.
                    Modified to use opscore.utility.timer.
                    Fixed the test code.
2010-05-26 ROwen    Documented includeName more thoroughly.
                    Bug fix: if includeName True and self.connection.cmdr is set
                    then replyIsMine doesn't recognize messages from makeReply.
                    Fixed by changing the commander for makeReply
                    from <self.connection.cmdr> to <self.connection.cmdr>.<self.connection.cmdr>
                    Bug fix: if includeName True and self.connection.cmdr != self.name then
                    replyIsMine doesn't recognize replies to executeCmd. Fixed by changing
                    executeCmd to use commander name <self.connection.cmdr>.<self.connection.cmdr>
                    instead of <self.name>.<self.name>.
2010-06-28 ROwen    Bug fix: sendAllKeyVarCallbacks argument includeNotCurrent
                    was ignored (thanks to pychecker).
                    Removed one of a duplicate import (thanks to pychecker).
2010-07-21 ROwen    Changed refreshAllVar to handle setting keyVars not current
                    differently; instead of implicitly basing it on the connection state, it now is
                    based on a new argument.
                    Added readUnixTime field.
                    Bug fix: command timeouts were broken.
2010-11-18 ROwen    Moved setLogFunc, logMsg, logReply methods to KeyDispatcher.
                    Moved name field to KeyDispatcher.
                    Moved logToStdOut function to KeyDispatcher.
2011-02-02 ROwen    Moved logReplyStr to KeyDispatcher.
                    Modified to let KeyDispatcher log replies.
2011-05-04 ROwen    Made makeReply a bit more robust by detecting cmdID == None and changing it to 0.
2011-06-13 ROwen    Added static method getMaxUserCmdID.
                    Changed to log cmdID when issuing a command.
2011-07-28 ROwen    Modified to not log commands as they are sent; use cmds actor data instead.
2012-07-24 ROwen    Added _formatCmdStr and _formatReplyHeader to simplify subclassing.
                    Improved error handling in makeReply.
                    Removed some duplication from KeyVarDispatcher.
2012-08-02 ROwen    Updated for RO 3.0.
2012-09-21 ROwen    Added disconnect method.
                    Removed __main__ example code; use the unit test instead.
2013-08-30 ROwen    Fixed a bug that caused _sendNextRefreshCmd to fail if a
                    refresh variable was removed while refreshing. Always calls
                    refreshCmdDictChanged if refreshCmdDict changed and this restarts the refresh
                    process if connected.
2014-06-23 ROwen    Added callKeyVarsOnDisconnect constructor argument.
                    This allows STUI to show pink fields on disconnect.
2015-11-03 ROwen    Replace "== None" with "is None" and "!= None" with "is not
                    None" to modernize the code.
2015-11-05 ROwen    Added from __future__ import and removed commented-out print statements.
                    Removed initial #! line.
"""

import sys
import time
import traceback

import opscore.RO.Alg
import opscore.RO.Constants
from opscore.RO.StringUtil import quoteStr, strFromException
from opscore.utility.timer import Timer

from .keydispatcher import KeyVarDispatcher
from .keyvar import CmdVar


__all__ = ["CmdKeyVarDispatcher"]


# intervals (in milliseconds) for various background tasks
_RefreshInterval = 1.0  # time interval between variable refresh checks (sec)
_TimeoutInterval = 1.3  # time interval between command timeout checks (sec)

_CmdNumWrap = 1000  # value at which user command ID numbers wrap

_RefreshTimeLim = 20  # time limit for refresh commands (sec)


class CmdKeyVarDispatcher(KeyVarDispatcher):
    """Parse replies and sets KeyVars. Also manage CmdVars and their replies.

    Fields:
    - readUnixTime: unix time at which last message received from connection;
      0 if no message ever received.
    """

    def __init__(
        self,
        name="CmdKeyVarDispatcher",
        connection=None,
        logFunc=None,
        includeName=True,
        delayCallbacks=False,
        callKeyVarsOnDisconnect=False,
    ):
        """Create a new CmdKeyVarDispatcher

        Inputs:
        - name: dispatcher name; must be a valid actor name (_ is OK; avoid other
                punctuation and whitespace).
            Used as the default actor for logMsg.
            If includeName is True, then sent as a prefix to all commands sent to the hub.
        - connection: an RO.Comm.HubConnection object or similar;
          if omitted, a NullConnection is used, which is useful for testing.
        - logFunc: a function that logs a message. Argument list must be:
            (msgStr, severity, actor, cmdr)
            where the first argument is positional and the others are by name
            and severity is an RO.Constants.sevX constant
            If None then nothing is logged.
        - includeName: if True then the commander name is prepended to all commands
            sent to the hub.
            The commander name is <self.connection.cmdr>.<self.connection.cmdr>
            unless cmdVar.forUserCmd is present, in which case the prefix is
            <cmdVar.forUserCmd.cmdr>.<self.connection.cmdr>.
            This option is used for "internal" actors that are not authenticated;
            such actors must include the commander name in commands
            (whereas authenticated actors such as TUI must (should?) not).
            Internal actors have a self.connection.cmd that does not contain a "."
            (and so is not a proper commander name, alas). Hence the doubled name.
        - delayCallbacks: if True then upon initial connection no KeyVar callbacks are made
            until all refresh commands have completed (at which point callbacks are made
            for each keyVar that has been set). Thus the set of keyVars will be maximally
            self-consistent, but it may take awhile after connecting before callbacks begin.
        - callKeyVarsOnDisconnect: if True then keyVars callbacks are called on disconnection
            (STUI uses this to show pink fields on disconnection).
            If False then keyVar callbacks are not called and all timers are cancelled.

        Raises ValueError if name cannot be used as an actor name
        """
        KeyVarDispatcher.__init__(self, name=name, logFunc=logFunc)

        self.includeName = bool(includeName)
        self.delayCallbacks = bool(delayCallbacks)
        self.callKeyVarsOnDisconnect = bool(callKeyVarsOnDisconnect)
        self.readUnixTime = 0

        self._isConnected = False

        # cmdDict keys are command ID and values are KeyCommands
        self.cmdDict = dict()

        # refreshCmdDict contains information about keyVar refresh commands:
        # key is: actor, refresh command, e.g. as returned by keyVar.refreshInfo
        # refresh command: set of keyVars that use this command
        self.refreshCmdDict = {}

        # list of refresh commands that have been executed; used to support delayCallbacks
        self._runningRefreshCmdSet = set()
        self._allRefreshCmdsSent = False
        self._enableCallbacks = not self.delayCallbacks

        # timers for various scheduled callbacks
        self._checkCmdTimer = Timer()
        self._checkRemCmdTimer = Timer()
        self._refreshAllTimer = Timer()
        self._refreshNextTimer = Timer()

        if connection:
            self.connection = connection
            self.connection.addReadCallback(self._readCallback)
            self.connection.addStateCallback(self.updConnState)
        else:
            self.connection = NullConnection()
        self._isConnected = self.connection.isConnected
        self.userCmdIDGen = opscore.RO.Alg.IDGen(1, _CmdNumWrap)
        self.refreshCmdIDGen = opscore.RO.Alg.IDGen(_CmdNumWrap + 1, 2 * _CmdNumWrap)

        try:
            self.makeReply(dataStr="TestName")
        except Exception as e:
            raise ValueError(
                "Invalid name=%s cannot be parsed as an actor name; error: %s"
                % (name, strFromException(e))
            )

        # start background tasks (refresh variables and check command timeout)
        self.refreshAllVar()
        self.checkCmdTimeouts()

    def abortCmdByID(self, cmdID):
        """Abort the command with the specified ID.

        Issue the command specified by cmdVar.abortCmdStr, if present.
        Report the command as failed.

        Has no effect if the command was never dispatched (cmdID is None)
        or has already finished.
        """
        if cmdID is None:
            return

        cmdVar = self.cmdDict.get(cmdID)
        if not cmdVar:
            return

        # check isDone
        if cmdVar.isDone:
            return

        # if relevant, issue abort command, with no callbacks
        if cmdVar.abortCmdStr and self._isConnected:
            abortCmd = CmdVar(
                cmdStr=cmdVar.abortCmdStr,
                actor=cmdVar.actor,
            )
            self.executeCmd(abortCmd)

        # report command as aborted
        errReply = self.makeReply(
            cmdID=cmdVar.cmdID,
            dataStr="Aborted; Actor=%r; Cmd=%r" % (cmdVar.actor, cmdVar.cmdStr),
        )
        self._replyToCmdVar(cmdVar, errReply)

    def addKeyVar(self, keyVar):
        """Add a keyword variable (opscore.actor.keyvar.KeyVar) to the collection.

        Inputs:
        - keyVar: the keyword variable (opscore.actor.keyvar.KeyVar)
        """
        KeyVarDispatcher.addKeyVar(self, keyVar)
        if keyVar.hasRefreshCmd:
            refreshInfo = keyVar.refreshInfo
            keyVarSet = self.refreshCmdDict.get(refreshInfo)
            if keyVarSet:
                keyVarSet.add(keyVar)
            else:
                self.refreshCmdDict[refreshInfo] = set((keyVar,))
            self.refreshCmdDictChanged()

    def checkCmdTimeouts(self):
        """Check all pending commands for timeouts"""

        # cancel pending update, if any
        self._checkCmdTimer.cancel()
        self._checkRemCmdTimer.cancel()

        # iterate over a copy of the values
        # so we can modify the dictionary while checking command timeouts
        cmdVarIter = iter(list(self.cmdDict.values()))
        self._checkRemCmdTimeouts(cmdVarIter)

    def disconnect(self):
        """Deprecated (use self.connection.disconnect()"""
        self.connection.disconnect()

    def dispatchReply(self, reply):
        """Log the reply, set KeyVars and CmdVars.

        reply is a parsed Reply object (opscore.protocols.messages.Reply)
        """
        # log message and set KeyVars
        KeyVarDispatcher.dispatchReply(self, reply, doCallbacks=self._enableCallbacks)

        # if you are the commander for this message, execute the command callback (if any)
        if self.replyIsMine(reply):
            # get the command for this command id, if any
            cmdVar = self.cmdDict.get(reply.header.commandId, None)
            if cmdVar is not None:
                # send reply but don't log (that's already been done)
                self._replyToCmdVar(cmdVar, reply, doLog=False)

    def executeCmd(self, cmdVar):
        """Execute a command (of type opscore.actor.CmdVar).

        Performs the following tasks:
        - Sets the command ID number
        - Sets the start time
        - Puts the command on the keyword dispatcher queue
        - Sends the command to the server

        Inputs:
        - cmdVar: the command, of class opscore.actor.CmdVar

        Note:
        - Always increments cmdID because every command must have a unique command ID
          (even commands that go to different actors); this simplifies the
          dispatcher code and also makes the hub's life easier
          (since it can report certain kinds of failures using actor=hub).
        """
        if not self._isConnected:
            errReply = self.makeReply(
                dataStr='Failed; Actor=%r; Cmd=%r; Text="not connected"'
                % (cmdVar.actor, cmdVar.cmdStr),
            )
            self._replyToCmdVar(cmdVar, errReply)
            return

        while True:
            if cmdVar.isRefresh:
                cmdID = next(self.refreshCmdIDGen)
            else:
                cmdID = next(self.userCmdIDGen)
            if cmdID not in self.cmdDict:
                break
        self.cmdDict[cmdID] = cmdVar
        cmdVar._setStartInfo(self, cmdID)

        try:
            fullCmdStr = self._formatCmdStr(cmdVar)
            self.connection.writeLine(fullCmdStr)
        except Exception as e:
            errReply = self.makeReply(
                cmdID=cmdVar.cmdID,
                dataStr="WriteFailed; Actor=%r; Cmd=%r; Text=%r"
                % (cmdVar.actor, cmdVar.cmdStr, strFromException(e)),
            )
            self._replyToCmdVar(cmdVar, errReply)

    @staticmethod
    def getMaxUserCmdID():
        """Return the maximum user command ID number.

        User command ID numbers range from 1 through getMaxUserCmdID()
        Refresh command ID numbers range from getMaxUserCmdID() + 1 through 2 * getMaxUserCmdID()
        """
        return _CmdNumWrap

    def makeReply(
        self,
        cmdr=None,
        cmdID=0,
        actor=None,
        msgCode="F",
        dataStr="",
    ):
        """Generate a Reply object (opscore.protocols.messages.Reply) based on the supplied data.

        Useful for reporting internal errors.
        """
        try:
            headerStr = self._formatReplyHeader(
                cmdr=cmdr, cmdID=cmdID, actor=actor, msgCode=msgCode
            )
            msgStr = " ".join((headerStr, dataStr))

            try:
                reply = self.parser.parse(msgStr)
            except Exception:
                sys.stderr.write(
                    "%s.makeReply could not parse msgStr=%r; trying a simplified msgStr\n"
                    % (self, msgStr)
                )
                traceback.print_exc(file=sys.stderr)
                simplerDataStr = "Text=%s" % (quoteStr(dataStr),)
                simplerMsgStr = " ".join((headerStr, simplerDataStr))
                try:
                    reply = self.parser.parse(simplerMsgStr)
                except Exception:
                    sys.stderr.write(
                        "%s.makeReply could not parse simplified msgStr=%r; giving up\n"
                        % (self, simplerMsgStr)
                    )
                    raise
            return reply

        except Exception:
            sys.stderr.write(
                "%s.makeReply(cmdr=%r, cmdID=%r, actor=%r, msgCode=%r, dataStr=%r) "
                "could not make message string:\n"
                % (self, cmdr, cmdID, actor, msgCode, dataStr)
            )
            traceback.print_exc(file=sys.stderr)
            logMsgStr = (
                "Could not create message from dataStr=%r; see log for details"
                % (dataStr,)
            )
            self.logMsg(msgStr=logMsgStr, severity=opscore.RO.Constants.sevError)
            raise

    def refreshAllVar(self, resetAll=True):
        """Issue all keyVar refresh commands after optionally setting them all to notCurrent.

        Inputs:
        - resetAll: reset all keyword variables to notCurrent
        """
        # cancel pending update, if any
        self._refreshAllTimer.cancel()
        self._refreshNextTimer.cancel()
        self._enableCallbacks = not self.delayCallbacks
        self._runningRefreshCmdSet = set()
        self._allRefreshCmdsSent = False

        if resetAll:
            for keyVarList in list(self.keyVarListDict.values()):
                for keyVar in keyVarList:
                    keyVar.setNotCurrent()

        self._sendNextRefreshCmd()

    def refreshCmdDictChanged(self):
        """Call if you change refrechCmdDict"""
        if self._isConnected:
            self._refreshAllTimer.start(0, self.refreshAllVar, resetAll=False)
        else:
            self._refreshAllTimer.cancel()

    def removeKeyVar(self, keyVar):
        """Remove the specified keyword variable, returning the KeyVar if removed, else None

        See also addKeyVar.

        Inputs:
        - keyVar: the keyword variable to remove

        Returns:
        - the removed keyVar, if present, None otherwise.
        """
        keyVar = KeyVarDispatcher.removeKeyVar(self, keyVar)

        keyVarSet = self.refreshCmdDict.get(keyVar.refreshInfo)
        if keyVarSet and keyVar in keyVarSet:
            keyVarSet.remove(keyVar)
            if not keyVarSet:
                # that was the only keyVar using this refresh command
                del self.refreshCmdDict[keyVar.refreshInfo]
            self.refreshCmdDictChanged()
        return keyVar

    def replyIsMine(self, reply):
        """Return True if I am the commander for this message."""
        return reply.header.cmdrName.endswith(
            self.connection.cmdr
        ) and reply.header.cmdrName[
            -len(self.connection.cmdr) - 1 : -len(self.connection.cmdr)
        ] in (
            "",
            ".",
        )

    def sendAllKeyVarCallbacks(self, includeNotCurrent=False):
        """Send all keyVar callbacks.

        Inputs:
        - includeNotCurrent: issue callbacks for keyVars that are not current?
        """
        keyVarListIter = iter(self.keyVarListDict.values())
        self._nextKeyVarCallback(keyVarListIter, includeNotCurrent=includeNotCurrent)

    def updConnState(self, conn):
        """If connection state changes, update refresh variables."""
        wasConnected = self._isConnected
        self._isConnected = conn.isConnected
        if wasConnected != self._isConnected:
            if self._isConnected or self.callKeyVarsOnDisconnect:
                self._refreshAllTimer.start(0, self.refreshAllVar)
            else:
                self._cancelTimers()

    def _cancelTimers(self):
        """Cancel all timers"""
        self._checkCmdTimer.cancel()
        self._checkRemCmdTimer.cancel()
        self._refreshAllTimer.cancel()
        self._refreshNextTimer.cancel()

    def _checkRemCmdTimeouts(self, cmdVarIter):
        """Helper function for checkCmdTimeouts.
        Check the remaining command variables in cmdVarIter.
        If a timeout is found, time out that one command
        and schedule myself to run again shortly
        (thereby giving other events a chance to run).

        Once the iterator is exhausted, schedule
        my parent function checkCmdTimeouts to run
        at the usual interval later.
        """
        try:
            for cmdVar in cmdVarIter:
                errReply = None
                currTime = time.time()
                # if cmd still exits (i.e. has not been deleted for other reasons)
                # check if it has a time limit and has timed out
                if cmdVar.cmdID not in self.cmdDict:
                    continue
                try:
                    if not self._isConnected:
                        errReply = self.makeReply(
                            cmdID=cmdVar.cmdID,
                            dataStr='Aborted; Actor=%r; Cmd=%r; Text="disconnected"'
                            % (cmdVar.actor, cmdVar.cmdStr),
                        )
                        # no connection, so cannot send abort command
                        cmdVar.abortCmdStr = ""
                    elif cmdVar.maxEndTime and (cmdVar.maxEndTime < currTime):
                        # time out this command
                        errReply = self.makeReply(
                            cmdID=cmdVar.cmdID,
                            dataStr="Timeout; Actor=%r; Cmd=%s"
                            % (cmdVar.actor, quoteStr(cmdVar.cmdStr)),
                        )
                    if errReply:
                        self._replyToCmdVar(cmdVar, errReply)

                        # schedule myself to run again shortly
                        # (thereby giving other time to other events)
                        # continuing where I left off
                        self._checkRemCmdTimer.start(
                            0, self._checkRemCmdTimeouts, cmdVarIter
                        )
                except Exception:
                    sys.stderr.write(
                        "%s._checkRemCmdTimeouts failed to timeout command %s\n"
                        % (self, cmdVar)
                    )
                    traceback.print_exc(file=sys.stderr)
                    cmdVar.maxEndTime = None
        except Exception:
            # this is very, very unlikely
            sys.stderr.write("%s._checkRemCmdTimeouts failed\n" % (self,))
            traceback.print_exc(file=sys.stderr)

        # finished checking all commands in the current cmdVarIter;
        # schedule a new checkCmdTimeouts at the usual interval
        self._checkCmdTimer.start(_TimeoutInterval, self.checkCmdTimeouts)

    def _formatCmdStr(self, cmdVar):
        """Format a command. The cmdVar must have cmdID set (you must have called cmdVar._setStartInfo)."""
        if self.includeName:
            # internal actor; must specify the commander
            if cmdVar.forUserCmd:
                cmdrStr = "%s.%s " % (cmdVar.forUserCmd.cmdr, self.connection.cmdr)
            else:
                cmdrStr = "%s.%s " % (self.connection.cmdr, self.connection.cmdr)
        else:
            # external actor; do not specify the commander
            cmdrStr = ""
        return "%s%d %s %s" % (cmdrStr, cmdVar.cmdID, cmdVar.actor, cmdVar.cmdStr)

    def _formatReplyHeader(
        self,
        cmdr=None,
        cmdID=0,
        actor=None,
        msgCode="F",
    ):
        """Generate header for Reply object"""
        if cmdr is None:
            if self.includeName:
                cmdr = "%s.%s" % (self.connection.cmdr, self.connection.cmdr)
            else:
                cmdr = self.connection.cmdr or "me.me"
        if actor is None:
            actor = self.name
        if cmdID is None:
            cmdID = 0

        return "%s %d %s %s" % (cmdr, cmdID, actor, msgCode)

    def _nextKeyVarCallback(self, keyVarListIter, includeNotCurrent=True):
        """Issue next keyVar callback

        Input:
        - keyVarListIter: iterator over values in self.keyVarListDict
        """
        try:
            keyVarList = next(keyVarListIter)
        except StopIteration:
            return
        for keyVar in keyVarList:
            if includeNotCurrent or keyVar.isCurrent:
                keyVar.doCallbacks()
        Timer(0.001, self._nextKeyVarCallback, keyVarListIter, includeNotCurrent)

    def _readCallback(self, sock, data):
        self.readUnixTime = time.time()
        self.dispatchReplyStr(data)

    def _refreshCmdCallback(self, refreshCmd):
        """Refresh command callback; complain if command failed or some keyVars not updated"""
        if not refreshCmd.isDone:
            return
        try:
            self._runningRefreshCmdSet.remove(refreshCmd)
        except Exception:
            sys.stderr.write(
                "could not find refresh command %s to remove it\n" % (refreshCmd,)
            )
        refreshInfo = (refreshCmd.actor, refreshCmd.cmdStr)
        keyVarSet = self.refreshCmdDict.get(refreshInfo, set())
        if refreshCmd.didFail:
            keyVarNamesStr = ", ".join(sorted([kv.name for kv in keyVarSet]))
            errMsg = "Refresh command %s %s failed; keyVars not refreshed: %s" % (
                refreshCmd.actor,
                refreshCmd.cmdStr,
                keyVarNamesStr,
            )
            self.logMsg(errMsg, severity=opscore.RO.Constants.sevWarning)
        elif keyVarSet:
            aKeyVar = next(iter(keyVarSet))
            actor = aKeyVar.actor
            missingKeyVarNamesStr = ", ".join(
                sorted([kv.name for kv in keyVarSet if not kv.isCurrent])
            )
            if missingKeyVarNamesStr:
                errMsg = "No refresh data for %s keyVars: %s" % (
                    actor,
                    missingKeyVarNamesStr,
                )
                self.logMsg(errMsg, severity=opscore.RO.Constants.sevWarning)
        else:
            # all of the keyVars were removed or there is a bug
            errMsg = (
                "Warning: refresh command %s %s finished but no keyVars found\n"
                % refreshInfo
            )
            self.logMsg(errMsg, severity=opscore.RO.Constants.sevWarning)

        # handle delayCallbacks:
        if (
            not self.delayCallbacks
            or not self._allRefreshCmdsSent
            or self._runningRefreshCmdSet
        ):
            return
        self._enableCallbacks = True
        self.sendAllKeyVarCallbacks(includeNotCurrent=False)

    def _replyToCmdVar(self, cmdVar, reply, doLog=True):
        """Send a message to a command variable and optionally log it.

        If the command is done, delete it from the command dict.
        If the command is a refresh command and is done,
        update the refresh command dict accordingly.

        Inputs:
        - cmdVar    command variable (opscore.actor.CmdVar)
        - reply     Reply object (opscore.protocols.messages.Reply) to send
        """
        if doLog:
            self.logReply(reply)
        cmdVar.handleReply(reply)
        if cmdVar.isDone and cmdVar.cmdID is not None:
            try:
                del self.cmdDict[cmdVar.cmdID]
            except KeyError:
                sys.stderr.write(
                    "CmdKeyVarDispatcher bug: tried to delete cmd %s=%s but it was missing\n"
                    % (cmdVar.cmdID, cmdVar)
                )

    def _sendNextRefreshCmd(self, refreshCmdItemIter=None):
        """Helper function for refreshAllVar.

        Plow through a keyVarList iterator until a refresh command is found that is wanted, issue it,
        then schedule a call for myself for ASAP (giving other events a chance to execute first).

        Inputs:
        - refreshCmdItemIter: iterator over items in refreshCmdDict;
          if None then set to self.refreshCmdDict.iteritems()
        """
        if not self._isConnected:
            return

        if refreshCmdItemIter is None:
            refreshCmdItemIter = iter(self.refreshCmdDict.items())

        try:
            refreshCmdInfo, keyVarSet = next(refreshCmdItemIter)
        except StopIteration:
            self._allRefreshCmdsSent = True
            return
        actor, cmdStr = refreshCmdInfo
        try:
            cmdVar = CmdVar(
                actor=actor,
                cmdStr=cmdStr,
                timeLim=_RefreshTimeLim,
                callFunc=self._refreshCmdCallback,
                isRefresh=True,
            )
            self._runningRefreshCmdSet.add(cmdVar)
            self.executeCmd(cmdVar)
        except Exception:
            sys.stderr.write(
                "%s._sendNextRefreshCmd: refresh command %s failed:\n"
                % (
                    self,
                    cmdVar,
                )
            )
            traceback.print_exc(file=sys.stderr)
        self._refreshNextTimer.start(0, self._sendNextRefreshCmd, refreshCmdItemIter)

    def __str__(self):
        return self.__class__.__name__


class NullConnection(object):
    """Null connection for test purposes.
    Always acts as if it is connected (so one can write data),
    but prohibits explicit connection (maybe not necessary,
    but done to make it clear to users that it is a fake).

    cmdr = "me.me"
    """

    def __init__(self):
        self.desUsername = "me"
        self.cmdr = "me.me"

    def connect(self):
        raise RuntimeError("NullConnection is always connected")

    def disconnect(self):
        raise RuntimeError("NullConnection cannot disconnect")

    def isConnected(self):
        return True

    def getCmdr(self):
        return self.cmdr

    def getProgID(self):
        cmdr = self.getCmdr()
        return cmdr and cmdr.split(".")[0]

    def writeLine(self, str):
        sys.stdout.write("Null connection asked to write: %s\n" % (str,))
