__all__ = ["tback"]

import inspect
import logging
import pprint
import sys
import traceback


def tback(system, e, info=None, logger=None):
    """Log a decently informative traceback."""

    if logger == None:
        logger = logging
    exc_type, exc_value, exc_traceback = sys.exc_info()

    try:
        frames = inspect.trace()
        toptrace = inspect.trace()[-1]
    except:
        one_liner = "%s: %s: %s" % (e, exc_type, exc_value)
        logger.critical("======== %s exception botch: %s" % (system, one_liner))
        return

    tr_list = []
    tr_list.append("\n\n====== trace:\n")
    tr_list.append(pprint.pformat(toptrace))

    i = 0
    frames.reverse()
    for f in frames:
        tr_list.append("\n\n====== frame %d locals:\n" % (i))
        tr_list.append(pprint.pformat(f[0].f_locals, depth=4))
        i += 1

    ex_list = traceback.format_exception(exc_type, exc_value, exc_traceback)
    logger.warn("\n======== %s exception: %s\n" % (system, "".join(ex_list)))
    logger.warn("".join(tr_list))
