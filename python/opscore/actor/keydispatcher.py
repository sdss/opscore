"""Sets KeyVars based on replies from the hub.

History:
2009-04-03 ROwen    Split out basic functionality from full dispatcher.
2009-07-18 ROwen    Added __all__.
2009-07-23 ROwen    Added doCallbacks argument to dispatchReply and dispatchReplyStr
                    to support delayCallbacks in CmdKeyVarDispatcher.
2010-07-20 ROwen    Improved the diagnostic output if a keyword's values cannot be set.
2010-11-18 ROwen    Added setLogFunc, logMsg, logReply methods from CmdKeyDispatcher.
                    Added name field from CmdKeyDispatcher.
                    Added logToStdOut function.
                    Modified dispatchReply to log an error (instead of printing a traceback)
                    when the values for a keyword are invalid.
2011-02-02 ROwen    API change: added keywords to logging function argument list.
                    Enhanced dispatchReplyStr's error handling and reporting to match
                    CmdKeyDispatcher.
                    Changed dispatchReply to log its replies, instead of CmdKeyDispatcher.
                    Added setKeyVarsFromReply which is called by dispatchReply.
2011-06-13 ROwen    API change: added cmdID to the logging function argument list.
2012-07-24 ROwen    Added _ParserClass class attribute.
2012-09-21 ROwen    Removed __main__ example code; use the unit test instead.
2015-11-03 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-05 ROwen    Added from __future__ import and removed commented-out print statements.
                    Removed initial #! line.
"""

import sys
import traceback

import opscore.protocols.messages
import opscore.RO.Constants
from opscore.protocols.parser import ReplyParser
from opscore.RO.StringUtil import strFromException

from .keyvar import MsgCodeSeverity


__all__ = ["logToStdOut", "KeyVarDispatcher"]


def logToStdOut(msgStr, *dumArgs, **dumKeyArgs):
    print(msgStr)


