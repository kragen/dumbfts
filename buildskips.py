#!/usr/bin/python
#  -*- coding: utf-8 -*-
"""Build N-level skip files for index segments.

Doesn’t bother rebuilding skip files that already exist; it assumes
they’re correct.

"""
import sys, sparse, os, skiplook, cgitb

def build_skipfiles(chunksize, infilename):
    outfilename = skiplook.skipfilename(infilename)
    if not os.path.exists(outfilename):
        print "building skipfile for `%s`  " % infilename
        outfile = file(outfilename + '.new', 'w')
        sparse.main(chunksize, infilename, outfile)
        os.fsync(outfile.fileno())
        outfile.close()
        os.rename(outfilename + '.new', outfilename)

    size = os.stat(outfilename).st_size
    if size > chunksize:
        build_skipfiles(chunksize, outfilename)
    else:
        print "don't need to build skip file for `%s`  " % outfilename
        #print "because %d <= %d" % (size, chunksize)

def main(chunksize, segments):
    for segment in segments:
        build_skipfiles(chunksize, segment)

if __name__ == '__main__':
    cgitb.enable(format='text')
    main(int(sys.argv[1]), sys.argv[2:])
