#!/usr/bin/env python2

import time

from twisted.internet import reactor

from opscore.utility.timer import Timer
from opscore.actor import CmdKeyVarDispatcher, ScriptRunner

dispatcher = CmdKeyVarDispatcher()

scriptList = []

def initFunc(sr):
    global scriptList
    print("%s init function called" % (sr,))
    scriptList.append(sr)

def endFunc(sr):
    print("%s end function called" % (sr,))

def script(sr):
    def threadFunc(nSec):
        time.sleep(nSec)
    nSec = 1.0
    print("%s waiting in a thread for %s sec" % (sr, nSec))
    yield sr.waitThread(threadFunc, 1.0)

    for val in range(5):
        print("%s value = %s" % (sr, val))
        yield sr.waitMS(1000)

def stateFunc(sr):
    state, reason = sr.fullState
    if reason:
        msgStr = "%s state=%s: %s" % (sr, state, reason)
    else:
        msgStr = "%s state=%s" % (sr, state)
    print(msgStr)
    for sr in scriptList:
        if not sr.isDone:
            return
    reactor.stop()

sr1 = ScriptRunner(
    runFunc = script,
    name = "Script 1",
    dispatcher = dispatcher,
    initFunc = initFunc,
    endFunc = endFunc,
    stateFunc = stateFunc,
)

sr2 = ScriptRunner(
    runFunc = script,
    name = "Script 2",
    dispatcher = dispatcher,
    initFunc = initFunc,
    endFunc = endFunc,
    stateFunc = stateFunc,
)

# start the scripts in a staggared fashion
sr1.start()
Timer(1.5, sr1.pause)
Timer(3.0, sr1.resume)
Timer(2.5, sr2.start)

reactor.run()
