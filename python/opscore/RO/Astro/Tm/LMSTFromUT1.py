

__all__ = ["lmstFromUT1"]

import opscore.RO.MathUtil
from .GMSTFromUT1 import gmstFromUT1

def lmstFromUT1(ut1, longitude):
    """Convert from universal time (MJD) to local apparent sidereal time (deg).

    Inputs:
    - ut1       UT1 MJD
    - longitude longitude east (deg)

    Returns:
    - lmst      local mean sideral time (deg)

    History:
    2002-08-05 R Owen.
    2014-04-25 ROwen    Add from __future__ import division, absolute_import and use relative import.
    """
    # convert UT1 to Greenwich mean sidereal time (GMST), in degrees
    gmst = gmstFromUT1(ut1)

    # find local mean sideral time, in degrees, in range [0, 360)
    return opscore.RO.MathUtil.wrapPos(gmst + longitude)   # degrees
