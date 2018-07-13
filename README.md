# piping

A simple language to glue programs together through a pipeline.

# Status

* Still experimental. Likely to change quickly.
* Fragile. Needs more tests and better parsing.

One might ask, "Why not just write a python, shell, ... script"?  You probably should.  But the simple syntax and readability might be for you since doing the same (outside of a shell script) typically requires a lot of boiler plate code.
 

# Features

* Simple and limited in capabilities.  Feature-less on purpose.
* Easy to understand syntax.
* Easy to program in.
* Strict formatting.
* Parsing requires 'tabs' to be 4 spaces. Tabs will not work. 2 space tabs won't work, etc...
* if, while, for, etc do not exist.
* Expressions, bit shifting, unary, etc do not exist.

# TODO

1. Add other transport types besides 'exec' (http[s] with things like auth and customer headers, sockets [tcp/udp], etc).
2. Add import (like Python import).
3. Add ability to create functions and not be stuck to 'main'.
4. Add compiler detection of variables only being referenced once and fold into a single pipeline.
5. Add race-condition detection and output variable locking.
6. Add optional intermediate message communication/transaction format with type enforcement.
7. Add multi-pipe support. For example, send the output of find to grep and sed simultaneously and store in x and y variables:
```bash
p.find(path='/foo') -> [p.grep(pattern='foo') :: x] + [p.sed(filter='s/foo/bar/g') :: y]
```

## Examples

```bash

## Define 'pipe namespaces' here

# This is namespace 'p'
pipes p:

    # Defined method ls in namespace p
    ls:
        # What to execute when p.ls is called
        exec /bin/ls path
        
    # More methods, should be intuitive
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

# This is namespace 'e'.
# Note that both p and e contain a 'ls' method
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
    # Run this pipeline in the background using '&' and store result in variable y
    p.find(path='/usr/local/') -> e.upper -> p.grep(pattern='bin', flags='-i') :: y &
    
    # Run this pipeline in the background using '&' and store result in variable z
    p.ls(path='/tmp/') -> p.sed(pattern='s/a/__A__/g') :: z &
    
    # Wait for all background processes to finish since we're going to be using
    # variables y and z
    wait

    # Write the output to a file (pip
    y -> e.filewriter(filename='/tmp/test.output')

    # Write to stdout in lowercase, sorted
    z -> e.lower -> p.sort
    
    # Create a race condition on purpose. Write to variable z from two pipelines
    p.find(path='/tmp/') :: z &
    p.find(path='/home/') :: z &
    
```
