#!/usr/bin/env python

import sys
import time

sys.path.insert(0, './')
from piping.parser import Parser
from piping.runtime import Runtime

filename = sys.argv[1]
data = open(filename).read().split('\n')
parser = Parser(data)
runner = Runtime(parser.pipes, parser.main, pipe_timeout=60, pipe_timeout_is_error=True) #False)
runner.run()

