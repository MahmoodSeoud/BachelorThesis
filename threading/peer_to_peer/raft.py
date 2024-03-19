import threading
import sys
import time
from pysyncobj import SyncObj, SyncObjConf, replicated
from pysyncobj.batteries import ReplList, ReplLockManager
from functools import partial

NUM_ELVES = 3


class o(SyncObj):

    def __init__(self, my_addr, other_addrs, elve_list):
        cfg = SyncObjConf(dynamicMembershipChange=True,
                          onStateChanged=handleOnStateChanged()
                          )
        super().__init__(my_addr, other_addrs, consumers=[elve_list], conf=cfg)
        self._list = elve_list  # Queue of waiting elves

 


def handleOnStateChanged():
    print('State changed')


def onRemove(res, err, node):
    print('Removed %s' % node, res, err)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: %s self_port partner1_port partner2_port ...' % sys.argv[0])
        sys.exit(-1)

    
        
    port = int(sys.argv[1])
    partners = ['localhost:%d' % int(p) for p in sys.argv[2:]]
    elve_list = ReplList()

    # Initialize the coordinator
    o = SyncObj('localhost:%d' % port, partners, consumers=[elve_list])
    while True:
        time.sleep(0.5)

        if o._getLeader() is None:
            continue

        print(elve_list.rawData())
        if o._isLeader():
            print('I am the leader')
            elve_list.append('Elve')



    