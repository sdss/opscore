#!/usr/bin/env python
"""KeyVar and CmdVar

TO DO:
- Add CmdVar
- Add support to KeyVar for refresh commands
"""
import sys
import time
import traceback

import RO.AddCallback
import RO.Constants

import opscore.protocols.messages as protoMess
import msgtypes

__all__ = ["KeyVar"]

class KeyVar(RO.AddCallback.BaseMixin):
    """Container for keyword data.
    
    Callback functions receive three arguments (see Design Note below):
    - valueList: the list of new values (may be an empty list)
    - isCurrent: see the isCurrent method below
    - self: this object
    """
    def __init__(self, actor, key, doPrint=False):
        """Create a KeyVar.
        
        Inputs are:
        - actor: the name of the actor issuing this keyword (string)
        - key: keyword description (opscore.protocols.keys.Key)
        - doPrint: do print data to stdout when set successfully (for debugging)? (boolean)
        """
        self.actor = actor
        self.name = key.name
        self.reply = None
        self._key = key
        self._typedValues = key.typedValues
        self.doPrint = bool(doPrint)
        self._valueList = ()
        self._isCurrent = False
        self._isGenuine = False
        self._timeStamp = 0
        RO.AddCallback.BaseMixin.__init__(self, defCallNow = True)
    
    def __repr__(self):
        """Return a long str representation of a KeyVar
        """
        return "%s(%r, %r, %s)" % \
            (self.__class__.__name__, self.actor, self.name, self._typedValues)

    def __str__(self):
        """Return a short str representation of a KeyVar
        """
        return "%s(%r, %r)" % \
            (self.__class__.__name__, self.actor, self.name)

    @property
    def valueList(self):
        """Return a copy of the list of values
        """
        return self._valueList[:]
    
    def __getitem__(self, ind):
        """Implement keyVar[ind] to return the specified value from the valueList.
        
        @raise IndexError if ind is out of range
        """
        return self._valueList[ind]

    @property
    def isCurrent(self):
        """Return True if the client is connected to the hub and if
        the actor has output the data since it was last connected to the hub.

        Warning: this value is maintained by a KeyVarDispatcher. Thus it is invalid and should be ignored
        unless you use the KewyordDispatcher or a replacement!
        """
        return self._isCurrent

    @property
    def isGenuine(self):
        """Return True if the value was set from the actor, rather than from a cache.

        Warning: this value is maintained by a KeyVarDispatcher. Thus it is invalid and should be ignored
        unless you use the KewyordDispatcher or a replacement!
        """
        return self._isGenuine
    
    @property
    def timestamp(self):
        """Return the time (in unix seconds, e.g. time.time()) at which value was last set, or 0 if not set.
        """
        return self._timeStamp
    
    def set(self, valueList, isCurrent=True, isGenuine=True, reply=None):
        """Set the values, converting from strings as necessary.

        Inputs:
        - valueList: a list of values (strings or converted to proper data type)
        - isCurrent: new value for isCurrent flag (generally leave this at its default of True)
        - isGenuine: set True if data came from the actor, False if it came from a data cache
        - reply: a parsed Reply object (opscore.protocols.messages.Reply)
        
        @raise RuntimeError if the values cannot be set.
        """
        if not self._typedValues.consume(valueList):
            raise RuntimeError("%s could not parse valueList=%s" % (self, valueList))

        # print to stderr, if requested
        if self.doPrint:
            sys.stderr.write("%s = %r\n" % (self, valueList))

        # apply callbacks, if any
        self._valueList = valueList
        self._timeStamp = time.time()
        self._isCurrent = bool(isCurrent)
        self._isGenuine = bool(isGenuine)
        self.reply = reply
        self._basicDoCallbacks(self)

    def setNotCurrent(self):
        """Clear the isCurrent flag
        
        Note: the flag is set automatically when you call "set", so there is no method to set it.
        """
        self._isCurrent = False
        self._basicDoCallbacks(self)

    def hasRefreshCmd(self):
        """Temporary hack"""
        return False


