"""Code to run scripts that can wait for various things without messing up the main event loop
(and thus starving the rest of your program).

BaseScriptRunner allows your script to wait for the following:
- wait for a given time interval using waitMS
- run a slow computation as a background thread using waitThread
- multiple commands to finish (use a subclass to start the commands) using waitCmdVars
- wait for a keyword variable to be set using waitKeyVar
- wait for a sub-script by yielding it (i.e. yield subscript(...));
  the sub-script must contain a yield for this to work; if it has no yield then
  just call it directly

An example is given as the test code at the end.

Code comments:
- Wait functions use a class to do all the work. This standardizes
  some tricky internals (such as registering and deregistering
  cancel functions) and allows the class to easily keep track
  of private internal data.
- The wait class is created but is not explicitly kept around.
  Why doesn't it immediately vanish? Because the wait class registers a method as a
  completion callback.
  As long as somebody has a pointer to that method then the instance is kept alive.
- waitThread originally relied on generating an event when the script ended.
  Unfortunately, that proved unreliable; if the thread was very short,
  it could actually start trying to continue before the current
  iteration of the generator was finished! I'm surprised that was
  possible (I expected the event to get queued), but in any case
  it was bad news. The current scheme is a kludge -- poll the thread.
  I hope I can figure out something better.

History:
2014-06-27 ROwen    Extracted most of ScriptRunner into BaseScriptRunner,
                    to make it easier to generate that commands an actor (instead of the hub).
2014-07-01 ROwen    Added waitSec method.
2015-05-08 ROwen    Added waitPause method.
2015-11-03 ROwen    Replace "== None" with "is None" and "!= None" with "is not None"
                    to modernize the code.
2015-11-05 ROwen    Added from __future__ import and removed commented-out print statements.
                    Removed initial #! line.
"""
import sys
import queue
import threading
import traceback

import opscore.RO.AddCallback
import opscore.RO.Constants
import opscore.RO.SeqUtil
import opscore.RO.StringUtil
from opscore.utility.timer import Timer

try:
    import Queue as queue
except ImportError:
    import queue


__all__ = ["ScriptError", "BaseScriptRunner"]

_DebugState = False

# internal constants
_PollDelaySec = 0.1  # polling interval for threads (sec)

# a list of possible keywords that hold reasons for a command failure
# in the order in which they are checked
_ErrKeys = ("text",)

_MSPerSec = 1000


class _Blank(object):
    def __init__(self):
        object.__init__(self)


class ScriptError(RuntimeError):
    """Use to raise exceptions in your script
    when you don't want a traceback.
    """

    pass


