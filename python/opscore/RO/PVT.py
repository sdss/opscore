
"""PVT implements a class to describe (position, velocity, time) triplets.

History:
2001-01-10 ROwen    Modified floatCnv to not handle NaN floating values,
    since this failed on Mac OS X; it will still handle string "NaN" (any case).
2002-08-08 ROwen    Modified to use new Astro.Tm functions which are in days, not sec.
2003-05-08 ROwen    Modified to use opscore.RO.CnvUtil.
2003-11-21 ROwen    Bug fix: __init__ did not check the data.
2005-06-08 ROwen    Changed PVT to a new-style class.
2007-07-02 ROwen    Added hasVel method.
2015-09-24 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
"""
__all__ = ["PVT"]

import time

import numpy

import opscore.RO.Astro.Tm
import opscore.RO.CnvUtil
import opscore.RO.MathUtil
import opscore.RO.PhysConst

class PVT(object):
    """Defines a position, velocity, time triplet, where time is in TAI.

    Inputs:
    - pos   position
    - vel   velocity (in units of position/sec)
    - time  TAI, MJD seconds

    Each value must be one of: a float, a string representation of a float,
    "NaN" (any case) or None. "NaN" and None mean "unknown" and are stored as None.

    Raises ValueError if any value is invalid.
    """
    def __init__(self, pos=None, vel=0.0, t=0.0):
        self.pos = None
        self.vel = 0.0
        self.t = 0.0
        self.set(pos, vel, t)

    def __repr__(self):
        return "PVT(%s, %s, %s)" % (str(self.pos), str(self.vel), str(self.t))

    def getPos(self, t=None):
        """Returns the position at the specified time.
        Time defaults to the current TAI.

        Returns None if the pvt is invalid.
        """
        if not self.isValid():
            return None

        if t is None:
            t = opscore.RO.Astro.Tm.taiFromPySec() * opscore.RO.PhysConst.SecPerDay

        return self.pos + (self.vel * (t - self.t))

    def hasVel(self):
        """Return True if velocity is known and nonzero.
        """
        return self.vel not in (0, None)

    def isValid(self):
        """Returns True if the pvt is valid, False otherwise.

        A pvt is valid if all values are known (not None and finite) and time > 0.
        """
        return  (self.pos is not None) and numpy.isfinite(self.pos) \
            and (self.vel is not None) and numpy.isfinite(self.vel) \
            and (self.t   is not None) and numpy.isfinite(self.t) \
            and (self.t > 0)

    def set(self, pos=None, vel=None, t=None):
        """Sets pos, vel and t; all default to their current values

        Each value must be one of: a float, a string representation of a float,
        "NaN" (any case) or None. "NaN" means "unknown" and is stored as None.

        Errors:
        Raises ValueError if any value is invalid.
        """
        if pos is not None:
            self.pos = opscore.RO.CnvUtil.asFloatOrNone(pos)
        if vel is not None:
            self.vel = opscore.RO.CnvUtil.asFloatOrNone(vel)
        if t is not None:
            self.t = opscore.RO.CnvUtil.asFloatOrNone(t)


if __name__ == "__main__":
    print("\nrunning PVT test")

    currTAI = opscore.RO.Astro.Tm.taiFromPySec() * opscore.RO.PhysConst.SecPerDay

    varList = (
        PVT(),
        PVT(25),
        PVT(25, 0, currTAI),
        PVT(25, 1),
        PVT(25, 1, currTAI),
        PVT('NaN', 'NaN', 'NaN')
    )

    for i in range(5):
        t = opscore.RO.Astro.Tm.taiFromPySec() * opscore.RO.PhysConst.SecPerDay
        print("\ntime =", t)
        for var in varList:
            print(var, "pos =", var.getPos(t))
        if i < 4:
            time.sleep(1)
