#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys, indexmail, os

def print_merge_candidates(mboxfile):
    index_dir = indexmail.index_dir_for(mboxfile)
    files = [(os.stat(os.path.join(index_dir, fname)).st_size, fname)
              for fname in os.listdir(index_dir) if not fname.startswith('.')]
    files.sort()
    total = 0
    by_total = []
    ii = 0
    for size, name in files:
        total += size
        ratio = float(total) / size
        print '%13s %23.23s %14s %.2f×' % (size, name, total, ratio)
        by_total.append((ratio, name, ii))
        ii += 1
    by_total.sort(reverse=True)
    ratio, name, ii = by_total[0]
    print "Best would be merging files up to %s (%.3f×)" % (name, ratio)
    print "This would reduce the number of index files by %.1f%%" % (
        100.0*(ii+1)/len(files))
    print "That is: LANG=C sort -m %s -o .new.merged-segment" % (
        ' '.join(name for size, name in files[:ii+1]))
    print "followed by renaming, deleting the old files, and building the skip file"
    print "(actually doing it isn't implemented yet)"

if __name__ == '__main__':
    print_merge_candidates(sys.argv[1])
