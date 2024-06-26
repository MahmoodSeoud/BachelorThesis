# Bachelor thesis 2024 - DIKU
This repo is for my BachelorThesis on DIKU 2024

## Bachelor Thesis Learning Notes

### Week 1: Introduction and Problem Solving
- Introduction to the goal of creating a Bluetooth mesh grid network with an emphasis on designing an adaptive network protocol.
- The objective is to facilitate the coordination of states across the network, accommodating dynamic node joinings and leavings.
- Learned about concepts such as CSP (Communicating Sequential Processes) and multiprocess and multithreading libraries in Python.
- Focused on solving a smaller problem, the Santa Claus Problem, to lay the groundwork for the main project.
- Chose Python for its familiarity and to concentrate on problem-solving rather than language intricacies.
- Utilized the multiprocessing library in Python, including classes such as Queues, Conditions, Lock, and Pipe.
- Program executed locally on a single terminal for initial development and testing.

### Week 2: Implementation and Multi-terminal Setup
- Transitioning from local execution to distributed setup across different terminals. (No more Pipes, Quees)
- Utilizing the Thread library in Python to handle concurrent execution.
- Learning about threads with sub-threads, such as listening and writing threads.
- Communication protocols involving AF_INET format.
- Assigning unique ports to each thread while residing within the same IP address space.
- Experimenting with network configurations to ensure seamless communication between terminals.
- Reading up on deadlock/race conditions

### Week 3: Fixing the implementation from week2
- Reading up on deadlocks (sharing variables between threads)
- Livelock vs deadlock
- Made a "protocol" to differentiate between reindeer communication and Santa communication because the handle action should be different in each case
- Experiencing some deadlocks with the elves
- Reading articles about some potential algorithms to use for the elves

### Week 4: Redoing the implementation
- I did draw the network diagram so that i could redo the entire problem.

![Initial Communication between the elves](./images/Elves_networking.png)

- I have gone over to JSON dumps instead of sending bytes individually since it
    scales better and I am more used to working with JSON
![Extended Communication](./images/Elves network extended.png)
- Right now I am sending signals to other elves and separating the login in the
    request handler. This may change in the future.
- I have tried to do without state machines, does not work
- Discovered the idea of using a state machine to denote the current state of these processes. For instance, they could include more info in that feeler acknowledgment, such as what state they are currently in. They could consider themselves a chain root whenever they have enough potential other elves to start forming a chain with. This could be some flag saying what they're trying to do atm. (e.g. are they waiting for more elves, trying to form a chain, building toys, etc).

![Elves state diagram](./images/Elves_state_diagram.png)

