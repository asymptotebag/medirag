#!/bin/bash
export AUTHLIB_INSECURE_TRANSPORT=1

for n in 20 15 10 5 1; 
do
    echo "Running Experiment (n=$n, d=1)"
    python3 scalability.py -n $n -d 1
    pkill -f 'python3'
done

# for d in 0 1 2 3 4;
for d in 1 2 3 4;
do
    echo "Running Experiment (n=1, d=$d)"
    python3 scalability.py -n 1 -d $d
    pkill -f 'python3'
done