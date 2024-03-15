import threading
import time
import sys
sys.path.append("../")
from pysyncobj import SyncObj
from pysyncobj.batteries import ReplList
from pysyncobj import SyncObj, SyncObjConf

NUM_ELVES = 9

class Elf(SyncObj):
    def __init__(self, selfAddr, partners):
        super().__init__(selfAddr, partners, SyncObjConf(dynamicMembershipChange=True))

    def run(self):
        n = 0
        while True:
            time.sleep(1)

            if self._getLeader() is None: # Check if the raft nodes have elected a leader
                continue

            status = self.getStatus()


            print(f'ELF - {status['self']} has {status['partner_nodes_count']}')
            n += 1

if __name__ == '__main__':
    ports = [3000, 3001, 3002]
    peer_addresses = ['localhost:%d' % p for p in ports]

    elfs = [Elf('localhost:%d' % ports[i], [peer_addresses[j] for j in range(len(ports)) if j != i]) for i in range(len(ports))]
    threads = [threading.Thread(target=elf.run) for elf in elfs]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join() 