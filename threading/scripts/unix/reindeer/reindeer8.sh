#!/bin/bash
clear
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../../reindeer_threads.py ./../../../log/unix/reindeer/$filename.txt  17000 11000 12000 13000 14000 15000 16000 10000 18000 
