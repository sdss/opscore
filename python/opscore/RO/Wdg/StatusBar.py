
"""Displays hot help, error messages and monitors the progress of commands
of the class opscore.RO.KeyVariable.cmdVar

History:
2003-04-04 ROwen    Adapted from StatusWdg.
2003-04-09 ROwen    Modified clearTempMsg to use 0 for "clear any"
                    and None for don't clear anything.
                    Made clearTempMsg explicitly return None and documented why.
2003-04-11 ROwen    Added handlers for <<EntryError>>, <Enter> and <Leave>
                    and automatically bind them to the toplevel.
2003-04-21 ROwen    Renamed StatusWdg to StatusBar to avoid conflicts.
2003-08-01 ROwen    Bug fix: _reset was not resetting self.permSeverity.
2003-08-11 ROwen    Modified because TypeDict and AllTypes were moved
                    from KeyDispatcher to KeyVariable.
2003-10-20 ROwen    Modified <<EntryError>> handler to beep (instead of event sender),
                    so other users can catch the event and notify in other ways.
2003-10-28 ROwen    Modified clear to clear permanent messages and reset everything.
2003-12-05 ROwen    Fixed some bugs associated with executing commands:
                    when a cmd started any existing permanent message was not cleared,
                    and the "command starting" message was not permanent.
2004-02-20 ROwen    Bug fix: clear did not set the current text color,
                    which caused incorrect color in some situations.
                    Ditched _reset after adding remaining functionality to clear.
2004-02-23 ROwen    Added support for playing a sound when a command ends.
2004-05-18 ROwen    Bug fix: missing import of sys for writing error messages.
                    Modified _cmdCallback to use dataStr (it was computed and ignored).
2004-07-20 ROwen    StatusBar now inherits from CtxMenu, making it easier to customize
                    the contextual menu.
2004-08-12 ROwen    Added helpText argument (which disables hot help display;
                    see documentation for helpText for more information).
                    Modified to no longer display informational messages for commands;
                    still displays warnings, failures and done.
                    Added playCmdDone, playCmdFailed methods.
                    Modified to use st_Normal, etc. constants for message level.
                    Define __all__ to restrict import.
2004-09-03 ROwen    Modified for opscore.RO.Wdg.sev... -> opscore.RO.Constants.sev...
2004-10-01 ROwen    Bug fix: width arg was being ignored.
2005-01-05 ROwen    setMsg: changed level to severity.
2005-05-12 ROwen    Mod. to use the default borderwidth.
2005-06-16 ROwen    Added cmdSummary argument to doCmd.
                    Modified to use severity built into opscore.RO.Wdg.EntryWdg
                    (prefs no longer need color prefs and the code is simpler).
                    Modified command output to ignore info messages
                    unless they contain a "Text" keyword.
2005-06-17 ROwen    Bug fix: mis-typed severity constant (reported by Craig Loomis).
2005-07-14 ROwen    Modified to use opscore.RO.Alg.IDGen for the temporary message ID.
                    Bug fix: clear reset the temporary message ID,
                    which could cause clearTempMsg to clear the wrong message.
                    Modified to not inherit from CtxMenu.CtxMenuMixin,
                    but dispatches ctxSetConfigFunc.
2005-09-07 ROwen    Bug fix: if text=... found in a command reply, it was shown in parens.
2009-02-23 ROwen    Show last warning if command fails with no explanatory text
2009-07-06 ROwen    setMsg function: cast duration argument to int to avoid a traceback if float
                    and document that it is definitely in ms (the original comment said "msec?").
2010-03-05 ROwen    Fixed an error in the tracking of command reply severity.
2010-03-08 ROwen    Bug fix: command replies were sometimes displayed with the wrong color.
2011-06-17 ROwen    Changed "type" to "msgType" in parsed message dictionaries to avoid conflict with builtin.
2012-07-09 ROwen    Modified to use opscore.RO.TkUtil.Timer.
2015-01-08 ROwen    If a message in reply to a command has unknown message type then report the problem
                    and assume the command failed.
2015-09-24 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
"""
__all__ = ['StatusBar']

import sys
from six.moves import tkinter
import opscore.RO.Alg
import opscore.RO.Constants
import opscore.RO.KeyVariable
import opscore.RO.Prefs.PrefVar
from opscore.RO.TkUtil import Timer
from . import Sound
from . import Entry

