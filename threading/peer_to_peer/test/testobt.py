from __future__ import print_function
import random
import time
import random
import threading
import sys
import os
import pysyncobj.pickle as pickle
import pysyncobj.dns_resolver as dns_resolver

if sys.version_info >= (3, 0):
    xrange = range
import logging
from pysyncobj import SyncObj, SyncObjConf, replicated, replicated_sync
from pysyncobj.batteries import ReplQueue

logging.basicConfig(format=u'[%(asctime)s %(filename)s:%(lineno)d %(levelname)s]  %(message)s', level=logging.DEBUG)

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

_g_nextAddress = 6000 + 60 * (int(time.time()) % 600)


def getNextAddr(ipv6=False, isLocalhost=False):
    global _g_nextAddress
    _g_nextAddress += 1
    if ipv6:
        return '::1:%d' % _g_nextAddress
    if isLocalhost:
        return 'localhost:%d' % _g_nextAddress
    return '127.0.0.1:%d' % _g_nextAddress

def test_ReplQueue():
    q = ReplQueue()
    q.put(42, _doApply=True)
    q.put(33, _doApply=True)
    q.put(14, _doApply=True)

    assert q.get(_doApply=True) == 42

    assert q.qsize() == 2
    assert len(q) == 2

    assert q.empty() == False

    assert q.get(_doApply=True) == 33
    assert q.get(-1, _doApply=True) == 14
    assert q.get(_doApply=True) == None
    assert q.get(-1, _doApply=True) == -1
    assert q.empty()

    q = ReplQueue(3)
    q.put(42, _doApply=True)
    q.put(33, _doApply=True)
    assert q.full() == False
    assert q.put(14, _doApply=True) == True
    assert q.full() == True
    assert q.put(19, _doApply=True) == False
    assert q.get(_doApply=True) == 42

_g_nextDumpFile = 1


def getNextDumpFile():
    global _g_nextDumpFile
    fname = 'dump%d.bin' % _g_nextDumpFile
    _g_nextDumpFile += 1
    return fname

def removeFiles(files):
    for f in (files):
        if os.path.isfile(f):
            for i in xrange(0, 15):
                try:
                    if os.path.isfile(f):
                        os.remove(f)
                        break
                    else:
                        break
                except:
                    time.sleep(1.0)


def checkDumpToFile(useFork):
    dumpFiles = ['dump1.bin', 'dump2.bin']
    removeFiles(dumpFiles)

    random.seed(42)

    a = [getNextAddr(), getNextAddr()]

    o1 = TestObj(a[0], [a[1]], TEST_TYPE.COMPACTION_2, dumpFile=dumpFiles[0], useFork=useFork)
    o2 = TestObj(a[1], [a[0]], TEST_TYPE.COMPACTION_2, dumpFile=dumpFiles[1], useFork=useFork)
    objs = [o1, o2]
    doTicks(objs, 10, stopFunc=lambda: o1._isReady() and o2._isReady())

    assert o1._getLeader().address in a
    assert o1._getLeader() == o2._getLeader()

    o1.addValue(150)
    o2.addValue(200)

    doTicks(objs, 10, stopFunc=lambda: o1.getCounter() == 350 and o2.getCounter() == 350)

    assert o1.getCounter() == 350
    assert o2.getCounter() == 350

    o1._forceLogCompaction()
    o2._forceLogCompaction()

    doTicks(objs, 1.5)


    removeFiles(dumpFiles)


def test_checkDumpToFile():
    checkDumpToFile(False)

test_checkDumpToFile()
