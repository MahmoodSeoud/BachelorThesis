# Bachelor thesis 2024 - DIKU
This repo is for my BachelorThesis on DIKU 2024



## Quick start

Start by installing the dependencies:
```bash
$ pip install -r requirements.txt
```

### Non distributed non dynamic
Run the program:

```bash
python3 santa_reindeer_elves.py
```


### Distributed non dynamic

#### Santa
Create a santa thread:
```bash
python3 santa_thread.py
```

#### Reindeer
Create a reindeer thread:
```bash
python3 reindeer_threads.py
```


#### Elves
Open 10 shells to represent 10 different servers. Then on each of these shells, start on of the correpsonding [scripts](/threading/scripts) for your system: 
