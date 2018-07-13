import os
import sys
import re
import subprocess
import shlex
import fcntl
import time
import threading

def pipe_stdin_writer(pipe, buf):
    pipe.stdin.write(buf)
    pipe.stdin.close()

def runner_wrap(pipes, main, piping, outputs, pipe_timeout, pipe_timeout_is_error):
    r = Runner(pipes, main, piping, outputs=outputs,
        pipe_timeout=pipe_timeout, pipe_timeout_is_error=pipe_timeout_is_error)

class Runner:
    def __init__(self, pipes, main, piping, outputs={}, pipe_timeout=10, pipe_timeout_is_error=False):
        self.pipes = pipes
        self.main = main
        self.piping = piping
        self.pipe_timeout = pipe_timeout
        self.pipe_timeout_is_error = pipe_timeout_is_error
        self.outputs = outputs
        self.piped = []
        self.count = 0
        self.namespace = None
        self.func = None
        self.execf = None
        self.var = None
        self.piped = []
        self.input_value = b''
        self.pipe_threads = []
        self.run()

    def _error(self, enumber, msg):
        print('E-RUNTIME(%d): %s' % (enumber, msg))
        sys.exit(1)

    def _handle_pipe(self, m, p):
        if p['type'] != 'pipe':
            return False

        self.namespace = p['namespace']
        self.func = p['func']
        self.execf = self.pipes[self.namespace]['pipes'][self.func]['path']
        args = ''
        for i in p['args']:
           args += i[1]+' '
        if len(self.piped) < 1:
            inp = subprocess.PIPE
        else:
            inp = self.piped[len(self.piped)-1].stdout
        pipe = subprocess.Popen(shlex.split(r'%s %s' % (self.execf, args)),
            stdin=inp, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        thread = None
        ## NOTE: Writing to pipe stdin will block if len is too large.  We must create a new thread to operate
        ## independently so we can write+read at the same time through the start to end of pipeline
        if self.input_value:
            thread = threading.Thread(target=pipe_stdin_writer, args=(pipe, self.input_value,))
            thread.start()
            self.pipe_threads.append(thread)
            self.input_value = b''

        self.piped.append(pipe)
        if self.count >= len(m):
            output = b''
            # use nonblocking for timeout on read (can happen on no input)
            fl = fcntl.fcntl(self.piped[-1].stdout, fcntl.F_GETFL)
            fcntl.fcntl(self.piped[-1].stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            then = time.time()
            while 1:
                try:
                    b = self.piped[-1].stdout.read(8192)
                    if not b: break
                    sys.stdout.write(b)
                    sys.stdout.flush()
                    then = time.time()
                except:
                    now = time.time()
                    if now - then > self.pipe_timeout:
                        if self.pipe_timeout_is_error:
                            self._error(10, 'Timeout reading pipe')
                        break
        sys.stdout.flush()
        return True

    def _handle_var_end(self, m, p):
        if not p['type'] == 'var' or not len(self.piped) > 0:
            return False

        output = b''
        fl = fcntl.fcntl(self.piped[-1].stdout, fcntl.F_GETFL)
        fcntl.fcntl(self.piped[-1].stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        then = time.time()
        while 1:
            try:
                b = self.piped[-1].stdout.read(1024)
                if not b: break
                output += b
                then = time.time()
            except:
                now = time.time()
                if now - then > self.pipe_timeout:
                    if self.pipe_timeout_is_error:
                        self._error(10, 'Timeout reading pipe')
                    break

        self.var = p['value']
        self.namespace = p['namespace']
        if not self.namespace in self.outputs:
            self.outputs[self.namespace] = {}
        if not self.var in self.outputs[self.namespace]:
            self.outputs[self.namespace][self.var] = None
        if output:
            self.outputs[self.namespace][self.var] = output
        return True

    def _handle_var_start(self, m, p):
        if not p['type'] == 'var' or not len(self.piped) < 1:
            return False
        self.var = p['value']
        self.namespace = p['namespace']
        ## NOTE: Wait for threads.... this is hackish but we should have already
        ## validated that this variable is defined during parsing.
        while 1:
            try:
                self.input_value = self.outputs[self.namespace][self.var]
                break
            except KeyError:
                time.sleep(0.25)

        return True

    def run(self):
        for count, p in enumerate(self.piping, start=1):
            self.count = count
            if self._handle_pipe(self.piping, p): continue
            if self._handle_var_end(self.piping, p): continue
            if self._handle_var_start(self.piping, p): continue

            # cleanup
            while len(self.pipe_threads) > 0:
                thread = self.pipe_threads.pop()
                thread.join()

            for p in self.piped:
                del(p)

class Runtime:
    def __init__(self, pipes, main, pipe_timeout=10, pipe_timeout_is_error=False):
        self.pipes = pipes
        self.main = main
        self.pipe_timeout = pipe_timeout
        self.pipe_timeout_is_error = pipe_timeout_is_error
        self.outputs = {}
        self.piped = []
        self.count = 0
        self.namespace = None
        self.func = None
        self.execf = None
        self.var = None
        self.threads = []

    def _error(self, enumber, msg):
        print('E-RUNTIME(%d): Line %d: %s' % (enumber, self.line_number, msg))
        sys.exit(1)

    def _is_threaded(self, m):
        if m[-1]['thread'] and m[-1]['thread'] != 'wait':
            return True
        return False

    def _is_thread_wait(self, m):
        if m[-1]['thread'] == 'wait':
            return True
        return False

    def run(self):
        for m in self.main:
            if self._is_thread_wait(m):
                not_done = True
                for thread in self.threads:
                    while thread.is_alive():
                        time.sleep(0.25)
                    thread.join()
                continue
            if self._is_threaded(m):
                t = threading.Thread(target=runner_wrap,
                    args=(self.pipes, self.main, m, self.outputs, self.pipe_timeout, self.pipe_timeout_is_error))
                t.start()
                self.threads.append(t)
            else:
                runner = Runner(self.pipes, self.main, m, outputs=self.outputs,
                    pipe_timeout=self.pipe_timeout, pipe_timeout_is_error=self.pipe_timeout_is_error)
                self.outputs.update(runner.outputs)

        for thread in self.threads:
            thread.join()

