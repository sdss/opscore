#!/usr/bin/env python
"""A single-actor version of CmdKeyDispatcher.

Send commands to a single actor and dispatches replies from that actor.

History:
2012-07-24 ROwen    first cut
"""
import sys
import time
import traceback

import RO.Alg
import RO.Constants
import RO.StringUtil

from opscore.utility.timer import Timer
import opscore.protocols.keys as protoKeys
from opscore.protocols.parser import ActorReplyParser
import opscore.protocols.messages as protoMess
import keydispatcher
import keyvar
from .cmdkeydispatcher import CmdKeyVarDispatcher

__all__ = ["ActorDispatcher"]

_CmdNumWrap = 1000 # value at which user command ID numbers wrap

_RefreshTimeLim = 20 # time limit for refresh commands (sec)

class ActorDispatcher(CmdKeyVarDispatcher):
    """Parse replies and sets KeyVars. Also manage CmdVars and their replies.

    Fields:
    - readUnixTime: unix time at which last message received from connection; 0 if no message ever received.
    """
    _ParserClass = ActorReplyParser
    def __init__(self,
        name,
        connection = None,
        logFunc = None,
        delayCallbacks = False,
    ):
        """Create a new ActorDispatcher
    
        Inputs:
        - name: actor name;
        - connection: an RO.Comm.HubConnection object or similar;
          if omitted, a NullConnection is used, which is useful for testing.
        - logFunc: a function that logs a message. Argument list must be:
            (msgStr, severity, actor, cmdr)
            where the first argument is positional and the others are by name
            and severity is an RO.Constants.sevX constant
            If None then nothing is logged.

        Raises ValueError if name cannot be used as an actor name
        """
        self._myUserID = 0
        CmdKeyVarDispatcher.__init__(self,
            name = name,
            connection = connection,
            logFunc = logFunc,
            includeName = False,
            delayCallbacks = False,
        )
        
        if self.refreshCmdDict:
            raise RuntimeError("Internal error: refreshCmdDict should be empty but contains %s" % (self.refreshCmdDict,))
        
        # start background tasks
        self.checkCmdTimeouts()
    
    def addKeyVar(self, keyVar):
        """Add a keyword variable (opscore.actor.keyvar.KeyVar) to the collection.
        
        This variant ignores the refresh command.
        
        Inputs:
        - keyVar: the keyword variable (opscore.actor.keyvar.KeyVar)
        """
#        print "%s.addKeyVar(%s); hasRefreshCmd=%s; refreshInfo=%s" % (self.__class__.__name__, keyVar, keyVar.hasRefreshCmd, keyVar.refreshInfo)
        if keyVar.actor != self.name:
            raise RuntimeError("keyVar.actor=%r; this actor dispatcher only handles actor %r" % (keyVar.actor, self.name))
        keydispatcher.KeyVarDispatcher.addKeyVar(self, keyVar)

    def logReply(self, reply, fallbackToStdOut = False):
        """Log a reply (an opscore.protocols.messages.Reply)

        Inputs:
        - reply is a parsed Reply object (opscore.protocols.messages.Reply) whose fields include:
          - header.program: name of the program that triggered the message (string)
          - header.commandId: command ID that triggered the message (int)
          - header.actor: the actor that generated the message (string)
          - header.code: the message type code (opscore.protocols.types.Enum)
          - string: the original unparsed message (string)
          - keywords: an ordered dictionary of message keywords (opscore.protocols.messages.Keywords)        
          Refer to https://trac.sdss3.org/wiki/Ops/Protocols for details.
        - fallbackToStdOut: if True and there is no logFunc then prints the message to stdout.
        """
        try:
            msgCode = reply.header.code
            severity = keyvar.MsgCodeSeverity[msgCode]
            self.logMsg(
                msgStr = reply.string,
                severity = severity,
                keywords = reply.keywords,
                cmdID = reply.header.commandId,
                fallbackToStdOut = fallbackToStdOut,
            )
        except Exception, e:
            sys.stderr.write("Could not log reply=%r\n    error=%s\n" % (reply, strFromException(e)))
            traceback.print_exc(file=sys.stderr)
    
    def replyIsMine(self, reply):
        """Return True if I am the commander for this message.
        """
        return reply.header.userId == self._myUserID

    def refreshAllVar(self, resetAll=True):
        """Disable refresh, since there is no hub and hence no keys cache

        Inputs:
        - resetAll: reset all keyword variables to notCurrent
        """
        if resetAll:
            for keyVarList in self.keyVarListDict.values():
                for keyVar in keyVarList:
                    keyVar.setNotCurrent()

    def setKeyVarsFromReply(self, reply, doCallbacks=True):
        """Set KeyVars based on the supplied Reply
        
        reply is a parsed Reply object (opscore.protocols.messages.Reply)
        """
