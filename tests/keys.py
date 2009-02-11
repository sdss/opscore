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
		self.k3 = protoMess.Keyword('key3',['0xdead','0xbeef'])
		self.key1 = protoKeys.Key('key1')
		self.key2 = protoKeys.Key('key2', protoTypes.Float())
		self.key3 = protoKeys.Key('key3', protoTypes.Hex()*2)

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
		self.assertRaises(protoKeys.KeysError,lambda: self.key3.create(0xdead,-1.2))
		self.assertRaises(protoKeys.KeysError,lambda: self.key3.create(-1.2,'0xdead'))

if __name__ == '__main__':
	unittest.main()
