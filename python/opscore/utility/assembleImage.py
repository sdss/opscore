"""Assemble a set of postage stamps images of guide fiber bundles into one image

The postage stamp images are displayed at full scale and in roughly
their correct position on the focal plane while using space efficiently.

This code implements an algorithm suggested by Jim Gunn, with a few refinements of my own.

History:
2009-07-14 ROwen    Initial work.
2009-10-29 ROwen    Modified for guider v1_0_10 preliminary.
2009-10-30 ROwen    Modified to test whether fits images have plate data; raise
                    new exceptions if not.
2009-11-02 ROwen    Removed code to set 0-valued pixels of postage stamps images to background
                    (now that the guider does this).
2009-11-04 ROwen    Added margin argument to AssembleImage (to leave room for annotations).
                    Bug fix: mis-handled guide images with no postage stamps.
2009-11-05 ROwen    PostageStamp.setDecimatedImagePos now keeps the stamp in bounds of the
                    larger image and also verifies that the requested position is finite.
                    AssembleImage.__call__ now checks that removeOverlap has a finite quality;
                    this catches a failure when multiple guide probes have the same plate position.
                    Bug fix: was requiring the # of postage stamps = # of data entries
                    but that is too picky.
2010-02-19 ROwen    Fix ticket #613: background levels are wrong. This was caused by ignoring
                    masked pixels when computing the background. The old guider did not set mask
                    bits, but the new one does, and so many pixels were masked that my crude
                    backround computation gave too large a value.
                    Fixed by using the guider-supplied image background (IMGBACK) if available,
                    else use the median of the entire image (ignoring the mask).
2010-06-28 ROwen    Removed debug statement that forced computation of background
                    (thanks to pychecker).
                    Removed a global variable and a few statements that had no effect
                    (thanks to pychecker).
2010-09-27 ROwen    Documented extra fields in PostageStampInfo.
2010-12-07 ROwen    Fix ticket #1181: in several places array size was treated as being
                    x,y order, but it is reversed. The code is explicitly uses i,j for
                    the reversed coordinate system.
                    Thanks to Craig Loomis for diagnosing the problem.
2010-12-27 ROwen    Handle images with no small postage stamps.
                    Thanks to Craig Loomis for the bug report and fix.
2011-08-29 ROwen    Modified to always return a 32-bit float array (was returning 64-bit).
2013-03-29 ROwen    Added gpBits field to PostageStamp.
2013-05-13 ROwen    Support older guide images that don't have gprobebits information.
"""

import sys
import math

import numpy


PlateDiameterMM = 0.06053 * 3600 * 3  # 60.53 arcsec/mm, 3 degree FOV


class AIException(Exception):
    """Base class for exceptions thrown by AssembleImage."""

    pass


class NoPlateInfo(AIException):
    """Exception thrown by AssembleImage if the image has no plate information."""

    pass


class PlateInfoWrongVersion(AIException):
    """Exception thrown by AssembleImage if the image has an unparseable version of plate info."""

    pass


class PlateInfoInvalid(AIException):
    """Plate information is invalid and cannot be parsed"""

    pass


def asArr(seq, shape=(2,), dtype=float):
    """Convert a sequence of floats to a numpy array"""
    retArr = numpy.array(seq, dtype=dtype)
    if retArr.shape != tuple(shape):
        raise ValueError(
            "Input data shape = %s != desired shape %s" % (retArr.shape, shape)
        )
    return retArr


class PlateInfo(object):
    """An object containing SDSS guide probe data including a plate image"""

    def __init__(self, plateImageArr, plateMaskArr, stampList):
        self.plateImageArr = plateImageArr
        self.plateMaskArr = plateMaskArr
        self.stampList = stampList