#         print "dispatchReply(reply=%s, doCallbacks=%s)" % (reply, doCallbacks)
        for keyword in reply.keywords:
            keyVarList = self.getKeyVarList(self.name, keyword.name)
            for keyVar in keyVarList:
                try:
                    keyVar.set(keyword.values, isGenuine=True, reply=reply, doCallbacks=doCallbacks)
                except TypeError:
                    self.logMsg(
                        "InvalidKeywordData=%s.%s, %s" % (self.name, keyword.name, keyword.values),
                        severity = RO.Constants.sevError,
                        fallbackToStdOut = True,
                    )
                except:
                    print "Failed to set %s to %s:" % (keyVar, keyword.values)
                    traceback.print_exc(file=sys.stderr)

    
    def setMyUserNum(self, myUserNum):
        self._myUserNum = int(myUserNum)
    
    def _formatCmdStr(self, cmdVar):
        """Format a command; one-actor version
        """
        return "%d %s" % (cmdVar.cmdID, cmdVar.cmdStr)
    
    def _formatReplyHeader(self,
        cmdr = None,
        cmdID = 0,
        actor = None,
        msgCode = "F",
        dataStr = "",
    ):
        """Format a reply header; one-actor version
        """
        return "%d %d %s" % (cmdID, self._myUserID, msgCode)


if __name__ == "__main__":
    print "\nTesting opscore.actor.ActorDispatcher\n"
    import opscore.protocols.types as protoTypes
    import twisted.internet.tksupport
    import Tkinter
    root = Tkinter.Tk()
    twisted.internet.tksupport.install(root)
    
    kvd = ActorDispatcher()

    def showVal(keyVar):
        print "keyVar %s.%s = %r, isCurrent = %s" % (keyVar.actor, keyVar.name, keyVar.valueList, keyVar.isCurrent)

    # scalars
    keyList = (
        protoKeys.Key("StringKey", protoTypes.String()),
        protoKeys.Key("IntKey", protoTypes.Int()),
        protoKeys.Key("FloatKey", protoTypes.Float()),
        protoKeys.Key("BooleanKey", protoTypes.Bool("F", "T")),
        protoKeys.Key("KeyList", protoTypes.String(), protoTypes.Int()),
    )
    keyVarList = [keyvar.KeyVar("test", key) for key in keyList]
    for keyVar in keyVarList:
        keyVar.addCallback(showVal)
        kvd.addKeyVar(keyVar)
    
    # command callback
    def cmdCall(cmdVar):
        print "command callback for actor=%s, cmdID=%d, cmdStr=%r, isDone=%s" % \
            (cmdVar.actor, cmdVar.cmdID, cmdVar.cmdStr, cmdVar.isDone)
    
    # command
    cmdVar = keyvar.CmdVar(
        cmdStr = "THIS IS A SAMPLE COMMAND",
        actor="test",
        callFunc=cmdCall,
        callCodes = keyvar.DoneCodes,
    )
    kvd.executeCmd(cmdVar)
    cmdID = cmdVar.cmdID

    dataList = [
        "StringKey=hello",
        "IntKey=1",
        "FloatKey=1.23456789",
        "BooleanKey=T",
        "KeyList=three, 3",
        "Coord2Key=45.0, 0.1, 32.1, -0.1, %s" % (time.time(),),
    ]
    dataStr = "; ".join(dataList)

    reply = kvd.makeReply(
        cmdr = "myprog.me",
        cmdID = cmdID - 1,
        actor = "test",
        msgCode = ":",
        dataStr = dataStr,
    )
    print "\nDispatching message with wrong cmdID; only KeyVar callbacks should called:"
    kvd.dispatchReply(reply)

    reply = kvd.makeReply(
        cmdID = cmdID,
        actor = "wrongActor",
        msgCode = ":",
        dataStr = dataStr,
    )
    print "\nDispatching message with wrong actor; only CmdVar callbacks should be called:"
    kvd.dispatchReply(reply)

    reply = kvd.makeReply(
        cmdID = cmdID,
        actor = "test",
        msgCode = ":",
        dataStr = dataStr,
    )
    print "\nDispatching message correctly; CmdVar done so only KeyVar callbacks should be called:"
    kvd.dispatchReply(reply)
    
    print "\nTesting keyVar refresh"
    kvd.refreshAllVar()
