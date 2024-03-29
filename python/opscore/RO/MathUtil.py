
"""Math utilities by Russell Owen

History:
2001-01-10 ROwen    Removed inf and nan stuff because it fails on Mac OS X
                    (and it was known to not work on all platforms).
                    Maybe someday Python will handle IEEE floating point!
2002-03-04 ROwen    Added checkRange.
2002-07-09 ROwen    Added compareFloats, matchLists and flattenList.
2002-08-01 ROwen    Renamed logEQ to logEq for consistency.
2002-08-08 ROwen    Moved to RO and renamed from ROMath.
2002-08-13 ROwen    Bug fix: wrapCtr gave the wrong result.
2003-03-12 ROwen    Added isSequence; rewrote flattenList to use it.
2003-04-01 ROwen    Added rot2D.
2003-05-29 ROwen    Added asList.
2003-06-27 ROwen    Added removeDups.
2003-07-18 ROwen    Added asSequence.
2003-11-18 ROwen    Moved asList, asSequence, flattenLists, isSequence,
                    removeDups and matchLists to SeqUtil.
2007-04-24 ROwen    Changed Numeric to numpy in a doc string.
2010-07-30 ROwen    Bug fix: wrapPos returned 360 if input was a very small negative value.
2011-07-21 ROwen    API change and bug fix: rThetaFromXY was documented to raise an exception
                    if too near the pole, but it did not do this reliably, if at all.
                    Changed to return theta = NaN (numpy.nan) if too near the pole.
2015-09-24 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
"""
__all__ = ["sind", "cosd", "tand", "asind", "acosd", "atand", "atan2d", "compareFloats", "checkRange",
    "nint", "sign", "logEq", "logNE", "rot2D", "rThetaFromXY", "xyFromRTheta", "vecMag", "wrapCtr", "wrapPos"]

import math
import numpy
from opscore.RO.PhysConst import RadPerDeg
import opscore.RO.SysConst

DegPerRad = 1.0 / RadPerDeg
_TinyFloat = numpy.finfo(float).tiny

# The following were commented out 2001-01-10 because inf and nan
# are not handled on Mac OS X (Python 2.2 from fink).
# the following probably works on all platforms that support IEEE floating point
# it has been tested on Solaris and MacOS classic.
# Probably it's simply an issue of whether Python was built with the -ieee option.
# Inf = inf = float("inf")
# NaN = nan = float("nan")

def sind(angDeg):
    """sine of angle, in degrees"""
    return math.sin(RadPerDeg * angDeg)

def cosd(angDeg):
    """cosine of angle, in degrees"""
    return math.cos(RadPerDeg * angDeg)

def tand(angDeg):
    """tangent of angle, in degrees"""
    return math.tan(RadPerDeg * angDeg)

def asind(x):
    """arcsine of x, in degrees"""
    return DegPerRad * math.asin(x)

def acosd(x):
    """arccosine of x, in degrees"""
    return DegPerRad * math.acos(x)

def atand(x):
    """arctangent of x, in degrees"""
    return DegPerRad * math.atan(x)

def atan2d(x, y):
    """arctangent of y/x, in degrees"""
    return DegPerRad * math.atan2(x, y)

def compareFloats(a, b, rtol=1.0e-5, atol=opscore.RO.SysConst.FAccuracy):
    """Compares values a and b
    Returns 0 if the values are approximately equals, i.e.:
    - |a - b| < atol + (rtol * |a + b|)
    Else 1 if a > b, -1 if a < b

    Inputs:
    - a, b: scalars to be compared (int or float)
    - atol: absolute tolerance
    - rtol: relative tolerance

    The algorithm used is the same one used by numpy.allclose.
    """
    if abs(a - b) < (atol + (rtol * abs(float(a + b)))):
        return 0
    return cmp(a, b)

