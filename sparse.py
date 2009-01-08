#!/usr/bin/python
import sys

def output_line(line, offset, output):
    if line.endswith('\n'): line = line[:-1]
    output.write('%s %s\n' % (line, offset))

def main(chunksize_str, infilename, output):
    chunksize = int(chunksize_str)
    infile = file(infilename)
    offset = 0

    output_line(infile.readline(), offset, output)
    while True:
        offset += chunksize
        infile.seek(offset)
        junk = infile.readline()
        if junk == '': break
        offset += len(junk)
        output_line(infile.readline(), offset, output)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.stdout)
