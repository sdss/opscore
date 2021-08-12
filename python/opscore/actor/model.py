"""A Model is a container for keyVars for an actor

History:
2009-03-30 ROwen
2009-07-18 ROwen    Modified to set the refreshCmd for each keyVar
                    before adding it to the dispatcher.
2009-07-18 ROwen    Added keyVarDict property.
2010-06-28 ROwen    Removed many unused imports (thanks to pychecker).
2012-07-24 ROwen    Improved the documentation
2015-11-03 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-05 ROwen    Added from __future__ import and removed commented-out print statements.
                    Removed initial #! line.
"""

from opscore.protocols.keys import KeysDictionary

from .keyvar import KeyVar


__all__ = ["Model"]

# number of keywork names to ask for in a given "keys getFor=actor" command
NumKeysToGetAtOnce = 20


class Model(object):
    """Model for an actor.

    The actor's keyword variables are available as named attributes.
    In addition, registers the actor's keyword variables with the dispatcher.

    Warnings:
    * You must have only one instance of this class per actor.
    * Before instantiating the first model, call setDispatcher (else you'll get a RuntimeError).
    * Only keyVars defined in the actor's dictionary are refreshed automatically.
      Any keyVars you add to the subclass are synthetic keyVars that you should set yourself.
    """

    _registeredActors = set()
    dispatcher = None

    def __init__(self, actor):
        self._keyNameVarDict = dict()
        if actor in self._registeredActors:
            raise RuntimeError("%s model already instantiated" % (actor,))

        self.actor = actor
        if self.dispatcher is None:
            raise RuntimeError("Dispatcher not set")

        cachedKeyVars = []
        keysDict = KeysDictionary.load(actor)
        for key in keysDict.keys.values():
            keyVar = KeyVar(actor, key)
            if key.doCache and not keyVar.hasRefreshCmd:
                cachedKeyVars.append(keyVar)
            else:
                self.dispatcher.addKeyVar(keyVar)
            setattr(self, keyVar.name, keyVar)

        for ind in range(0, len(cachedKeyVars), NumKeysToGetAtOnce):
            keyVars = cachedKeyVars[ind : ind + NumKeysToGetAtOnce]
            keyNames = [(kv.name) for kv in keyVars]
            refreshCmdStr = "getFor=%s %s" % (self.actor, " ".join(keyNames))
            for keyVar in keyVars:
                keyVar.refreshActor = "keys"
                keyVar.refreshCmd = refreshCmdStr
                self.dispatcher.addKeyVar(keyVar)

        self._registeredActors.add(actor)

    @property
    def keyVarDict(self):
        """Return a dictionary of keyVar name:keyVar"""
        retDict = dict()
        for name, item in self.__dict__.items():
            if isinstance(item, KeyVar):
                retDict[name] = item
        return retDict

    @classmethod
    def setDispatcher(cls, dispatcher):
        """Set the keyword dispatcher.

        Inputs:
        - dispatcher: a keyword dispatcher. An instance of KeyVarDispatcher or a subclass

        Warning: must be called exactly once, before instantiating the first Model.
        """
        if cls.dispatcher:
            raise RuntimeError("Dispatcher cannot be modified once set")
        cls.dispatcher = dispatcher