class CmdVar(object):
    """Issue a command via the dispatcher and receive callbacks
    as replies are received.
    """
    def __init__(self,
        cmdStr = "",
        actor = "",
        timeLim = 0,
        description = "",
        callFunc = None,
        callCodes = protoMess.ReplyHeader.DoneCodes,
        isRefresh = False,
        timeLimKeyVar = None,
        timeLimKeyInd = 0,
        abortCmdStr = None,
        keyVars = None,
    ):
        """
        Inputs:
        - actor: the name of the device which issued the keyword
        - cmdStr: the command; no terminating \n wanted
        - timeLim: maximum time before command expires, in sec; 0 for no limit
        - description: a string describing the command, useful for help systems
        - callFunc: a function to call when the command changes state; see addCallback for details.
        - callCodes: message codes for which to call the callback; see addCallback for details.
        - isRefresh: the command was triggered by a refresh request, else is a user command
        - timeLimKeyVar: a KeyVar specifying a delta-time by which the command must finish
            this KeyVar must be registered with the message dispatcher.
        - timeLimKeyInd: the index of the time limit value in timeLimKeyVar; defaults to 0;
            ignored if timeLimKeyVar is None.
        - abortCmdStr: a command string that will abort the command.
            Sent to the actor if abort is called and if the command is executing.
        - keyVars: a sequence of 0 or more keyword variables to monitor for this command.
            Any data for those variables that arrives IN RESPONSE TO THIS COMMAND is saved
            and can be retrieved using cmdVar.getKeyVarData or cmdVar.getLastKeyVarData.
        
        Note: timeLim and timeLimKeyInfo work together as follows:
        - The initial time limit for the command is timeLim
        - If timeLimKeyInfo is seen before timeLim seconds have passed
          then self.maxEndTime is updated with the new value
          
        Also the time limit is a lower limit. The command is guaranteed to expire no sooner than this.
        """
        self.cmdStr = cmdStr
        self.actor = actor
        self.cmdID = None
        self.timeLim = timeLim
        self.description = description
        self.isRefresh = isRefresh
        self._timeLimKeyVar = timeLimKeyVar
        self._timeLimKeyInd = int(timeLimKeyInd)
        if self._timeLimKeyVar:
            # check that value exists and can be cast to a float
            key = timeLimKeyVar.key
            nVals = len(key.typedValues)
            if nVals < self._timeLimKeyInd:
                raise IndexError("timeLimKeyInd = %s too large; timeLimKeyVar %s has %s values" %
                    (self._timeLimKeyInd, self._timeLimKeyVar, nVals))
            valType = key[self._timeLimKeyInd]
            try:
                float(valType(5))
            except ValueError:
                raise ValueError("timeLimKeyVar %s[%s] is of type %s, which cannot be used as a time limit" % 
                    (self._timeLimKeyVar, self._timeLimKeyInd, valType))
        self.abortCmdStr = abortCmdStr
        # a dictionary of keyVar values; keys is keyVar; value is a list of keyVar.valueList seen for that keyVar
        self.keyVars = keyVars or ()
        self.keyVarDataDict = dict()
        for keyVar in self.keyVars:
            self.keyVarDataDict[keyVar] = []

        self.dispatcher = None # set by dispatcher when it executes the command
        self.lastReply = None
        self.lastType = "i"
        self.startTime = None
        self.maxEndTime = None

        # the following is a list of (callCodes, callFunc)
        self.callCodesFuncList = []

        if callFunc:
            self.addCallback(callFunc, callCodes)
    
    def abort(self):
        """Abort the command, including:
        - deregister the command from the dispatcher
        - send the abort command (if it exists)
        - set state to failed, calling the appropriate callbacks

        Has no effect if the command was never dispatched or has already ended.
        """
        if self.dispatcher and not self.isDone():
            self.dispatcher.abortCmdByID(self.cmdID)

    def addCallback(self, callFunc, callCodes = protoMess.ReplyHeader.DoneCodes):
        """Executes the given function whenever a reply is seen
        for this user with a matching command number

        Inputs:
        - callFunc: a function to call when the command changes state;
            it receives one argument: this CmdVar
        - callCodes: the message codes for which to call the callback;
            a collection of one or more opscore.protocols.messages.ReplyHeader.MsgCode values.
            useful predefined sets include:
                opscore.protocols.messages.ReplyHeader.DoneCodes (command finished or failed)
                opscore.protocols.messages.ReplyHeader.FailedCodes (command failed)
                opscore.protocols.messages.ReplyHeader.MsgCode (all message codes, thus any reply)
        """
        self.callCodesFuncList.append((callCodes, callFunc))
    
    @property
    def didFail(self):
        """Return True if the command failed, False otherwise.
        """
        return self.lastType in protoMess.ReplyHeader.FailTypes
    
    @property
    def severity(self):
        """Return severity of most recent message, or RO.Constants.sevNormal if no messages received.
        """
        if not self.lastType:
            return RO.Constants.sevNormal
        return TypeDict[self.lastType][1]
    
    def getKeyVarData(self, keyVar):
        """Return a list of data seen for the specified keyword variable, or [] if no data seen.
        
        Inputs:
        - keyVar: the keyword variable for which to return data
    
        Returns a list of data seen for the specified keyVar that was in response to this command,
        in the order received (oldest to most recent). Each entry is the list of values seen for the keyword.
        For example:
            getKeyVarData(keyVar)[-1] is the most recent list of data
                (or an index error if the keyVar was not seen was seen!)
        
        Warning: the return value is NOT a copy. Please do not modify it.
        
        Raises KeyError if the keyVar is not being monitored for this command.
        """
        return self.keyVarDataDict[keyVar]
    
    def getLastKeyVarData(self, keyVar):
        """Return the most recent list of values seen for the specified keyword variable, or None if no data seen.
        
        Inputs:
        - keyVar: the keyword variable for which to return data
        
        Returns the most recent list of values seen for the specified keyVar, or None if no data seen.
        Note: returns None instead of [] because this allows one to tell the difference between
        the keyword value list being itself empty and no data seen for the keyword.

        Warning: the return value is NOT a copy. Please do not modify it.

        Raises KeyError if the keyVar is not being monitored for this command.
        """
        allVals = self.keyVarDataDict[keyVar]
        if not allVals:
            return None
        return allVals[-1]
    
    @property
    def isDone(self):
        """Return True if the command is finished, False otherwise.
        """
        return self.lastType in protoMess.ReplyHeader.DoneCodes

    def removeCallback(self, callFunc, doRaise=True):
        """Delete the callback function.
        Return True if successful, raise error or return False otherwise.

        Inputs:
        - callFunc  callback function to remove
        - doRaise   raise exception if unsuccessful? True by default.
        
        If doRaise true:
        - Raises ValueError if callback not found
        - Raises RuntimeError if executing callbacks when called
        Otherwise returns False in either case.
        """
        for callCodeFunc in self.callCodesFuncList:
            if callFunc == callCodeFunc[1]:
                self.callCodesFuncList.remove(callCodeFunc)
                return True
        if doRaise:
            raise ValueError("Callback %r not found" % callFunc)
        return False
    
    def handleReply(self, reply):
        """Call command callbacks.
        Warn and do nothing else if called after the command has finished.
        """
        if self.lastType in protoMess.ReplyHeader.DoneCodes:
            sys.stderr.write("Command %s already finished; no more replies allowed\n" % (self,))
            return
        self.lastReply = reply
        msgType = reply.header.code
        self.lastType = msgType
        for callCodes, callFunc in self.callCodesFuncList[:]:
            if msgType in callCodes:
                try:
                    callFunc(self)
                except Exception:
                    sys.stderr.write ("%s callback %s failed\n" % (self, callFunc))
                    traceback.print_exc(file=sys.stderr)
        if self.lastType in protoMess.ReplyHeader.DoneCodes:
            self._cleanup()
    
    def _timeLimKeyVarCallback(self, keyVar):
        """Handle callback from the time limit keyVar.
        
        Update self.maxEndTime (adding self.timeLim as a margin if timeLim was specified).

        Raises ValueError if the keyword exists but the value is invalid.
        """
        newTimeLim = keyVar[self._timeLimKeyInd]
        try:
            newTimeLim = float(valueTuple[0])
        except Exception:
            raise ValueError("Invalid value %r for timeout for command %d"
                % (valueTuple, keywd, self.cmdID))
        self.maxEndTime = time.time() + newTimeLim
        if self.timeLim:
            self.maxEndTime += self.timeLim

    def _cleanup(self):
        """Call when command is finished to remove callbacks.
        
        This reduces the chance of memory leaks.
        """
        self.callCodesFuncList = []
        for keyVar in self.keyVars:
            keyVar.removeCallback(self._keyVarCallback, doRaise=False)
        if self._timeLimKeyVar:
            self._timeLimKeyVar.removeCallback(self._timeLimKeyVarCallback, doRaise=False)
    
    def _setStartInfo(self, dispatcher, cmdID):
        """Called by the dispatcher when dispatching the command.
        """
        self.dispatcher = dispatcher
        self.cmdID = cmdID
        self.startTime = time.time()
        if self.timeLim:
            self.maxEndTime = self.startTime + self.timeLim

        for keyVar in self.keyVars:
            keyVar.addCallback(self._keyVarCallback, callNow=False)
        if self._timeLimKeyVar:
            self._timeLimKeyVar.addCallback(self._timeLimKeyVarCallback, callNow=False)

    def _keyVarCallback(self, keyVar):
        """Keyword seen; archive the data.
        """
        if not keyVar.isCurrent or keyVar.reply:
            return
        if keyVar.reply.header.commandID != self.cmdID:
            return
        if keyVar.reply.header.commander != self.dispatcher.connection.cmdr:
            return
        self.keyVarDataDict[keyVar].append(keyVar.valueList)
    
    def _keyVarID(self, keyVar):
        """Return an ID suitable for use in a dictionary.
        """
        return id(keyVar)
    
    def __repr__(self):
        return "%s(cmdID=%r, actor=%r, cmdStr=%r)" % (self.__class__.__name__, self.cmdID, self.actor, self.cmdStr)
    
    def __str__(self):
        return "%s %r" % (self.actor, self.cmdStr)