class PostageStamp(object):
    """Information about a postage stamp

    For now allow much of the info to be None, but once the names are nailed down
    for the FITS file then require all of these that my code uses
    (and perhaps ditch the rest).

    Useful attributes:
    - All those specified in the constructor plus:
    - decImStartPos: start position of postage stamp on image
                     (i,j int pixels); None until set by setDecimatedImagePos
    - decImCtrPos: center position of postage stamp on main image
                   (i,j *float* pixels); None until set by setDecimatedImagePos
    - decImEndPos: end position of postage stamp on main image
                   (i,j int pixels); None until set by setDecimatedImagePos
    """

    Separation = 2  # separation between postage stamps, in binned pixels

    def __init__(
        self,
        image,
        mask,
        gpNumber,
        gpExists=True,
        gpEnabled=True,
        gpBits=None,
        gpPlatePosMM=(numpy.nan, numpy.nan),
        gpCtr=(numpy.nan, numpy.nan),
        gpRadius=numpy.nan,
        gpFocusOffset=numpy.nan,
        starCtr=(numpy.nan, numpy.nan),
        starRotation=numpy.nan,
        starXYErrArcsec=(numpy.nan, numpy.nan),
        starRADecErrArcSec=(numpy.nan, numpy.nan),
        fwhmArcSec=numpy.nan,
        posErr=numpy.nan,
    ):
        """Create a PostageStamp
        Inputs (all in binned pixels unless noted):
        - image: postage stamp image array
        - mask: postage stamp mask array
        - gpNumber: guide probe number
        - gpExists: guide probe exists
        - gpEnabled: guide probe enabled (forced False if gpExists is False)
        - gpBits: guide probe bits ("gprobebits" in FITS table and guider keyword);
            0 for guide images that are too old to contain this information
        - gpPlatePosMM: x,y position of guide probe on plate (mm)
        - gpCtr: expected x,y center of probe on image (pixels)
        - gpRadius: radius of guide probe active area; binned pixels
        - gpFocusOffset: focus offset of guide probe (um, direction unknown)
        - starCtr: measured star x,y center
        - starRotation: rotation of star on sky (deg)
        - starXYErrArcsec: position error of guide star on image (arcsec);
            warning: the value in the image table is in mm; be sure to convert it
        - starRADecErrArcSec: position error of guide star on image in RA, Dec on sky arcsec
            warning: the value in the image table is in mm; be sure to convert it
        - fwhmArcSec: FWHM of star (arcsec)
        - posErr: ???a scalar of some kind; centroid uncertainty? (???)
        """
        self.image = numpy.array(image)
        self.mask = numpy.array(mask)
        self.gpNumber = int(gpNumber)
        self.gpExists = bool(gpExists)
        self.gpEnabled = (
            bool(gpEnabled) and self.gpExists
        )  # force false if probe does not exist
        self.gpBits = None if gpBits is None else int(gpBits)
        self.gpPlatePosMM = asArr(gpPlatePosMM)
        self.gpCtr = asArr(gpCtr)
        self.gpRadius = float(gpRadius)
        self.gpFocusOffset = float(gpFocusOffset)
        self.starCtr = asArr(starCtr)
        self.starRotation = float(starRotation)
        self.starXYErrArcsec = asArr(starXYErrArcsec)
        self.starRADecErrArcSec = asArr(starRADecErrArcSec)
        self.fwhmArcSec = float(fwhmArcSec)
        self.posErr = float(posErr)
        self.decImStartPos = None
        self.decImCtrPos = None
        self.decImEndPos = None

    def setDecimatedImagePos(self, ctrPos, mainImageShape):
        """Set position of stamp on decimated image.

        Sets the following fields:
        - decImStartPos
        - decImCtrPos
        - decImEndPos

        Inputs:
        - ctrPos: desired position of center of postage stamp on decimated image (float x,y pixels)
        - mainImageShape: shape of main image (i, j pixels)
            the decimated image position is adjusted as required to keep the probe
            entirely on the main image
        """
        ctrPos = numpy.array(ctrPos, dtype=float)
        if numpy.any(numpy.logical_not(numpy.isfinite(ctrPos))):
            raise RuntimeError("ctrPos %s is not finite" % (ctrPos,))
        if numpy.any(self.image.shape > mainImageShape):
            raise RuntimeError(
                "main image shape %s < %s stamp image shape"
                % (self.image.shape, mainImageShape)
            )

        # swap i,j axes to get x,y axes
        imageXYShape = numpy.array(self.image.shape[::-1], dtype=int)
        mainImageXYShape = numpy.array(mainImageShape[::-1], dtype=int)
        adjustment = (0, 0)
        self.decImStartPos = numpy.round(ctrPos - (imageXYShape / 2.0)).astype(int)
        self.decImEndPos = self.decImStartPos + imageXYShape
        self.decImCtrPos = (self.decImStartPos + self.decImEndPos) / 2.0
        minStartPos = numpy.zeros([2], dtype=int)
        maxEndPos = mainImageXYShape
        leftMargin = self.decImStartPos - minStartPos
        rightMargin = maxEndPos - self.decImEndPos
        adjustment = numpy.where(
            leftMargin < 0,
            -leftMargin,
            numpy.where(rightMargin < 0, rightMargin, (0, 0)),
        )
        if numpy.any(adjustment != (0, 0)):
            self.decImStartPos += adjustment
            self.decImEndPos += adjustment
            self.decImCtrPos += adjustment

    def getDecimatedImageRegion(self):
        """Return region of this stamp on the decimated image.

        Returns a tuple:
        - startSlice: slice(i,j int pixels) for start of region
        - endSlice: slice(i, j int pixels) of end of region
        """
        return tuple(slice(self.decImStartPos[i], self.decImEndPos[i]) for i in (1, 0))

    def getRadius(self):
        """Return radius of this region (float pixels)"""
        return (
            math.sqrt(self.image.shape[0] ** 2 + self.image.shape[1] ** 2)
            + self.Separation
        ) / 2.0


