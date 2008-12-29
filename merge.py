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
    for size, name in files:
        total += size
        ratio = float(total) / size
        print '%13s %23.23s %14s %.2f×' % (size, name, total, ratio)
        by_total.append((ratio, name))
    by_total.sort(reverse=True)
    ratio, name = by_total[0]
    print "Best would be merging files up to %s (%.3f×)" % (name, ratio)
    print "(actually doing it isn't implemented yet)"

if __name__ == '__main__':
    print_merge_candidates(sys.argv[1])
