#!/bin/sh
# batch.sh N — contact sheet of the Nth batch of 20 undated records
N=$1
IDS=$(sed -n "$(( (N-1)*20 + 1 )),$(( N*20 ))p" /tmp/undated.txt | tr '\n' ' ')
[ -z "$IDS" ] && { echo "batch $N empty"; exit 0; }
python3 _detect/sheet.py $IDS /tmp/batch$N.jpg
