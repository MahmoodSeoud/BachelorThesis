#!/usr/bin/env python
from __future__ import print_function
from pysyncobj.batteries import ReplList, ReplLockManager, ReplCounter
from pysyncobj import SyncObj, SyncObjException, SyncObjConf

import sys
import struct
import socket
import pickle
import time
from functools import partial
sys.path.append("../")
SANTA_PORT = 29800
LOCAL_HOST = "127.0.0.1"

def onAppend(res, err, sts):
    print('Appended:', "\n list:", sts, "\n result", res, "\n error:", err)
    print('list value:', list.rawData())
    lockManager.release('testLockName')  
    o.removeNodeFromCluster(sts, callback=partial(onRemove, node=sts))
    #time.sleep(0.5)

def onRemove(res, err, node):
    print('Removed %s' % node, res, err)
    my_addr = o.getStatus()['self']
    contact_santa(my_addr)

def contact_santa(my_addr):
        # Sent msg to Santa whom then msg's back here so that we can notify_all()
        try:
            print(f"ELF: {my_addr} -  Connecting to Santa at: " f"{LOCAL_HOST}:{SANTA_PORT}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn_socket:

                conn_socket.connect((LOCAL_HOST, SANTA_PORT))
                
                identifier = 'E' # E for elves as identifier
                node = o.getStatus()['self']
                node_bytes = pickle.dumps(node)  # Serialize TCPNode to bytes

                buffer = bytearray()
                buffer.extend(identifier.encode())
                buffer.extend(node_bytes)
                
                conn_socket.sendall(buffer)

        except ConnectionRefusedError:
            print(f"ELF: {my_addr} -  Couldn't conncect at: " f"{LOCAL_HOST}:{SANTA_PORT}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: %s self_port partner1_port partner2_port ...' %
              sys.argv[0])
        sys.exit(-1)

    port = 'localhost:%d' % int(sys.argv[1])
    partners = ['localhost:%d' % int(p) for p in sys.argv[2:]]

    counter = ReplCounter()
    list = ReplList()
    lockManager = ReplLockManager(autoUnlockTime=10, selfID='testLockName')

    o = SyncObj(port, partners, consumers=[
                list, lockManager, counter], conf=SyncObjConf(dynamicMembershipChange=True))
    while True:
        time.sleep(0.5)

        if o._getLeader() is None:
            continue

        print(counter.get())

        try:
            if lockManager.tryAcquire('testLockName', sync=True):
                status = o.getStatus()['self']
                if status not in list.rawData() and not o._isLeader() and len(list.rawData()) < 3:
                    list.append(status, callback=partial(onAppend, sts=status))
        except SyncObjException as e:
            print(f"Failed to acquire lock: {e}")

        counter.inc()
