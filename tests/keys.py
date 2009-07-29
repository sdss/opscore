#!/usr/bin/env python
"""Unit tests for opscore.protocols.keys
"""

# Created 18-Nov-2008 by David Kirkby (dkirkby@uci.edu)

import unittest
import opscore.protocols.keys as protoKeys
import opscore.protocols.messages as protoMess
import opscore.protocols.types as protoTypes

class KeysTest(unittest.TestCase):

    def setUp(self):
        self.k1 = protoMess.Keyword('key1')
        self.k2 = protoMess.Keyword('key2',['-1.2'])
        self.k3 = protoMess.Keyword('key3',[0xdead,0xbeef])
        self.key1 = protoKeys.Key('Key1')
        self.key2 = protoKeys.Key('Key2', protoTypes.Float())
        self.key3 = protoKeys.Key('Key3', protoTypes.UInt()*2)

    def test00(self):
        "Key validation passes"
        self.failUnless(self.key1.consume(self.k1))
        self.failUnless(self.key2.consume(self.k2))
        self.failUnless(self.key3.consume(self.k3))
        self.failUnless(len(self.k1.values) == 0)
        self.failUnless(self.k2.values[0] == -1.2)
        self.failUnless(self.k3.values[0] == 0xdead)
        self.failUnless(self.k3.values[1] == 0xbeef)

    def test01(self):
        "Key validation fails"
        self.failIf(self.key1.consume(self.k2))
        self.failIf(self.key1.consume(self.k3))
        self.failIf(self.key2.consume(self.k1))
        self.failIf(self.key2.consume(self.k3))
        self.failIf(self.key3.consume(self.k1))
        self.failIf(self.key3.consume(self.k2))

    def test02(self):
        "Keyword creation with a list of valid string values"
        self.assertEqual(self.key1.create([]),self.k1)
        self.assertEqual(self.key2.create(['-1.2']),self.k2)
        self.assertEqual(self.key3.create(['0xdead','0xbeef']),self.k3)

    def test03(self):
        "Keyword creation with varargs valid string values"
        self.assertEqual(self.key1.create(),self.k1)
        self.assertEqual(self.key2.create('-1.2'),self.k2)
        self.assertEqual(self.key3.create('0xdead','0xbeef'),self.k3)

    def test04(self):
        "Keyword creation with valid typed values"
        self.assertEqual(self.key2.create(-1.2),self.k2)
        self.assertEqual(self.key3.create(0xdead,0xbeef),self.k3)
        self.assertEqual(self.key3.create('0xdead',0xbeef),self.k3)
        self.assertEqual(self.key3.create([0xdead,'0xbeef']),self.k3)

    def test05(self):
        "Keyword creation with wrong number of values"
        self.assertRaises(protoKeys.KeysError,lambda: self.key1.create(-1.2))
        self.assertRaises(protoKeys.KeysError,lambda: self.key2.create())
        self.assertRaises(protoKeys.KeysError,lambda: self.key3.create('0xdead'))

    def test06(self):
        "Keyword creation with wrong value types"
        self.assertRaises(protoKeys.KeysError,lambda: self.key2.create('abc'))
        self.assertRaises(protoKeys.KeysError,lambda: self.key3.create(0xdead,'abc'))
        self.assertRaises(protoKeys.KeysError,lambda: self.key3.create('abc','0xdead'))
        
    def test07(self):
        "Read testing dictionary"
        kdict = protoKeys.KeysDictionary.load("testing")
        self.failUnless('unsigned' in kdict)
        self.failUnless('UnSigned' in kdict)
        
    def test08(self):
        "Generic compound value type without explicit wrapper"
        msgKey = protoKeys.Key('msg',protoTypes.CompoundValueType(
            protoTypes.Enum('INFO','WARN','ERROR',name='code'),
            protoTypes.String(name='text')
        ))
        msg = protoMess.Keyword('msg',['INFO','Hello, world'])
        self.failUnless(msgKey.consume(msg))
        self.assertEqual(len(msg.values),1)
        self.failUnless(isinstance(msg.values[0],tuple))
        self.failUnless(msg.values[0] == ('INFO','Hello, world'))
    
    def test09(self):
        "Generic compound value type with explicit wrapper"
        class Wrapped(object):
            def __init__(self,code,text):
                pass
        msgKey = protoKeys.Key('msg',protoTypes.CompoundValueType(
            protoTypes.Enum('INFO','WARN','ERROR',name='code'),
            protoTypes.String(name='text'),
            wrapper = Wrapped
        ))
        msg = protoMess.Keyword('msg',['INFO','Hello, world'])
        self.failUnless(msgKey.consume(msg))
        self.assertEqual(len(msg.values),1)
        self.failUnless(isinstance(msg.values[0],Wrapped))

    def test10(self):
        "Generic compound value type with wrapping disabled"
        msgKey = protoKeys.Key('msg',protoTypes.CompoundValueType(
            protoTypes.Enum('INFO','WARN','ERROR',name='code'),
            protoTypes.String(name='text')
        ))
        msg = protoMess.Keyword('msg',['INFO','Hello, world'])
        protoTypes.CompoundValueType.WrapEnable = False
        self.failUnless(msgKey.consume(msg))
        protoTypes.CompoundValueType.WrapEnable = True
        self.assertEqual(len(msg.values),2)
        self.failUnless(msg.values[0] == 'INFO')
        self.failUnless(msg.values[1] == 'Hello, world')
        
    def test11(self):
        "PVT test"
        pvtKey = protoKeys.Key('pvtMsg',protoTypes.PVT(),protoTypes.Float())
        msg = protoMess.Keyword('pvtMsg',[1,2,3,4])
        self.failUnless(pvtKey.consume(msg))
        self.assertEqual(len(msg.values),2)
        import RO.PVT
        self.failUnless(isinstance(msg.values[0],RO.PVT.PVT))
        self.assertEqual(repr(msg.values[0]),repr(RO.PVT.PVT(1,2,3)))
        self.assertEqual(msg.values[1],4)

if __name__ == '__main__':
    unittest.main()
