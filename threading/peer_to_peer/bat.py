#!/usr/bin/env python
from __future__ import print_function

import sys
import time
from functools import partial
sys.path.append("../")
from pysyncobj import SyncObj, replicated
from pysyncobj.batteries import ReplLockManager
from pysyncobj import SyncObjException

class TestObj(SyncObj):

    def __init__(self, selfNodeAddr, otherNodeAddrs, lock):
        super(TestObj, self).__init__(selfNodeAddr, otherNodeAddrs, consumers=[lock])
        #self.__lock = lock
        self.__list = []

    @replicated
    def append(self, value):
        self.__list.append(value)
        return self.__list

    def getList(self):
        return self.__list



def onAppend(res, err, sts):
    print('onAppend:',"\n list:" , sts, "\n result", res, "\n error:",err)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: %s self_port partner1_port partner2_port ...' % sys.argv[0])
        sys.exit(-1)

    port = 'localhost:%d' % int(sys.argv[1])
    partners = ['localhost:%d' % int(p) for p in sys.argv[2:]]
    lockManager = ReplLockManager(autoUnlockTime=75, selfID='testLockName')
    o = TestObj(port, partners, lockManager)

    while True:
        time.sleep(0.5)

        if o._getLeader() is None:
            continue

        status = o.getStatus()['self']
        leader = o._getLeader()
        try:
            if lockManager.tryAcquire('testLockName', sync=True):
                if leader not in o.getList():
                    o.append(leader, callback=partial(onAppend, sts=leader))
                lockManager.release('testLockName')
        except SyncObjException as e:
            print(f"Failed to acquire lock: {e}")
    

        #print('list value:', o.getList(), o._getLeader())
