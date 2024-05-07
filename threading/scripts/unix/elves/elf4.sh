#!/bin/bash
clear
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../../elves_threads.py ../../../log/unix/elves/$filename.txt  13000 11000 12000 10000 14000 15000 16000 17000 18000 19000
