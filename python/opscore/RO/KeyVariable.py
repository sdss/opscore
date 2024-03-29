#!/usr/bin/env python

"""KeyVar and its cousins are used monitor data from the keyword dispatcher.
Keyword data may trigger callbacks or automatically update opscore.RO.Wdg widgets.

CmdVar is used to issue commands via the keyword dispatcher and monitor replies.

Error handling:
KeyVar.__init__ may raise an exception
KeyVar.set must not raise an exception; it should print warnings and errors to sys.stderr

History:
2001-01-10 R Owen: mod. FloatCnv to stop using nan (since python on Mac OS X doesn't support it);
    FloatCnv can now only detect the string version of "NaN".
2002-01-25 R Owen: Mod. to use the new opscore.RO.Wdg.getWdgBG function to determine
    background colors for good and bad vlues. Mod. to use SetWidgetText class,
    which reduces the complexity of the addWdgText, etc.
2002-02-05 R Owen: Mod. Intcnv to accept "NaN" for integers.
2002-03-04 R Owen: improved error messages from conversion classes.
2002-03-14 R Owen: major overhaul of callbacks:
    - addSetFunc renamed to addIndexedCallback; they now receive a 2nd positional argument isValid*
    - addCallback now receives a list of value, isValid duples*
    - added addValueListCallback, which is like the old addCallback
    The two callbacks that receive isValid may now get non-None values when isValid false
2002-05-02 R Owen: added an isRefresh field to KeyCmd. (It may be smarter to just
    let the opscore.RO.KeyDispatcher handle this knowledge by itself. We'll see.)
2002-05-29 R Owen: modified KeyCommand to accept timeLimKeyword and to compute self.maxEndTime
2002-06-11 R Owen: added a substitution dictionary to StringCnv.
2003-03-05 ROwen    Got rid of the whole idea of isValid; this simplifies get and callbacks;
    get now matches set (except for aggregate variables like PVTVar)
2003-04-10 ROwen    Modified FloatCnv and IntCnv to work with unicode strings.
2003-04-28 ROwen    Modified converter functions to use __call__ instead of cnv.
2003-05-08 ROwen    Corrected the test suite (was crashing on too few values);
                    moved all conversion functions to opscore.RO.CnvUtil
                    and removed use of typeName attribute in cnv functions.
2003-06-09 ROwen    Bug fix: inconsistent use of self.msgDict and self._msgDict.
2003-06-11 ROwen    Removed keyword argument from set.
2003-06-17 ROwen    Modified to call PVTVar callbacks 1/second if vel nonzero for any component;
                    note that this means KeyVariable now relies on Tkinter;
                    removed SetWidgetText class; it was not being used.
2003-06-25 ROwen    Modified to handle message data as a dict.
2003-07-16 ROwen    Added refreshTimeLim to KeyVar.
2003-08-04 ROwen    Changed default callNow to False.
2003-08-13 ROwen    Moved TypeDict and AllTypes from KeyDispatcher
                    and added DoneTypes.
2003-09-23 ROwen    KeyCommand modified: added isDone and reply rejects attempts
                    once the command has finished.
2003-10-22 ROwen    Bug fix: KeyCommand was looking for uppercase match strings;
                    also modified KeyCommand to always lowercase callTypes
                    to avoid this sort of problem in the future.
2003-11-21 ROwen    Overhauled handling of nval to permit varying-length KeyVars
                    and to auto-computate nval by default.
                    Modified to use SeqUtil instead of MathUtil.
2003-12-05 ROwen    Modified for opscore.RO.Wdg.Entry changes.
2003-12-17 ROwen    Added KeyVarFactory.
                    Modified KeyVar to support the actor "keys", via new keyword refreshKeys
                    and new attribute refreshInfo. Keys is used to refresh values from a cache,
                    to save querying the original actor.
2003-12-26 ROwen    Added removeCallback method.
2004-01-06 ROwen    Removed refreshKeys arg from KeyVar (use KeyVarFactory.setKeysRefreshCmd instead);
                    added hasRefreshCmd and getRefreshInfo to KeyVar;
                    added setKeysRefreshCmd to KeyVarFactory.
2004-01-29 ROwen    Added isGenuine method to key variables.
2004-03-11 ROwen    KeyCommand timeLim documentation now states 0=no limit.
2004-04-19 ROwen    Speeded up handling of timeLimKeyword, based on the message's
                    keyword data being a dictionary instead of (formerly) a list.
2004-07-21 ROwen    Renamed KeyCommand to CmdVar and modified as follows:
                    - Added abortCmdStr argument
                    - Added abort method
                    - Added didFail method
                    - changed callback named argument from keyCmd to cmdVar
                    - changed cmdStarted to _setStartInfo (for clarity)
                      and added dispatcher and cmdID arguments.
                    - callbacks are now protected (if a callback
                      fails a traceback is printed and the others are called).
                    - initialized with type "i" (information) instead of None;
                      this assures CmdVars always have a character type.
                    - added a dispatcher argument which immediately
                    - added removeCallback method
                    KeyVar changes:
                    - setNotCurrent()-induced callbacks are now protected (if a callback
                      fails a traceback is printed and the others are called)
                    - added __str__, which includes no type info
                    - added removeCallback method (via inheriting from opscore.RO.AddCallback.BaseMixin)
                    Added constant FailTypes.
2004-08-13 ROwen    Modified CmdVar.abort to make it only call the dispatcher
                    if command not already done.
                    KeyVarFactory: added refreshOptional argument.
2004-09-23 ROwen    Made callNow=True the default for callbacks
                    script displays are current when first displayed.
2004-09-28 ROwen    Modified to allow removing callbacks while executing.
                    Removed use of attribute _inCallbacks.
2005-02-01 ROwen    Bug fix: if an error occurred early in instantiation,
                    formatting the exception string failed because no self.actor.
2005-06-08 ROwen    Changed CmdVar and KeyVarFactory to new style classes.
2005-06-14 ROwen    Modified CmdVar to clear all callbacks when command is done
                    (to allow garbage collection).
2005-06-16 ROwen    Added getSeverity method to KeyVar and CmdVar.
                    Modified TypeDict; 2nd element of each value is now severity
                    (one of opscore.RO.Constants.sev...) instead of a logger category.
2005-06-24 ROwen    Added getCmdrCmdID method to KeyVar.
                    Changed CmdVar.replies to CmdVar.lastReply.
2006-03-06 ROwen    KeyVar now emulates a normal sequence for read-only access to its values,
                    thus "a in var", var[i], var[i:j] and len(var).
2006-11-02 ROwen    Added keyVars argument to CmdVar. This allows retrieving data
                    returned as the result of a command.
2006-11-09 ROwen    Typo fix: self_keyVarID -> self._keyVarID.
2007-07-02 ROwen    Added hasVel method to PVTKeyVar.
2008-06-26 ROwen    Improved documentation for abortCmdStr and keyVars arguments to CmdVar constructor.
2009-05-12 ROwen    TypeDict changes: added "d" (debug) and removed obsolete "s" (status).
2009-06-24 ROwen    Bug fix: an error message had values reversed.
2009-07-20 ROwen    Modified for tweaked KeyDispatcher API.
                    Removed support for refreshTimeLim (it is now a constant in the KeyDispatcher).
2011-02-17 ROwen    Document that addROWdgSet can take fewer widgets than values, but not more.
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
2011-06-17 ROwen    Changed "type" to "msgType" in parsed message dictionaries to avoid conflict with builtin.
2012-06-01 ROwen    Modified CmdVar cleanup as follows:
                    - Do NOT remove keyVars (so the user can still read them)
                    - Remove the time limit keyVar callback, if present
                    - Use best effort to remove callbacks (do not raise an exception)
2012-07-09 ROwen    Removed unused import in demo section.
2012-07-18 ROwen    Modified to use opscore.RO.Comm.Generic.Timer.
2012-11-29 ROwen    In CmdVar cast actor, cmdStr and abortCmdStr to str to avoid unicode.
2014-03-14 ROwen    Bug fix: abortCmdStr was cast to str even if it was None: changed default to "",
                    but also test for None for backwards compability.
2014-09-15 ROwen    Bug fix: an error message used a nonexistent variable.
                    Tweaked PVTVar._doCallbacks to do nothing if callbacks disabled.
2015-09-24 ROwen    Replace "== None" with "is None" to modernize the code.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
2015-11-05 ROwen    Stop using dangerous bare "except:".
"""
__all__ = ["TypeDict", "AllTypes", "DoneTypes", "FailTypes", "KeyVar", "PVTKeyVar", "CmdVar", "KeyVarFactory"]