class BaseScriptRunner(opscore.RO.AddCallback.BaseMixin):
    """Execute a script.

    Allows waiting for various things without messing up the main event loop.
    """

    # state constants
    Ready = "Ready"
    Paused = "Paused"
    Running = "Running"
    Done = "Done"
    Cancelled = "Cancelled"
    Failed = "Failed"
    _AllStates = (Ready, Paused, Running, Done, Cancelled, Failed)
    _RunningStates = (Paused, Running)
    _DoneStates = (Done, Cancelled, Failed)
    _FailedStates = (Cancelled, Failed)

    def __init__(
        self,
        name,
        runFunc=None,
        scriptClass=None,
        dispatcher=None,
        initFunc=None,
        endFunc=None,
        stateFunc=None,
        startNow=False,
        debug=False,
    ):
        """Create a BaseScriptRunner

        Inputs:
        - name          script name; used to report status
        - runFunc       the main script function; executed whenever
                        the start button is pressed
        - scriptClass   a class with a run method and an optional end method;
                        if specified, runFunc, initFunc and endFunc may not be specified.
        - dispatcher    keyword dispatcher (opscore.actor.CmdKeyVarDispatcher);
                        required to use wait methods and startCmd.
        - initFunc      function to call ONCE when the BaseScriptRunner is constructed
        - endFunc       function to call when runFunc ends for any reason
                        (finishes, fails or is cancelled); used for cleanup
        - stateFunc     function to call when the BaseScriptRunner changes state
        - startNow      if True, starts executing the script immediately
                        instead of waiting for user to call start.
        - debug         if True, startCmd and wait... print diagnostic messages to stdout
                        and there is no waiting for commands or keyword variables. Thus:
                        - waitCmdVars returns success immediately
                        - waitKeyVar returns defVal (or None if not specified) immediately

        All functions (runFunc, initFunc, endFunc and stateFunc) receive one argument: sr,
        this BaseScriptRunner object. The functions can pass information using sr.globals,
        an initially empty object (to which you can add instance variables and set or read them).

        Only runFunc is allowed to call sr methods that wait.
        The other functions may only run non-waiting code.

        WARNING: when runFunc calls any of the BaseScriptRunner methods that wait,
        IT MUST YIELD THE RESULT, as in:
            def runFunc(sr):
                ...
                yield sr.waitMS(500)
                ...
        All such methods are marked "yield required".

        If you forget to yield, your script will not wait. Your script will then halt
        with an error message when it calls the next BaseScriptRunner method that involves waiting
        (but by the time it gets that far it may have done some strange things).

        If your script yields when it should not, it will simply halt.
        """
        if scriptClass:
            if runFunc or initFunc or endFunc:
                raise ValueError(
                    "Cannot specify runFunc, initFunc or endFunc with scriptClass"
                )
            if not hasattr(scriptClass, "run"):
                raise ValueError("scriptClass=%r has no run method" % scriptClass)
        elif runFunc is None:
            raise ValueError("Must specify runFunc or scriptClass")
        elif not callable(runFunc):
            raise ValueError("runFunc=%r not callable" % (runFunc,))

        self.runFunc = runFunc
        self.name = name
        self.dispatcher = dispatcher
        self.initFunc = initFunc
        self.endFunc = endFunc
        self.debug = bool(debug)

        # useful constant for script writers
        self.ScriptError = ScriptError

        opscore.RO.AddCallback.BaseMixin.__init__(self)

        self.globals = _Blank()

        self.initVars()

        if stateFunc:
            self.addCallback(stateFunc)

        # initialize, as appropriate
        if scriptClass:
            self.scriptObj = scriptClass(self)
            self.runFunc = self.scriptObj.run
            self.endFunc = getattr(self.scriptObj, "end", None)
        elif self.initFunc:
            res = self.initFunc(self)
            if hasattr(res, "next"):
                raise RuntimeError("init function tried to wait")

        if startNow:
            self.start()

    # methods for starting, pausing and aborting script
    # and for getting the current state of execution.

    def cancel(self):
        """Cancel the script.

        The script will not actually halt until the next
        waitXXX or doXXX method is called, but this should
        occur quickly.
        """
        if self.isExecuting:
            self._setState(self.Cancelled, "")

    def debugPrint(self, msgStr):
        """Print the message to stdout if in debug mode.
        Handles unicode as best it can.
        """
        if not self.debug:
            return
        try:
            print(msgStr)
        except (TypeError, ValueError):
            print(repr(msgStr))

    @property
    def fullState(self):
        """Returns the current state as a tuple:
        - state: a string value; should match a named state constant
        - reason: the reason for the state ("" if none)
        """
        state, reason = self._state, self._reason
        return (state, reason)

    @property
    def state(self):
        """Return the current state as a string.
        See the state constants defined in this class.
        See also fullState.
        """
        return self._state

    def initVars(self):
        """Initialize variables.
        Call at construction and when starting a new run.
        """
        self._cancelFuncs = []
        self._endingState = None
        self._state = self.Ready
        self._reason = ""
        self._iterID = [0]
        self._iterStack = []
        self._waiting = False  # set when waiting for a callback
        self._userWaitID = None
        self.value = None

    @property
    def didFail(self):
        """Return True if script aborted or failed.

        Note: may not be fully ended (there may be cleanup to do and callbacks to call).
        """
        return self._endingState in self._FailedStates

    @property
    def isDone(self):
        """Return True if script is finished, successfully or otherwise.

        Note: may not be fully ended (there may be cleanup to do and callbacks to call).
        """
        return self._state in self._DoneStates

    @property
    def isExecuting(self):
        """Returns True if script is running or paused."""
        return self._state in self._RunningStates

    @property
    def isPaused(self):
        """Return True if script is paused."""
        return self._state == self.Paused

    def pause(self):
        """Pause execution.

        Note that the script must be waiting for something when the pause occurs
        (because that's when the GUI will be freed up to get the request to pause).
        If the thing being waited for fails then the script will fail (thus going
        from Paused to Failed with no user interation).

        Has no effect unless the script is running.
        """
        self._printState("pause")
        if not self._state == self.Running:
            return

        self._setState(self.Paused)

    def resume(self):
        """Resume execution after a pause.

        Has no effect if not paused.
        """
        self._printState("resume")
        if not self._state == self.Paused:
            return

        self._setState(self.Running)
        if not self._waiting:
            self._continue(self._iterID, val=self.value)

    def resumeUser(self):
        """Resume execution from waitUser"""
        if self._userWaitID is None:
            raise RuntimeError("Not in user wait mode")

        iterID = self._userWaitID
        self._userWaitID = None
        self._continue(iterID)

    def start(self):
        """Start executing runFunc.

        If already running, raises RuntimeError
        """
        if self.isExecuting:
            raise RuntimeError("already executing")

        self.initVars()

        self._iterID = [0]
        self._iterStack = []
        self._setState(self.Running)
        self._continue(self._iterID)

    # methods for use in scripts
    # with few exceptions all wait for something
    # and thus require a "yield"

    def getKeyVar(
        self,
        keyVar,
        ind=0,
        defVal=Exception,
    ):
        """Return the current value of keyVar.
        See also waitKeyVar, which can wait for a value.

        Note: if you want to be sure the keyword data was in response to a particular command
        that you sent, then use the keyVars argument of startCmd or waitCmd instead.

        Do not use yield because it does not wait for anything.

        Inputs:
        - keyVar    keyword variable
        - ind       which value is wanted? (None for all values)
        - defVal    value to return if value cannot be determined
                    (if omitted, the script halts)
        """
        if self.debug:
            argList = ["keyVar=%s" % (keyVar,)]
            if ind != 0:
                argList.append("ind=%s" % (ind,))
            if defVal != Exception:
                argList.append("defVal=%r" % (defVal,))
            if defVal == Exception:
                defVal = None

        if keyVar.isCurrent:
            if ind is not None:
                retVal = keyVar[ind]
            else:
                retVal = keyVar.valueList
        else:
            if defVal == Exception:
                raise ScriptError("Value of %s invalid" % (keyVar,))
            else:
                retVal = defVal

        if self.debug:  # else argList does not exist
            self.debugPrint(
                "getKeyVar(%s); returning %r" % (", ".join(argList), retVal)
            )
        return retVal

    def waitCmdVars(self, cmdVars, checkFail=True, retVal=None):
        """Wait for one or more command variables to finish.
        Command variables are the objects returned by startCmd.

        A yield is required.

        Returns successfully if all commands succeed.
        Fails as soon as any command fails.

        Inputs:
        - one or more command variables (keyvar.CmdVar objects)
        - checkFail: check for command failure?
            if True (the default) command failure will halt your script
        - retVal: value to return at the end; defaults to None
        """
        _WaitCmdVars(self, cmdVars, checkFail=checkFail, retVal=retVal)

    def waitKeyVar(
        self,
        keyVar,
        ind=0,
        defVal=Exception,
        waitNext=False,
    ):
        """Get the value of keyVar in self.value.
        If it is currently unknown or if waitNext is true,
        wait for the variable to be updated.
        See also getKeyVar (which does not wait).

        A yield is required.

        Inputs:
        - keyVar    keyword variable
        - ind       index of desired value (None for all values)
        - defVal    value to return if value cannot be determined; if Exception, the script halts
        - waitNext  if True, ignore the current value and wait for the next transition.
        """
        _WaitKeyVar(
            scriptRunner=self,
            keyVar=keyVar,
            ind=ind,
            defVal=defVal,
            waitNext=waitNext,
        )

    def waitMS(self, msec):
        """Waits for msec milliseconds.

        A yield is required.

        Inputs:
        - msec  number of milliseconds to pause
        """
        self.debugPrint("waitMS(msec=%s)" % (msec,))

        _WaitMS(self, msec)

    def waitSec(self, sec):
        """Wait for sec seconds

        Inputs:
        - sec  number of seconds to pause
        """
        self.debugPrint("waitSec(sec=%s)" % (sec,))

        _WaitMS(self, sec * _MSPerSec)

    def waitPause(self, msgStr="Paused", severity=opscore.RO.Constants.sevNormal):
        """Pause execution and wait

        A no-op if not running
        """
        Timer(0, self.showMsg, msgStr, severity=severity)
        self.pause()

    def waitThread(self, func, *args, **kargs):
        """Run func as a background thread, waits for completion
        and sets self.value = the result of that function call.

        A yield is required.

        Warning: func must NOT interact with Tkinter widgets or variables
        (not even reading them) because Tkinter is not thread-safe.
        (The only thing I'm sure a background thread can safely do with Tkinter
        is generate an event, a technique that is used to detect end of thread).
        """
        self.debugPrint(
            "waitThread(func=%r, args=%s, keyArgs=%s)" % (func, args, kargs)
        )

        _WaitThread(self, func, *args, **kargs)

    def waitUser(self):
        """Wait until resumeUser called.

        Typically used if waiting for user input
        but can be used for any external trigger.
        """
        self._waitCheck(setWait=True)

        if self._userWaitID is not None:
            raise RuntimeError("Already in user wait mode")

        self._userWaitID = self._getNextID()

    def _cmdFailCallback(self, cmdVar):
        """Use as a callback for when an asynchronous command fails."""
        if not cmdVar.didFail:
            errMsg = (
                "Bug! RO.BaseScriptRunner._cmdFail(%r) called for non-failed command"
                % (cmdVar,)
            )
            raise RuntimeError(errMsg)
        MaxLen = 10
        if len(cmdVar.cmdStr) > MaxLen:
            cmdDescr = "%s %s..." % (cmdVar.actor, cmdVar.cmdStr[0:MaxLen])
        else:
            cmdDescr = "%s %s" % (cmdVar.actor, cmdVar.cmdStr)
        lastReply = cmdVar.lastReply
        if lastReply:
            for keyword in lastReply.keywords:
                if keyword.name.lower() in _ErrKeys:
                    reason = keyword.values[0] or "?"
                    break
            else:
                reason = lastReply.string or "?"
        else:
            reason = "?"
        self._setState(self.Failed, reason="%s failed: %s" % (cmdDescr, reason))

    def _continue(self, iterID, val=None):
        """Continue executing the script.

        Inputs:
        - iterID: ID of iterator that is continuing
        - val: self.value is set to val
        """
        self._printState("_continue(%r, %r)" % (iterID, val))
        if not self.isExecuting:
            raise RuntimeError(
                "%s: bug! _continue called but script not executing" % (self,)
            )

        try:
            if iterID != self._iterID:
                raise RuntimeError(
                    "%s: bug! _continue called with bad id; got %r, expected %r"
                    % (self, iterID, self._iterID)
                )

            self.value = val

            self._waiting = False

            if self.isPaused:
                return

            if not self._iterStack:
                # just started; call run function,
                # and if it's an iterator, put it on the stack
                res = self.runFunc(self)
                if not hasattr(res, "next"):
                    # function was a function, not a generator; all done
                    self._setState(self.Done)
                    return

                self._iterStack = [res]

            self._printState("_continue: before iteration")
            self._state = self.Running
            possIter = next(self._iterStack[-1])
            if hasattr(possIter, "next"):
                self._iterStack.append(possIter)
                self._iterID = self._getNextID(addLevel=True)
                self._continue(self._iterID)
            else:
                self._iterID = self._getNextID()

            self._printState("_continue: after iteration")

        except StopIteration:
            self._iterStack.pop(-1)
            if not self._iterStack:
                self._setState(self.Done)
            else:
                self._continue(self._iterID, val=self.value)
        except KeyboardInterrupt:
            self._setState(self.Cancelled, "keyboard interrupt")
        except SystemExit:
            self.__del__()
            sys.exit(0)
        except ScriptError as e:
            self._setState(self.Failed, opscore.RO.StringUtil.strFromException(e))
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            self._setState(self.Failed, opscore.RO.StringUtil.strFromException(e))

    def _printState(self, prefix):
        """Print the state at various times.
        Ignored unless _DebugState or self.debug true.
        """
        if _DebugState:
            print(
                "Script %s: %s: state=%s, iterID=%s, waiting=%s, iterStack depth=%s"
                % (
                    self.name,
                    prefix,
                    self._state,
                    self._iterID,
                    self._waiting,
                    len(self._iterStack),
                )
            )

    def __del__(self):
        """Called just before the object is deleted.
        Deletes any state callbacks and then cancels script execution.
        """
        self._callbacks = []
        self.cancel()

    def _end(self):
        """Call the end function (if any)."""
        # Warning: this code must not execute _setState or __del__
        # to avoid infinite loops. It also need not execute _cancelFuncs.
        if self.endFunc:
            self.debugPrint("BaseScriptRunner._end: calling end function")
            try:
                res = self.endFunc(self)
                if hasattr(res, "next"):
                    self._state = self.Failed
                    self._reason = "endFunc tried to wait"
            except KeyboardInterrupt:
                self._state = self.Cancelled
                self._reason = "keyboard interrupt"
            except SystemExit:
                raise
            except Exception as e:
                self._state = self.Failed
                self._reason = "endFunc failed: %s" % (
                    opscore.RO.StringUtil.strFromException(e),
                )
                traceback.print_exc(file=sys.stderr)
        else:
            self.debugPrint("BaseScriptRunner._end: no end function to call")

    def _getNextID(self, addLevel=False):
        """Return the next iterator ID"""
        self._printState("_getNextID(addLevel=%s)" % (addLevel,))
        newID = self._iterID[:]
        if addLevel:
            newID += [0]
        else:
            newID[-1] = (newID[-1] + 1) % 10000
        return newID

    def _setState(self, newState, reason=None):
        """Update the state of the script runner.

        If the new state is Cancelled or Failed
        then any existing cancel function is called
        to abort outstanding callbacks.

        If the state is unknown, then the command is rejected.
        """
        self._printState("_setState(%r, %r)" % (newState, reason))
        if newState not in self._AllStates:
            raise RuntimeError("Unknown state", newState)

        # if ending, clean up appropriately
        if self.isExecuting and newState in self._DoneStates:
            self._endingState = newState
            # if aborting and a cancel function exists, call it
            if newState in self._FailedStates:
                for func in self._cancelFuncs:
                    func()
            self._cancelFuncs = []
            self._end()

        self._state = newState
        if reason is not None:
            self._reason = reason
        self._doCallbacks()

    def __str__(self):
        """String representation of script"""
        return "script %s" % (self.name,)

    def _waitCheck(self, setWait=False):
        """Verifies that the script runner is running and not already waiting
        (as can easily happen if the script is missing a "yield").

        Call at the beginning of every waitXXX method.

        Inputs:
        - setWait: if True, sets the _waiting flag True
        """
        if self._state != self.Running:
            raise RuntimeError("Tried to wait when not running")

        if self._waiting:
            raise RuntimeError(
                "Already waiting; did you forget the 'yield' when calling a BaseScriptRunner method?"
            )

        if setWait:
            self._waiting = True