def decimateStrip(imArr):
    """Break an image consisting of a row of square postage stamps into
    individual postage stamp images.

    Inputs:
    - imArr: an image array of shape [imageShape * numIm, imageShape], where numIm is an integer

    Returns:
    - stampImageList: a list of numIm image arrays, each imageShape x imageShape

    Note: the axes of imArr are (y, x) relative to ds9 display of the image.

    Raise ValueError if imArr shape is not [imageShape * numIm, imageShape],
    where numIm is an integer
    """
    stampShape = imArr.shape
    stampSize = imArr.shape[1]
    if stampSize == 0:
        return []
    numIm = stampShape[0] // stampSize
    if stampSize * numIm != stampShape[0]:
        raise ValueError(
            "image shape %s is not a column of an even number of squares"
            % (stampShape,)
        )
    stampImageList = [
        imArr[(ind * stampSize) : ((ind + 1) * stampSize), :] for ind in range(numIm)
    ]
    return stampImageList


class AssembleImage(object):
    # tuning constants
    InitialCorrFrac = 1.5
    MinQuality = 5.0  # system is solved when quality metric reaches this value
    MaxIters = 100

    def __init__(self, relSize=1.0, margin=20):
        """Create a new AssembleImage

        Inputs:
        - relSize: shape of assembled image (along i or j) / shape of original image
        - margin: number of pixels of margin around each edge
        """
        self.relSize = float(relSize)
        self.margin = int(margin)

    def __call__(self, guideImage):
        """Assemble an image array by arranging postage stamps from a guider FITS image

        Inputs:
        - guideImage: a guider image (pyfits image):

        Returns a PlateInfo object

        Note: the contents of the images and masks are not interpreted by this routine;
        the data is simply rearranged into a new output image and mask.

        Written for image format: SDSSFmt = gproc 1 0, but will try to deal with higher versions.

        Raise class NoPlateInfo if the image has no plate information
        Raise PlateInfoWrongVersion if the image has an unparseable version of plate info
        """
        # check version info
        try:
            sdssFmtStr = guideImage[0].header["SDSSFMT"]
        except Exception:
            raise NoPlateInfo("Could not find SDSSFMT header entry")
        try:
            formatName, versMajStr, versMinStr = sdssFmtStr.split()
            formatMajorVers = int(versMajStr)
            # formatMinorVers = int(versMinStr) # don't need minor number for anything
        except Exception:
            raise NoPlateInfo(
                "Could not parse SDSSFMT = {}".format(
                    sdssFmtStr,
                )
            )
        if formatName.lower() != "gproc":
            raise NoPlateInfo(
                "SDSSFMT {} != gproc".format(
                    formatName.lower(),
                )
            )
        if formatMajorVers != 1:
            raise PlateInfoWrongVersion(
                "Can only process SDSSFMT version 1: found {}".format(formatMajorVers)
            )

        # IMAGETYP 'object' has all the necessary HDUs, while 'flat' and 'dark' do not.
        try:
            imagetyp = guideImage[0].header["IMAGETYP"].lower()
        except Exception as e:
            raise NoPlateInfo("Could not find IMAGETYP header entry: {}".format(e))
        if imagetyp != "object":
            raise NoPlateInfo(
                "SDSS guider {} files do not have a plate view.".format(imagetyp)
            )

        try:
            plateScale = float(
                guideImage[0].header["PLATSCAL"]
            )  # plate scale in mm/deg
            plateArcSecPerMM = 3600.0 / plateScale  # plate scale in arcsec/mm
        except Exception:
            raise PlateInfoInvalid("Could not find or parse PLATSCAL header entry")

        inImageShape = numpy.array(guideImage[0].data.shape, dtype=int)
        imageShape = numpy.array(inImageShape * self.relSize, dtype=int)
        dataTable = guideImage[6].data

        try:
            background = float(guideImage[0].header["IMGBACK"])
        except Exception:
            sys.stderr.write(
                "AssembleImage: IMGBACK header missing; estimating background locally\n"
            )
            background = numpy.median(guideImage[0].data.astype(numpy.float))

        smallStampImage = guideImage[2].data - background
        largeStampImage = guideImage[4].data - background

        smallStampImageList = decimateStrip(smallStampImage)
        smallStampMaskList = decimateStrip(guideImage[3].data)
        if len(smallStampImageList) != len(smallStampMaskList):
            raise PlateInfoInvalid(
                "%s small image stamps != %s small image masks"
                % (len(smallStampImageList), len(smallStampMaskList))
            )
        numSmallStamps = len(smallStampImageList)

        largeStampImageList = decimateStrip(largeStampImage)
        largeStampMaskList = decimateStrip(guideImage[5].data)
        if len(largeStampImageList) != len(largeStampMaskList):
            raise PlateInfoInvalid(
                "%s large image stamps != %s large image masks"
                % (len(largeStampImageList), len(largeStampMaskList))
            )
        numLargeStamps = len(largeStampImageList)
        numStamps = numSmallStamps + numLargeStamps

        if numStamps == 0:
            raise NoPlateInfo("No postage stamps")

        if smallStampImageList:
            smallStampShape = smallStampImageList[0].shape
        else:
            # no small postage stamps; use the usual value
            smallStampShape = (19, 19)
        bgPixPerMM = (
            numpy.mean((imageShape - smallStampShape - (2 * self.margin)))
            / PlateDiameterMM
        )
        minPosXYMM = -imageShape[::-1] / (2.0 * bgPixPerMM)

        stampList = []
        for ind, dataEntry in enumerate(dataTable):
            stampSizeIndex = dataEntry["stampSize"]
            stampIndex = dataEntry["stampIdx"]
            if (stampSizeIndex < 0) or (stampIndex < 0):
                continue
            if stampSizeIndex == 1:
                if stampIndex > numSmallStamps:
                    raise PlateInfoInvalid(
                        "stampSize=%s and stampIdx=%s but there are only %s small stamps"
                        % (stampSizeIndex, stampIndex, numSmallStamps)
                    )
                image = smallStampImageList[stampIndex]
                mask = smallStampMaskList[stampIndex]
            elif stampSizeIndex == 2:
                if stampIndex > numLargeStamps:
                    raise PlateInfoInvalid(
                        "stampSize=%s and stampIdx=%s but there are only %s large stamps"
                        % (stampSizeIndex, stampIndex, numLargeStamps)
                    )
                image = largeStampImageList[stampIndex]
                mask = largeStampMaskList[stampIndex]
            else:
                continue
            if not dataEntry["exists"]:
                # do not show postage stamp images for nonexistent (e.g. broken) probes
                continue

            # older image files don't contain gprobebits
            # and pyfits tables don't support "get", so...
            try:
                gpBits = dataEntry["gprobebits"]
            except KeyError:
                gpBits = None
            stampList.append(
                PostageStamp(
                    image=image,
                    mask=mask,
                    gpNumber=ind + 1,
                    gpExists=dataEntry["exists"],
                    gpEnabled=dataEntry["enabled"],
                    gpBits=gpBits,
                    gpPlatePosMM=(dataEntry["xFocal"], dataEntry["yFocal"]),
                    gpCtr=(dataEntry["xCenter"], dataEntry["yCenter"]),
                    gpRadius=dataEntry["radius"],
                    gpFocusOffset=dataEntry["focusOffset"],
                    starRotation=dataEntry["rotStar2Sky"],
                    starCtr=(dataEntry["xstar"], dataEntry["ystar"]),
                    starXYErrArcsec=numpy.array((dataEntry["dx"], dataEntry["dy"]))
                    * plateArcSecPerMM,
                    starRADecErrArcSec=numpy.array(
                        (dataEntry["dRA"], dataEntry["dDec"])
                    )
                    * plateArcSecPerMM,
                    fwhmArcSec=(dataEntry["fwhm"]),
                    posErr=dataEntry["poserr"],
                )
            )
        radArr = numpy.array([stamp.getRadius() for stamp in stampList])
        desPosArrMM = numpy.array([stamp.gpPlatePosMM for stamp in stampList])
        desPosArr = (desPosArrMM - minPosXYMM) * bgPixPerMM

        actPosArr, quality, nIter = self.removeOverlap(desPosArr, radArr, imageShape)
        if not numpy.isfinite(quality):
            raise PlateInfoInvalid(
                "removeOverlap failed: guide probe plate positions probably invalid"
            )

        plateImageArr = numpy.zeros(imageShape, dtype=numpy.float32)
        plateMaskArr = numpy.zeros(imageShape, dtype=numpy.uint8)
        for stamp, actPos in zip(stampList, actPosArr):
            stamp.setDecimatedImagePos(actPos, plateImageArr.shape)
            mainRegion = stamp.getDecimatedImageRegion()
            plateImageArr[mainRegion] = stamp.image
            plateMaskArr[mainRegion] = stamp.mask
        return PlateInfo(plateImageArr, plateMaskArr, stampList)

    def removeOverlap(self, desPosArr, radArr, imageShape):
        """Remove overlap from an array of bundle positions.

        Inputs:
        - desPosArr: an array of the desired position of the center of
                     each postage stamp (x,y pixels)
        - radArr: an array of the radius of each postage stamp
        - imageShape: shape of image (i,j pixels)

        Returns:
        - actPosArr: an array of positions of the center of each postage stamp (x,y pixels)
        - quality: quality of solution; smaller is better
        - nIter: number of iterations
        """
        actPosArr = desPosArr.copy()
        maxCorr = radArr.min()
        quality = numpy.inf
        corrArr = numpy.zeros(actPosArr.shape, dtype=float)
        corrFrac = self.InitialCorrFrac
        nIter = 0
        while quality >= self.MinQuality:
            corrArr[:, :] = 0.0
            edgeQuality = self.computeEdgeCorr(
                corrArr, actPosArr, radArr, corrFrac, imageShape
            )
            conflictQuality = self.computeConflictCorr(
                corrArr, actPosArr, radArr, corrFrac
            )
            quality = edgeQuality + conflictQuality

            # limit correction to max corr
            corrRadius = numpy.sqrt(corrArr[:, 0] ** 2 + corrArr[:, 1] ** 2)
            for ind in range(2):
                corrArr[:, ind] = numpy.where(
                    corrRadius > maxCorr,
                    (corrArr[:, ind] / corrRadius) * maxCorr,
                    corrArr[:, ind],
                )
            actPosArr += corrArr
            quality = edgeQuality + conflictQuality

            nIter += 1
            if nIter > self.MaxIters:
                break

        return (actPosArr, quality, nIter)

    def computeEdgeCorr(self, corrArr, posArr, radArr, corrFrac, imageShape):
        """Compute corrections to keep fiber bundles on the display

        In/Out:
        - corrArr: updated

        In:
        - posArr: position of each fiber bundle (x,y pixels)
        - radArr: radius of each bundle (pixels)
        - corrFrac: fraction of computed correction to apply
        - imageShape: shape of image (i,j pixels)

        Returns:
        - quality: quality of solution due to edge overlap
        """
        quality = 0
        xyImageSize = numpy.array(imageShape[::-1])
        maxXYPosArr = xyImageSize - radArr[:, numpy.newaxis]
        corrArr = numpy.where(
            posArr < radArr[:, numpy.newaxis], radArr[:, numpy.newaxis] - posArr, 0
        )
        corrArr += numpy.where(posArr > maxXYPosArr, maxXYPosArr - posArr, 0)
        quality = numpy.sum(corrArr[:, 0] ** 2 + corrArr[:, 1] ** 2)
        corrArr *= corrFrac
        return quality

    def computeConflictCorr(self, corrArr, posArr, radArr, corrFrac):
        """Compute corrections to avoid overlap with other bundles

        In:
        - posArr: position of each fiber bundle (x,y pixels)
        - radArr: radius of each bundle (pixels)
        - corrFrac: fraction of computed correction to apply

        Returns:
        - quality: quality of solution due to overlap with other bundles
        """
        quality = 0
        corr = numpy.zeros(2, dtype=float)
        for ind, pos in enumerate(posArr):
            rad = radArr[ind]
            minSepArr = radArr + rad
            corr = numpy.zeros(2, dtype=float)
            diffVec = pos - posArr
            radSepArr = numpy.sqrt(diffVec[:, 0] ** 2 + diffVec[:, 1] ** 2)
            radSepArr[ind] = minSepArr[ind]  # don't try to avoid self
            # note: correct half of error; let other object correct the rest
            corrRadArr = numpy.where(
                radSepArr < minSepArr, 0.5 * (minSepArr - radSepArr), 0.0
            )
            corrArr2 = (diffVec / radSepArr[:, numpy.newaxis]) * corrRadArr[
                :, numpy.newaxis
            ]
            corr = numpy.sum(corrArr2, 0)
            quality += corr[0] ** 2 + corr[1] ** 2
            corrArr[ind] += corr * corrFrac
        return quality
