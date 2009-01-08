#!/usr/bin/python
"""Mail posting extractor.

The idea is that you use Unix utilities like `sort` and `look` to
handle the postings once they've been extracted.

It handles about 250-300 kB per second on my 550MHz PIII: 5 236 465
bytes in 17.857 seconds.  It takes another 10-15% to sort the output
with sort(1) with LANG=C; if it takes you longer, see if you're using
some other silly locale.

The output is about as big as the input in my tests.  bzip2 can
compress it by about 6:1, in another 30% or so of the time to build
it.

TO DO:
- rename functions to something sensible
- write a script to intelligently merge index chunks with `sort -m`
- write something that ingests MIME messages, decoded, instead of
  plain text
- make it store the un-tokenized values of header fields as well, in
  separate files, more or less as follows:
    subject 38052032 Re: your mail
  (Maybe this should be a separate program?)

"""

import os, sys, re, errno
import util, buildskips

chunksize = 50000

class MissingFromLine(Exception): pass

class MessageReader:
    def __init__(self, mbox, offset):
        self.mbox = mbox
        self.next_message_offset = offset
        self.end_of_file = offset >= os.fstat(mbox.fileno()).st_size

    splitter = re.compile('[^a-zA-Z0-9\x80-\xff]+')
    words = splitter.split

    def message_terms(self):
        """Yield all the terms found in the next mail message.

        A term is either a word by itself (if it's in the body), or a word
        followed by a space and a header name.

        """
        in_headers = True
        current_offset = self.next_message_offset
        self.mbox.seek(current_offset)
        current_header = 'envelope-from'
        seen = {}
        first_line = True

        while True:
            line = self.mbox.readline()
            nbytes = len(line)

            if first_line and line.startswith('From '):
                first_line = False
            elif first_line:
                raise MissingFromLine(self.next_message_offset, line)
            elif not line:
                self.next_message_offset = current_offset
                self.end_of_file = True
                return
            elif line.startswith('From '): # found next message
                self.next_message_offset = current_offset
                return
            elif line == '\n':
                in_headers = False
                current_header = None
            elif in_headers and line[0] not in ' \t':
                current_header, line = line.split(':', 1)
                current_header = current_header.lower()

            for word in self.words(line):
                if word == '' or len(word) > 20: continue

                if in_headers:
                    term = word.lower() + ' ' + current_header
                else:
                    term = word.lower()

                if term not in seen:
                    yield term
                    seen[term] = True

            current_offset += nbytes

def index_until(messages, cb, end_bytes):
    while messages.next_message_offset < end_bytes and not messages.end_of_file:
        offset = messages.next_message_offset
        for term in messages.message_terms():
            cb(term, offset)

class SortFailed(Exception): pass

def sort_file(infile, outfile):
    env = os.environ.copy()
    for var in ('LANG LC_ALL LC_COLLATE LC_CTYPE LC_MESSAGES '
                'LC_MONETARY LC_NUMERIC LC_TIME').split():
        env[var] = 'C'
    status = os.spawnlpe(os.P_WAIT, 'sort', 'sort', infile, '-o', outfile, env)
    if status != 0:
        # XXX os.spawn*'s error handling is suboptimal; you don't get
        # the error code from exec*, nor any error message
        raise SortFailed(status, infile, outfile)
    insize = os.stat(infile).st_size
    outsize = os.stat(outfile).st_size
    assert insize == outsize, (insize, outsize)

name_index = 0
def fresh_name(base):
    global name_index
    while True:
        name_index += 1
        name = '%s.%s' % (base, name_index)
        if not os.path.exists(name): return name

def index_dir_for(filename):
    index_dir = '%s.idx' % filename
    if not os.path.isdir(index_dir):
        os.mkdir(index_dir)
    return index_dir

def index_until_3(filename, reader, end_bytes, index_out, index_out_sorted):
    index_file = open(index_out, 'w')   # XXX no O_EXCL
    def add_term(term, offset):
        index_file.write('%s %s\n' % (term, offset))
    index_until(reader, add_term, end_bytes)
    util.commit(index_file)

    sort_file(index_out, index_out_sorted)
    util.commit(open(index_out_sorted, 'r+')) # sort(1) might not fsync(2)

    # XXX raceable, but that's okay
    seg = fresh_name(os.path.join(index_dir_for(filename),
                                  'index-segment.%s' % os.getpid()))
    os.rename(index_out_sorted, seg)
    buildskips.build_skipfiles(chunksize, seg)

def index_until_2(filename, reader, end_bytes):
    index_dir = index_dir_for(filename)

    index_out = os.path.join(index_dir, '.new-index-segment.%s' % os.getpid())
    index_out_sorted = index_out + '.sorted'
    try:
        index_until_3(filename, reader, end_bytes, index_out, index_out_sorted)
    finally:
        for index_file_name in [index_out, index_out_sorted]:
            if os.path.exists(index_file_name):
                os.unlink(index_file_name)

def get_indexed_up_to(index_dir):        # XXX terrible name
    try:
        indexed_up_to_file = open(os.path.join(index_dir, '.indexed-up-to'))
    except IOError, e:
        if e.errno == errno.ENOENT:
            return 0
        else:
            raise
    else:
        return int(indexed_up_to_file.read())

def index_some(filename):
    mbox = open(filename)
    index_dir = index_dir_for(filename)
    start_bytes = get_indexed_up_to(index_dir)
    reader = MessageReader(mbox, start_bytes)
    if reader.end_of_file:
        return False

    # 50 megs is chosen to be around a minute's worth of work, because
    # that's a reasonable amount of progress to lose if you hit ^C
    indexed_up_to = index_until_2(filename, reader, start_bytes + 50*1000*1000)
    
    # XXX no O_EXCL
    new_indexed_up_to = os.path.join(index_dir, '.new-indexed-up-to')
    new_indexed_up_to_file = open(new_indexed_up_to, 'w')
    new_indexed_up_to_file.write('%s\n' % reader.next_message_offset)
    util.commit(new_indexed_up_to_file)
    os.rename(new_indexed_up_to, os.path.join(index_dir, '.indexed-up-to'))

    return True

def index_all(filename):
    f = MessageReader(open(filename), 0)
    while not f.end_of_file:
        offset = f.next_message_offset
        for term in f.message_terms():
            print term, offset
    sys.stderr.write('got to %d bytes\n' % f.next_message_offset)

if __name__ == '__main__':
    while index_some(sys.argv[1]):
        pass
