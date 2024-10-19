# Bachelor Thesis 2024 - DIKU

Welcome to the repository for my Bachelor Thesis conducted at DIKU in 2024. The paper is published [here](https://easychair.org/publications/paper/Gv4N)). 

## Overview

This repository contains the code and documentation for my Bachelor Thesis project. You can find detailed notes and insights in the [documentation](/notes.md) file.

## Quick Start

To get started, follow these steps:

1. Install the necessary dependencies by running:

```bash
$ pip install -r requirements.txt
```

2. Choose the appropriate section based on your setup:

### Non-Distributed, Non-Dynamic

To run the program, execute the following command:

```bash
$ python3 ./multiprocess/santa_reindeer_elves.py
```

Santa has his own log file located [here](/threading/log/)

### Distributed, Non-Dynamic

#### Santa

Start a Santa thread by running:

```bash
$ python3 ./threading/santa_thread.py
```

#### Reindeer

For each server, open a separate shell. Then, run the corresponding script from the [scripts](/threading/scripts) directory. Alternatively, you can manually specify ports. 
```bash
$ python3 logFilePath self_port partner1_port partner2_port ...
```
**NOTICE**: Each process utilizses the port provided and also the just after. Therefore it is important to make sure that both of these ports are not in use before providing them. For example if you want to have a cluster starting from `8000`, then you need to also make sure that port `8001` also is free.

```bash
$ python3 logFilePath self_port partner1_port partner2_port ...
```

#### Elves

Similar to Reindeer, open a separate shell for each server. Run the appropriate script from the [scripts](/threading/scripts) directory. You can also manually specify ports:

```bash
$ python3 logFilePath self_port partner1_port partner2_port ...
```

Feel free to explore the codebase and documentation to gain a deeper understanding of the thesis project. If you have any questions or feedback, please don't hesitate to reach out.
