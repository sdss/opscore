#!/usr/bin/env python
"""
Unit tests for opscore.actor.KeyVarDispatcher
"""
import unittest

try:
    import RO.Comm.Generic
    RO.Comm.Generic.setFramework("twisted")
except ImportError:
    # older version of RO
    pass
from opscore.actor import Model, KeyVarDispatcher

Model.setDispatcher(KeyVarDispatcher())
HubModel = Model("hub")

class ModelTests(unittest.TestCase):
    model = HubModel
    dispatcher = model.dispatcher

    def testDispatch(self):
        """Test dispatching"""
        # keywords are initialized to empty tuples or tuples of None
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVar = getattr(self.model, keyName)
            self.assertEquals(keyVar[:], (None,)*len(keyVar))

        replyStr = self.makeReplyStr(actor="badactor", dataStr="actors=calvin,hobbes; commanders=tu01.mice,tu02.men; users=anon,you,me; version=1.0; httpRoot=hub25m.apo, image/dir")
        self.dispatcher.dispatchReplyStr(replyStr)
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVar = getattr(self.model, keyName)
            self.assertEquals(keyVar[:], (None,)*len(keyVar))
        
        replyStr = self.makeReplyStr(actor="hub", dataStr="actors=calvin,hobbes; commanders=tu01.mice,tu02.men; users=anon,you,me; version=1.0; httpRoot=hub25m.apo, image/dir")
        self.dispatcher.dispatchReplyStr(replyStr)
        self.assertEquals(self.model.actors[:], ("calvin", "hobbes"))
        self.assertEquals(self.model.commanders[:], ("tu01.mice", "tu02.men"))
        self.assertEquals(self.model.users[:], ("anon", "you", "me"))
        self.assertEquals(self.model.version[:], ("1.0",))
        self.assertEquals(self.model.httpRoot[:], ("hub25m.apo", "image/dir"))
    
    def testGetKeyVarList(self):
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVarList = self.dispatcher.getKeyVarList("hub", keyName)
            self.assertEqual(len(keyVarList), 1)
            self.assertEqual(keyVarList[0], getattr(self.model, keyName))
        self.assertEquals(self.dispatcher.getKeyVarList("badactorname", "users"), [])
        self.assertEquals(self.dispatcher.getKeyVarList("hub", "badkeyvarname"), [])
    
    def testGetKeyVar(self):
        self.assertTrue(self.model.actors is self.dispatcher.getKeyVar("hub", "actors"))
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            keyVar = self.dispatcher.getKeyVar("hub", keyName)
            self.assertEqual(keyVar, getattr(self.model, keyName))
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "badactorname", "users")
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "hub", "badkeyvarname")
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "nonexistentKeyVar")
    
    def makeReplyStr(self, dataStr, cmdr="me.me", cmdID=0, actor="hub"):
        return "%s %d %s : %s" % (cmdr, cmdID, actor, dataStr)

if __name__ == "__main__":
   unittest.main()
