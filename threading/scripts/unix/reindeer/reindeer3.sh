#!/bin/bash
clear
filename=$(basename -- "$0")
filename="${filename%.*}"
python3 ./../../../reindeer_threads.py ./../../../log/unix/reindeer/$filename.txt 8024 8026 8028 8030 8032 8034 8036 8020 8022
