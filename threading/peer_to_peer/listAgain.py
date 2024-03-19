#!/usr/bin/env python
from __future__ import print_function

import sys
import time
from functools import partial
sys.path.append("../")
from pysyncobj import SyncObj, SyncObjException, SyncObjConf
from pysyncobj.batteries import ReplList, ReplLockManager

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
    
    list = ReplList()
    lockManager = ReplLockManager(autoUnlockTime=10, selfID='testLockName')

    o = SyncObj(port, partners, consumers=[list, lockManager], conf=SyncObjConf(dynamicMembershipChange=True))

    while True:
        time.sleep(0.5)

        if o._getLeader() is None:
            continue
    
        try:
            if lockManager.tryAcquire('testLockName', sync=True):
                status = o.getStatus()['self']
                leader = o._getLeader()
                print('List:', list.rawData())
                if leader not in list.rawData() and len(list.rawData()) < 3:
                    list.append(leader, callback=partial(onAppend, sts=leader))
        except SyncObjException as e:
            print(f"Failed to acquire lock: {e}")