class KeyVarDispatcher(object):
    """Parse replies and set KeyVars."""

    _ParserClass = ReplyParser

    def __init__(
        self,
        name="KeyVarDispatcher",
        logFunc=None,
    ):
        """Create a new KeyVarDispatcher

        Inputs:
        - name: dispatcher name; must be a valid actor name (_ is OK; avoid other
                punctuation and whitespace).
            Used as the default actor for logMsg.
        - logFunc: a function that logs a message. Argument list must be:
            (msgStr, severity, actor, cmdr, keywords)
            where the first argument is positional and the others are by name
            and severity is an RO.Constants.sevX constant
            If None then nothing is logged.
            See logMsg for details on the arguments.
        """
        self.name = str(name)
        self.parser = self._ParserClass()

        # dictionary of lists of KeyVars; keys are as returned by _makeDictKey;
        # values are lists of KeyVars
        # (having a list of KeyVars allows more than one KeyVar for the same actor keyword,
        # which is a historical feature that is probably not needed)
        self.keyVarListDict = dict()

        self.setLogFunc(logFunc)

    def addKeyVar(self, keyVar):
        """
        Adds a keyword variable (opscore.actor.keyvar.KeyVar) to the collection.

        Inputs:
        - keyVar: the keyword variable (opscore.actor.keyvar.KeyVar)
        """
        dictKey = self._makeDictKey(keyVar.actor, keyVar.name)
        # get list of existing keyVars with the same actor and keyword name,
        # adding an empty list to self.keyVarListDict if none are already present
        keyList = self.keyVarListDict.setdefault(dictKey, [])
        # append new keyVar to the list
        keyList.append(keyVar)

    def dispatchReply(self, reply, doCallbacks=True):
        """Log the reply and set KeyVars based on the supplied Reply

        reply is a parsed Reply object (opscore.protocols.messages.Reply)
        """
        self.logReply(reply)
        self.setKeyVarsFromReply(reply, doCallbacks=doCallbacks)

    def dispatchReplyStr(self, replyStr):
        """Read, parse and dispatch a message from the hub.

        If parsing fails then log an error message.
        If dispatching fails then log an error message and print a traceback to stderr.
        """
        # parse message; if that fails, log it as an error
        try:
            reply = self.parser.parse(replyStr.decode())
        except Exception as e:
            self.logMsg(
                msgStr="CouldNotParse; Reply=%r; Text=%r"
                % (replyStr, strFromException(e)),
                severity=opscore.RO.Constants.sevError,
            )
            return

        # dispatch message
        try:
            self.dispatchReply(reply)
        except Exception:
            sys.stderr.write(
                "Could not dispatch replyStr=%r\n    which was parsed as reply=%r\n"
                % (replyStr, reply)
            )
            traceback.print_exc(file=sys.stderr)

    def getKeyVarList(self, actor, keyName):
        """Return the list of KeyVars by this name and actor; return [] if no match.

        Do not modify the returned list. It may not be a copy.
        """
        return self.keyVarListDict.get(self._makeDictKey(actor, keyName), [])

    def getKeyVar(self, actor, keyName):
        """Return a keyVar by this name and actor.

        If there are multiple matching keyVars returns the first registered;
        to get a different keyVar use getKeyVarList.

        Raise LookupError if no such keyword found.
        """
        keyVarList = self.getKeyVarList(actor, keyName)
        if not keyVarList:
            raise LookupError(
                "Could not find a keyVar with actor=%s, keyName=%s" % (actor, keyName)
            )
        return keyVarList[0]

    def logMsg(
        self,
        msgStr,
        severity=opscore.RO.Constants.sevNormal,
        actor=None,
        cmdr=None,
        cmdID=0,
        keywords=None,
        fallbackToStdOut=False,
    ):
        """Writes a message to the log.
        On error, prints an error message that includes the original message data
        plus a traceback to stderr and returns normally.

        Inputs:
        - msgStr: message to display; a final \n is appended
        - severity: message severity (an RO.Constants.sevX constant)
        - actor: name of actor
        - cmdr: commander; defaults to self
        - cmdID: command ID; defaults to 0
        - keywords: parsed keywords (an opscore.protocols.messages.Keywords);
            warning: this is not KeyVars from the model; it is lower-level data
        - fallbackToStdOut: if True and there is no logFunc then prints the message to stdout.
        """
        if actor is None:
            actor = self.name
        if keywords is None:
            keywords = opscore.protocols.messages.Keywords()

        if not self.logFunc:
            if fallbackToStdOut:
                logToStdOut(
                    msgStr,
                    severity=severity,
                    actor=actor,
                    cmdr=cmdr,
                    cmdID=cmdID,
                    keywords=keywords,
                )
            return

        try:
            self.logFunc(
                msgStr,
                severity=severity,
                actor=actor,
                cmdr=cmdr,
                cmdID=cmdID,
                keywords=keywords,
            )
        except Exception as e:
            sys.stderr.write(
                "Could not log msgStr=%r; severity=%r; actor=%r; "
                "cmdr=%r; keywords=%r\n    error: %s\n"
                % (msgStr, severity, actor, cmdr, keywords, strFromException(e))
            )
            traceback.print_exc(file=sys.stderr)

    def logReply(self, reply, fallbackToStdOut=False):
        """Log a reply (an opscore.protocols.messages.Reply)

        Inputs:
        - reply is a parsed Reply object (opscore.protocols.messages.Reply)
        - fallbackToStdOut: if True and there is no logFunc then prints the message to stdout.
        """
        try:
            msgCode = reply.header.code
            severity = MsgCodeSeverity[str(msgCode)]
            self.logMsg(
                msgStr=reply.string,
                severity=severity,
                keywords=reply.keywords,
                actor=reply.header.actor,
                cmdr=reply.header.cmdrName,
                cmdID=reply.header.commandId,
                fallbackToStdOut=fallbackToStdOut,
            )
        except Exception as e:
            sys.stderr.write(
                "Could not log reply=%r\n    error=%s\n" % (reply, strFromException(e))
            )
            traceback.print_exc(file=sys.stderr)

    def removeKeyVar(self, keyVar):
        """Remove the specified keyword variable, returning the KeyVar if removed, else None

        See also "addKeyVar".

        Inputs:
        - keyVar: the keyword variable to remove

        Returns:
        - the removed keyVar, if present, None otherwise.
        """
        dictKey = self._makeDictKey(keyVar.actor, keyVar.name)
        keyVarList = self.keyVarListDict.get(dictKey, [])
        if keyVar in keyVarList:
            keyVarList.remove(keyVar)
            return keyVar
        else:
            return None

    def setKeyVarsFromReply(self, reply, doCallbacks=True):
        """Set KeyVars based on the supplied Reply

        reply is a parsed Reply object (opscore.protocols.messages.Reply)
        """
        #         print "dispatchReply(reply=%s, doCallbacks=%s)" % (reply, doCallbacks)
        actor = reply.header.actor.lower()
        if actor.startswith("keys_"):
            # data is from the hub's keyword cache
            actor = actor[5:]
            isGenuine = False
        else:
            isGenuine = True
        for keyword in reply.keywords:
            keyVarList = self.getKeyVarList(actor, keyword.name)
            for keyVar in keyVarList:
                try:
                    keyVar.set(
                        keyword.values,
                        isGenuine=isGenuine,
                        reply=reply,
                        doCallbacks=doCallbacks,
                    )
                except TypeError:
                    self.logMsg(
                        "InvalidKeywordData=%s.%s, %s"
                        % (actor, keyword.name, keyword.values),
                        severity=opscore.RO.Constants.sevError,
                        fallbackToStdOut=True,
                    )
                except Exception:
                    print("Failed to set %s to %s:" % (keyVar, keyword.values))
                    traceback.print_exc(file=sys.stderr)

    def setLogFunc(self, logFunc=None):
        """Set the log output device, or clears it if None specified.

        The function must take the following arguments: (msgStr, severity, actor, cmdr)
        where the first argument is positional and the others are by name
        """
        self.logFunc = logFunc

    @staticmethod
    def _makeDictKey(actor, keyName):
        """Make a keyVarListDict key out of an actor and keyword name"""
        return (actor.lower(), keyName.lower())
