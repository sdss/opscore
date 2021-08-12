"""Code to run scripts that can wait for various things without messing up the main event loop
(and thus starving the rest of your program).

ScriptRunner allows your script to wait for the following:
- wait for a given time interval using: yield waitMS(...)
- run a slow computation as a background thread using waitThread
- run a command via the keyword dispatcher using waitCmd
- run multiple commands at the same time:
  - start each command with startCmd,
  - wait for one or more commands to finish using waitCmdVars
- wait for a keyword variable to be set using waitKeyVar
- wait for a sub-script by yielding it (i.e. yield subscript(...));
  the sub-script must contain a yield for this to work; if it has no yield
  then just call it directly

An example is given as the test code at the end.

History:
2004-08-12 ROwen
2004-09-10 ROwen    Modified for RO.Wdg.Constants->RO.Constants.
                    Bug fix: _WaitMS cancel used afterID instead of self.afterID.
                    Bug fix: test for resume while wait callback pending was broken,
                    leading to false "You forgot the 'yield'" errors.
2004-10-01 ROwen    Bug fix: waitKeyVar was totally broken.
2004-10-08 ROwen    Bug fix: waitThread could fail if the thread was too short.
2004-12-16 ROwen    Added a debug mode that prints diagnostics to stdout
                    and does not wait for commands or keyword variables.
2005-01-05 ROwen    showMsg: changed level to severity.
2005-06-16 ROwen    Changed default cmdStatusBar from statusBar to no bar.
2005-06-24 ROwen    Changed to use new CmdVar.lastReply instead of .replies.
2005-08-22 ROwen    Clarified _WaitCmdVars.getState() doc string.
2006-03-09 ROwen    Added scriptClass argument to ScriptRunner.
2006-03-28 ROwen    Modified to allow scripts to call subscripts.
2006-04-24 ROwen    Improved error handling in _continue.
                    Bug fixes to debug mode:
                    - waitCmd miscomputed iterID
                    - startCmd dispatched commands
2006-11-02 ROwen    Added checkFail argument to waitCmd and waitCmdVars methods.
                    waitCmd now returns the cmdVar in sr.value.
                    Added keyVars argument to startCmd and waitCmd.
2006-11-13 ROwen    Added waitUser and resumeUser methods.
2006-12-12 ROwen    Bug fix: start did not initialize waitUser instance vars.
                    Added initVars method to centralize initialization.
2008-04-21 ROwen    Improved debug mode output:
                    - showMsg prints messages
                    - _setState prints requested state
                    - _end prints the end function
                    Added debugPrint method to simplify handling unicode errors.
2008-04-24 ROwen    Bug fix: waitKeyVar referenced a nonexistent variable in non-debug mode.
2008-04-29 ROwen    Fixed reporting of exceptions that contain unicode arguments.
2008-06-26 ROwen    Improved documentation for abortCmdStr and keyVars arguments to waitCmd
2010-02-17 ROwen    Copied from RO to opscore and adapted to work with opscore.
                    Changed state constants from module constants to class constants
                    and from integers to strings.
2010-03-11 ROwen    Fixed a few instances of obsolete keyVar.get() and keyVar.isCurrent().
2010-06-28 ROwen    Made _WaitBase a modern class (thanks to pychecker).
                    Removed unused and broken internal method _waitEndFunc (thanks to pychecker).
2010-11-19 ROwen    Bug fix: FailCodes -> FailedCodes.
2011-05-04 ROwen    Bug fix: startCmd debug mode was broken; it called
                    nonexistent dispatcher.makeMsgDict instead of dispatcher.makeReply and
                    cmdVar.reply instead of cmdVar.handleReply.
2012-06-01 ROwen    Use best effort to remove callbacks during cleanup, instead of raising an
                    exception on failure.
                    Modified _WaitCmdVars to not try to register
                    callbacks on commands that are finished,
                    and to not try to remove callbacks from CmdVars that are done.
2014-03-25 ROwen    Documentation fix: keyvar.TypeDict is now keyvar.MsgCodeSeverity.
2014-06-27 ROwen    Moved the core to BaseScriptRunner.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
2015-11-05 ROwen    Added from __future__ import and removed commented-out print statements.
                    Removed initial #! line.
"""

import opscore.RO.Constants

from opscore.utility.timer import Timer

from . import keyvar
from .basescriptrunner import BaseScriptRunner, ScriptError


__all__ = ["ScriptError", "ScriptRunner"]


