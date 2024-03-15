import time
import sys
sys.path.append("../")
from pysyncobj import SyncObj
from pysyncobj.batteries import ReplList
from pysyncobj import SyncObj, SyncObjConf

if __name__ == '__main__':

    selfAddr = 'localhost:%d' % int(sys.argv[1])
    partners = ['localhost:%d' % int(p) for p in sys.argv[2:]]
    cfg = SyncObjConf(dynamicMembershipChange=True)
    syncObj = SyncObj(selfAddr, partners, cfg)
    n = 0
    while True:
        time.sleep(1)

        if syncObj._getLeader() is None: # Check if the raft nodes have elected a leader
            continue

        print(syncObj.getStatus()['partner_nodes_count'])

        if n == 10:
            print('adding node')
            
            user_input = int(input('Enter port:'))
            peer = sys.argv[2]
            syncObj.addNodeToCluster('localhost:%d' % user_input)

        n += 1



