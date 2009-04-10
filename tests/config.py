#!/usr/bin/env python
"""
Unit tests for opscore.utility.config
"""

# Created 9-Apr-2009 by David Kirkby (dkirkby@uci.edu)

import unittest
import optparse

from opscore.utility import config

class ConfigTest(unittest.TestCase):
    
    def setUp(self):
        self.cli = config.ConfigOptionParser(
            config_file='config-test.ini',config_section='test')
        self.short_message = 'hello, world'
        self.long_message = ''.join([chr(i%256) for i in range(1000)])
        
    def test00(self):
        "String option"
        self.cli.add_option('--stringOpt')
        (options,args) = self.cli.parse_args([])
        self.assertEqual(options.stringOpt,'string')
        
    def test01(self):
        "String option with spaces"
        self.cli.add_option('--spacesOpt')
        (options,args) = self.cli.parse_args([])
        self.assertEqual(options.spacesOpt,"'quoted string with spaces'")
                
    def test02(self):
        "Float option"
        self.cli.add_option('--floatOpt',type='float')
        (options,args) = self.cli.parse_args([])
        self.assertEqual(options.floatOpt,3.141)
        
    def test03(self):
        "Decimal int option"
        self.cli.add_option('--decIntOpt',type='int')
        (options,args) = self.cli.parse_args([])
        self.assertEqual(options.decIntOpt,-123)

    def test04(self):
        "Hex log option"
        self.cli.add_option('--hexIntOpt',type='long')
        (options,args) = self.cli.parse_args([])
        self.assertEqual(options.hexIntOpt,long(0x123))

    def test05(self):
        "Boolean option"
        self.cli.add_option('--boolOpt1',action='store_true')
        (options,args) = self.cli.parse_args([])
        self.failUnless(options.boolOpt1)

    def test06(self):
        "Boolean option"
        self.cli.add_option('--boolOpt2',action='store_false')
        (options,args) = self.cli.parse_args([])
        self.failUnless(options.boolOpt2)

    def test07(self):
        "Boolean option"
        self.cli.add_option('--boolOpt3',action='store_true')
        (options,args) = self.cli.parse_args([])
        self.failUnless(options.boolOpt3)

    def test08(self):
        "Boolean option"
        self.cli.add_option('--boolOpt4',action='store_false')
        (options,args) = self.cli.parse_args([])
        self.failUnless(options.boolOpt4)

    def test09(self):
        "Invalid bool option"
        self.assertRaises(ValueError,
            lambda: self.cli.add_option('--badBoolOpt',action='store_true'))

    def test10(self):
        "Secret option"
        self.cli.add_option('--goodSecret',type='secret',dest='goodSecret')
        (options,args) = self.cli.parse_args(args=[],
            passphrase='The quick brown fox jumps over the lazy dog')
        self.assertEqual(options.goodSecret,'Secret Value')

    def test11(self):
        "Secret option without dest"
        self.assertRaises(optparse.OptionValueError,
            lambda: self.cli.add_option('--goodSecret',type='secret'))

    def test12(self):
        "Secret option"
        self.cli.add_option('--badSecret1',type='secret',dest='secretOpt')
        self.assertRaises(config.ConfigError,lambda: self.cli.parse_args(args=[],
            passphrase='The quick brown fox jumps over the lazy dog'))
            
    def test13(self):
        "Secret option"
        self.cli.add_option('--badSecret2',type='secret',dest='secretOpt')
        self.assertRaises(config.ConfigError,lambda: self.cli.parse_args(args=[],
            passphrase='The quick brown fox jumps over the lazy dog'))

    def test14(self):
        "bin2hex - hex2bin roundtrip for short message"
        hex = config.ConfigOptionParser.bin2hex(self.short_message)
        self.assertEqual(config.ConfigOptionParser.hex2bin(hex),self.short_message)

    def test15(self):
        "bin2hex - hex2bin roundtrip for long message"
        hex = config.ConfigOptionParser.bin2hex(self.long_message)
        self.assertEqual(config.ConfigOptionParser.hex2bin(hex),self.long_message)
        
    def test16(self):
        "DEFAULT section option"
        self.cli.add_option('--defaultSectionOpt')
        (options,args) = self.cli.parse_args([])
        self.assertEqual(options.defaultSectionOpt,'ok')
    

if __name__ == '__main__':
    unittest.main()