def _getSound(playCmdSounds, prefs, prefName):
    noPlay = Sound.NoPlay()
    if not playCmdSounds:
        return noPlay
    soundPref = prefs.getPrefVar(prefName)
    if soundPref is None:
        sys.stderr.write("StatusBar cannot play %r; no such preference" % prefName)
        return noPlay
    elif not hasattr(soundPref, "play"):
        sys.stderr.write("StatusBar cannot play %r; preference exists but is not a sound" % prefName)
        return noPlay
    return soundPref


class StatusBar(tkinter.Frame):
    """Display hot help and error messages and execute commands
    and display their progress.

    Inputs:
    - dispatcher    an opscore.RO.KeyDispatcher
    - prefs         a opscore.RO.Prefs.PrefSet of preferences; uses:
                    - "Command Done" and "Command Failed" sounds if playCmdSounds true
    - playCmdSounds if true, play "Command Done", "Command Failed" sounds
                    when a command started by doCmd succeeds or fails.
                    if true and these prefs aren't available or are available but aren't sounds,
                    prints a warning to stderr.
    - summaryLen    maximum number of characters of command to show, excluding final "..."
    - helpURL       URL for on-line help
    - helpText      Warning: if specified then the status bar will NOT display
                    help text and entry errors. This is typically only used if you have
                    more than one status bar in a window, in which case one should show
                    help and the others should have helpText strings.
    - width         desired width in average-sized characters
    """
    def __init__(self,
        master,
        dispatcher = None,
        prefs = None,
        playCmdSounds = False,
        summaryLen = 10,
        helpURL = None,
        helpText = None,
        width = 20,
    **kargs):
        self.dispatcher = dispatcher
        self.summaryLen = int(summaryLen)
        self.cmdDoneSound = _getSound(playCmdSounds, prefs, "Command Done")
        self.cmdFailedSound = _getSound(playCmdSounds, prefs, "Command Failed")
        self.tempIDGen = opscore.RO.Alg.IDGen(1, sys.maxsize)

        tkinter.Frame.__init__(self, master, **kargs)
        self.displayWdg = Entry.StrEntry(
            master = self,
            readOnly = True,
            width = width,
            helpURL = helpURL,
        )
        self.displayWdg.pack(expand="yes", fill="x")

        self.clear()

        # bind to catch events
        self.helpText = helpText
        if not helpText:
            tl = self.winfo_toplevel()
            tl.bind("<<EntryError>>", self.handleEntryError)
            tl.bind("<Enter>", self.handleEnter)
            tl.bind("<Leave>", self.handleLeave)

    def clear(self):
        """Clear the display and cancels all messages.
        """
        self.displayWdg.set("", severity=opscore.RO.Constants.sevNormal)
        self.permSeverity = opscore.RO.Constants.sevNormal
        self.permMsg = None
        self.currID = None # None if perm msg, tempID if temporary msg
        self.entryErrorID = None
        self.helpID = None

    def clearTempMsg(self, msgID=0):
        """Clear a temporary message, if any.

        Returns None, so a common paradigm to avoid saving a stale ID is:
        savedID = statusBar.clearTempMsg(savedID)

        Input:
        - msgID:    ID of message to clear;
                0 will clear any temporary message,
                None will not clear anything
        """
        if self.currID is None or msgID is None:
            return None

        if msgID == 0 or self.currID == msgID:
            self.setMsg(self.permMsg, self.permSeverity)
            self.currID = None
        return None

    def ctxSetConfigFunc(self, configFunc=None):
        self.displayWdg.ctxSetConfigFunc(configFunc)

    def doCmd(self, cmdVar, cmdSummary=None):
        """Execute the given command and display progress reports
        for command start warnings and command completion or failure.
        """
        self.clear()

        self.cmdVar = cmdVar
        self.cmdMaxSeverity = opscore.RO.Constants.sevNormal
        self.cmdLastWarning = None
        if cmdSummary is None:
            if len(self.cmdVar.cmdStr) > self.summaryLen + 3:
                cmdSummary = self.cmdVar.cmdStr[0:self.summaryLen] + "..."
            else:
                cmdSummary = self.cmdVar.cmdStr
        self.cmdSummary = cmdSummary

        if self.dispatcher:
            cmdVar.addCallback(self._cmdCallback, ":wf!")
            self.setMsg("%s started" % self.cmdSummary)
            self.dispatcher.executeCmd(self.cmdVar)
        else:
            self._cmdCallback(msgType = "f", msgDict = {
                "msgType":"f",
                "msgStr":"No dispatcher",
                "dataStart":0,
            })

    def handleEntryError(self, evt):
        """Handle the <<EntryError>> event to report a data entry error.
        To do anything useful, the sender must have a getEntryError method.
        """
        msgStr = evt.widget.getEntryError()
        if msgStr:
            self.entryErrorID = self.setMsg(
                msgStr = msgStr,
                severity = opscore.RO.Constants.sevWarning,
                isTemp = True,
            )
            self.bell()
        else:
            self.entryErrorID = self.clearTempMsg(self.entryErrorID)

    def handleEnter(self, evt):
        """Handle the <Enter> event to show help.
        To do anything useful, the sender must have a helpText attribute.
        """
        try:
            msgStr = evt.widget.helpText
        except AttributeError:
            return
        if msgStr:
            self.helpID = self.setMsg(msgStr, severity=opscore.RO.Constants.sevNormal, isTemp=True)

    def handleLeave(self, evt):
        """Handle the <Leave> event to erase help.
        """
        if self.helpID:
            self.helpID = self.clearTempMsg(self.helpID)

    def playCmdDone(self):
        """Play "command done" sound.
        """
        self.cmdDoneSound.play()

    def playCmdFailed(self):
        """Play "command failed" sound.
        """
        self.cmdFailedSound.play()

    def setMsg(self, msgStr, severity=opscore.RO.Constants.sevNormal, isTemp=False, duration=None):
        """Display a new message.

        Inputs:
        - msgStr    the new string to display
        - severity  one of opscore.RO.Constants.sevNormal (default), sevWarning or sevError
        - isTemp    if true, message is temporary and can be cleared with clearTempMsg;
                    if false, any existing temp info is ditched
        - duration  the amount of time (msec) to leave a temporary message;
                    if omitted, there is no time limit;
                    ignored if isTemp false

        Returns None if a permanent message, else a unique positive message ID.
        """
        self.displayWdg.set(msgStr, severity=severity)
        if isTemp:
            self.currID = next(self.tempIDGen)
            if duration is not None:
                Timer(duration / 1000.0, self.clearTempMsg, self.currID)
        else:
            self.permMsg = msgStr
            self.permSeverity = severity
            self.currID = None
        return self.currID

    def _cmdCallback(self, msgType, msgDict, cmdVar=None):
        # print "StatusBar _cmdCallback(%r, %r, %r)" % (msgType, msgDict, cmdVar)
        try:
            msgDescr, newSeverity = opscore.RO.KeyVariable.TypeDict[msgType]
        except KeyError:
            # invalid msgType; print a warning, then assume failure
            sys.stderr.write("StatusBar._cmdCallback: invalid msgType=%r for msgDict=%s; assuming failure\n" % (msgType, msgDict,))
            msgDescr = "invalid msgType=%r" % (msgType,)
            msgType = "f"
            newSeverity = opscore.RO.Constants.sevError
        self.cmdMaxSeverity = max(newSeverity, self.cmdMaxSeverity)
        if msgType == ":":
            # command finished; omit associated text,
            # but append warning info if there were warnings.
            if self.cmdMaxSeverity == opscore.RO.Constants.sevWarning:
                if self.cmdLastWarning:
                    msgDescr += "; warning: " + self.cmdLastWarning
                else:
                    msgDescr += " with warnings"
            infoText = "%s %s" % (
                self.cmdSummary,
                msgDescr,
            )
            self.playCmdDone()
            self.setMsg(infoText, severity=self.cmdMaxSeverity)
            return

        try:
            dataStr = msgDict["data"]["text"][0]
        except LookupError:
            if newSeverity == opscore.RO.Constants.sevNormal:
                # info message with no textual info; skip it
                return
            dataStr = msgDict.get("msgStr", "")[msgDict.get("dataStart", 0):]
        if msgType == "w" and dataStr:
            # save last warning in case command fails with no text
            self.cmdLastWarning = dataStr
        elif msgType in opscore.RO.KeyVariable.DoneTypes and not dataStr:
            # message failed without an explanation; use last warning
            dataStr = self.cmdLastWarning
        infoText = "%s %s: %s" % (self.cmdSummary, msgDescr, dataStr)
        self.setMsg(infoText, severity=newSeverity)
        if msgType in opscore.RO.KeyVariable.DoneTypes:
            self.playCmdFailed()
