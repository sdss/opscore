
"""Constants for the RO package, especially opscore.RO.Wdg.

Supplies the following constants:

For widgets displaying data differently depending on state:
- Normal
- Warning
- Error

Functions to get and set the base url (prefix) for url help
(these are not imported with from ... import *
since they are mainly used internally to opscore.RO.Wdg):
- _joinHelpURL
- _setHelpURLBase

History:
2004-08-11 ROwen    Split out from opscore.RO.Wdg.Label and opscore.RO.Wdg.CtxMenu.
                    Add sev prefix to state constants.
2004-09-02 ROwen    Moved to opscore.RO.Constants to solve circular import problems.
2005-01-05 ROwen    Changed st_Normal, to sevNormal, etc.
2006-10-24 ROwen    Added sevDebug.
2009-09-02 ROwen    Added sevCritical.
2010-03-11 ROwen    Added SevNameDict and NameSevDict.
2014-09-17 ROwen    Modified to use OrderedDict from collections instead of opscore.RO.Alg.
"""
__all__ = ['sevDebug', 'sevNormal', 'sevWarning', 'sevError', 'sevCritical', 'SevNameDict', 'NameSevDict']

import six.moves.urllib.parse as parse
from collections import OrderedDict

# severity constants; numeric value increases with severity
sevDebug = -1
sevNormal = 0
sevWarning = 1
sevError = 2
sevCritical = 3

# ordered dictionary of severity: name (lowercase); order is least to most severe
SevNameDict = OrderedDict((
    (sevDebug, "debug"),
    (sevNormal, "normal"),
    (sevWarning, "warning"),
    (sevError, "error"),
    (sevCritical, "critical"),
))

# ordered dictionary of severity name (lowercase): severity; order is least to most severe
NameSevDict = OrderedDict(list(zip(list(SevNameDict.values()), list(SevNameDict.keys()))))

# Call setHelpURLBase if you want to specify URLs relative to a base
_HelpURLBase = ""
_gotHelpURLBase = False

def _joinHelpURL(urlSuffix=""):
    """Prepend the help url base and return the result.
    If urlSuffix is "" then return the help url base.
    """
#   print "_joinHelpURL(urlSuffix=%r)" % (urlSuffix,)
    global _HelpURLBase, _gotHelpURLBase
    _gotHelpURLBase = True
    return parse.urljoin(_HelpURLBase, urlSuffix)

def _setHelpURLBase(urlBase):
    """Set the base url for help urls.
    May only be called before getHelpURLBase is called
    (i.e. before any widgets are created that use url help).
    """
#   print "_setHelpURLBase(urlBase=%r)" % (urlBase,)
    global _HelpURLBase, _gotHelpURLBase
    if _gotHelpURLBase:
        raise RuntimeError("helpURL already requested; cannot change it now.")

    if urlBase.endswith("/"):
        _HelpURLBase = urlBase
    else:
        _HelpURLBase = urlBase + "/"
