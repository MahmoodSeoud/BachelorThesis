#!/bin/bash
clear
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../../elves_threads.py ../../../log/unix/elves/$filename.txt 4000 3000 8000 5000 8888 8443 9000 8080 12345 6000
