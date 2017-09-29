#!/usr/bin/env python
"""
Elementary unit tests for opscore.actor.CmdKeyVarDispatcher

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
from opscore.actor import Model, CmdKeyVarDispatcher, CmdVar

Model.setDispatcher(CmdKeyVarDispatcher())
HubModel = Model("hub")

class ModelTests(unittest.TestCase):
    model = HubModel
    dispatcher = model.dispatcher

    def testDispatch(self):
        """Test dispatching"""
        # keywords are initialized to empty tuples or tuples of None
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVar = getattr(self.model, keyName)
            self.assertEqual(keyVar[:], (None,)*len(keyVar))

        reply = self.dispatcher.makeReply(actor="badactor", dataStr="actors=calvin,hobbes; commanders=tu01.mice,tu02.men; users=anon,you,me; version=1.0; httpRoot=hub25m.apo, image/dir")
        self.dispatcher.dispatchReply(reply)
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVar = getattr(self.model, keyName)
            self.assertEqual(keyVar[:], (None,)*len(keyVar))
        
        reply = self.dispatcher.makeReply(actor="hub", dataStr="actors=calvin,hobbes; commanders=tu01.mice,tu02.men; users=anon,you,me; version=1.0; httpRoot=hub25m.apo, image/dir")
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
        cmdVar1 = CmdVar(actor="hub", cmdStr="command 1")
        self.dispatcher.executeCmd(cmdVar1)
        self.assertNotEqual(cmdVar1.cmdID, 0)
        self.assertTrue(not cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)
        reply = self.dispatcher.makeReply(actor="hub", cmdID=cmdVar1.cmdID, msgCode="i")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(not cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)
        reply = self.dispatcher.makeReply(actor="hub", cmdID=cmdVar1.cmdID + 1, msgCode=":")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(not cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)
        reply = self.dispatcher.makeReply(actor="hub", cmdID=cmdVar1.cmdID, msgCode=":")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(cmdVar1.isDone)
        self.assertTrue(not cmdVar1.didFail)

        cmdVar2 = CmdVar(actor="hub", cmdStr="command 2")
        self.dispatcher.executeCmd(cmdVar2)
        self.assertNotEqual(cmdVar2.cmdID, 0)
        self.assertTrue(not cmdVar2.isDone)
        self.assertTrue(not cmdVar2.didFail)
        reply = self.dispatcher.makeReply(actor="hub", cmdID=cmdVar2.cmdID, msgCode="f")
        self.dispatcher.dispatchReply(reply)
        self.assertTrue(cmdVar2.isDone)
        self.assertTrue(cmdVar2.didFail)
    
    def testAbortCmdByID(self):
        """test abortCmdByID"""
        cmdVar = CmdVar(actor="hub", cmdStr="a command")
        self.dispatcher.executeCmd(cmdVar)
        self.assertNotEqual(cmdVar.cmdID, 0)
        self.assertTrue(not cmdVar.isDone)
        self.assertTrue(not cmdVar.didFail)
        self.dispatcher.abortCmdByID(cmdVar.cmdID)
        self.assertTrue(cmdVar.isDone)
        self.assertTrue(cmdVar.didFail)


if __name__ == "__main__":
   unittest.main()
