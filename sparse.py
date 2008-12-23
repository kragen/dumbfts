#!/usr/bin/python
import sys

def output_line(line, offset):
    if line.endswith('\n'): line = line[:-1]
    print line, offset

chunksize = int(sys.argv[1])
infile = file(sys.argv[2])
offset = 0

output_line(infile.readline(), offset)
while True:
    offset += chunksize
    infile.seek(offset)
    junk = infile.readline()
    if junk == '': break
    offset += len(junk)
    output_line(infile.readline(), offset)
