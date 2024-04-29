#!/bin/bash
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../elves_threads.py ../../log/unix/$filename.txt  16000 11000 12000 13000 14000 15000 10000 17000 18000 19000
