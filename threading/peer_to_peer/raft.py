import threading
import time
import sys
sys.path.append("../")
from pysyncobj import SyncObj
from pysyncobj.batteries import ReplList
from pysyncobj import SyncObj, SyncObjConf, replicated

NUM_ELVES = 9

class Elf(SyncObj):
    def __init__(self, selfAddr, partners):
        super().__init__(selfAddr, partners, SyncObjConf(dynamicMembershipChange=True))
        self.__elvesHavingIssues = []

    @replicated
    def handle_elf_having_problem(self):
        my_addr = self.getStatus()['self']
        if my_addr not in self.__elvesHavingIssues:  # Check if the current elf is already in the array
            if len(self.__elvesHavingIssues) < 3:
                self.__elvesHavingIssues.append(my_addr)
                if len(self.__elvesHavingIssues) == 3:
                    # If three elves are waiting, wake up Santa
                    self._wake_up_santa()   

    def _wake_up_santa(self):
        print("Three elves are waiting, waking up Santa!")
        # Perform actions to wake up Santa and handle elves' requests

    def run(self):
        while True:
            time.sleep(1)

            if self._getLeader() is None: # Check if the raft nodes have elected a leader
                continue

            self.handle_elf_having_problem()

            

if __name__ == '__main__':
    ports = [3000, 3001, 3002]
    peer_addresses = ['localhost:%d' % p for p in ports]

    elfs = [Elf('localhost:%d' % ports[i], [peer_addresses[j] for j in range(len(ports)) if j != i]) for i in range(len(ports))]
    threads = [threading.Thread(target=elf.run) for elf in elfs]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join() 