class _WaitBase(object):
    """Base class for waiting.
    Handles verifying iterID, registering the termination function,
    registering and unregistering the cancel function, etc.
    """

    def __init__(self, scriptRunner):
        scriptRunner._printState("%s init" % (self.__class__.__name__))
        scriptRunner._waitCheck(setWait=True)
        self.scriptRunner = scriptRunner
        self._iterID = scriptRunner._getNextID()
        self.scriptRunner._cancelFuncs.append(self.cancelWait)

    def cancelWait(self):
        """Call to cancel waiting.
        Perform necessary cleanup but do not set state.
        Subclasses can override and should usually call cleanup.
        """
        self.cleanup()

    def fail(self, reason):
        """Call if waiting fails."""
        # report failure; this causes the scriptRunner to call
        # all pending cancelWait functions, so don't do that here
        self.scriptRunner._setState(self.scriptRunner.Failed, reason)

    def cleanup(self):
        """Called when ending for any reason
        (unless overridden cancelWait does not call cleanup).
        """
        pass

    def _continue(self, val=None):
        """Call to resume execution."""
        self.cleanup()
        try:
            self.scriptRunner._cancelFuncs.remove(self.cancelWait)
        except ValueError:
            raise RuntimeError(
                "Cancel function missing; did you forgot the 'yield' when "
                "calling a BaseScriptRunner method?"
            )
        if self.scriptRunner.debug and val is not None:
            print("wait returns %r" % (val,))
        self.scriptRunner._continue(self._iterID, val)


