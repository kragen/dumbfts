#!/usr/bin/python
import sys, os

def skipfilename(filename):
    dirname, filename = os.path.split(filename)
    if filename.startswith('.'):
        filename = '.skip' + filename
    else:
        filename = '.skip.' + filename
    return os.path.join(dirname, filename)

def skiplook(prefix, filename):
    """Yields the last line that doesn't end in prefix from filename,
    then all the lines that do.

    Will fail on an empty file, or a file whose skipfile points into
    nothingness.

    XXX does the wrong thing when the first line should be included!

    """
    fo = open(filename)
    if os.path.exists(skipfilename(filename)):
        # XXX can crash here!
        skipline = skiplook(prefix, skipfilename(filename)).next()
        offset = int(skipline.split()[-1])
        #print "seeking to", offset, 'for', skipline.split()
        fo.seek(offset)
    lastline = fo.readline()
    for line in fo:
        if line.startswith(prefix):
            yield lastline
            yield line
            break
        elif line > prefix:
            yield lastline
            return
        lastline = line
    for line in fo:
        if line.startswith(prefix):
            yield line
        else:
            return

def main(prefix, files):
    for eachfile in files:
        lines = skiplook(prefix, eachfile)
        lines.next()                    # discard first line
        for line in lines:
            sys.stdout.write(line)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