import sys
import time
import traceback
import opscore.RO.AddCallback
import opscore.RO.Alg
import opscore.RO.CnvUtil
import opscore.RO.Constants
import opscore.RO.LangUtil
import opscore.RO.PVT
import opscore.RO.StringUtil
import opscore.RO.SeqUtil
import opscore.RO.Comm.Generic
if opscore.RO.Comm.Generic.getFramework() is None:
    print("Warning: opscore.RO.Comm.Generic framework not set; setting to tk")
    opscore.RO.Comm.Generic.setFramework("tk")
from opscore.RO.Comm.Generic import Timer

# TypeDict translates message type characters to message categories
# entries are: (meaning, category), where:
# meaning is used for messages displaying what's going on
# category is coarser and is used for filtering by category
TypeDict = {
    "!":("fatal error", opscore.RO.Constants.sevError), # a process dies
    "e":("error", opscore.RO.Constants.sevError),  # error, but command is not done
    "f":("failed", opscore.RO.Constants.sevError), # command failed
    "w":("warning", opscore.RO.Constants.sevWarning),
    "i":("information", opscore.RO.Constants.sevNormal), # the initial state
    "d":("debug", opscore.RO.Constants.sevDebug),
    ">":("queued", opscore.RO.Constants.sevNormal),
    ":":("finished", opscore.RO.Constants.sevNormal),
}
# all message types
AllTypes = "".join(list(TypeDict.keys()))
# useful other message types
DoneTypes = ":f!"
FailTypes = "f!"

