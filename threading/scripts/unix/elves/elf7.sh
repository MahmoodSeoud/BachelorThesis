#!/bin/bash
clear
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../../elves_threads.py ./../../../log/unix/elves/$filename.txt 8012 8014 8016 8018 8000 8002 8004 8006 8008 8010
