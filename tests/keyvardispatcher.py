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
from RO.PVT import PVT

Model.setDispatcher(KeyVarDispatcher())
TCCModel = Model("tcc")


class ModelTests(unittest.TestCase):
    model = TCCModel
    dispatcher = model.dispatcher

    def testDispatch(self):
        """Test dispatching"""
        # keywords are initialized to empty tuples or tuples of None
        for keyName in ("axisConnState", "userNum", "version", "ut1"):
            keyVar = getattr(self.model, keyName)
            self.assertEqual(keyVar[:], (None,) * len(keyVar))

        replyStr = self.makeReplyStr(actor="badactor", dataStr="userNum=5; version=1.0")
        self.dispatcher.dispatchReplyStr(replyStr)
        for keyName in ("userNum", "version"):
            keyVar = getattr(self.model, keyName)
            self.assertEqual(keyVar[:], (None,) * len(keyVar))

        replyStr = self.makeReplyStr(
            actor="tcc",
            dataStr="tccPos=123.4, 45.6, -23.4; userNum=5; version=1.0; convAng=1.1, 0.22, 1234.5",
        )
        self.dispatcher.dispatchReplyStr(replyStr)
        for i in range(3):
            self.assertAlmostEqual(self.model.tccPos[i], (123.4, 45.6, -23.4)[i])
            self.assertEqual(type(self.model.tccPos[i]), float)
        self.assertEqual(self.model.userNum[0], 5)
        self.assertEqual(type(self.model.userNum[0]), int)
        self.assertEqual(self.model.version[0], "1.0")
        self.assertEqual(type(self.model.version[0]), str)
        convAng = self.model.convAng[0]
        self.assertAlmostEqual(convAng.pos, 1.1)
        self.assertAlmostEqual(convAng.vel, 0.22)
        self.assertAlmostEqual(convAng.t, 1234.5)
        self.assertEqual(type(convAng), PVT)

    def testInvalidValues(self):
        """Test that invalid values map to None (but invalid PVTs map to invalid PVTs)"""
        replyStr = self.makeReplyStr(
            actor="tcc", dataStr="tccPos=nan, nan, nan; convAng=1.1, 0.22, nan"
        )
        self.dispatcher.dispatchReplyStr(replyStr)
        for i in range(3):
            self.assertTrue(self.model.tccPos[i] is None)
        self.assertFalse(self.model.convAng[0].isValid())

    def testGetKeyVarList(self):
        for keyName in ("userNum", "version", "convAng"):
            keyVarList = self.dispatcher.getKeyVarList("tcc", keyName)
            self.assertEqual(len(keyVarList), 1)
            self.assertEqual(keyVarList[0], getattr(self.model, keyName))
        self.assertEqual(self.dispatcher.getKeyVarList("badactorname", "users"), [])
        self.assertEqual(self.dispatcher.getKeyVarList("tcc", "badkeyvarname"), [])

    def testGetKeyVar(self):
        for keyName in ("convAng", "userNum", "version"):
            keyVar = self.dispatcher.getKeyVar("tcc", keyName)
            self.assertEqual(keyVar, getattr(self.model, keyName))
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "badactorname", "users")
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "tcc", "badkeyvarname")
        self.assertRaises(Exception, self.dispatcher.getKeyVar, "nonexistentKeyVar")

    def makeReplyStr(self, dataStr, cmdr="me.me", cmdID=0, actor="tcc"):
        return "%s %d %s : %s" % (cmdr, cmdID, actor, dataStr)


if __name__ == "__main__":
    unittest.main()
