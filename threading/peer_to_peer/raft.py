import threading
import time
from pysyncobj import SyncObj, SyncObjConf, replicated
from pysyncobj.batteries import ReplList
from functools import partial

NUM_ELVES = 5


class Elf(SyncObj):

    def __init__(self, id, my_addr, other_addrs, elve_list):
        cfg = SyncObjConf(dynamicMembershipChange=True, commandsWaitLeader=True)
        super().__init__(my_addr, other_addrs, consumers=[elve_list], conf=cfg)
        self._elve_list = elve_list  # Queue of waiting elves
        self._id = id

    def run(self):
        print('Running')
        while True:
            node = self.getStatus()['self']
            leader = self._getLeader()
            list = self._elve_list.rawData()

            self.waitReady()

            time.sleep(2)
            if self._isLeader():
                print("leader", leader, "self",  node)
                print('list:', list)
                #self._elve_list.append(node)
                #self.removeNodeFromCluster(node, callback=partial(self.onRemove, node=node))
                #self.removeNodeVdFromCluster()
               # self.addNodeToCluster('localhost:4000')
                print('Count-uno', self.getStatus()['partner_nodes_count'])

                #print('Count-secundoro', self.getStatus()['partner_nodes_count'])
                if self.getStatus()['partner_nodes_count'] < NUM_ELVES - 1:
                    print('ferro')



def onRemove(res, err, node):
    print('Removed %s' % node, res, err)


if __name__ == "__main__":
    start_port = 3000
    ports = [start_port + i for i in range(NUM_ELVES)]
    peer_addresses = ['localhost:%d' % p for p in ports]
    elve_list = ReplList()

    # Initialize the coordinator
    elves = []
    for i in range(len(ports)):
        elf = Elf(i, 'localhost:%d' % ports[i],
                  [peer_addresses[j] for j in range(len(ports)) if j != i],
                  elve_list)
        elves.append(elf)

    # Each elf process/thread:
    # 1. Requests to join the queue
    threads = [threading.Thread(target=elf.run) for elf in elves]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()