class KeyVar(opscore.RO.AddCallback.BaseMixin):
    """Processes data associated with a keyword.

    Inputs:
    - keyword: the keyword associated with this variable (a string)
    - nval: the number of values:
        - if None, a fixed length KeyVar is assumed whose length is computed from converters
        - if a single integer, specifies the exact # of value required
        - if a pair of integers, specifies (min, max) # of values required;
            max = None means "no limit"
    - converters: one or a sequence of data converters (see below for more details);
        if there are more values than converters, the last converter is repeated;
        if there are more converters than allowed values, a ValueError is raised
    - actor: the name of the device which issued the keyword
    - description: a string describing the data, useful for help systems
    - refreshCmd: a command which can executed to refresh this item of data
    - dispatcher: keyword dispatcher; if supplied, the keyword subscribes itself to the dispatcher.
        Note that no record of that dispatcher is kept in the keyword (to reduce
        circular references, which as of this writing may not be garbage collected);
        so to unsubscribe this keyword you must talk to the dispatcher.
    - defValues: the value used initially and when data cannot be parsed;
        if one value, it is copied as many times as needed (max # of val, if finite, else min # of val)
        if a list of values, it is used "as is", after verifying the # of elements is in range
        Warning: default values are not converted and must be of the correct type; no checking is done
    - doPrint: a boolean flag controlling whether data is printed as set; for debugging

    Converters are functions that take one argument and return the converted data.
    The data supplied will usually be a string, but pre-converted data should
    also be acceptable. The converter should raise ValueError or TypeError for invalid data.

    There is an addCallback function that adds a callback function
    that is passed the following arguments whenever the KeyVar gets a reply
    or isCurrent goes false (as happens upon disconnection):
    - valueList: the new list of values,
      (or the existing list if the variable is explicitly invalidated)
    - isCurrent (by name): false if value is not current
    - keyVar (by name): this keyword variable

    If a subclass sets self.cnvDescr before calling __init__
    then the original is retained.
    """
    def __init__(self,
        keyword,
        nval = None,
        converters = opscore.RO.CnvUtil.nullCnv,
        actor = "",
        description = "",
        refreshCmd = None,
        dispatcher = None,
        doPrint = False,
        defValues = None,
    ):
        self.actor = actor
        self.keyword = keyword
        self.description = description
        self.lastType = None
        if not hasattr(self, "cnvDescr"):
            self.cnvDescr = "" # temporary value for error messages

        # set and check self._converterList, self.minNVal and self.maxNVal
        self._converterList = opscore.RO.SeqUtil.asList(converters)
        if nval is None:
            # auto-compute
            self.minNVal = self.maxNVal = len(self._converterList)
        else:
            try:
                self.minNVal, self.maxNVal = opscore.RO.SeqUtil.oneOrNAsList(nval, 2, "nval")
                assert isinstance(self.minNVal, int)
                assert self.minNVal >= 0
                if self.maxNVal is not None:
                    assert isinstance(self.maxNVal, int)
                    assert self.maxNVal >= self.minNVal
            except (ValueError, TypeError, AssertionError):
                raise ValueError("invalid nval = %r for %s" % (nval, self))

            if opscore.RO.SeqUtil.isSequence(converters) and self.maxNVal is not None and len(converters) > self.maxNVal:
                raise ValueError("Too many converters (%d > %d=max) for %s" %
                    (len(converters), self.maxNVal, self))

        #+
        # set self.cnvDescr (if necessary); this is used for __repr__ and error messages
        #-
        def nvalDescr():
            """Returns a string describing the range of values:
            """
            def asStr(numOrNone):
                if numOrNone is None:
                    return "?"
                return "%r" % (numOrNone,)

            if self.minNVal == self.maxNVal:
                # fixed number of values; return it as a string
                return str(self.minNVal)
            else:
                # number of values varies; return the range as a string
                return "(%s-%s)" % (asStr(self.minNVal), asStr(self.maxNVal))

        if not self.cnvDescr:
            if self.maxNVal == 0:
                cnvDescr = "0"
            elif opscore.RO.SeqUtil.isSequence(converters):
                cnvNameList = [opscore.RO.LangUtil.funcName(cnv) for cnv in converters]
                cnvNameStr = ", ".join(cnvNameList)
                if not (self.minNVal == self.maxNVal == len(cnvNameList)):
                    # not a fixed length keyVar or length != # of converters
                    cnvNameStr += "..."
                cnvDescr = "%s, (%s)" % (nvalDescr(), cnvNameStr)
            else:
                cnvDescr = "%s, %s" % (nvalDescr(), opscore.RO.LangUtil.funcName(converters))
            self.cnvDescr = cnvDescr


        # handle refresh info; having a separate refreshActor
        # allows KeyVarFactory.setKeysRefreshCmd to set it to "keys"
        self.refreshActor = self.actor
        self.refreshCmd = refreshCmd

        self.doPrint = doPrint
        self._msgDict = None    # message dictionary used to set KeyVar; can be None
        self._setTime = None
        self._refreshKeyCmd = None  # most recent command used to refresh
        self._valueList = []

        opscore.RO.AddCallback.BaseMixin.__init__(self, defCallNow = True)

        # handle defaults
        if opscore.RO.SeqUtil.isSequence(defValues):
            self._defValues = defValues
        else:
            if self.maxNVal is not None:
                nval = self.maxNVal
            else:
                nval = self.minNVal
            self._defValues = (defValues,) * nval
        self._restoreDefault()

        self._isCurrent = False

        # if a keyword dispatcher is specified, add the keyword to it
        if dispatcher:
            dispatcher.addKeyVar(self)

    def __repr__(self):
        return "%s(%r, %r, %s)" % \
            (self.__class__.__name__, self.actor, self.keyword, self.cnvDescr)

    def __str__(self):
        return "%s(%r, %r)" % \
            (self.__class__.__name__, self.actor, self.keyword)

    def _restoreDefault(self):
        """Set self._valueList to initial values but does not call callbacks."""
        if self._defValues is not None:
            self._valueList = self._defValues[:]

    def addDict (self, dict, item, fmtStr, ind=0):
        """Adds a dictionary whose specified item is to be set"""
        def setFunc (value, isCurrent, keyVar, dict=dict, item=item, fmtStr=fmtStr):
            if value is not None:
                dict[item] = fmtStr % value
            else:
                dict[item] = None
        self.addIndexedCallback (setFunc, ind)

    def addDictDMS (self, dict, item, nFields=3, precision=1, ind=0):
        """Adds a dictionary whose specified item is to be set to the DMS representation of the data"""
        def setFunc (value, isCurrent, keyVar, dict=dict, item=item, precision=precision):
            if value is not None:
                dict[item] = opscore.RO.StringUtil.dmsStrFromDeg(value, nFields, precision)
            else:
                dict[item] = None
        self.addIndexedCallback (setFunc, ind)

    def addIndexedCallback(self, callFunc, ind=0, callNow=True):
        """Similar to addCallback, but the call function receives the value at one index.
        This simplifies callbacks a bit, especially for aggregate values (see PVTKeyVar).

        Note: if the keyvariable has a variable # of values and the one specified
        by ind is not set, the callback is not called. In general, it is discouraged
        to use indexed callbacks for variable-length keyvariables.

        Inputs:
        - callFunc: callback function with arguments:
          - value: new value at the specified index (or the existing value
                if the variable is explicitly invalidated)
          - isCurrent (by name): false if value is not current
          - keyVar (by name): this keyword variable
        - callNow: if true, execute callFunc immediately,
          else wait until the keyword is seen
        """
        if self.maxNVal == 0:
            raise ValueError("%s has 0 values; addIndexedCallback prohibited" % (self,))
        try:
            opscore.RO.MathUtil.checkRange(ind+1, 1, self.maxNVal)
        except ValueError:
            raise ValueError("invalid ind=%r for %s" % (ind, self,))

        def fullCallFunc(valueList, isCurrent, keyVar, ind=ind):
            try:
                val = valueList[ind]
            except IndexError:
                return
            callFunc(val, isCurrent=isCurrent, keyVar=keyVar)
        self.addCallback(fullCallFunc, callNow)

    def addROWdg (self, wdg, ind=0, setDefault=False):
        """Adds an opscore.RO.Wdg; these format their own data via the set
        or setDefault function (depending on setDefault).
        Typically one uses set for a display widget
        and setDefault for an Entry widget
        """
        if setDefault:
            self.addIndexedCallback (wdg.setDefault, ind)
        else:
            self.addIndexedCallback (wdg.set, ind)

    def addROWdgSet (self, wdgSet, setDefault=False):
        """Adds a set of opscore.RO.Wdg wigets

        There may be fewer widgets than values, but not more widgets.

        This should be more efficient than adding them one at a time with addROWdg.

        Raise IndexError if there are more widgets than values.
        """
        if self.maxNVal is not None and len(wdgSet) > self.maxNVal:
            raise IndexError("too many widgets (%d > max=%d) for %s" % (len(wdgSet), self.maxNVal, self,))
        if setDefault:
            class callWdgSet(object):
                def __init__(self, wdgSet):
                    self.wdgSet = wdgSet
                    self.wdgInd = list(range(len(wdgSet)))
                def __call__(self, valueList, isCurrent, keyVar):
                    for wdg, val in zip(self.wdgSet, valueList):
                        wdg.setDefault(val, isCurrent=isCurrent, keyVar=keyVar)
        else:
            class callWdgSet(object):
                def __init__(self, wdgSet):
                    self.wdgSet = wdgSet
                    self.wdgInd = list(range(len(wdgSet)))
                def __call__(self, valueList, isCurrent, keyVar):
                    for wdg, val in zip(self.wdgSet, valueList):
                        wdg.set(val, isCurrent=isCurrent, keyVar=keyVar)
        self.addCallback (callWdgSet(wdgSet))

    def get(self):
        """Returns the data as a tuple:
        - valueList: a copy of the list of values
        - isCurrent
        """
        return self._valueList[:], self._isCurrent

    def getInd(self, ind):
        """Returns the data at index=ind as a tuple:
        - value: the value at index=ind
        - isCurrent
        """
        return self._valueList[ind], self._isCurrent

    def getCmdrCmdID(self):
        """Return (cmdr, cmdID) of the most recent message,
        or None if no message ever received.
        """
        if not self._msgDict:
            return None
        return (self._msgDict["cmdr"], self._msgDict["cmdID"])

    def getMsgDict(self):
        """Returns the message dictionary from the most recent call to "set",
        or an empty dictionary if no dictionary supplied or "set" never called.
        """
        return self._msgDict or {}

    def getRefreshInfo(self):
        """Return refresh actor, refresh command (None if no command).
        """
        return (self.refreshActor, self.refreshCmd)

    def getSeverity(self):
        """Return severity of most recent message,
        or opscore.RO.Constants.sevNormal if no messages received.
        """
        if not self.lastType:
            return opscore.RO.Constants.sevNormal
        return TypeDict[self.lastType][1]

    def hasRefreshCmd(self):
        """Return True if has a refresh command.
        """
        return bool(self.refreshCmd)

    def isCurrent(self):
        return self._isCurrent

    def isGenuine(self):
        """Return True if there is a message dict and it is from the actual actor.
        """
        actor = self.getMsgDict().get("actor")
        return actor == self.actor

    def set(self, valueList, isCurrent=True, msgDict=None):
        """Sets the variable's value,
        then updates the time stamp and executes the callbacks (if any)

        Inputs:
        - valueList: a tuple of new values; if None then all values are reset to default
        - msgDict: the full keyword dictionary, see KeywordDispatcher for details
          note: if supplied, msgDict must contain a field "msgType" with a valid type character

        Errors:
        If valueList has the wrong number of elements then the data is rejected
        and an error message is printed to sys.stderr
        If msgType in msgDict is missing or invalid, a warning message is printed
        to sys.stderr and self.lastType is set to warning.
        """
        if valueList is None:
            self._restoreDefault()
        else:
            nout = self._countValues(valueList)

            # set values
            self._valueList = [self._convertValueFromList(ind, valueList) for ind in range(nout)]

        # update remaining parameters
        self._isCurrent = isCurrent
        self._setTime = time.time()
        self._msgDict = msgDict
        if msgDict:
            try:
                self.lastType = msgDict["msgType"]
            except KeyError:
                sys.stderr.write("%s.set warning: 'msgType' missing in msgDict %r" % (self, msgDict))
                self.lastType = "w"
            if self.lastType not in TypeDict:
                sys.stderr.write("%s.set warning: invalid 'msgType'=%r in msgDict %r" % (self, self.lastType, msgDict))
                self.lastType = "w"

        # print to stderr, if requested
        if self.doPrint:
            sys.stderr.write ("%s = %r\n" % (self, self._valueList))

        # apply callbacks, if any
        self._doCallbacks()

    def setNotCurrent(self):
        """Clears the isCurrent flag

        Does NOT update _setTime because that tells us when the value was last set;
        if we need a timestamp updated when the data was marked stale, add a new one.
        """
        self._isCurrent = False

        # print to stderr, if requested
        if self.doPrint:
            sys.stderr.write ("%s=%r\n" % (self, self._valueList))

        self._doCallbacks()

    def _convertValueFromList(self, ind, valueList):
        """A utility function for use on list of raw (unconverted) values.
        Returns cnvValue for valueList[ind], or None if value cannot be converted.

        Error handling:
        - If the value cannot be converted, complains and returns (valueList[ind], 0)
        - If the value does not exist in the list (or the converter does not exist),
          silently returns (None, 0) (a message has already been printed)
        """
        rawValue = valueList[ind]
        if rawValue is None:
            return None
        try:
            return self._getCnvFunc(ind)(rawValue)
        except (ValueError, TypeError) as e:
            # value could not be converted
            sys.stderr.write("invalid value %r for ind %s of %s\n" % (rawValue, ind, self))
            return None
        except Exception as e:
            # unknown error; this should not happen
            sys.stderr.write("could not convert %r for ind %d of %s: %s\n" % (rawValue, ind, self, e))
            return None

    def _countValues(self, valueList):
        """Check length of valueList and return the number of values there should be after conversion.
        """
        nval = len(valueList)
        if nval < self.minNVal:
            raise ValueError("too few values in %r for %s (%s < %s)" % (valueList, self, nval, self.minNVal))
        if self.maxNVal is not None and nval > self.maxNVal:
            raise ValueError("too many values in %r for %s (%s > %s)" % (valueList, self, nval, self.maxNVal))
        return nval

    def _doCallbacks(self):
        """Call the callback functions.
        """
        self._basicDoCallbacks(
            self._valueList,
            isCurrent = self._isCurrent,
            keyVar = self,
        )

    def _getCnvFunc(self, ind):
        """Returns the appropriate converter function for index ind.
        If ind < 0, returns the last one
        """
        try:
            return self._converterList[ind]
        except IndexError:
            return self._converterList[-1]

    def __contains__(self, a):
        """Return a in values"""
        return a in self._valueList

    def __getitem__(self, ind):
        """Return value[ind]"""
        return self._valueList[ind]

    def __getslice__(self, i, j):
        """Return values[i:j]"""
        return self._valueList[i:j]

    def __len__(self):
        """Return len(values)"""
        return len(self._valueList)


