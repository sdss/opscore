#!/usr/bin/env python
"""
Unit tests for opscore.protocols.messages
"""

# Created 10-Oct-2008 by David Kirkby (dkirkby@uci.edu)

import unittest

from opscore.protocols import messages as msg

class MessageTests(unittest.TestCase):

    def setUp(self):
        self.keywords = msg.Keywords([
            msg.Keyword("key3"),
            msg.Keyword("key2",["1.23","abc"]),
            msg.Keyword("key1",["-999"])
        ])

    def test00(self):
        "Keyword list operations"
        self.assertEqual(len(self.keywords),3)
        self.assertEqual(self.keywords[0].name,"key3")
        self.assertEqual(self.keywords[1].name,"key2")
        self.assertEqual(self.keywords[2].name,"key1")
        self.assertEqual(self.keywords[-1].name,"key1")
        self.assertRaises(IndexError,lambda : self.keywords[3])
        names = [ ]
        for key in self.keywords:
            names.append(key.name)
        self.assertEqual(names,['key3','key2','key1'])
        
    def test01(self):
        "Keyword dictionary operations"
        self.assertEqual(self.keywords['key1'].values[0],"-999")
        self.assertRaises(KeyError,lambda: self.keywords['key4'])
        self.assertRaises(TypeError,lambda: self.keywords[{}])

    def test02(self):
        "Keyword slice operations"
        self.assertEqual(type(self.keywords),type(self.keywords[:]))
        self.assertEqual(type(self.keywords),type(self.keywords[0:0]))
        self.assertEqual(type(self.keywords),type(self.keywords[:-1]))
        self.assertEqual(type(self.keywords),type(self.keywords[0:-1]))
        self.assertEqual(type(self.keywords),type(self.keywords[1:]))
        self.assertEqual(type(self.keywords),type(self.keywords[1:2]))
        self.assertEqual(len(self.keywords[0:2]),2)
        
    def test03(self):
        "Containment tests"
        self.assertEqual('key1' in self.keywords,True)
        self.assertEqual(not 'key1' in self.keywords,False)
        self.assertEqual('key1' not in self.keywords,False)
        self.assertEqual('key2' in self.keywords,True)
        self.assertEqual('key3' in self.keywords,True)
        self.assertEqual('key4' in self.keywords,False)
        self.assertRaises(TypeError,lambda: 123 in self.keywords)
        self.assertEqual('key1' in self.keywords[1:],True)
        self.assertEqual('key1' in self.keywords[:-1],False)
    
    def test04(self):
        "Reply headers"
        hdr = msg.ReplyHeader('prog','user','',123,'actor',':')
        self.assertEqual(hdr.code,':')
        self.assertRaises(ValueError,
            lambda: msg.ReplyHeader('prog','user','','abc','actor','!'))
        self.assertRaises(msg.MessageError,
            lambda: msg.ReplyHeader('prog','user','',123,'actor','?'))
            
if __name__ == "__main__":
    unittest.main()
