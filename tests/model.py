#!/usr/bin/env python
"""
Unit tests for opscore.actor.Model
"""
import unittest

try:
    import opscore.RO.Comm.Generic

    opscore.RO.Comm.Generic.setFramework("twisted")
except ImportError:
    # older version of RO
    pass
from opscore.actor import Model, KeyVarDispatcher


class ModelTests(unittest.TestCase):
    def testModel(self):
        """Test most or all aspects of Model"""
        self.assertRaises(Exception, Model, "hub")  # no dispatcher set

        Model.setDispatcher(KeyVarDispatcher())
        model = Model("hub")
        for keyName in ("actors", "commanders", "user", "users", "version", "httpRoot"):
            if not hasattr(model, keyName):
                self.fail("model is missing attribute %s" % (keyName,))
        self.assertEqual(model.actor, "hub")

        newDispatcher = KeyVarDispatcher()
        self.assertRaises(Exception, Model.setDispatcher, newDispatcher)  # already set
        self.assertRaises(Exception, Model, "hub")  # already added

        keyNames = set(model.keyVarDict.keys())
        self.assertTrue(
            keyNames
            > set(("actors", "commanders", "user", "users", "version", "httpRoot"))
        )


if __name__ == "__main__":
    unittest.main()