class PVTKeyVar(KeyVar):
    """Position, velocity, time tuple for a given # of axes.

    To do: make regular callbacks optional for vel!=0 or remove entirely
    and ask the user to implement this directly.

    Similar to KeyVar, but:
    - The supplied keyword data is in the form:
        pos1, vel1, t1, pos2, vel2, t2..., pos<naxes>, vel<naxes>, t<naxes>
    - Values are PVTs
    - The callback function is called once per second if velocity nonzero for any axis.
    """
    def __init__(self,
        keyword,
        naxes=1,
        **kargs
    ):
        if naxes < 1:
            raise ValueError("naxes = %d, but must be positive" % (naxes))
        self.cnvDescr = str(naxes)
        KeyVar.__init__(self,
            keyword = keyword,
            nval = naxes,
            converters = opscore.RO.CnvUtil.asFloat,
            defValues = opscore.RO.PVT.PVT(),
        **kargs)

        self._hasVel = False
        self._timer = Timer()

    def addPosCallback(self, callFunc, ind=0, callNow=True):
        """Similar to addIndexedCallback, but the call function
        receives the current position at one index.

        Inputs:
        - callFunc: callback function with arguments:
          - value: new current position of the PVT at the specified index
            (or of the existing PVT if the variable is explicitly invalidated)
          - isCurrent (by name): false if value is not current
          - keyVar (by name): this keyword variable
        - callNow: if true, execute callFunc immediately,
          else wait until the keyword is seen
        """
        def fullCallFunc(valueList, isCurrent, keyVar, ind=ind):
            return callFunc(valueList[ind].getPos(), isCurrent=isCurrent, keyVar=keyVar)
        self.addCallback(fullCallFunc, callNow)

    def addROWdg (self, wdg, ind=0):
        """Adds an opscore.RO.Wdg; these format their own data via the set function"""
        self.addPosCallback (wdg.set, ind)

    def addROWdgSet (self, wdgSet):
        """Adds a set of opscore.RO.Wdg wigets that are set to the current position.

        There may be fewer widgets than values, but not more widgets.

        This should be more efficient than adding them one at a time with addROWdg.

        Raise IndexError if there are more widgets than values.
        """
        if self.maxNVal is not None and len(wdgSet) > self.maxNVal:
            raise IndexError("too many widgets (%d > max=%d) for %s" % (len(wdgSet), self.maxNVal, self,))
        class callWdgSet(object):
            def __init__(self, wdgSet):
                self.wdgSet = wdgSet
                self.wdgInd = list(range(len(wdgSet)))
            def __call__(self, valueList, isCurrent, keyVar):
                for ind in self.wdgInd:
                    wdgSet[ind].set(valueList[ind].getPos(), isCurrent=isCurrent, keyVar=keyVar)
        self.addCallback (callWdgSet(wdgSet))

    def hasVel(self):
        """Return True if velocity known and nonzero for any axis
        """
        return self._hasVel

    def set(self, *args, **kargs):
        self._hasVel = False
        KeyVar.set(self, *args, **kargs)

    def _convertValueFromList(self, ind, valueList):
        """Returns converted value at index ind, given valueList,
        or a null PVT if cannot convert. Should only be called by set.

        Error handling:
        - If the value cannot be converted, complains and returns a null PVT
        - If the value does not exist in the list (or the converter does not exist),
          returns a null PVT after somebody prints a message
        """
        try:
            startInd = ind * 3
            rawValue = valueList[startInd:startInd+3]
            pvt = opscore.RO.PVT.PVT(*rawValue)
            if pvt.vel not in (0.0, None):
                self._hasVel = True
            return pvt
        except (ValueError, TypeError):
            # value could not be converted
            sys.stderr.write("invalid value %r at index %d for %s\n" % (rawValue, ind, self))
            return opscore.RO.PVT.PVT()
        except IndexError:
            # value does not exist (or converter does not exist, but that's much less likely)
            # a message should already have been printed
            return opscore.RO.PVT.PVT()
        except Exception as e:
            # unknown error; this should not happen
            sys.stderr.write("could not convert %r at index %d for %s: %s\n" % (rawValue, ind, self, e))
            return opscore.RO.PVT.PVT()

    def _countValues(self, valueList):
        """Check length of valueList and return the number of values there should be after conversion.
        """
        nval = len(valueList)
        if nval < self.minNVal * 3:
            raise ValueError("too few values in %r for %s (%s < %s)" % (valueList, self, nval, self.minNVal * 3))
        if self.maxNVal is not None and nval > self.maxNVal * 3:
            raise ValueError("too many values in %r for %s (%s > %s)" % (valueList, self, nval, self.maxNVal * 3))
        if nval % 3 != 0:
            raise ValueError("%s must contain a multiple of 3 elements for %s" % (valueList, self))
        return nval // 3

    def _doCallbacks(self):
        """Call the callback functions.
        """
        if self.callbacksEnabled():
            self._timer.cancel()
            KeyVar._doCallbacks(self)
            if self._hasVel:
                self._timer.start(1.0, self._doCallbacks)

