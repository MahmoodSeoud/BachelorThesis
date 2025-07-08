<div align="center">
  <h1>Bachelor Thesis 2024 - DIKU</h1>
  <br>

  [documentation](/notes.md) | [paper](https://easychair.org/publications/paper/Gv4N) | [scripts](/threading/scripts)

  <br>
</div>

# Santa Claus Problem - Distributed Systems Implementation

## Introduction

This repository contains the implementation for my Bachelor Thesis conducted at DIKU in 2024. The project explores distributed systems concepts through the classic Santa Claus Problem, implementing both non-distributed and distributed solutions.

## Features

### Core Capabilities
- **Non-Distributed Implementation**: Multiprocess solution with shared memory
- **Distributed Implementation**: Network-based solution with separate processes for Santa, Reindeer, and Elves

### Architecture
- **Multiprocess Design**: Efficient process management and synchronization
- **Network Communication**: Custom protocol for distributed coordination
- **Logging System**: Comprehensive logging for debugging and analysis

## Installation

Install the necessary dependencies:

```bash
pip install -r requirements.txt
```

## Example Usage

### Non-Distributed, Non-Dynamic

To run the multiprocess implementation:

```bash
python3 ./multiprocess/santa_reindeer_elves.py
```

Santa's log file is located in `/threading/log/`

### Distributed, Non-Dynamic

#### Santa

Start the Santa process:

```bash
python3 ./threading/santa_thread.py
```

#### Reindeer & Elves

For each Reindeer/Elf server, open a separate shell and run:

```bash
python3 script.py logFilePath self_port partner1_port partner2_port ...
```

> **Note**: Each process uses the provided port and the next one (e.g., if using port 8000, port 8001 must also be free).

## Documentation

Detailed notes and insights can be found in the [documentation](/notes.md) file.
