#!/usr/bin/env python
import sys

outfile = sys.argv[1]

with open(outfile, 'wb') as f:
    while 1:
        buf = sys.stdin.read(8192)
        if not buf: break
        f.write(buf)


