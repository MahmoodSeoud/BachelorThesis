#!/bin/bash
clear
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../../elves_threads.py ../../../log/unix/elves/$filename.txt 24001 21000 22000 23000 20000 25000 26000 27000 28000 29000
