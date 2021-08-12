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
        self.assertAlmostEqual(types.Float()("1.23"), 1.23)
        self.assertEqual(types.Int()("-123"), -123)
        self.assertEqual(types.String()("hello, world"), "hello, world")
        self.assertEqual(types.UInt()("+123"), 123)
        self.assertEqual(types.Long()("-123456789000"), -123456789000)

    def testNativeStrVal(self):
        """Test the native method of types created with valid string values"""
        self.assertAlmostEqual(types.Float()("1.23").native, 1.23)
        self.assertEqual(type(types.Float()("1.23").native), float)
        self.assertEqual(types.Int()("-123").native, -123)
        self.assertEqual(type(types.Int()("-123").native), int)
        self.assertEqual(types.String()("hello, world").native, "hello, world")
        self.assertEqual(type(types.String()("hello, world").native), str)
        self.assertEqual(types.UInt()("+123").native, 123)
        self.assertTrue(type(types.UInt()("+123").native), int)
        self.assertEqual(types.Long()("-123456789000").native, -123456789000)
        self.assertEqual(type(types.Long()("-123456789000").native), int)

    def test01(self):
        "Types created with valid non-string values"
        self.assertEqual(types.Float()(1.23), 1.23)
        self.assertEqual(types.Int()(-123), -123)
        self.assertEqual(types.Int()(-12.3), -12)
        self.assertEqual(types.String()(+123), "123")
        self.assertEqual(types.UInt()(+123), 123)
        self.assertEqual(types.Int()(0x123), 0x123)

    def testNativeNonStrVal(self):
        """Test the native method of types created with valid non-string values"""
        self.assertAlmostEqual(types.Float()(1.23).native, 1.23)
        self.assertEqual(type(types.Float()(1.23).native), float)
        self.assertEqual(types.Int()(-123).native, -123)
        self.assertEqual(type(types.Int()(-123).native), int)
        self.assertEqual(types.UInt()(+123).native, 123)
        self.assertTrue(type(types.UInt()(+123).native), int)
        self.assertEqual(types.Long()(-123456789000).native, -123456789000)
        self.assertEqual(type(types.Long()(-123456789000).native), int)

    def test02(self):
        "Types created with invalid string values"
        self.assertRaises(ValueError, lambda: types.Float()("1.2*3"))
        self.assertRaises(ValueError, lambda: types.Int()("1.2"))
        self.assertRaises(ValueError, lambda: types.UInt()("xyz"))

    def test03(self):
        "Types created with invalid non-string values"
        self.assertRaises(ValueError, lambda: types.String()("\u1234"))

    def test04(self):
        "Enumeration created with valid values"
        COLOR = types.Enum("Red", "Green", "Blue")
        self.assertEqual(COLOR("green"), "green")
        self.assertEqual(COLOR("BLUE"), "blue")
        self.assertEqual(COLOR(2), "blue")
        self.assertEqual(str(COLOR("red")), "Red")
        self.assertEqual(str(COLOR(2)), "Blue")

    def test05(self):
        "Enumeration created with invalid values"
        COLOR = types.Enum("Red", "Green", "Blue")
        self.assertRaises(ValueError, lambda: COLOR("brown"))
        self.assertRaises(ValueError, lambda: COLOR("0"))
        self.assertRaises(ValueError, lambda: COLOR(3))
        self.assertRaises(ValueError, lambda: COLOR(-1))

    def test06(self):
        "Bitfield created with valid values"
        REG = types.Bits("addr:8", ":1", "strobe")
        r1 = REG(0x27F)
        self.assertEqual(r1.addr, 0x7F)
        self.assertEqual(r1.strobe, 1)
        r2 = REG(0).set("strobe", 1).set("addr", 0x7F)
        self.assertEqual(r2, 0x27F)
        self.assertEqual(repr(r2), "(addr=01111111,strobe=1)")
        self.assertEqual(str(r2), str(int("1001111111", 2)))

    def test07(self):
        "Invalid bitfield ctor"
        self.assertRaises(types.ValueTypeError, lambda: types.Bits())
        self.assertRaises(types.ValueTypeError, lambda: types.Bits("addr*:2"))
        self.assertRaises(types.ValueTypeError, lambda: types.Bits("addr:-2"))
        self.assertRaises(types.ValueTypeError, lambda: types.Bits("addr:99"))
        self.assertRaises(types.ValueTypeError, lambda: types.Bits("native:8"))

    def test08(self):
        "Bool created with valid values"
        B = types.Bool("Nay", "Yay")
        self.assertEqual(B("Yay"), True)
        self.assertTrue(B("Yay").native is True)
        self.assertEqual(B("Nay"), False)
        self.assertTrue(B("Nay").native is False)
        self.assertEqual(B(False), False)
        self.assertTrue(B(False).native is False)
        self.assertEqual(B(True), True)
        self.assertTrue(B(True).native is True)
        self.assertEqual(str(B(False)), "Nay")
        self.assertEqual(str(B(True)), "Yay")

    def test09(self):
        "Repeated value types with valid ctor"
        vec1 = types.RepeatedValueType(types.Float(), 3, 3)
        self.assertEqual(vec1.minRepeat, 3)
        self.assertEqual(vec1.maxRepeat, 3)
        vec2 = types.RepeatedValueType(types.Float(), 0, 3)
        self.assertEqual(vec2.minRepeat, 0)
        self.assertEqual(vec2.maxRepeat, 3)
        vec3 = types.Float() * 3
        self.assertEqual(vec3.minRepeat, 3)
        self.assertEqual(vec3.maxRepeat, 3)
        vec4 = types.Float() * (0, 3)
        self.assertEqual(vec4.minRepeat, 0)
        self.assertEqual(vec4.maxRepeat, 3)
        vec5 = types.Float() * (1,)
        self.assertEqual(vec5.minRepeat, 1)
        self.assertEqual(vec5.maxRepeat, None)

    def test10(self):
        "Repeated value types with invalid ctor"
        self.assertRaises(
            types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(), "1", "2"),
        )
        self.assertRaises(
            types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(), 1.0, 2.1),
        )
        self.assertRaises(
            types.ValueTypeError, lambda: types.RepeatedValueType(types.Float(), 2, 1)
        )
        self.assertRaises(
            types.ValueTypeError, lambda: types.RepeatedValueType(types.Float(), -1, 1)
        )
        self.assertRaises(
            types.ValueTypeError,
            lambda: types.RepeatedValueType(types.Float(), 1, "abc"),
        )

    def test11(self):
        "Values initialized with an invalid string literal"
        self.assertRaises(
            types.InvalidValueError, lambda: types.Float(invalid="???")("???")
        )
        self.assertRaises(
            types.InvalidValueError,
            lambda: types.Enum("RED", "GREEN", "BLUE", invalid="PINK")("PinK"),
        )
        self.assertRaises(types.InvalidValueError, lambda: types.UInt(invalid="-")("-"))

    def test12(self):
        "Sign bit and overflow handling for 4-byte integers"
        self.assertEqual(types.Hex()("ff00ff00"), 0xFF00FF00)
        self.assertEqual(types.Hex()("ff00ff00").native, 0xFF00FF00)
        self.assertEqual(type(types.Hex()("ff00ff00").native), int)
        self.assertEqual(types.UInt()("4278255360"), 4278255360)
        self.assertEqual(types.UInt()("4278255360").native, 4278255360)
        self.assertEqual(type(types.UInt()("4278255360").native), int)
        self.assertEqual(types.Long()(0x100000000), 0x100000000)
        self.assertEqual(types.Long()(0x100000000).native, 0x100000000)
        self.assertEqual(type(types.Long()(0x100000000).native), int)
        self.assertRaises(OverflowError, lambda: types.Int()(0xFF00FF00))
        self.assertRaises(OverflowError, lambda: types.UInt()(0x100000000))
        self.assertRaises(OverflowError, lambda: types.UInt()(-0x100000000))

    def test13(self):
        "Storage values calculated for enumerated type"
        COLOR = types.Enum("red", "green", "blue")
        self.assertEqual(COLOR("red").storageValue(), "0")
        self.assertEqual(COLOR("red").native, "red")
        self.assertEqual(type(COLOR("red").native), str)
        self.assertEqual(COLOR("green").storageValue(), "1")
        self.assertEqual(COLOR("green").native, "green")
        self.assertEqual(COLOR("blue").storageValue(), "2")
        self.assertEqual(COLOR("blue").native, "blue")
        self.assertEqual(COLOR(0).storageValue(), "0")
        self.assertEqual(COLOR(0).native, "red")
        self.assertEqual(COLOR(1).storageValue(), "1")
        self.assertEqual(COLOR(1).native, "green")
        self.assertEqual(COLOR(2).storageValue(), "2")
        self.assertEqual(COLOR(2).native, "blue")

    def test14(self):
        "Invalid value tests"
        myInvalid = types.Invalid()
        self.assertEqual(types.InvalidValue, myInvalid)
        self.assertEqual(types.InvalidValue, None)
        self.assertTrue(types.InvalidValue.native is None)

    def test15(self):
        "Float overflow tests"
        F = types.Float()
        maxFloat = float(3.4028234663852886e38)
        epsilon = float(2e22)
        self.assertEqual(F(maxFloat), maxFloat)
        self.assertEqual(F(-maxFloat), -maxFloat)
        self.assertRaises(OverflowError, lambda: F(maxFloat + epsilon))
        self.assertRaises(OverflowError, lambda: F(-maxFloat - epsilon))

    def test16(self):
        "Name metadata must be valid identifier"
        F = types.Float(name="aValue123")
        self.assertEqual(F.name, "aValue123")
        self.assertRaises(types.ValueTypeError, lambda: types.Float(name="_aValue"))
        self.assertRaises(types.ValueTypeError, lambda: types.Float(name="a Value"))
        self.assertRaises(types.ValueTypeError, lambda: types.Float(name="123Value"))
        self.assertRaises(types.ValueTypeError, lambda: types.Float(name="a-Value"))

    def test17(self):
        "Enumerated value containment tests"
        COLOR = types.Enum("Red", "Green", "Blue")
        self.assertTrue(COLOR("Red") in ["Red", "Green"])
        self.assertTrue(COLOR("Red") in ["RED", "GREEN"])

    def test18(self):
        "Compound value type"
        msgType = types.CompoundValueType(
            types.Enum(
                "INFO", "WARN", "ERROR", "FAIL", name="code", help="Status code"
            ),
            types.String(name="text", help="Message body"),
            types.UInt(name="source", help="Message source"),
            name="message",
            help="A tagged message",
        )
        self.assertEqual(
            [type(t) for t in msgType.vtypes], [types.Enum, types.String, types.UInt]
        )
        self.assertEqual(msgType.name, "message")
        self.assertEqual(msgType.help, "A tagged message")

    def test19(self):
        "PVT type"
        pvtType = types.PVT()
        pvt1 = pvtType.wrapper(1, 2, 3)
        import opscore.RO.PVT

        self.assertTrue(isinstance(pvt1, opscore.RO.PVT.PVT))
        pvt2 = opscore.RO.PVT.PVT(1, 2, 3)
        self.assertEqual(repr(pvt1), repr(pvt2))

    def test20(self):
        "Bitfield input conversions"
        # removed when Bits.inputBase attribute was dropped
        pass

    def test21(self):
        "Hex literals for integer types"
        self.assertEqual(types.Int()("0x123"), 0x123)
        self.assertEqual(types.UInt()("0x123"), 0x123)
        self.assertEqual(types.Long()("0x123"), 0x123)
        self.assertRaises(ValueError, lambda: types.UInt()("ff"))

    def test22(self):
        "Coercion of 32-bit signed to unsigned"
        self.assertEqual(types.UInt()(-0x7FFFFFFF), 0xFFFFFFFF)
        self.assertEqual(types.UInt()(-1), 0x80000001)

    def test23(self):
        "Invalid reprFmt or strFmt metadata"
        self.assertRaises(types.ValueTypeError, lambda: types.Int(reprFmt="=%s="))
        self.assertRaises(types.ValueTypeError, lambda: types.Int(reprFmt="=%r="))
        self.assertRaises(types.ValueTypeError, lambda: types.Int(strFmt="=%s="))
        self.assertRaises(types.ValueTypeError, lambda: types.Int(strFmt="=%r="))


if __name__ == "__main__":
    unittest.main()
