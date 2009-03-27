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
        self.key1 = protoKeys.Key('key1')
        self.key2 = protoKeys.Key('key2',protoTypes.Float())
        self.key3 = protoKeys.Key('key3',protoTypes.Hex()*2)
        self.c123 = protoMess.Command('cmd',keywords=[self.k1,self.k2,self.k3])
        self.c321 = protoMess.Command('cmd',keywords=[self.k3,self.k2,self.k1])
        self.c12v = protoMess.Command('cmd',keywords=[self.k1,self.k2],values=['1.23','0xbeef'])
        protoKeys.CmdKey.setKeys(protoKeys.KeysDictionary('<command>',(1,0),self.key2,self.key3))
        self.cmd1 = protoValid.Cmd('cmd','key1 <key2> <key3>')
        self.cmd2 = protoValid.Cmd('cmd','@key1 <key2> [<key3>]')
        self.cmd3 = protoValid.Cmd('cmd',protoTypes.Float(),protoTypes.Hex(),'(@key1 [<key2>]) [<key3>]')
    
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
            self.cmd1.create('key1',('key2','1.2'),('key3',['0xdead','0xbeef']),values=[1.2,2.3]))
        self.assertRaises(ValidationError,lambda:
            self.cmd3.create('key1',values=['abc','0xbeef']))

if __name__ == '__main__':
    unittest.main()