class ScriptRunner(BaseScriptRunner):
    """Execute a script.

    Allows waiting for various things without messing up the main event loop.
    """

    def __init__(
        self,
        name,
        runFunc=None,
        scriptClass=None,
        dispatcher=None,
        master=None,
        initFunc=None,
        endFunc=None,
        stateFunc=None,
        startNow=False,
        statusBar=None,
        cmdStatusBar=None,
        debug=False,
    ):
        """Create a ScriptRunner

        Inputs:
        - name          script name; used to report status
        - runFunc       the main script function; executed whenever
                        the start button is pressed
        - scriptClass   a class with a run method and an optional end method;
                        if specified, runFunc, initFunc and endFunc may not be specified.
        - dispatcher    keyword dispatcher (opscore.actor.CmdKeyVarDispatcher);
                        required to use wait methods and startCmd.
        - master        master Tk widget; your script may grid or pack objects into this;
                        may be None for scripts that do not have widgets.
        - initFunc      function to call ONCE when the ScriptRunner is constructed
        - endFunc       function to call when runFunc ends for any reason
                        (finishes, fails or is cancelled); used for cleanup
        - stateFunc     function to call when the ScriptRunner changes state
        - startNow      if True, starts executing the script immediately
                        instead of waiting for user to call start.
        - statusBar     status bar, if available. Used by showMsg
        - cmdStatusBar  command status bar, if available.
                        Used to show the status of executing commands.
                        May be the same as statusBar.
        - debug         if True, startCmd and wait... print diagnostic messages to stdout
                        and there is no waiting for commands or keyword variables. Thus:
                        - waitCmd and waitCmdVars return success immediately
                        - waitKeyVar returns defVal (or None if not specified) immediately

        All functions (runFunc, initFunc, endFunc and stateFunc) receive one argument: sr,
        this ScriptRunner object. The functions can pass information using sr.globals,
        an initially empty object (to which you can add instance variables and set or read them).

        Only runFunc is allowed to call sr methods that wait.
        The other functions may only run non-waiting code.

        WARNING: when runFunc calls any of the ScriptRunner methods that wait,
        IT MUST YIELD THE RESULT, as in:
            def runFunc(sr):
                ...
                yield sr.waitMS(500)
                ...
        All such methods are marked "yield required".

        If you forget to yield, your script will not wait. Your script will then halt
        with an error message when it calls the next ScriptRunner method that involves waiting
        (but by the time it gets that far it may have done some strange things).

        If your script yields when it should not, it will simply halt.
        """
        self.master = master
        self._statusBar = statusBar
        self._cmdStatusBar = cmdStatusBar

        BaseScriptRunner.__init__(
            self,
            name=name,
            runFunc=runFunc,
            scriptClass=scriptClass,
            dispatcher=dispatcher,
            initFunc=initFunc,
            endFunc=endFunc,
            stateFunc=stateFunc,
            startNow=startNow,
            debug=False,
        )

    def showMsg(self, msg, severity=opscore.RO.Constants.sevNormal):
        """Display a message--on the status bar, if available,
        else sys.stdout.

        Do not use yield because it does not wait for anything.

        Inputs:
        - msg: string to display, without a final \n
        - severity: one of RO.Constants.sevNormal (default), sevWarning or sevError
        """
        if self._statusBar:
            self._statusBar.setMsg(msg, severity)
            self.debugPrint(msg)
        else:
            print(msg)

    def startCmd(
        self,
        actor="",
        cmdStr="",
        timeLim=0,
        callFunc=None,
        callCodes=keyvar.DoneCodes,
        timeLimKeyVar=None,
        timeLimKeyInd=0,
        abortCmdStr=None,
        keyVars=None,
        checkFail=True,
    ):
        """Start a command using the same arguments as waitCmd.

        Inputs: same as waitCmd, which see.

        Returns a command variable that you can wait for using waitCmdVars.

        Do not use yield because it does not wait for anything.
        """
        cmdVar = keyvar.CmdVar(
            actor=actor,
            cmdStr=cmdStr,
            timeLim=timeLim,
            callFunc=callFunc,
            callCodes=callCodes,
            timeLimKeyVar=timeLimKeyVar,
            timeLimKeyInd=timeLimKeyInd,
            abortCmdStr=abortCmdStr,
            keyVars=keyVars,
        )

        if checkFail:
            cmdVar.addCallback(
                callFunc=self._cmdFailCallback,
                callCodes=keyvar.FailedCodes,
            )
        if self.debug:
            argList = ["actor=%r, cmdStr=%r" % (actor, cmdStr)]
            if timeLim != 0:
                argList.append("timeLim=%s" % (timeLim,))
            if callFunc is not None:
                argList.append("callFunc=%r" % (callFunc,))
            if callCodes != keyvar.DoneCodes:
                argList.append("callCodes=%r" % (callCodes,))
            if timeLimKeyVar is not None:
                argList.append("timeLimKeyVar=%r" % (timeLimKeyVar,))
            if abortCmdStr is not None:
                argList.append("abortCmdStr=%r" % (abortCmdStr,))
            if not checkFail:
                argList.append("checkFail=%r" % (checkFail,))
            self.debugPrint("startCmd(%s)" % ", ".join(argList))

            self.showMsg("%s started" % cmdStr)

            # set up command completion callback
            def endCmd(self=self, cmdVar=cmdVar):
                endReply = self.dispatcher.makeReply(
                    cmdr=None,
                    cmdID=cmdVar.cmdID,
                    actor=cmdVar.actor,
                    msgCode=":",
                )
                cmdVar.handleReply(endReply)
                self.showMsg("%s finished" % cmdVar.cmdStr)

            Timer(1.0, endCmd)

        else:
            if self._cmdStatusBar:
                self._cmdStatusBar.doCmd(cmdVar)
            else:
                self.dispatcher.executeCmd(cmdVar)

        return cmdVar

    def waitCmd(
        self,
        actor="",
        cmdStr="",
        timeLim=0,
        callFunc=None,
        callCodes=keyvar.DoneCodes,
        timeLimKeyVar=None,
        timeLimKeyInd=0,
        abortCmdStr=None,
        keyVars=None,
        checkFail=True,
    ):
        """Start a command and wait for it to finish.
        Returns the command variable (an opscore.actor.CmdVar) in sr.value.

        A yield is required.

        Inputs:
        - actor: the name of the device to command
        - cmdStr: the command (without a terminating \n)
        - timeLim: maximum time before command expires, in sec; 0 for no limit
        - callFunc: a function to call when the command changes state;
            see below for details.
        - callCodes: the message types for which to call the callback;
            a string of one or more choices; see keyvar.MsgCodeSeverity for the choices;
            useful constants include DoneTypes (command finished or failed)
            and AllTypes (all message types, thus any reply).
            Not case sensitive (the string you supply will be lowercased).
        - timeLimKeyVar: a keyword (opscore.actor.KeyVar) whose value at index timeLimKeyInd
            is used as a time within which the command must finish (in seconds).
        - timeLimKeyInd: see timeLimKeyVar; ignored if timeLimKeyVar omitted.
        - abortCmdStr: a command string that will abort the command. This string is
            sent to the actor if the command is aborted, e.g. if the script is cancelled while
            the command is executing.
        - keyVars: a sequence of 0 or more keyword variables (opscore.actor.KeyVar) to monitor.
            Any data for those variables that arrives IN RESPONSE TO THIS COMMAND is saved in the
            cmdVar returned in sr.value and can be retrieved using cmdVar.getKeyVarData or
            cmdVar.getLastKeyVarData
        - checkFail: check for command failure?
            if True (the default) command failure will halt your script

        The callback receives one argument: the command variable (an opscore.actor.CmdVar).

        Note: timeLim and timeLimKeyVar work together as follows:
        - The initial time limit for the command is timeLim
        - If timeLimKeyVar is seen before timeLim seconds have passed
          then self.maxEndTime is updated with the new value

        Also the time limit is a lower limit. The command is guaranteed to
        expire no sooner than this but it may take a second longer.
        """
        self._waitCheck(setWait=False)

        self.debugPrint("waitCmd calling startCmd")

        cmdVar = self.startCmd(
            actor=actor,
            cmdStr=cmdStr,
            timeLim=timeLim,
            callFunc=callFunc,
            callCodes=callCodes,
            timeLimKeyVar=timeLimKeyVar,
            timeLimKeyInd=timeLimKeyInd,
            abortCmdStr=abortCmdStr,
            keyVars=keyVars,
            checkFail=False,
        )

        self.waitCmdVars(cmdVar, checkFail=checkFail, retVal=cmdVar)

        self.waitCmdVars(cmdVar, checkFail=checkFail, retVal=cmdVar)