class _WaitMS(_WaitBase):
    def __init__(self, scriptRunner, msec):
        self._waitTimer = Timer()
        _WaitBase.__init__(self, scriptRunner)
        self._waitTimer.start(msec / 1000.0, self._continue)

    def cancelWait(self):
        self._waitTimer.cancel()


class _WaitCmdVars(_WaitBase):
    """Wait for one or more command variables to finish.

    Inputs:
    - scriptRunner: the script runner
    - one or more command variables (keyvar.CmdVar objects)
    - checkFail: check for command failure?
        if True (the default) command failure will halt your script
    - retVal: the value to return at the end (in scriptRunner.value)
    """

    def __init__(self, scriptRunner, cmdVars, checkFail=True, retVal=None):
        self.cmdVars = opscore.RO.SeqUtil.asSequence(cmdVars)
        self.checkFail = bool(checkFail)
        self.retVal = retVal
        self.addedCallback = False
        _WaitBase.__init__(self, scriptRunner)

        if self.state[0] != 0:
            # no need to wait; commands are already done or one has failed
            # schedule a callback for asap
            Timer(0.001, self.varCallback)
        else:
            # need to wait; add self as callback to each cmdVar
            # and remove self.scriptRunner._cmdFailCallback if present
            for cmdVar in self.cmdVars:
                if not cmdVar.isDone:
                    cmdVar.removeCallback(
                        self.scriptRunner._cmdFailCallback, doRaise=False
                    )
                    cmdVar.addCallback(self.varCallback)
                    self.addedCallback = True

    @property
    def state(self):
        """Return one of:
        - (-1, failedCmdVar) if a command has failed and checkFail True
        - (1, None) if all commands are done (and possibly failed if checkFail False)
        - (0, None) not finished yet
        Note that state[0] is logically True if done waiting.
        """
        allDone = 1
        for cmdVar in self.cmdVars:
            if cmdVar.isDone:
                if cmdVar.didFail and self.checkFail:
                    return (-1, cmdVar)
            else:
                allDone = 0
        return (allDone, None)

    def varCallback(self, *args, **kargs):
        """Check state of script runner and fail or continue if appropriate"""
        currState, cmdVar = self.state
        if currState < 0:
            self.fail(cmdVar)
        elif currState > 0:
            self._continue(self.retVal)

    def cancelWait(self):
        """Call when aborting early."""
        self.cleanup()
        for cmdVar in self.cmdVars:
            cmdVar.abort()

    def cleanup(self):
        """Called when ending for any reason."""
        if self.addedCallback:
            for cmdVar in self.cmdVars:
                if not cmdVar.isDone:
                    didRemove = cmdVar.removeCallback(self.varCallback, doRaise=False)
                    if not didRemove:
                        sys.stderr.write(
                            "_WaitCmdVar cleanup could not remove callback from %s\n"
                            % (cmdVar,)
                        )

    def fail(self, cmdVar):
        """A command var failed."""
        self.scriptRunner._cmdFailCallback(cmdVar)


