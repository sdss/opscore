#!/usr/bin/env python
"""
Keys format string parser for SDSS-3 command validation

Refer to https://trac.sdss3.org/wiki/Ops/Validation for details.
"""

# Created 18-Nov-2008 by David Kirkby (dkirkby@uci.edu)

import unittest
import opscore.protocols.keys as protoKeys
import opscore.protocols.keysformat as protoKeysFormat

class KeysFormatTest(unittest.TestCase):

	def setUp(self):
		self.p = protoKeysFormat.KeysFormatParser()

	def test00(self):
		"Valid format string without dict"
		self.p.parse("key1 key2 key3")
		self.p.parse("key1 key2 [key3]")
		self.p.parse("key1 (key2 [key3])")
		self.p.parse("@key1 key2 key3")
		self.p.parse("key1 [@key2 [key3]]")

	def test01(self):
		"Valid format string with dict"
		from opscore.protocols.keys import KeysDictionary
		protoKeys.CmdKey.setKeys(KeysDictionary("<command>",protoKeys.Key("key1"),protoKeys.Key("key2"),protoKeys.Key("key3")))
		self.p.parse("<key1> <key2> <key3>")
		self.p.parse("<key1> <key2> [<key3>]")
		self.p.parse("<key1> (<key2> [<key3>])")
		self.p.parse("@<key1> <key2> <key3>")
		self.p.parse("<key1> [@<key2> [<key3>]]")		
		
unittest.main()
