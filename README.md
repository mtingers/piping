# piping

A simple language to glue programs together through a pipeline.

# Status

* Experimental
* Fragile

One might ask, "Why not just use a shell script"?  Well, you probably should.

# TODO

1. Add other transport types besides 'exec' (http[s] with things like auth and customer headers, sockets [tcp/udp], etc).
2. Add optional intermediate message communication/transaction format with type enforcement.
3. Add import (like Python import).
4. Add ability to create functions and not stuck to 'main'.

## Examples

```bash
pipes p:
    ls:
        exec /bin/ls path
    grep:
        exec /usr/bin/grep flags pattern
    sed:
        exec /usr/bin/sed pattern
    ps:
        exec /bin/ps flags
    find:
        exec /usr/bin/find path
    sort:
        exec /usr/bin/sort

pipes e:
    upper:
        exec ./examples/upper.py
    lower:
        exec ./examples/lower.py
    filewriter:
        exec ./examples/filewriter.py filename

    # example namespace duplicate name from "p"
    ls:
        exec /bin/ls

main:
    # Example threading and wait for finish before continuing on
    p.find(path='/usr/local/') -> e.upper -> p.grep(pattern='bin', flags='-i') :: y &
    p.ls(path='/tmp/') -> p.sed(pattern='s/a/__A__/g') :: z &
    wait

    # Write the output to a file
    y -> e.filewriter(filename='/tmp/test.output')

    # Write to stdout in lowercase, sorted
    z -> e.lower -> p.sort

```
