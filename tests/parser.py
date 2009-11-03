#!/usr/bin/env python
"""
Unit tests for opscore.protocols.parser
"""

# Created 2-Mar-2009 by David Kirkby (dkirkby@uci.edu)

import unittest

from opscore.protocols import parser,validation,messages

class ParserTests(unittest.TestCase):

    def roundTrip(self,parser,msg):
        parsed1 = parser.parse(msg).canonical()
        parsed2 = parser.parse(parsed1).canonical()
        self.assertEqual(parsed1,parsed2)

    def test00(self):
        """Valid reply headers"""
        rParser = parser.ReplyParser()
        reply = rParser.parse("tui.operator 911 BossICC : key=value")
        hdr = reply.header
        self.assertEqual(hdr.program,"tui")
        self.assertEqual(hdr.user,"operator")
        self.assertEqual(hdr.actorStack,"")
        self.assertEqual(hdr.commandId,911)
        self.assertEqual(hdr.actor,"BossICC")
        self.assertEqual(hdr.cmdrName,"tui.operator")
        reply = rParser.parse(".operator 911 BossICC : key=value")
        hdr = reply.header
        self.assertEqual(hdr.program,"")
        self.assertEqual(hdr.user,"operator")
        self.assertEqual(hdr.actorStack,"")
        self.assertEqual(hdr.commandId,911)
        self.assertEqual(hdr.actor,"BossICC")
        self.assertEqual(hdr.cmdrName,".operator")
        reply = rParser.parse("tui.operator.actor1 911 BossICC : key=value")
        hdr = reply.header
        self.assertEqual(hdr.program,"tui")
        self.assertEqual(hdr.user,"operator")
        self.assertEqual(hdr.actorStack,".actor1")
        self.assertEqual(hdr.commandId,911)
        self.assertEqual(hdr.actor,"BossICC")
        self.assertEqual(hdr.cmdrName,"tui.operator.actor1")
        reply = rParser.parse("tui.operator.actor1.actor2.actor3 911 BossICC : key=value")
        hdr = reply.header
        self.assertEqual(hdr.program,"tui")
        self.assertEqual(hdr.user,"operator")
        self.assertEqual(hdr.actorStack,".actor1.actor2.actor3")
        self.assertEqual(hdr.commandId,911)
        self.assertEqual(hdr.actor,"BossICC")
        self.assertEqual(hdr.cmdrName,"tui.operator.actor1.actor2.actor3")

    def test02(self):
        """Invalid reply headers"""
        rParser = parser.ReplyParser()
        self.assertRaises(parser.ParseError,
            lambda: rParser.parse("tui 911 BossICC : key=value"))
        self.assertRaises(parser.ParseError,
            lambda: rParser.parse("tui. 911 BossICC : key=value"))
        self.assertRaises(parser.ParseError,
            lambda: rParser.parse("tui.operator. 911 BossICC : key=value"))
        self.assertRaises(parser.ParseError,
            lambda: rParser.parse(". 911 BossICC : key=value"))
        self.assertRaises(parser.ParseError,
            lambda: rParser.parse(".. 911 BossICC : key=value"))

    def test03(self):
        """Valid reply keywords"""
        rParser = parser.ReplyParser()
        msg = "tui.op 911 CoffeeMakerICC : type=decaf;blend = 20:80, Kenyan,Bolivian ; now"
        reply = rParser.parse(msg)
        self.assertEqual(reply.string,msg)
        self.assertEqual(len(reply.keywords),3)
        self.assertEqual(reply.keywords[0].name,"type")
        self.assertEqual(reply.keywords[1].name,"blend")
        self.assertEqual(reply.keywords[2].name,"now")
        self.assertEqual(len(reply.keywords[0].values),1)
        self.assertEqual(len(reply.keywords[1].values),3)
        self.assertEqual(len(reply.keywords[2].values),0)

    def test04(self):
        "Valid command keywords"
        cParser = parser.CommandParser()
        msg = 'cmd key1 raw=raw;text=goes"here key2'
        cmd = cParser.parse(msg)
        self.assertEqual(cmd.string,msg)
        rawcmd = validation.Cmd('cmd','@[key1] raw [key2]')
        self.failUnless(rawcmd.consume(cmd))
        self.assertEqual(cmd.keywords[0].name,'key1')
        self.assertEqual(cmd.keywords[1].name,'raw')
        self.assertEqual(len(cmd.keywords),2)
        self.failUnless(isinstance(cmd.keywords[1],messages.RawKeyword))
        self.assertEqual(len(cmd.keywords[1].values),1)
        self.assertEqual(cmd.keywords[1].values[0],'raw;text=goes"here key2')

    def test05(self):
        """Canonical round trips"""
        rParser = parser.ReplyParser()
        self.roundTrip(rParser,"tui.op 911 CoffeeMakerICC : type=decaf;blend = 20:80, Kenyan,Bolivian ; now")

if __name__ == "__main__":
   unittest.main()
