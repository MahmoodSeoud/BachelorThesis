#!/bin/bash
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../elves_threads.py ../../log/unix/$filename.txt  15000 11000 12000 13000 14000 10000 16000 17000 18000 19000