def checkRange(value, minValue, maxValue, valDescr="value"):
    """Checks that value is in range [minValue, maxValue] and raises a ValueError if not.
    If minValue or maxValue is None, that limit is not checked.
    If value is None, nothing is checked.
    """
    if value is None:
        return
    if maxValue is not None and value > maxValue:
        raise ValueError("%s too large: %r > %r" % (valDescr, value, maxValue))
    if minValue is not None and value < minValue:
        raise ValueError("%s too small: %r < %r" % (valDescr, value, minValue))

def nint(x, n=0):
    """Returns x rounded to the nearast multiple of 10**-n.
    Values of n > 0 are treated as 0, so that the result is an integer.

    In other words, just like the built in function round,
    but returns an integer and treats n > 0 as 0.

    Inputs:
    - x: the value to round
    - n: negative of power of 10 to which to round (e.g. -2 => round to nearest 100)

    Error Conditions:
    - raises OverflowError if x is too large to express as an integer (after rounding)
    """
    return int (round (x, min(n, 0)) + 0.5)

def sign(x):
    """Returns -1 if x < 0, 1 otherwise

    Error Conditions:
    - raises TypeError if x is not a number
    """
    abs(x)  # checks type of argument
    if x < 0:
        return -1
    else:
        return 1

def logEq(a, b):
    """Returns 1 if the logical value of a equals the logical value of b, 0 otherwise"""
    return (not a) == (not b)

def logNE(a, b):
    """Returns 1 if the logical value of does not equal the logical value of b, 0 otherwise"""
    return (not a) != (not b)

def rot2D(xyVec, angDeg):
    """Rotates a 2-dimensional vector by a given angle.

    Inputs:
    - xyVec     x,y vector to be rotated
    - angDeg    angle (degrees, 0 along x, 90 along y)

    Outputs:
    rotVec  x,y rotated vector

    Error Conditions:
    Raises ValueError if:
    - xyVec is not two numbers
    - angDeg is not a number

    Details:
    Changing coordinate systems:
    Given a point P whose position in coordinate system A is P_A_xy
    and another coordinate system B whose angle with respect to A is B_A_ang
    and whose position with respect to A is B_A_xy,
    then P_B_xy, the position of P in coordinate system B is:
    P_B_xy = (P_A_xy - B_A_xy) rotated by -B_A_ang

    History:
    2003-04-01 Converted to Python from TCC cnv_Rot2D
    """
    x, y = xyVec
    sinAng = sind (angDeg)
    cosAng = cosd (angDeg)

    return (
        cosAng * x - sinAng * y,
        sinAng * x + cosAng * y,
    )

def rThetaFromXY(xy):
    """Returns the magnitude and angle of a 2-dim vector.

    Inputs:
    - xy: cartesian coordinates

    Returns:
    - r: radius
    - theta: theta (deg); NaN if cannot be reliably computed
    """
    r = math.hypot(*xy)
    if r < _TinyFloat:
        theta = numpy.nan
    else:
        theta = math.atan2(xy[1], xy[0]) / opscore.RO.PhysConst.RadPerDeg
    return (r, theta)

def xyFromRTheta(rTheta):
    """Returns the x and y components of a polar vector"""
    r, theta = rTheta
    return (
        r * cosd(theta),
        r * sind(theta),
    )

def vecMag(a):
    """Returns the magnitude of vector a"""
    sumSq = 0
    for ai in a:
        sumSq += ai * ai
    return math.sqrt(sumSq)

def wrapCtr(angDeg):
    """Returns the angle (in degrees) wrapped into the range (-180, 180]"""
    # First wrap into [0, 360]; result is 360 if ctrAng < 0 but so near 0 that adding 360 rounds it
    ctrAng = angDeg % 360.0
    if ctrAng > 180.0:
        ctrAng -= 360.0
    return ctrAng

def wrapPos(angDeg):
    """Returns the angle (in degrees) wrapped into the range [0, 360)"""
    res = angDeg % 360.0
    # First wrap into [0, 360]; result is 360 if ctrAng < 0 but so near 0 that adding 360 rounds it
    if res == 360.0:
        return 0.0
    return res