### Week 5: Paxos vs VR vs Raft 
- I am gonna rework large parts of the logic, and here I discovered two algorithms that could help me. Both of these algorithms are for getting processes over a distributed system to have consensus. Paxos is an older one which is harder to implement and also is Viewstamped Replication [(VR)](https://raft.github.io/raft.pdf), thus I am going for [Raft!](https://raft.github.io) 
- Paxos is harder to understand "The experiment favored Paxos in
two ways: 15 of the 43 participants reported having some
prior experience with Paxos, and the Paxos video is 14%"
- I found a git [repo](https://github.com/bakwc/PySyncObj) that implements Raft! I am now reading up on this and how to call it. This lib gives you the possibility of sharing classes on different servers.
- Useful enums to remember for this lib:
    ```py
    class _RAFT_STATE:
        FOLLOWER = 0
        CANDIDATE = 1
        LEADER = 2
    ```

    ```py
    class CONNECTION_STATE:
        DISCONNECTED = 0
        CONNECTING = 1
        CONNECTED = 2
    ```

    ```py
    class FAIL_REASON:
        SUCCESS = 0             #: Command successfully applied.
        QUEUE_FULL = 1          #: Commands queue full
        MISSING_LEADER = 2      #: Leader is currently missing (leader election in progress, or no connection)
        DISCARDED = 3           #: Command discarded (cause of new leader elected and another command was applied instead)
        NOT_LEADER = 4          #: Leader has changed, old leader did not have time to commit command.
        LEADER_CHANGED = 5      #: Simmilar to NOT_LEADER - leader has changed without command commit.
        REQUEST_DENIED = 6      #: Command denied
    ```

- Here is an example of what we get when calling `SyncObj.getStatus()`:
    ```json
  {
   "version":"0.3.12",
   "revision":"deprecated",
   "self":"TCPNode(""localhost:3000"")",
   "state":0,
   "leader":"TCPNode(""localhost:3001"")",
   "has_quorum":true,
   "partner_nodes_count":1,
   "partner_node_status_server_localhost:3001":2,
   "readonly_nodes_count":0,
   "log_len":2,
   "last_applied":1,
   "commit_idx":1,
   "raft_term":1,
   "next_node_idx_count":0,
   "match_idx_count":0,
   "leader_commit_idx":1,
   "uptime":0,
   "self_code_version":1,
   "enabled_code_version":0
   }
    ```
- Now I am investing in some dynamic membership changes. The possibility of adding members so that the network can grow. Again this is for working towards making it Bluetooth at some point. This was done by setting the `dynamicMembershipChange` so

```py
cfg = SyncObjConf(dynamicMembershipChange=True)
cfg = SyncObjConf(dynamicMembershipChange=True)
syncObj = SyncObj(selfAddr, partners, cfg)
```
- Some drawback i found: "Raft requires (n/2) + 1 nodes to be alive to do anything (you would need a different protocol to survive up to n-1 failures)." [ref](https://app.gitter.im/#/room/#bakwc_PySyncObj:gitter.im)
- Raft servers communicate using remote procedure calls
(RPCs)

- Note to selv `removeNodeFromCluster` and `addNodeToCluster` does not work nodes that are themselves
### Week 6: TCP nodes added and removed from cluster 
I've successfully obtained the first chain of 3 TCP nodes (elfs ready to visit Santa). Now, I'm at a juncture where we need to decide on our next course of action:

a. Remove and Create Separate Cluster: One option is to remove these TCP nodes and create individual clusters for them.

b. Keep and Wait: Alternatively, we could choose to retain these nodes and have them wait for a designated period and make them return back to the others.

However, it's worth noting that if I opt for the first option, there's a potential caveat. Removing TCP nodes might lead to complications, particularly if they happen to be the leaders of the current cluster (removing leader is not possible with this library). 
However regarding a, do the even need their own communication channel? Could we not just let them wait it out and then clear our the chain? That way we would be certain that only one chain is out visiting Santa and once they return they others can then start their own chain. Keep in mind that every TCP node is aware of this chain,  so there is no chance of them thinking they belong in two chains at the same time

```py
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
                #leader = o._getLeader()
                print('List:', list.rawData())
                if status not in list.rawData() and len(list.rawData()) < 3:
                    list.append(status, callback=partial(onAppend, sts=status))
        except SyncObjException as e:
            print(f"Failed to acquire lock: {e}")
```

- The [documentation](https://github.com/bakwc/PySyncObj/wiki/syncobj_admin#add-new-node) states that you should "turn off" or "turn on" the node you are removing or adding. I however may not do that since these nodes have other tasks todo when not a member of these clusters.  
- Remember that this potential [issue](https://github.com/bakwc/PySyncObj/issues/112) is still not resolved. Thus meaning that once a chain of elves have been formed and contacted santa, they could experience issues connecting back to their original cluster due to them only knowing part of the chain.
- Right now I am experiencing issues with either the distributed lock provided by the library (ReplLockManager) or something else. I am going to test this further
- What seems to have fixed the lockManager for now is removing the `selfID` option from the lock initialations so that looks like this `lockManager = ReplLockManager(autoUnlockTime=75)`
- I have experiemented with changing the strategy a bit. Instead of taking out the leader in the elvesWithProblems array, I take everyone else out to not disturb the election, since this has caused some problems.
- The reason that the election had problems was due to the amount of the nodes in the cluster being under (n/2) + 1, meaning that they would struggle to elect a new leader. I have since then changed the stragety to only take the leaders into chain and delete them as they get into it, also removing them from the cluster. That means that I'm first using `self.destroy()` and then  `self.removeNodeFromCluster()`

### Week 7: Getting the contact from elves to Santa right
- I will have todo:
- [x] See if every elf thread that is kicked can contact each other and create a cluster
- [x] Then the leader of that cluster contacts Santa 
- [ ] Then I will have these kick each other again, and connect to the other cluster. (Keep in mind the other cluster also properly are deleting some more elves from their cluster. You maybve need to make a queue, in which they wait)
- I am using `server.handle_request()` because it will handle the request from Santa and then close instead of serving forever.
- How can I implement communication between two separate clusters in a distributed system?
- I am still buggleing with removing leaders. One thing I may try is to make a manager class that is supposed to be the leader.
    This could be helpful:
    ```python
  for node in self.__otherNodes:
                    self.__transport.send(node, {
                        'type': 'request_vote',
                        'term': self.__raftCurrentTerm,
                        'last_log_index': self.__getCurrentLogIndex(),
                        'last_log_term': self.__getCurrentLogTerm(),
                    })
    ```


### Week 8: Writing and notesa
- pycsp exists, worth mentioning the report. Also menation that JCSP is
    outedated and we wanted to use python3 instead of python2
    - We are working towards having it on different machines
- Experiment with removing elves. Might be easy or really hard or time consuming!
- Remember to to try and make a red thread in your thesis i.e. first sentence
    and last sentence should match in each paragraph.
- Also remember that David Marchant has inspired my work, since I am using some
    elements of his design (The chain). 
- Write some test.
- Also maybe it would be good that each elf would log into their own file some
    info like: state, chain, and such

### Week 9: Testing
I Changes the code structure a bit to avoid an issue with Raft not being able to compact the log, due to it trying to compact a socket.poll, which is not possible.
So far the testing of ![this](/images/elfLosingConnection.jpg) particular case works very good!

- Resaearch about time out thinks python socketserver librayr.
- What happens if an elf dies before reaching out to Santa?
- How can we handle this? because would hgave not solved problem if less than 3
    appears at Santa.
- There will be a gap between reaching out to santa and santa reaching back to
    the elf chain, but we have minimuzed the issue as much as possible.
- I am using logging to track the time and info of each thread.
- Rememeber to include the python socker and socketserver with requestHandler for the setup.
-
###  Wekk 10: writing
-  The purpsose of this is to make a dynamic system that could be in context related to text communication on phones. Make sure to time some of the instances and compare the distributred and the non distributed one to explain why it does not matter since phone communication for humans does not need to be instant.  

## Week idk: Writing
- I am trying to implementhte the feature that handles this issue "the gap
    between reaching out to santa and santa reaching back to the elf chain, but
    we have minimuzed the issue as much as possible." but i dicovered that I
    need a list of which chain members are in. I do hvae this, but I have a list
    of their extraPorts, so i need their real selfPorts. I may have to change
    this part 
    ```python
    chain.add(
        elf_worker._extra_port,
        callback=partial(
            onNodeAdded, node=elf_worker.selfNode, cluster="chain"
        ),
    )
    ```
- One thing to note is that the system is very large and complex. I NEED to make a bigger diagram with everything working together and then highlight some critical points. and explain them in detail but not necessarily everything for every point in the system. (acquiring the locks, Santa communication, waiting). Also, consider when we have done enough to ensure the system is right. For instance, do we absolutely need those three elves to arrive at Santa (Yes) how can we ensure that?

- You do need to implement everything right now. You can wait until the defense. Do make it future work tho.  

- For the testing of the performance of the system, I can keep track of a count for respectively the reindeer and the elves and how long does it takes for them to reach a certain count that Santa keeps. Maybe compare the elves and the reindeer and also compare the distributed and the non-distributed with each other. Maybe experiment with making the reindeer and elves count very large?

- Talk in The discussion of how the network in Bluetooth functions- leaving and joining at will. But also introduce your limitations for the system including Raft but more importantly the implementation of it. 

- Also discuss your hardware and CPU cores and their limitations., TALK about threshing and track the time of the elves and the reindeer separately and together.

- I maybe need to drop the introduction of new nodes part. We'll see
- i need to put a timeout on each listener just incase.


#### Week 11: Polishing the project
- Lookking at the comments to create this red thread
- Create the rest of the tests
- devlop new feature: introduce new nodes (TCP handshake)