class _WaitKeyVar(_WaitBase):
    """Wait for one keyword variable, returning the value in scriptRunner.value."""

    def __init__(
        self,
        scriptRunner,
        keyVar,
        ind,
        defVal,
        waitNext,
    ):
        """
        Inputs:
        - scriptRunner: a BaseScriptRunner instance
        - keyVar    keyword variable
        - ind       index of desired value (None for all values)
        - defVal    value to return if value cannot be determined; if Exception, the script halts
        - waitNext  if True, ignore the current value and wait for the next transition.
        """
        self.keyVar = keyVar
        self.ind = ind
        self.defVal = defVal
        self.waitNext = bool(waitNext)
        self.addedCallback = False
        _WaitBase.__init__(self, scriptRunner)

        if self.keyVar.isCurrent and not self.waitNext:
            # no need to wait; value already known
            # schedule a wakeup for asap
            Timer(0.001, self.varCallback)
        elif self.scriptRunner.debug:
            # display message
            argList = ["keyVar=%s" % (keyVar,)]
            if ind != 0:
                argList.append("ind=%s" % (ind,))
            if defVal != Exception:
                argList.append("defVal=%r" % (defVal,))
            if waitNext:
                argList.append("waitNext=%r" % (waitNext,))
            print("waitKeyVar(%s)" % ", ".join(argList))

            # prevent the call from failing by using None instead of Exception
            if self.defVal == Exception:
                self.defVal = None

            Timer(0.001, self.varCallback)
        else:
            # need to wait; set self as a callback
            self.keyVar.addCallback(self.varCallback, callNow=False)
            self.addedCallback = True

    def varCallback(self, keyVar):
        """Set scriptRunner.value to value. If value is invalid,
        use defVal (if specified) else cancel the wait and fail.
        """
        if self.keyVar.isCurrent:
            self._continue(self.getVal())
        elif self.defVal != Exception:
            self._continue(self.defVal)
        else:
            self.fail("Value of %s invalid" % (self.keyVar,))

    def cleanup(self):
        """Called when ending for any reason."""
        if self.addedCallback:
            self.keyVar.removeCallback(self.varCallback, doRaise=False)

    def getVal(self):
        """Return current value[ind] or the list of values if ind=None."""
        if self.ind is not None:
            return self.keyVar[self.ind]
        else:
            return self.keyVar.valueList


class _WaitThread(_WaitBase):
    def __init__(self, scriptRunner, func, *args, **kargs):
        self._pollTimer = Timer()
        _WaitBase.__init__(self, scriptRunner)

        if not callable(func):
            raise ValueError("%r is not callable" % func)

        self.queue = queue.Queue()
        self.func = func

        self.threadObj = threading.Thread(
            target=self.threadFunc, args=args, kwargs=kargs
        )
        self.threadObj.setDaemon(True)
        self.threadObj.start()
        self._pollTimer.start(_PollDelaySec, self.checkEnd)

    def checkEnd(self):
        if self.threadObj.isAlive():
            self._pollTimer.start(_PollDelaySec, self.checkEnd)
            return

        retVal = self.queue.get()
        self._continue(val=retVal)

    def cleanup(self):
        self._pollTimer.cancel()
        self.threadObj = None

    def threadFunc(self, *args, **kargs):
        retVal = self.func(*args, **kargs)
        self.queue.put(retVal)
