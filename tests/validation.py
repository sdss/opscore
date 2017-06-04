#!/usr/bin/env python
"""Unit tests for opscore.protocols.validation
"""

# Created 7-Nov-2008 by David Kirkby (dkirkby@uci.edu)

import unittest

import opscore.protocols.keys as protoKeys
import opscore.protocols.messages as protoMess
import opscore.protocols.types as protoTypes
import opscore.protocols.validation as protoValid

class ValidationTest(unittest.TestCase):

    def setUp(self):
        self.k1 = protoMess.Keyword('key1')
        self.k2 = protoMess.Keyword('key2',['-1.2'])
        self.k3 = protoMess.Keyword('key3',['0xdead','0xbeef'])
        self.rawkey = protoMess.RawKeyword('raw;text=goes"here')
        self.key1 = protoKeys.Key('key1')
        self.key2 = protoKeys.Key('key2',protoTypes.Float())
        self.key3 = protoKeys.Key('key3',protoTypes.Hex()*2)
        self.c0 = protoMess.Command('cmd')
        self.c123 = protoMess.Command('cmd',keywords=[self.k1,self.k2,self.k3])
        self.c321 = protoMess.Command('cmd',keywords=[self.k3,self.k2,self.k1])
        self.c12v = protoMess.Command('cmd',
            keywords=[self.k1,self.k2],values=['1.23',0xbeef])
        self.raw1 = protoMess.Command('cmd',keywords=[self.rawkey])
        self.raw2 = protoMess.Command('cmd',keywords=[self.k1,self.rawkey])
        self.raw3 = protoMess.Command('cmd',keywords=[self.k1,self.k2,self.rawkey])
        self.raw4 = protoMess.Command('cmd',keywords=[self.k1,self.rawkey,self.k2])
        protoKeys.CmdKey.setKeys(
            protoKeys.KeysDictionary('<command>',(1,0),self.key2,self.key3))
        self.cmd0a = protoValid.Cmd('cmd',help='no keywords')
        self.cmd0b = protoValid.Cmd('cmd','',help='no keywords (empty keysformat)')
        self.cmd1 = protoValid.Cmd('cmd','key1 <key2> <key3>')
        self.cmd2 = protoValid.Cmd('cmd','@key1 <key2> [<key3>]')
        self.cmd3 = protoValid.Cmd('cmd',protoTypes.Float(),protoTypes.UInt(),
            '(@key1 [<key2>]) [<key3>]')

        self.cmd4 = protoValid.Cmd('cmd','key1 <key2>')
        self.cmd4.callbacks = []

        # key2 will never be matched here because it follows raw
        self.rawcmd = protoValid.Cmd('cmd','@[key1] raw [<key2>]')

    def test00(self):
        "Cmd validation passes"
        self.failUnless(self.cmd1.consume(self.c123))
        self.failUnless(self.cmd1.consume(self.c321))
        self.failUnless(self.cmd2.consume(self.c123))
        self.failUnless(self.cmd3.consume(self.c12v))
        self.failUnless(self.k2.values[0] == -1.2)
        self.failUnless(self.k3.values[0] == 0xdead)
        self.failUnless(self.k3.values[1] == 0xbeef)
        self.failUnless(self.c12v.values[0] == 1.23)
        self.failUnless(self.c12v.values[1] == 0xbeef)

    def test01(self):
        "Cmd validation fails"
        self.failIf(self.cmd1.consume(self.c12v))
        self.failIf(self.cmd2.consume(self.c321))
        self.failIf(self.cmd2.consume(self.c12v))
        self.failIf(self.cmd3.consume(self.c123))
        self.failIf(self.cmd3.consume(self.c321))

    def test02(self):
        "Cmd creation with valid args"
        self.assertEqual(self.c123,
            self.cmd1.create('key1',('key2','-1.2'),('key3',['0xdead','0xbeef'])))
        self.assertEqual(self.c321,
            self.cmd1.create(('key3','0xdead','0xbeef'),('key2',['-1.2']),'key1'))
        self.assertEqual(self.c12v,
            self.cmd3.create('key1',('key2',-1.2),values=[1.23,'0xbeef']))

    def test03(self):
        "Cmd creation with invalid keyword values"
        from opscore.protocols.keys import KeysError
        self.assertRaises(KeysError,lambda:
            self.cmd1.create('key1',('key2','abc'),('key3',['0xdead','0xbeef'])))
        self.assertRaises(KeysError,lambda:
            self.cmd1.create('key1',('key2','1.2'),('key3',['1.2','0xbeef'])))
        self.assertRaises(KeysError,lambda:
            self.cmd1.create('key1',('key2','1.2','2.3'),('key3',['0xdead','0xbeef'])))

    def test04(self):
        "Cmd creation with invalid keywords or command values"
        from opscore.protocols.validation import ValidationError
        self.assertRaises(ValidationError,lambda:
            self.cmd1.create(('key2','1.2'),('key3',['0xdead','0xbeef'])))
        self.assertRaises(ValidationError,lambda:
            self.cmd1.create('key4',('key2','1.2'),('key3',['0xdead','0xbeef'])))
        self.assertRaises(ValidationError,lambda:
            self.cmd1.create('key1',('key2','1.2'),
                ('key3',['0xdead','0xbeef']),values=[1.2,2.3]))
        self.assertRaises(ValidationError,lambda:
            self.cmd3.create('key1',values=['abc','0xbeef']))

    def test05(self):
        "Validate Cmd that takes no keywords"
        self.failUnless(self.cmd0a.consume(self.c0))
        self.failUnless(self.cmd0b.consume(self.c0))

    def test06(self):
        "Raw keyword validation"
        self.failUnless(self.rawcmd.consume(self.raw1))
        self.failUnless(self.rawkey.values[0] == 'raw;text=goes"here')
        self.failUnless(self.rawcmd.consume(self.raw2))
        self.failUnless(self.rawcmd.consume(self.raw3))
        self.failUnless(self.rawcmd.consume(self.raw4))

    def test07(self):
        "Test Cmd validation with extra keywords"
        self.failUnless(self.cmd4.match(self.c123))

        message, __ = self.cmd4.match(self.c123)
        self.assertTrue(len(message.extra_keywords) > 0)

if __name__ == '__main__':
    unittest.main()
