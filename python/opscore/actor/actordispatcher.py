"""A single-actor version of CmdKeyVarDispatcher.

Send commands to a single actor and dispatches replies from that actor.

History:
2012-07-24 ROwen
2015-11-05 ROwen    Change default for ActorDispatcher._myUserID to 0 if yourUserIDKeyName is None;
                    0 works for actors that only support a single user (which is the usual reason
                    to not have a keyword for your user ID).
                    Added from __future__ import and removed commented-out print statements.
"""

import sys
import traceback

import opscore.RO.Constants
from opscore.protocols.keys import KeysDictionary
from opscore.protocols.parser import ActorReplyParser
from opscore.RO.StringUtil import strFromException

from .cmdkeydispatcher import CmdKeyVarDispatcher
from .keydispatcher import KeyVarDispatcher
from .keyvar import KeyVar, MsgCodeSeverity


__all__ = ["ActorDispatcher"]


class SimpleModel(object):
    """Model for an ActorDispatcher

    This is a variant opscore.actor.Model that has no common registry
    and knows nothing about refresh commands. It is intended for use with ActorDispatcher.

    The actor's keyword variables are available as named attributes.
    """

    def __init__(self, dispatcher):
        self._keyNameVarDict = dict()
        self.dispatcher = dispatcher
        self.actor = dispatcher.name

        keysDict = KeysDictionary.load(self.actor)
        for key in keysDict.keys.values():
            keyVar = KeyVar(self.actor, key)
            self.dispatcher.addKeyVar(keyVar)
            setattr(self, keyVar.name, keyVar)

    @property
    def keyVarDict(self):
        """Return a dictionary of keyVar name:keyVar"""
        retDict = dict()
        for name, item in self.__dict__.items():
            if isinstance(item, KeyVar):
                retDict[name] = item
        return retDict


class ActorDispatcher(CmdKeyVarDispatcher):
    """Parse replies and sets KeyVars. Also manage CmdVars and their replies.

    Fields:
    - readUnixTime: unix time at which last message received from connection;
      0 if no message ever received.
    """

    _ParserClass = ActorReplyParser

    def __init__(
        self,
        name,
        connection=None,
        logFunc=None,
        yourUserIDKeyName="yourUserID",
    ):
        """Create a new ActorDispatcher

        Inputs:
        - name: actor name; must have an associated dictionary in actorkeys.
        - connection: an RO.Comm.HubConnection object or similar;
          if omitted, a NullConnection is used, which is useful for testing.
        - logFunc: a function that logs a message. Argument list must be:
            (msgStr, severity, actor, cmdr)
            where the first argument is positional and the others are by name
            and severity is an RO.Constants.sevX constant
            If None then nothing is logged.
        - yourUserIDKeyName: name of keyword variable that provides your user ID;
            if the actor provides no such kewyord then specify None, and if the actor
            supports multiple users then set self._myUserID manually to the correct value.

        Raises ValueError if name has no actor dictionary in actorkeys.
        """
        self._myUserID = None
        CmdKeyVarDispatcher.__init__(
            self,
            name=name,
            connection=connection,
            logFunc=logFunc,
            includeName=False,
            delayCallbacks=False,
        )

        self.model = SimpleModel(self)

        if yourUserIDKeyName:
            yourUserIDKeyVar = getattr(self.model, yourUserIDKeyName)
            yourUserIDKeyVar.addCallback(self._yourUserIDKeyVarCallback)
        else:
            # assume actor only supports one user
            self._myUserID = 0

        if self.refreshCmdDict:
            raise RuntimeError(
                "Internal error: refreshCmdDict should be empty but contains %s"
                % (self.refreshCmdDict,)
            )

        # start background tasks
        self.checkCmdTimeouts()

    def addKeyVar(self, keyVar):
        """Add a keyword variable (opscore.actor.keyvar.KeyVar) to the collection.

        This variant ignores the refresh command.

        Inputs:
        - keyVar: the keyword variable (opscore.actor.keyvar.KeyVar)
        """
        if keyVar.actor != self.name:
            raise RuntimeError(
                "keyVar.actor=%r; this actor dispatcher only handles actor %r"
                % (keyVar.actor, self.name)
            )
        KeyVarDispatcher.addKeyVar(self, keyVar)

    def logReply(self, reply, fallbackToStdOut=False):
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
            severity = MsgCodeSeverity[msgCode]
            self.logMsg(
                msgStr=reply.string,
                severity=severity,
                keywords=reply.keywords,
                cmdID=reply.header.commandId,
                fallbackToStdOut=fallbackToStdOut,
            )
        except Exception as e:
            sys.stderr.write(
                "Could not log reply=%r\n    error=%s\n" % (reply, strFromException(e))
            )
            traceback.print_exc(file=sys.stderr)

    def replyIsMine(self, reply):
        """Return True if I am the commander for this message."""
        return reply.header.userId == self._myUserID

    def refreshAllVar(self, resetAll=True):
        """Disable refresh, since there is no hub and hence no keys cache

        Inputs:
        - resetAll: reset all keyword variables to notCurrent
        """
        if resetAll:
            for keyVarList in list(self.keyVarListDict.values()):
                for keyVar in keyVarList:
                    keyVar.setNotCurrent()

    def setKeyVarsFromReply(self, reply, doCallbacks=True):
        """Set KeyVars based on the supplied Reply

        reply is a parsed Reply object (opscore.protocols.messages.Reply)
        """
        for keyword in reply.keywords:
            keyVarList = self.getKeyVarList(self.name, keyword.name)
            for keyVar in keyVarList:
                try:
                    keyVar.set(
                        keyword.values,
                        isGenuine=True,
                        reply=reply,
                        doCallbacks=doCallbacks,
                    )
                except TypeError:
                    self.logMsg(
                        "InvalidKeywordData=%s.%s, %s"
                        % (self.name, keyword.name, keyword.values),
                        severity=opscore.RO.Constants.sevError,
                        fallbackToStdOut=True,
                    )
                except Exception:
                    print("Failed to set %s to %s:" % (keyVar, keyword.values))
                    traceback.print_exc(file=sys.stderr)

    def _formatCmdStr(self, cmdVar):
        """Format a command; one-actor version"""
        return "%d %s" % (cmdVar.cmdID, cmdVar.cmdStr)

    def _formatReplyHeader(
        self,
        cmdr=None,
        cmdID=0,
        actor=None,
        msgCode="F",
        dataStr="",
    ):
        """Format a reply header; one-actor version"""
        id = self._myUserID or 0
        return "%d %d %s" % (cmdID, id, msgCode)

    def _yourUserIDKeyVarCallback(self, keyVar):
        """Set _myUserID based on the keyVar; called by the keyVar specified by yourUserIDKeyName"""
        self._myUserID = keyVar[0]
