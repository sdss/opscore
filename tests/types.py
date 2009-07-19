#!/usr/bin/env python
"""
Unit tests for opscore.protocols.types
"""

# Created 30-Oct-2008 by David Kirkby (dkirkby@uci.edu)

import unittest

from opscore.protocols import types

class TypesTest(unittest.TestCase):
    
    def test00(self):
        "Types created with valid string values"
        self.assertEqual(types.Float()('1.23'),1.23)
        self.assertEqual(types.Int()('-123'),-123)
        self.assertEqual(types.String()('hello, world'),'hello, world')
        self.assertEqual(types.UInt()('+123'),123)
        self.assertEqual(types.Hex()('123'),0x123)
        self.assertEqual(types.Long()('-123456789000'),-123456789000L)

    def test01(self):
        "Types created with valid non-string values"
        self.assertEqual(types.Float()(1.23),1.23)
        self.assertEqual(types.Int()(-123),-123)
        self.assertEqual(types.Int()(-12.3),-12)
        self.assertEqual(types.String()(+123),'123')
        self.assertEqual(types.UInt()(+123),123)
        self.assertEqual(types.Hex()(0x123),0x123)
        self.assertEqual(types.Hex()(123),123)

    def test02(self):
        "Types created with invalid string values"
        self.assertRaises(ValueError,lambda: types.Float()('1.2*3'))
        self.assertRaises(ValueError,lambda: types.Int()('1.2'))
        self.assertRaises(ValueError,lambda: types.UInt()('-123'))
        self.assertRaises(ValueError,lambda: types.Hex()('xyz'))

    def test03(self):
        "Types created with invalid non-string values"
        self.assertRaises(ValueError,lambda: types.String()(u'\u1234'))
        self.assertRaises(ValueError,lambda: types.UInt()(-123))
        self.assertRaises(ValueError,lambda: types.Hex()(-123))
        
    def test04(self):
        "Enumeration created with valid values"
        COLOR = types.Enum('Red','Green','Blue')
        self.assertEqual(COLOR('green'),'green')
        self.assertEqual(COLOR('BLUE'),'blue')
        self.assertEqual(COLOR(2),'blue')
        self.assertEqual(str(COLOR('red')),'Red')
        self.assertEqual(str(COLOR(2)),'Blue')
        
    def test05(self):
        "Enumeration created with invalid values"
        COLOR = types.Enum('Red','Green','Blue')
        self.assertRaises(ValueError,lambda: COLOR('brown'))
        self.assertRaises(ValueError,lambda: COLOR('0'))
        self.assertRaises(ValueError,lambda: COLOR(3))
        self.assertRaises(ValueError,lambda: COLOR(-1))
        
    def test06(self):
        "Bitfield created with valid values"
        REG = types.Bits('addr:8',':1','strobe')
        r1 = REG(0x27f)
        self.assertEqual(r1.addr,0x7f)
        self.assertEqual(r1.strobe,1)
        r2 = REG(0).set('strobe',1).set('addr',0x7f)
        self.assertEqual(r2,0x27f)
        self.assertEqual(str(r2),'(addr=01111111,strobe=1)')
        
    def test07(self):
        "Invalid bitfield ctor"
        self.assertRaises(types.ValueTypeError,lambda: types.Bits())
        self.assertRaises(types.ValueTypeError,lambda: types.Bits('addr*:2'))
        self.assertRaises(types.ValueTypeError,lambda: types.Bits('addr:-2'))
        self.assertRaises(types.ValueTypeError,lambda: types.Bits('addr:99'))
        
    def test08(self):
        "Bool created with valid values"
        B = types.Bool('Nay','Yay')
        self.failUnless(B('Yay') == True)
        self.failUnless(B('Nay') == False)
        self.failUnless(B(False) == False)
        self.failUnless(B(True) == True)
        self.assertEqual(str(B(False)),'Nay')
        self.assertEqual(str(B(True)),'Yay')
        
    def test09(self):
        "Repeated value types with valid ctor"
        vec1 = types.RepeatedValueType(types.Float(),3,3)
        vec2 = types.RepeatedValueType(types.Float(),0,3)
        vec3 = types.Float()*3
        vec4 = types.Float()*(0,3)
        vec5 = types.Float()*(1,)
        
    def test10(self):
        "Repeated value types with invalid ctor"
        self.assertRaises(types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(),'1','2'))
        self.assertRaises(types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(),1.0,2.1))
        self.assertRaises(types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(),2,1))
        self.assertRaises(types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(),-1,1))
        self.assertRaises(types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(),1,'abc'))
        
    def test11(self):
        "Values initialized with an invalid string literal"
        self.assertRaises(types.InvalidValueError,lambda: types.Float(invalid='???')('???'))
        self.assertRaises(types.InvalidValueError,
            lambda: types.Enum('RED','GREEN','BLUE',invalid='PINK')('PinK'))
        self.assertRaises(types.InvalidValueError,lambda: types.UInt(invalid='-')('-'))

    def test12(self):
        "Sign bit and overflow handling for 4-byte integers"
        self.assertEqual(types.Hex()('ff00ff00'),0xff00ff00)
        self.assertEqual(types.UInt()('4278255360'),4278255360)
        self.assertRaises(OverflowError,lambda: types.Int()(0xff00ff00))
        self.assertRaises(ValueError,lambda: types.UInt()(0x100000000))
        self.assertEqual(types.Long()(0x100000000),0x100000000)

    def test13(self):
        "Storage values calculated for enumerated type"
        COLOR = types.Enum('red','green','blue')
        self.assertEqual(COLOR('red').storageValue(),'0')
        self.assertEqual(COLOR('green').storageValue(),'1')
        self.assertEqual(COLOR('blue').storageValue(),'2')
        self.assertEqual(COLOR(0).storageValue(),'0')
        self.assertEqual(COLOR(1).storageValue(),'1')
        self.assertEqual(COLOR(2).storageValue(),'2')
    
    def test14(self):
        "Invalid value tests"
        myInvalid = types.Invalid()
        self.assertEqual(types.InvalidValue,myInvalid)
        self.assertEqual(types.InvalidValue,None)
        
    def test15(self):
        "Float overflow tests"
        F = types.Float()
        maxFloat = float(3.4028234663852886e+38)
        epsilon = float(2e22)
        self.assertEqual(F(maxFloat),maxFloat)
        self.assertEqual(F(-maxFloat),-maxFloat)
        self.assertRaises(ValueError,lambda: F(maxFloat+epsilon))
        self.assertRaises(ValueError,lambda: F(-maxFloat-epsilon))
    
    def test16(self):
        "Name metadata must be valid identifier"
        F = types.Float(name='aValue123')
        self.assertEqual(F.name,'aValue123')
        self.assertRaises(types.ValueTypeError,lambda: types.Float(name='_aValue'))
        self.assertRaises(types.ValueTypeError,lambda: types.Float(name='a Value'))
        self.assertRaises(types.ValueTypeError,lambda: types.Float(name='123Value'))
        self.assertRaises(types.ValueTypeError,lambda: types.Float(name='a-Value'))
        
    def test17(self):
        "Enumerated value containment tests"
        COLOR = types.Enum('Red','Green','Blue')
        self.failUnless(COLOR('Red') in ['Red','Green'])
        self.failUnless(COLOR('Red') in ['RED','GREEN'])
        
    def test18(self):
        "Compound value type"
        msgType = types.CompoundValueType(
            types.Enum('INFO','WARN','ERROR','FAIL',name='code',help='Status code'),
            types.String(name='text',help='Message body'),
            types.UInt(name='source',help='Message source'),
            name = 'message',
            help = 'A tagged message'
        )
        
    def test19(self):
        "PVT type"
        pvtType = types.PVT()
        pvt1 = pvtType.wrapper(1,2,3)
        import RO.PVT
        self.failUnless(isinstance(pvt1,RO.PVT.PVT))
        pvt2 = RO.PVT.PVT(1,2,3)
        self.assertEqual(repr(pvt1),repr(pvt2))
        
if __name__ == '__main__':
    unittest.main()
