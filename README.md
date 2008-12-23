Dumb Full Text Search
=====================

This is a full-text indexing and search engine for my email, in about
250 lines of code.  It can produce results for many (most?) queries on
my 12-gigabyte mailbox in under two seconds on my 700MHz laptop.
(Which sometimes reduces its clock rate to 550MHz.)  I just updated
the index after not doing so for three months, and it took about three
hours to index the two new gigabytes of email.

Feature list
------------

- full-text email search
- incremental reindexing
- fielded search on arbitrary mail headers
- partial-word search
- multi-term search
- extreme internal simplicity
- all in Python except for a bash script

Applicability
-------------

Obviously such a simple system is somewhat limited in its
applicability.  Here are some things that must be true in order to use
it:

1.  The entire corpus to be searched is in a single big Berkeley mbox
    file.
2.  As with `grep` or `mboxgrep`, the objective is to get all of the
    results, without ranking them in terms of relevance.
3.  The corpus size is in the tens-of-megabytes to tens-of-gigabytes
    range.
4.  The mbox file is updated only by appending onto the end.  (This is
    a reasonable assumption given #1 and #3.)
5.  Given #3, incremental reindexing is desirable.  Given #4, it is
    feasible.
6.  You have enough disk space for an index that is the same size as
    the original mbox file.
7.  The mail and the index are stored on a spinning-rust
    electromechanical disk, on which non-sequential reads imply a
    delay of 5–20 milliseconds, not a solid-state Flash disk (“SSD”)
    where the corresponding delay is around 0.1 milliseconds.  (It
    should still work fine on a Flash disk but it could be a lot more
    efficient.)
8.  You don’t care about full-text search finding words in attachments
    or base64-encoded message bodies, or partially-encoded words in
    quoted-printable-encoded message bodies, or encoded message headers.
9.  You’re on a Unix system, such as Linux or Mac OS X.
10. You don’t mind manually administering the index.
11. The index is being used to answer interactive queries on a
    single-user machine with a single-user corpus, so the thing to
    optimize for is query latency when the index is on disk, not, say,
    query throughput or query latency with an in-RAM index.

Architecture
------------

It stores a bunch of index segments in an index directory; each one is
a sorted list of postings.  Off to the side of each index segment,
there is a “skip file” which is smaller, about 6000 times smaller in
my case, although that’s a tunable parameter; it contains about one
out of every 6000 or so postings from the index segment, along with
the position where it can be found in the index segment.  Index
segments are generated at some manageable size and then merged into
new, larger index segments later on.

If this design sounds familiar it’s probably because it’s exactly like
Lucene.

So, to find a term in a 2.0-gibibyte index segment, we start reading
through the skip file (346 kibibytes in my example case), and stop as
soon as we find something later than the term, on average a little
over halfway through.  At that point we open the index segment, seek
to the last posting mentioned in the skip file before the term we’re
seeking, and then read sequentially through the index file until we
find all the postings we’re looking for.

Most terms have relatively few postings — in fact, the vast majority
have only a single posting, although those tend not to get searched
for — so we will usually have to read less than 6000 postings from the
index segment, maybe a bit over 3000 on average.

So we opened the skip file, read about half of it (one seek and 5000
postings, which are 170kiB), opened the index file and read a chunk
from the middle of it (one seek and 3000 postings, which are 98kiB),
and got our result.  My laptop disk transfers almost 9 megabytes per
second, so that’s about 3ms of I/O bandwidth.

So to look up a single rare term in a single index segment is 3ms of
data transfer, 20ms of seeking, and processing 8000 lines in Python,
so somewhere around 30ms.  To look up N rare terms in M index files is
then N×M×30ms.  Right now I have 10 index segments.

Once the posting lists have been fetched, they are intersected to get
a list of search hits, which are messages that are then fetched from
the mailbox file.

Looking up common terms is more expensive because the number of
postings to process can far exceed the number of postings to sift
through to find them.  For example, something like 0.7% of my index
files consist of postings for the word “from”, which occurs in every
mail message.  In the 2-gibibyte segment I was using as an example,
there are presumably about 600 000 postings for the word “from”,
consuming 14 mebibytes.  Reading 14 mebibytes from disk is going to
take almost two seconds by itself, let alone the time to parse them.

The index segments are plain ASCII text files (as long as the corpus
is plain ASCII text), with one posting per line: first the lowercase
version of the word itself, then the name of the header field in which
the word was found (if any), then the byte offset in the mailbox where
the message containing the posting begins.  Here are some example
postings from one of my index segments:

    headers 98697592
    headers 99125817
    headers x-asf-spam-status 47638180
    headhunter 59154903
    headhunter 65973658
    headhunters 110711591

This means that, for example, the message in my mailbox starting at
byte 47638180 contains the word “headers” in the message header
“X-ASF-Spam-Status”, probably as part of the phrase
“tests=MISSING_HEADERS”.

Usage
-----

To generate new index segments for a mailbox:

    $ indexmail.py ~/mail/themailbox

To find all messages containing a word beginning with “curt”:

    $ fts ~/mail/mailbox curt | less

To find all messages containing the word “curt”:

    $ fts ~/mail/mailbox 'curt ' | less

To find all messages containing the word “curt” in the “From:” header:

    $ fts ~/mail/mailbox 'curt from ' | less

To find all messages containing the words “Curt” and “Martindale” in
the “From:” header:

    $ fts ~/mail/mailbox 'curt from ' 'martindale from ' | less

But you have to manually administer the index to get anything
approaching reasonable performance.

The index is in `~/mail/mailbox.idx`.  New index segments are created
in this directory with names like “.new-index.segment.6244.1” and
atomically renamed to “index-segment.6244.1” once they have been
generated.  Skip files for them, which don’t exist unless you generate
them manually, should be in files with the same name, but with
“.skip.” at the beginning of their names, like
“.skip.index-segment.6244.1”.  To generate a skip file:

    $ sparse.py 200000 ~/mail/mailbox.idx/index-segment.6244.1 > \
                       ~/mail/mailbox.idx/.skip.index-segment.6244.1

The number “200000” is a tunable parameter called “chunksize”.  200000
is a reasonable value.

If you have a whole bunch of index segments and it’s slowing down your
searches, you should merge them.  Any file in the index directory
whose name doesn’t begin with a “.” will be used as an index segment.

    $ LANG=C sort -m ~/mail/mailbox.idx/index-segment.* \
                  -o ~/mail/mailbox.idx/.new.merged-segment-serno
    $ mv ~/mail/mailbox.idx/.new.merged-segment-serno \
         ~/mail/mailbox.idx/merged-segment-serno
    $ rm ~/mail/mailbox.idx/index-segment.*
    $ sparse.py 200000 ~/mail/mailbox.idx/merged-segment-serno > \
                       ~/mail/mailbox.idx/.skip.merged-segment-serno

In the third step, make sure you’re only deleting the
`index-segment.*` files that you merged together in the first step.

There’s a file in the index directory called `.indexed-up-to` that
tells how much of the mailbox file has been indexed.

Tuning
------

Chunksize is the approximate number of index segment bytes to go
between skip file entries.  It should be in the neighborhood of the
product of your disk’s access latency (seek time plus rotational
latency) and its read bandwidth.  So if your access latency is 8ms and
your read bandwidth is 9MB/s, it should be in the neighborhood of 8 ×
9000 = 72000.  Making it larger will give you smaller skip files;
making it smaller will give you larger skip files.  If your skip files
get too big, you can make skip files `.skip.skip.index-segment.6244.1`
for the skip files, and so on ad infinitum.  But every level of skip
files costs a seek.

Merging all of your index segments into a single big index segment
will always give you better query performance, but it takes a long
time and can take a lot of disk space for the intermediate results.
Trying to merge too many segments at once could in theory make the
merge slower, but I think the number of segments where you have that
problem is in the neighborhood of (RAM size / chunksize), so these
days you should be able to merge tens of thousands of index segments
at once, so that’s probably a problem of the past.

Probably the best merging policy is something resembling the
following:

- Delay merging while you’re actively indexing.
- Merge whenever some index segment and all of the smaller index
  segments total more than N times the size of that index segment.  A
  good value for N might be in the range of 4–10.

I think this keeps the number of index segments to a maximum of
something like 1 + (N-1) * log(indexsize / min_index_segment_size) /
log(N).  “min_index_segment_size” is normally about 50MB.  If
“indexsize” is 100GB, that ratio is 2000; with an N of 4, the ratio of
the logarithms is under 6, so the maximum number of index segments is
19.  With an N of 10, the maximum increases to 37.  In either case,
the usual number of index segments is much smaller.

The tradeoff here is that a smaller N means you spend more time
merging, inversely proportional to log(N).  In a 100GB index with N=4,
each posting will pass through about 6 merges on the way to the final
index, for a final I/O cost of 1100GB.  If N=10, it need only pass
through about 3 merges.

A smarter merging policy might perform smaller merges more eagerly,
bigger merges more reluctantly, and perform merges more eagerly when
the total number of index segments is large.

Bugs
----

- It doesn’t automatically merge indices or generate skip files.
- It doesn’t do any kind of query optimization to avoid fetching
  millions of useless postings for common words.  This limits its use
  to corpuses of a few million documents at most.
- Given the index structure, at least for full-word searches or
  full-word fielded searches, it would be straightforward to use a
  sort-merge join to produce results incrementally.  Instead it uses a
  hash join because that’s like 15 lines of Python and doesn’t require
  making a duplicate non-fielded posting of words that occur in
  headers.
- It should generate skip files as it writes the index segment, rather
  than requiring another read of the index segment to do that.
- It should use `gzip` or something to reduce the size of the index
  files.  Gzipping a 129MB segment on my machine takes about 135 CPU
  seconds, compressing it to 33MB, but gunzipping it takes only about
  6 CPU seconds.  So the 270kiB we retrieved in 30ms in the
  “Architecture” scenario would have been compressed to 69kiB, which
  would have taken 13ms to decompress (minus 2ms of saved disk
  bandwidth), slowing down searches by about a 3:4 ratio in exchange
  for using a quarter of the disk space.
- Index-segment merges are “big-bang” affairs, using a lot of
  temporary disk space and a lot of time all at once, and this problem
  gets worse as corpus sizes get bigger.  If index segments output
  from a merge were partitioned into independently-mergeable subfiles
  by key-space subdivision, this could 
- I think there’s a bug in `skiplook.py` that will prevent successful
  retrieval of the first posting in an index segment.
- It doesn’t have an option to return results from the part of the
  mailbox that hasn’t been indexed yet.
- The information about which part of the mailbox has been indexed is
  stored separately from the index segments themselves.  This means
  you can’t, for example, delete a corrupt index segment in order to
  recreate it; you can’t generate index segments on a fast machine and
  transmit them to a slow machine; you can’t partition index-segment
  generation across a cluster with any kind of reasonable failure
  handling; you can’t detect whether coverage is duplicated between a
  merged segment and some input segment you failed to delete.  This
  coverage information ought to be stored in the index segments
  themselves.

Provenance
----------

The awesomely simple data format is due to Dave Long.

The overall structure that allows it to be efficient is Lucene’s,
which is Doug Cutting’s design, although of course Lucene differs from
this software by not being stupid.

Kragen Javier Sitaker wrote the software in 2008.  It is dedicated to
the public domain.

Misc
----

Document made with Markdown.

<link rel="stylesheet" href="http://canonical.org/~kragen/style.css" />
<!-- LocalWords:  chunksize idx serno indexmail themailbox fts martindale gzip
     LocalWords:  skiplook Gzipping gunzipping mbox mboxgrep SSD asf py doesn
     LocalWords:  mv rm indexsize min GB hasn Misc rel stylesheet href http css
     LocalWords:  LocalWords
-->
