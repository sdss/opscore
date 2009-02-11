#!/usr/bin/env python
"""Unit tests for opscore.utility.astrotime
"""

# Created 29-Jul-2008 by David Kirkby (dkirkby@uci.edu)

import unittest

from datetime import tzinfo,timedelta,datetime

import opscore.utility.astrotime as astrotime

class AstroTimeTests(unittest.TestCase):
	def test00_AstroTime(self):
		"""Special astrotime.AstroTime constructors"""
		dt = datetime.now()
		dt1 = astrotime.AstroTime(datetime=dt)
		dt2 = astrotime.AstroTime(datetime=dt,deltasecs=+10)
		self.assertEqual(dt2 - dt1,timedelta(seconds=+10))
		dt3 = astrotime.AstroTime(datetime=dt,deltasecs=-10)
		self.assertEqual(dt3 - dt1,timedelta(seconds=-10))
		self.assertRaises(astrotime.AstroTimeException,lambda: astrotime.AstroTime(datetime='invalid'))
		self.assertRaises(TypeError,lambda: astrotime.AstroTime(deltasecs=0))
	def test01_AstroTime(self):
		"""astrotime.AstroTime constructor tests without timezone"""
		args = (2008,7,24,1,2,3,4)
		dt1 = datetime(*args)
		dt2 = astrotime.AstroTime(*args)
		self.assertEqual(dt1.timetuple(),dt2.timetuple())
		self.assertEqual(dt1.utctimetuple(),dt2.utctimetuple())
		self.assertNotEqual(str(dt1),str(dt2))
		self.assertNotEqual(repr(dt1),repr(dt2))
	def test02_AstroTime(self):
		"""astrotime.AstroTime constructor tests using UTC"""
		args = (2008,7,24,1,2,3,4,astrotime.UTC)
		dt1 = datetime(*args)
		dt2 = astrotime.AstroTime(*args)
		self.assertEqual(dt1.timetuple(),dt2.timetuple())
		self.assertEqual(dt1.utctimetuple(),dt2.utctimetuple())
		self.assertNotEqual(str(dt1),str(dt2))
		self.assertNotEqual(repr(dt1),repr(dt2))
	def test03_AstroTime(self):
		"""astrotime.AstroTime constructor tests using TAI"""
		args = (2008,7,24,1,2,3,4,astrotime.TAI)
		dt1 = datetime(*args)
		dt2 = astrotime.AstroTime(*args)
		self.assertEqual(dt1.timetuple(),dt2.timetuple())
		self.assertNotEqual(dt1.utctimetuple(),dt2.utctimetuple())
		self.assertNotEqual(str(dt1),str(dt2))
		self.assertNotEqual(repr(dt1),repr(dt2))
	def test04_AstroTime(self):
		"""astrotime.AstroTime leap second adjustments"""
		utc = astrotime.AstroTime(2008,7,24,1,2,3,4,astrotime.UTC)
		tai = utc.astimezone(astrotime.TAI)
		offset = timedelta(seconds=+33)
		self.assertEqual(utc.utcoffset(),astrotime.ZERO)
		self.assertEqual(tai.utcoffset(),offset)
		self.assertEqual(utc.utctimetuple(),tai.utctimetuple())
		self.assertNotEqual(utc.timetuple(),tai.timetuple())
		self.assertEqual(utc.timetuple(),tai.astimezone(astrotime.UTC).timetuple())
		self.assertEqual(tai-utc,offset)
	def test05_AstroTime(self):
		"""astrotime.AstroTime static methods"""
		dt1 = astrotime.AstroTime.now(astrotime.UTC)
		dt2 = astrotime.AstroTime.now(astrotime.TAI)
		self.assert_(dt2 - dt1 >= timedelta(seconds=+33))
		ts = 1234567890
		dt1 = astrotime.AstroTime.fromtimestamp(ts,astrotime.UTC)
		dt2 = astrotime.AstroTime.fromtimestamp(ts,astrotime.TAI)
		self.assertEqual(dt1.utctimetuple(),dt2.utctimetuple())
		self.assertNotEqual(dt1.timetuple(),dt2.timetuple())
	def test06_AstroTime(self):
		"""astrotime.AstroTime MJD calculations"""
		dt1 = astrotime.AstroTime(2008,7,24,12,tzinfo=astrotime.TAI)
		self.assertEqual(dt1.MJD(),54671.5)
		dt2 = astrotime.AstroTime.fromMJD(dt1.MJD(),astrotime.TAI)
		self.assertEqual(dt1.timetuple(),dt2.timetuple())
		dt3 = astrotime.AstroTime.fromMJD(dt1.MJD(),astrotime.UTC)
		self.assertEqual(dt1.timetuple(),dt3.timetuple())
		self.assertNotEqual(dt1.utctimetuple(),dt3.utctimetuple())

if __name__ == '__main__':
	unittest.main()
