#!/usr/bin/python
"Return the message-IDs in the last columns of all inputs."
import sys
last, rest = sys.argv[1], sys.argv[2:]
filterer = lambda id: True
for intersector in rest:
    newhash = {}
    for line in file(intersector):
        msg_id = line.split()[-1]
        if filterer(msg_id): newhash[msg_id] = True
    filterer = newhash.get
seen = {}
for line in file(last):
    msg_id = line.split()[-1]
    if filterer(msg_id) and msg_id not in seen:
        print msg_id
        seen[msg_id] = True
