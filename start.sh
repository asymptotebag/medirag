#!/bin/bash
pkill -f 'flask'
cd orgs/hospitalA
export AUTHLIB_INSECURE_TRANSPORT=1
flask run --port=5001 &
echo "hospital A started!"
cd ../hospitalB
export AUTHLIB_INSECURE_TRANSPORT=1
flask run --port=5002 &
echo "hospital B started!"
cd ../hospitalC
export AUTHLIB_INSECURE_TRANSPORT=1
flask run --port=5003 &
echo "hospital C started!"