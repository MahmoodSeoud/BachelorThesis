#!/usr/bin/env python
from __future__ import print_function

import sys
import time
from functools import partial
sys.path.append("../")
from pysyncobj import SyncObj, SyncObjException, SyncObjConf
from pysyncobj.batteries import ReplList, ReplLockManager, ReplCounter

def onAppend(res, err, sts):
    print('onAppend:',"\n list:" , sts, "\n result", res, "\n error:",err)
    print('list value:', list.rawData())
    lockManager.release('testLockName')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: %s self_port partner1_port partner2_port ...' % sys.argv[0])
        sys.exit(-1)

    port = 'localhost:%d' % int(sys.argv[1])
    partners = ['localhost:%d' % int(p) for p in sys.argv[2:]]
    
    counter = ReplCounter()
    list = ReplList()
    lockManager = ReplLockManager(autoUnlockTime=10, selfID='testLockName')

    o = SyncObj(port, partners, consumers=[list, lockManager, counter], conf=SyncObjConf(dynamicMembershipChange=True))
    while True:
        time.sleep(0.5)

        if o._getLeader() is None:
            continue

        print(counter.get())

        try:
            if lockManager.tryAcquire('testLockName', sync=True):
                status = o.getStatus()['self']
                if status not in list.rawData() and len(list.rawData()) < 3:
                    list.append(status, callback=partial(onAppend, sts=status))
        except SyncObjException as e:
            print(f"Failed to acquire lock: {e}")
        
        counter.increment()
