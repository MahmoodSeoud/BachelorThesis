#!/bin/bash

filename=$(basename -- "$0")
filename="${filename%.*}"

python3 ./../../elves_threads.py ../../log/unix/$filename.txt  12000 11000 10000 13000 14000 15000 16000 17000 18000 19000
