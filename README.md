# piping

A simple language to glue programs together through a pipeline.

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
