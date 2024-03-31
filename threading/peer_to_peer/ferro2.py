from __future__ import print_function
from pysyncobj.batteries import ReplList, ReplLockManager, ReplCounter, ReplQueue, ReplDict
from pysyncobj import SyncObj, SyncObjException, SyncObjConf, FAIL_REASON, replicated, replicated_sync


import sys
import threading
import struct
import socketserver
import socket
import pickle
import time
import random
from functools import partial

sys.path.append("../")
SANTA_PORT = 29800
LOCAL_HOST = "127.0.0.1"
NUM_ELVES = 7


class TEST_TYPE:
    DEFAULT = 0
    COMPACTION_1 = 1
    COMPACTION_2 = 2
    RAND_1 = 3
    JOURNAL_1 = 4
    AUTO_TICK_1 = 5
    WAIT_BIND = 6
    LARGE_COMMAND = 7


class TestObj(SyncObj):

    def __init__(self, selfNodeAddr, otherNodeAddrs,
                 testType=TEST_TYPE.DEFAULT,
                 compactionMinEntries=0,
                 dumpFile=None,
                 journalFile=None,
                 password=None,
                 dynamicMembershipChange=False,
                 useFork=True,
                 testBindAddr=False,
                 consumers=None,
                 onStateChanged=None,
                 leaderFallbackTimeout=None):

        cfg = SyncObjConf(autoTick=False, appendEntriesUseBatch=False)
        cfg.appendEntriesPeriod = 0.1
        cfg.raftMinTimeout = 0.5
        cfg.raftMaxTimeout = 1.0
        cfg.dynamicMembershipChange = dynamicMembershipChange
        cfg.onStateChanged = onStateChanged
        if leaderFallbackTimeout is not None:
            cfg.leaderFallbackTimeout = leaderFallbackTimeout

        if testBindAddr:
            cfg.bindAddress = selfNodeAddr

        if dumpFile is not None:
            cfg.fullDumpFile = dumpFile

        if password is not None:
            cfg.password = password

        cfg.useFork = useFork

        if testType == TEST_TYPE.COMPACTION_1:
            cfg.logCompactionMinEntries = compactionMinEntries
            cfg.logCompactionMinTime = 0.1
            cfg.appendEntriesUseBatch = True

        if testType == TEST_TYPE.COMPACTION_2:
            cfg.logCompactionMinEntries = 99999
            cfg.logCompactionMinTime = 99999
            cfg.fullDumpFile = dumpFile

        if testType == TEST_TYPE.LARGE_COMMAND:
            cfg.connectionTimeout = 15.0
            cfg.logCompactionMinEntries = 99999
            cfg.logCompactionMinTime = 99999
            cfg.fullDumpFile = dumpFile
            cfg.raftMinTimeout = 1.5
            cfg.raftMaxTimeout = 2.5
        # cfg.appendEntriesBatchSizeBytes = 2 ** 13

        if testType == TEST_TYPE.RAND_1:
            cfg.autoTickPeriod = 0.05
            cfg.appendEntriesPeriod = 0.02
            cfg.raftMinTimeout = 0.1
            cfg.raftMaxTimeout = 0.2
            cfg.logCompactionMinTime = 9999999
            cfg.logCompactionMinEntries = 9999999
            cfg.journalFile = journalFile

        if testType == TEST_TYPE.JOURNAL_1:
            cfg.logCompactionMinTime = 999999
            cfg.logCompactionMinEntries = 999999
            cfg.fullDumpFile = dumpFile
            cfg.journalFile = journalFile

        if testType == TEST_TYPE.AUTO_TICK_1:
            cfg.autoTick = True
            cfg.pollerType = 'select'

        if testType == TEST_TYPE.WAIT_BIND:
            cfg.maxBindRetries = 1
            cfg.autoTick = True

        super(TestObj, self).__init__(
            selfNodeAddr, otherNodeAddrs, cfg, consumers)
        self.__counter = 0
        self.__data = {}

        if testType == TEST_TYPE.RAND_1:
            self._SyncObj__transport._send_random_sleep_duration = 0.03

    @replicated
    def addValue(self, value):
        self.__counter += value
        return self.__counter

    @replicated
    def addKeyValue(self, key, value):
        self.__data[key] = value

    @replicated_sync
    def addValueSync(self, value):
        self.__counter += value
        return self.__counter

    @replicated
    def testMethod(self):
        self.__data['testKey'] = 'valueVer1'

    @replicated(ver=1)
    def testMethod(self):
        self.__data['testKey'] = 'valueVer2'

    def getCounter(self):
        return self.__counter

    def getValue(self, key):
        return self.__data.get(key, None)

    def dumpKeys(self):
        print('keys:', sorted(self.__data.keys()))


def onAppend(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        print(f"Append - REQUEST [SUCCESS]: {node}")


def onNodeAdded(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        print(f"Added - REQUEST [SUCCESS]: {node}")


def onNodeRemoved(result, error, node):
    if error == FAIL_REASON.SUCCESS:
        print(f"Removal - REQUEST [SUCCESS]: {node}")

def singleTickFunc(o, timeToTick, interval, stopFunc):
    currTime = time.time()
    finishTime = currTime + timeToTick
    while time.time() < finishTime:
        o._onTick(interval)
        if stopFunc is not None:
            if stopFunc():
                break

def doTicks(objects, timeToTick, interval=0.05, stopFunc=None):
    threads = []
    for o in objects:
        t = threading.Thread(target=singleTickFunc, args=(
            o, timeToTick, interval, stopFunc))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

def doAutoTicks(interval=0.05, stopFunc=None):
    deadline = time.time() + interval
    while not stopFunc():
        time.sleep(0.02)
        t2 = time.time()
        if t2 >= deadline:
            break

_g_nextAddress = 6000 + 60 * (int(time.time()) % 600)


def getNextAddr(ipv6=False, isLocalhost=False):
    global _g_nextAddress
    _g_nextAddress += 1
    if ipv6:
        return '::1:%d' % _g_nextAddress
    if isLocalhost:
        return 'localhost:%d' % _g_nextAddress
    return '127.0.0.1:%d' % _g_nextAddress



if __name__ == "__main__":
    q1 = ReplQueue()
    q2 = ReplQueue()

    a = [getNextAddr(), getNextAddr()]

    o1 = TestObj(a[0], [a[1]], TEST_TYPE.AUTO_TICK_1, consumers=[q1])
    o2 = TestObj(a[1], [a[0]], TEST_TYPE.AUTO_TICK_1, consumers=[q2])

    doAutoTicks(10.0, stopFunc=lambda: o1.isReady() and o2.isReady())

    assert o1.isReady() and o2.isReady()

    q1.put(42, sync=True)
    doAutoTicks(3.0, stopFunc=lambda: q2.get(sync=True) == 42)

    assert q2.get(sync=True) == 42

  
