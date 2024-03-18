from pysyncobj import SyncObj, replicated
import time
import threading

class MySyncObj(SyncObj):
    def __init__(self, selfNodeAddr, otherNodeAddrs):
        super(MySyncObj, self).__init__(selfNodeAddr, otherNodeAddrs)
        self.__connectionTimes = {}

    @replicated
    def nodeConnected(self, nodeAddr):
        self.__connectionTimes[nodeAddr] = time.time()

    def getConnectionTimes(self):
        return self.__connectionTimes


if __name__ == 'main':
    node1 = MySyncObj('localhost:4321', ['localhost:4322', 'localhost:4323'])
    node2 = MySyncObj('localhost:4322', ['localhost:4321', 'localhost:4323'])
    node3 = MySyncObj('localhost:4323', ['localhost:4321', 'localhost:4322'])


    node1.waitBinded()
    node1.nodeConnected('localhost:4321')

    node2.waitBinded()
    node2.nodeConnected('localhost:4322')

    node3.waitBinded()
    node3.nodeConnected('localhost:4323')


    print("node1",node1.getConnectionTimes())
    print("node2",node2.getConnectionTimes())
    print("node3",node3.getConnectionTimes())