class CmdVar(object):
    """Issue a command via the dispatcher and receive callbacks
    as replies are received.
    """
    def __init__(self,
        cmdStr = "",
        actor = "",
        timeLim = 0,
        description = "",
        callFunc = None,
        callTypes = DoneTypes,
        isRefresh = False,
        timeLimKeyword = None,
        abortCmdStr = "",
        dispatcher = None,
        keyVars = None,
    ):
        """
        Inputs:
        - actor: the name of the device which issued the keyword
        - cmdStr: the command; no terminating \n wanted
        - timeLim: maximum time before command expires, in sec; 0 for no limit
        - description: a string describing the command, useful for help systems
        - callFunc: a function to call when the command changes state;
            see addCallback for details.
        - callTypes: the message types for which to call the callback;
            see addCallback for details.
        - isRefresh: the command was triggered by a refresh request, else is a user command
        - timeLimKeyword: a keyword specifying a delta-time by which the command must finish
        - abortCmdStr: a command string that will abort the command, or "" if none.
            Sent to the actor if abort is called and if the command is executing.
        - dispatcher: command dispatcher; if specified, the command is automatically dispatched;
            otherwise you have to dispatch it yourself
        - keyVars: a sequence of 0 or more keyword variables to monitor.
            Any data for those variables that arrives IN RESPONSE TO THIS COMMAND is saved
            and can be retrieved using cmdVar.getKeyVarData or cmdVar.getLastKeyVarData.

        Note: timeLim and timeLimKeyword work together as follows:
        - The initial time limit for the command is timeLim
        - If timeLimKeyword is seen before timeLim seconds have passed
          then self.maxEndTime is updated with the new value

        Also the time limit is a lower limit. The command is guaranteed to
        expire no sooner than this
        """
        self.cmdStr = str(cmdStr)
        self.actor = str(actor)
        self.cmdID = None
        self.timeLim = timeLim
        self.description = description
        self.isRefresh = isRefresh
        self.timeLimKeyword = timeLimKeyword
        self.abortCmdStr = str(abortCmdStr) if abortCmdStr else None # test None for backwards compatibility
        self.keyVarDict = dict()
        if keyVars is None:
            keyVars = ()
        else:
            for keyVar in keyVars:
                self.keyVarDict[self._keyVarID(keyVar)] = []
        self.keyVars = keyVars

        self.dispatcher = None # dispatcher arg is handled later
        self.lastReply = None
        self.lastType = "i"
        self.startTime = None
        self.maxEndTime = None

        # the following is a list of (callTypes, callFunc)
        self.callTypesFuncList = []

        # if a timeLimKeyword specified
        # set up a callback, but only for non-final message types
        # (changing the time limit for the final message is a waste of time)
        if self.timeLimKeyword:
            self.addCallback(self._checkForTimeLimKeyword, callTypes = ">siw")

        if callFunc:
            self.addCallback(callFunc, callTypes)

        if dispatcher:
            dispatcher.executeCmd(self)

    def abort(self):
        """Abort the command, including:
        - deregister the command from the dispatcher
        - send the abort command (if it exists)
        - set state to failed, calling the appropriate callbacks

        Has no effect if the command was never dispatched or has already ended.
        """
        if self.dispatcher and not self.isDone():
            self.dispatcher.abortCmdByID(self.cmdID)

    def addCallback(self, callFunc, callTypes = DoneTypes):
        """Executes the given function whenever a reply is seen
        for this user with a matching command number

        Inputs:
        - callFunc: a function to call when the command changes state
        - callTypes: the message types for which to call the callback;
            a string of one or more choices; see TypeDict for the choices;
            useful constants include DoneTypes (command finished or failed)
            and AllTypes (all message types, thus any reply).
            Not case sensitive (the string you supply will be lowercased).

        Callback arguments:
            msgType: the message type, a character (e.g. "i", "w" or ":");
                see TypeDict for the various types.
            msgDict: the entire message dictionary
            cmdVar (by name): this command variable
        """
        self.callTypesFuncList.append((callTypes.lower(), callFunc))

    def didFail(self):
        """Return True if the command failed, False otherwise.
        """
        return self.lastType in FailTypes

    def getSeverity(self):
        """Return severity of most recent message,
        or opscore.RO.Constants.sevNormal if no messages received.
        """
        if not self.lastType:
            return opscore.RO.Constants.sevNormal
        return TypeDict[self.lastType][1]

    def getKeyVarData(self, keyVar):
        """Return all data seen for a given keyword variable,
        or [] if the keyVar was not seen.

        Inputs:
        - keyVar: the keyword variable for which to return data

        Returns a list of time-ordered keyword data
        (the first entry for the first time the keyword was seen, etc.).
        Each entry is a list of keyword data.
        Thus retVal[-1] is the most recent list of data
        and retval[-1][0] is the first item of the most recent list of data.

        Raises KeyError if the keyword variable was not specified at creation.
        """
        return self.keyVarDict[self._keyVarID(keyVar)]

    def getLastKeyVarData(self, keyVar, ind=0):
        """Return that most recent keyword data,
        or None if the keyVar was not seen.

        Inputs:
        - keyVar: the keyword variable for which to return data
        - ind: index of desired value; None for all values

        Raises KeyError if the keyword variable was not specified at creation.
        """
        allVals = self.keyVarDict[self._keyVarID(keyVar)]
        if not allVals:
            return None
        lastVal = allVals[-1]
        if ind is None:
            return lastVal
        return lastVal[ind]

    def isDone(self):
        """Return True if the command is finished, False otherwise.
        """
        return self.lastType in DoneTypes

    def removeCallback(self, callFunc, doRaise=True):
        """Delete the callback function.
        Return True if successful, raise error or return False otherwise.

        Inputs:
        - callFunc  callback function to remove
        - doRaise   raise exception if unsuccessful? True by default.

        If doRaise true:
        - Raises ValueError if callback not found
        - Raises RuntimeError if executing callbacks when called
        Otherwise returns False in either case.
        """
        for typesFunc in self.callTypesFuncList:
            if callFunc == typesFunc[1]:
                self.callTypesFuncList.remove(typesFunc)
                return True
        if doRaise:
            raise ValueError("Callback %r not found" % callFunc)
        return False

    def reply(self, msgDict):
        """Call command callbacks.
        Warn and do nothing else if called after the command has finished.
        """
        if self.lastType in DoneTypes:
            sys.stderr.write("Command %s already finished; no more replies allowed\n" % (self,))
            return
        self.lastReply = msgDict
        msgType = msgDict["msgType"]
        self.lastType = msgType
        for callTypes, callFunc in self.callTypesFuncList[:]:
            if msgType in callTypes:
                try:
                    callFunc(msgType, msgDict, cmdVar=self)
                except Exception:
                    sys.stderr.write ("%s callback %s failed\n" % (self, callFunc))
                    traceback.print_exc(file=sys.stderr)
        if self.lastType in DoneTypes:
            self._cleanup()

    def _checkForTimeLimKeyword(self, msgType, msgDict, **kargs):
        """Looks for self.timeLimKeyword in the message dictionary
        and updates self.maxEndTime if found.
        Adds self.timeLim as a margin (if self.timeLim was ever specified).
        Raises ValueError if the keyword exists but the value is invalid.
        """
        valueTuple = msgDict["data"].get(self.timeLimKeyword)
        if valueTuple is not None:
            if len(valueTuple) != 1:
                raise ValueError("Invalid value %r for timeout keyword %r for command %d: must be length 1"
                    % (valueTuple, self.timeLimKeyword, self.cmdID))
            try:
                newTimeLim = float(valueTuple[0])
            except Exception:
                raise ValueError("Invalid value %r for timeout keyword %r for command %d: must be (number,)"
                    % (valueTuple, self.timeLimKeyword, self.cmdID))
            self.maxEndTime = time.time() + newTimeLim
            if self.timeLim:
                self.maxEndTime += self.timeLim

    def _cleanup(self):
        """Call when command is finished to remove callbacks and avoid wasting or leaking memory.
        """
        self.callTypesFuncList = []
        for keyVar in self.keyVars:
            try:
                keyVar.removeCallback(self._keyVarCallback, doRaise=False)
            except ValueError:
                pass
        if self.timeLimKeyword:
            self.removeCallback(self._checkForTimeLimKeyword, doRaise=False)

    def _setStartInfo(self, dispatcher, cmdID):
        """Called by the dispatcher when dispatching the command.
        """
        self.dispatcher = dispatcher
        self.cmdID = cmdID
        self.startTime = time.time()
        if self.timeLim:
            self.maxEndTime = self.startTime + self.timeLim

        for keyVar in self.keyVars:
            keyVar.addCallback(self._keyVarCallback)

    def _keyVarCallback(self, values, isCurrent, keyVar):
        """Keyword seen; archive the data.
        """
        if not isCurrent:
            return
        keyCmdr, keyCmdID = keyVar.getCmdrCmdID()
        if keyCmdr != self.dispatcher.connection.cmdr:
            return
        if keyCmdID != self.cmdID:
            return
        self.keyVarDict[self._keyVarID(keyVar)].append(values)

    def _keyVarID(self, keyVar):
        """Return an ID suitable for use in a dictionary.
        """
        return id(keyVar)

    def __repr__(self):
        return "%s(cmdID=%r, actor=%r, cmdStr=%r)" % (self.__class__.__name__, self.cmdID, self.actor, self.cmdStr)

    def __str__(self):
        return "%s %r" % (self.actor, self.cmdStr)


