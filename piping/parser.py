import os
import sys
import re
import subprocess
import shlex
import fcntl
import time


class Parser:
    def __init__(self, data, debug=False):
        self.data = data
        self.line_number = 0
        self.pipes = {}
        self.main = []
        self.capture_pipes = False
        self.capture_main = False
        self.namespace = ''
        self.namespace_def = ''
        self.debug = debug
        self._parse()

    def _error(self, enumber, msg):
        print('E-PARSER(%d): Line %d: %s' % (enumber, self.line_number, msg))
        sys.exit(1)

    def _parse_pipes(self, line):
        if not re.search('^pipes .*:$', line):
            return False
        self.capture_pipes = True
        self.namespace = re.sub('^pipes ', '', line).replace(':', '').strip()
        if self.namespace in self.pipes:
            self._error(1, 'Namespace previously defined on line %d: %s' % (pipes[self.namespace]['line'], self.namespace))
        self.pipes[self.namespace] = {'line':self.line_number, 'pipes':{}}
        return True

    def _capture_pipes(self, line):
        if not self.capture_pipes or not self.namespace:
            return False

        if line.strip() == '':
            return True

        # Get namespace.pipe name
        if re.search('^    [0-9a-zA-Z_-]+:$', line):
            self.namespace_def = line.strip().split(':')[0]
            self.pipes[self.namespace]['pipes'][self.namespace_def] = {'line':self.line_number, 'type':None, 'path':None, 'args':[]}

        # Get namespace.pipe definition
        elif re.search('^        [a-zA-Z0-9]', line):
            try:
                (dtype, dpath, dargs) = line.strip().split(' ', 2)
                dargs = dargs.split(' ')
            except:
                try:
                    (dtype, dpath) = line.strip().split(' ', 1)
                    dargs = []
                except:
                    self._error(2, 'Failed to parse namespace.pipe definition "%s.%s":\n\t"%s"' % (
                        self.namespace, self.namespace_def, line))
            self.pipes[self.namespace]['pipes'][self.namespace_def]['type'] = dtype
            self.pipes[self.namespace]['pipes'][self.namespace_def]['path'] = dpath
            self.pipes[self.namespace]['pipes'][self.namespace_def]['args'] = dargs
        else:
            self.capture_pipes = False

        if self.capture_pipes:
            return True
        return False

    def _parse_main(self, line):
        if not re.search('^main:$', line.strip()):
            return False
        self.capture_pipes = False
        self.capture_main = True
        return True

    def _capture_main(self, line):
        if not self.capture_main:
            return False

        parts = line.split('->')
        chain = []
        for part in parts:
            if part.strip() == '':
                continue
            if '.' in part:
                (self.namespace, self.func) = part.strip().split('::', 1)[0].split('.', 1)
                self.func = self.func.strip()
                args = []
                if '(' in part:
                    self.func = self.func.split('(', 1)[0]
                    args = part.split('(', 1)[1]
                    args = re.sub('\) |\) &|\)$', '', args)
                    args = args.split(', ')

                threaded = False
                if re.search('.*&$', self.func):
                    self.func = self.func.rsplit('&', 1)[0].strip()
                    threaded = True

                if not self.namespace in self.pipes:
                    self._error(3, 'Failed to find namespace %s with pipe %s' % (self.namespace, self.func))

                # validate args exist in definition
                dargs = []
                aargs = []
                for arg in args:
                    if not '=' in arg:
                        self._error(4, 'Invalid argument format. Expected arg=value:\n\t"%s"' % (line))
                    aargs.append(arg.split('::')[0].strip().split('='))
                    arg = arg.split('=')[0]
                    dargs.append(arg)

                    if not self.func in self.pipes[self.namespace]['pipes']:
                        self._error(11, 'Could not find pipe "%s" in namespace "%s":\n\t"%s"' % (
                            self.func, self.namespace, line))

                    if not arg in self.pipes[self.namespace]['pipes'][self.func]['args']:
                        self._error(5, 'Invalid argument name "%s" to %s.%s:\n\t"%s"' % (
                            arg, self.namespace, self.func, line))

                # check for missing args
                for arg in self.pipes[self.namespace]['pipes'][self.func]['args']:
                    if arg == '*':
                        continue
                    if not arg in dargs:
                        self._error(6, 'Missing argument named "%s" to %s.%s:\n\t"%s"' % (
                            arg, self.namespace, self.func, line))

                d = {'type':'pipe', 'namespace':self.namespace, 'func':self.func, 'line':self.line_number,
                    'value':None, 'args':aargs, 'thread':threaded}
                chain.append(d)

            elif not '.' in part and not '(' in part:
                var = part.strip()
                if var == 'wait':
                    thread_wait = 'wait'
                else:
                    thread_wait = False
                d = {'type':'var', 'namespace':None, 'func':None, 'value':var, 'line':self.line_number, 'args':None,
                    'thread':thread_wait}
                # Check if var exists if it's item 0
                if len(chain) < 1 and var != 'wait':
                    found = False
                    for m in self.main:
                        for x in m:
                            if x['type'] == 'var' and x['value'] == var:
                                found = True
                    if not found:
                        self._error(7, 'Could not find previously defined variable named "%s":\n\t"%s"' % (var, line))
                chain.append(d)
            else:
                self._error(8, 'Parser error:\n\t"%s"\n\t"%s"' % (line, part))

            # Capture assignment
            if '::' in part:
                var = part.split('::')[1].strip()
                var = var.split(' ')[0]
                d = {'type':'var', 'namespace':None, 'func':None, 'value':var, 'line':self.line_number, 'args':None, 'thread':False}
                chain.append(d)
                if re.search('&$', part):
                    d = {'type':'var', 'thread': True, 'namespace':None, 'func':None, 'value':None,
                        'line':self.line_number, 'args':None}
                    chain.append(d)
        if chain:
            self.main.append(chain)
        return True


    def _parse(self):
        for line in self.data:
            self.line_number += 1
            if re.search('^(\s+)?#', line): continue
            if self._parse_pipes(line): continue
            if self._capture_pipes(line): continue
            if self._parse_main(line): continue
            if self._capture_main(line): continue
            if line.strip() != '':
                self._error(9, 'Invalid format:\n\t"%s"' % (line))
                sys.exit(1)


