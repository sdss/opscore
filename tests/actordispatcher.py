#!/usr/bin/env python
"""
Elementary unit tests for opscore.actor.ActorDispatcher

For more elaborate tests, such as testing command timeouts, it would be necessary to run an event loop,
e.g. run this test with Twisted trial, to test command timeouts.
"""
import unittest

try:
    import RO.Comm.Generic

    RO.Comm.Generic.setFramework("twisted")
except ImportError:
    # older version of RO
    pass
from opscore.actor import Model, ActorDispatcher, CmdVar

HubDispatcher = ActorDispatcher("hub", yourUserIDKeyName=None)
HubDispatcher._myUserID = 0


class ModelTests(unittest.TestCase):
    model = HubDispatcher.model
    dispatcher = model.dispatcher

    def testDispatch(self):
        """Test dispatching"""
        # keywords are initialized to empty tuples or tuples of None
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVar = getattr(self.model, keyName)
            self.assertEqual(keyVar[:], (None,) * len(keyVar))

        reply = self.dispatcher.makeReply(
            dataStr="actors=calvin,hobbes; commanders=tu01.mice,tu02.men; users=anon,you,me; version=1.0; httpRoot=hub25m.apo, image/dir"
        )
        self.dispatcher.dispatchReply(reply)
        self.assertEqual(self.model.actors[:], ("calvin", "hobbes"))
        self.assertEqual(self.model.commanders[:], ("tu01.mice", "tu02.men"))
        self.assertEqual(self.model.users[:], ("anon", "you", "me"))
        self.assertEqual(self.model.version[:], ("1.0",))
        self.assertEqual(self.model.httpRoot[:], ("hub25m.apo", "image/dir"))

    def testGetKeyVarList(self):
        """test getKeyVarList"""
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVarList = self.dispatcher.getKeyVarList("hub", keyName)
            self.assertEqual(len(keyVarList), 1)
            self.assertEqual(keyVarList[0], getattr(self.model, keyName))
        self.assertEqual(self.dispatcher.getKeyVarList("badactorname", "users"), [])
        self.assertEqual(self.dispatcher.getKeyVarList("hub", "badkeyvarname"), [])

    def testGetKeyVar(self):
        """test getKeyVar"""
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVar = self.dispatcher.getKeyVar("hub", keyName)
            self.assertEqual(keyVar, getattr(self.model, keyName))
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "badactorname", "users")
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "hub", "badkeyvarname")

    def testExecuteCmd(self):
        """test executeCmd

        More complete testing would require an event loop
        """
        cmdVar1 = CmdVar(cmdStr="command 1")
        self.dispatcher.executeCmd(cmdVar1)
        self.assertNotEqual(cmdVar1.cmdID, 0)
        self.assertTrue(not cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)
        reply = self.dispatcher.makeReply(cmdID=cmdVar1.cmdID, msgCode="i")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(not cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)
        reply = self.dispatcher.makeReply(cmdID=cmdVar1.cmdID + 1, msgCode=":")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(not cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)
        reply = self.dispatcher.makeReply(cmdID=cmdVar1.cmdID, msgCode=":")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)

        cmdVar2 = CmdVar(cmdStr="command 2")
        self.dispatcher.executeCmd(cmdVar2)
        self.assertNotEqual(cmdVar2.cmdID, 0)
        self.assertTrue(not cmdVar2.isDone)
        self.assertTrue(not cmdVar2.didFail)
        reply = self.dispatcher.makeReply(cmdID=cmdVar2.cmdID, msgCode="f")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(cmdVar2.isDone)
        self.assertTrue(cmdVar2.didFail)

    def testAbortCmdByID(self):
        """test abortCmdByID"""
        cmdVar = CmdVar(cmdStr="a command")
        self.dispatcher.executeCmd(cmdVar)
        self.assertNotEqual(cmdVar.cmdID, 0)
        self.assertTrue(not cmdVar.isDone)
        self.assertTrue(not cmdVar.didFail)
        self.dispatcher.abortCmdByID(cmdVar.cmdID)
        self.assertTrue(cmdVar.isDone)
        self.assertTrue(cmdVar.didFail)

    def testWrongActorModel(self):
        """Test that we can only add the correct model to this dispatcher"""
        self.assertRaises(Exception, Model, "apo")

    def testModel(self):
        """Test most or all aspects of the model (an instance of SimpleModel)"""
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            if not hasattr(self.model, keyName):
                self.fail("model is missing attribute %s" % (keyName,))
        self.assertEqual(self.model.actor, "hub")

        keyNames = set(self.model.keyVarDict.keys())
        self.assertTrue(
            keyNames
            > set(("actors", "commanders", "user", "users", "version", "httpRoot"))
        )


if __name__ == "__main__":
    unittest.main()