class KeyVarFactory(object):
    """Factory for contructing sets of similar KeyVars.

    It allows one to specify default values for parameters
    and override them as desired.

    Inputs are the default values for the key variable type plus:
    - keyVarType: the desired type (KeyVar by default)
    - allowRefresh: default for allowRefresh (see __call__)
    """
    def __init__(self,
        keyVarType = KeyVar,
        allowRefresh = True,
    **defKeyArgs):
        """Specify the default arguments for the key variable type;
        the usual choices are:
        - actor
        - dispatcher
        - refreshCmd
        and possibly:
        - nval
        - converters
        """
        self._keyVarType = keyVarType
        self._allowRefresh = allowRefresh
        self._defKeyArgs = defKeyArgs
        # _actorKeyVarsRefreshDict is for use by setKeysRefreshCmd
        # entries are actor:list of keyVars that are not local
        # and don't have an explicit refresh command
        self._actorKeyVarsRefreshDict = opscore.RO.Alg.ListDict()
        self._actorOptKeywordsRefreshDict = opscore.RO.Alg.ListDict()

    def __call__(self,
        keyword,
        isLocal = False,
        allowRefresh = None,
        refreshOptional = False,
    **keyArgs):
        """Create and return a new key variable.

        The arguments are the same as for the key variable class being constructed
        (with the defaults specified during __init__), plus:
        - isLocal   True means you only want to set the keyword yourself;
                    it forces dispatcher and refreshCmd to None;
        - allowRefresh  is a refresh command allowed?
        - refreshOptional is a refresh command optional?
                    this means it'll be requested from keys, but TUI will pay
                    no attention if it fails to update the keyword.
                    It is ignored if allowRefresh is False
                    and requires at least one other keyword be updated for this actor.

        Raises RuntimeError if allowRefresh true and:
        - isLocal True
        - refreshCmd specified in this call (the default is irrelevant)
        """
        if isLocal:
            keyArgs["dispatcher"] = None
            keyArgs["refreshCmd"] = None

        netKeyArgs = self._defKeyArgs.copy()
        netKeyArgs.update(keyArgs)
        keyVar = self._keyVarType(keyword, **netKeyArgs)

        if allowRefresh is None:
            allowRefresh = self._allowRefresh
        elif allowRefresh:
            # allowRefresh specified True in this call;
            # test for invalid combination of keyword args
            if keyArgs.get("refreshCmd", None):
                raise RuntimeError("%s: refreshCmd prohibited if allowRefresh false" % (keyVar,))
            if isLocal:
                raise RuntimeError("%s: isLocal prohibited if allowRefresh true" % (keyVar,))
            keyArgs["refreshCmd"] = None

        if allowRefresh and (not isLocal) and ("refreshCmd" not in netKeyArgs):
            if refreshOptional:
                self._actorOptKeywordsRefreshDict[keyVar.actor] = keyword
            else:
                self._actorKeyVarsRefreshDict[keyVar.actor] = keyVar
        return keyVar

    def setKeysRefreshCmd(self, getAllKeys = False):
        """Sets a refresh command of keys getFor=<actor> <key1> <key2>...
        for all key variables that meet these criteria:
        - are not local
        - do not have an explicit refresh command
        - produced since the last call to setKeysRefreshCmd

        Inputs:
        - getAllKeys: if True, gets all keys for this actor;
            the refresh command becomes: keys getFor=<actor>
            (without an explicit list of keywords)

        In case key variables with more than one actor have been produced,
        those for each actor get their own command.
        """
        for actor, keyVars in self._actorKeyVarsRefreshDict.items():
            if getAllKeys:
                refreshCmd = "getFor=%s" % (actor,)
            else:
                refreshKeys = [keyVar.keyword for keyVar in keyVars]
                extraKeys = self._actorOptKeywordsRefreshDict.get(actor, [])
                refreshKeys += extraKeys
                refreshCmd = "getFor=%s %s" % (actor, " ".join(refreshKeys))
            #print "setting refreshCmd=%r for keys %s" % (refreshCmd, refreshKeys)
            for keyVar in keyVars:
                keyVar.refreshActor = "keys"
                keyVar.refreshCmd = refreshCmd
        self._actorKeyVarsRefreshDict = opscore.RO.Alg.ListDict()
        self._actorOptKeywordsRefreshDict = opscore.RO.Alg.ListDict()


