#!/usr/bin/python
"""Print out the messages from the specified mailbox
at the byte offsets specified on stdin."""
import sys
mbox = file(sys.argv[1])
for line in sys.stdin:
    offset = int(line)
    mbox.seek(offset)
    sys.stdout.write(mbox.readline())
    while True:
        line = mbox.readline()
        if not line: break
        if line.startswith('From '): break
        sys.stdout.write(line)