if __name__ == "__main__":
    from six.moves import tkinter
    doBasic = True
    doFmt = True
    import opscore.RO.Astro.Tm

    root = tkinter.Tk()

    if doBasic:
        print("\nrunning basic variables test")
        varList = (
            KeyVar("Str0-?",       nval=(0,None), converters=str, doPrint=True),
            KeyVar("Empty",        nval=0, doPrint=True),
            KeyVar("Str",          converters=str, doPrint=True),
            KeyVar("Int",          converters=opscore.RO.CnvUtil.asInt, doPrint=True),
            KeyVar("Float",        converters=opscore.RO.CnvUtil.asFloat, doPrint=True),
            KeyVar("Bool",         converters=opscore.RO.CnvUtil.asBool, doPrint=True),
            KeyVar("IntStr",       converters=(opscore.RO.CnvUtil.asInt, str), doPrint=True),
            KeyVar("Str1-2",       nval=(1,2), converters=str, doPrint=True),
            KeyVar("Str2",         nval=2, converters=str, doPrint=True),
            PVTKeyVar("PVT1-2",    naxes=(1,2), doPrint=True),
            PVTKeyVar("PVT2",      naxes=2, doPrint=True),
        )
        dataList = (
            (),
            ("hello",), ("t",), ("F",), (None,), ("",), ("NaN",), (0,), ("0",), (1,), ("1",), (2,), ("2",), (1.2,), ("1.2",),
            ("hello",)*2, ("t",)*2, ("F",)*2, (None,)*2, ("",)*2, ("NaN",)*2, (0,)*2, ("0",)*2, (1,)*2, ("1",)*2, (2,)*2, ("2",)*2, (1.2,)*2, ("1.2",)*2,
            ("hello",)*3, ("t",)*3, ("F",)*3, (None,)*3, ("",)*3, ("NaN",)*3, (0,)*3, ("0",)*3, (1,)*3, ("1",)*3, (2,)*3, ("2",)*3, (1.2,)*3, ("1.2",)*3,
            ("lots", "of", "data", 1, 2, 3),
            (25, "hello",),
            (20, 0.1, 79842, 47, -0.2, 79842,),
            (20, 0.1, "NaN", 47, -0.2, 79842,),
            (20, 0.1, 79842, 47, -0.2, 79842, 88, 0.4, 79842,),
        )

        for data in dataList:
            print("\ndata: ", data)
            for var in varList:
                try:
                    var.set(data)
                except (ValueError, IndexError) as e:
                    print("failed with %s: %s" % (e.__class__.__name__, e))

    if doFmt:
        print("\nrunning format test")
        afl = KeyVar("FloatVar", 1, opscore.RO.CnvUtil.asFloat)
        fmtSet = ("%.2f", "%10.5f", "%.0f")
        dictList = []
        for fmtStr in fmtSet:
            dict = {"text":None}
            dictList.append(dict)
            afl.addDict (dict, "text", fmtStr)

        dict = {"text":None}
        dictList.append(dict)
        afl.addDictDMS (dict, "text", nFields=3, precision=1)


        # create a set of values and apply them one at a time, showing the results each time
        valSet = (0, 3.14159, -98.7654321)
        for val in valSet:
            print("\nval=", val)
            try:
                afl.set((val,))
                for dict in dictList:
                    print(repr(dict["text"]))
            except Exception as e:
                    print(e)

    # test PVT callback
    print("\nrunning pvt callback test; hit ctrl-C to end")

    def pvtCallback(valList, isCurrent, keyVar):
        if valList is None:
            return
        pvt = valList[0]
        print("%s pos = %s" % (pvt, pvt.getPos()))
    pvtVar = PVTKeyVar("PVT")
    pvtVar.addCallback(pvtCallback)
    currTAI = opscore.RO.Astro.Tm.TAI.taiFromPySec()
    pvtVar.set((1.0, 0.1, currTAI))

    root.mainloop()
