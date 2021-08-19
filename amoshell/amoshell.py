#!/bin/bash
import os
import sys
import re
import glob
import copy
import subprocess

"""
    args:
    - parallel: max number of parallel sessions mobatch will use. default=10.
    - bin_path: path, if moshell/mobatch binaries are installed in a
                non-standard location.

"""
class Amos:

    def __init__(self, **kwargs):
        self.bin_path = None
        self.moshellbin = None
        self.mobatchbin = None
        self.parallel = 10

        allowed = ('parallel', 'bin_path')
        for k, v in kwargs.items():
            if not k in allowed:
                raise KeyError("Invalid option-key: %s" % k)

            setattr(self, k, v)

        if not self.moshellbin:
            try:

                self.moshellbin = amos_location(self,self.bin_path)
            except:
                raise RuntimeError('amos or moshell program not found')

        if not self.mobatchbin:
            try:
                self.mobatchbin = self.__amosbatch_location(self.bin_path)
            except:
                raise RuntimeError('amosbatch or mobatch program not found')


    """
    moshell()
    send amos command to node, and get results

    params:
        node name (or ip address)
        command string
        optional keyword-args (valid amos optional variables only)
    returns:
        tuple (return-code[0 ok|1 fail], stdout text, stderr text)
    """
    def moshell(self, node, cmd, **kwargs):
        opts = parse_kvargs(self,kwargs)
        return self.__amos_runner(node, cmd, opts)



    """
    mobatch()
    send amosbatch(mobatch) commands to nodes, and get result logs.

    WARNING! mobatch commands can take a very, very long time to complete,
    depending on number of nodes and commands to be run. commands run against
    thousands of nodes may take 6-10 hours(or more) to complete!
    Also, using over 30 parallel sessions is not recommended.

    params:
        node list (or path to existing sitefile)
        command string (or path to existing mos command file)
        optional keyword-args (valid amos optional variables only)

    returns:
        a list-of-tuples. Each result tuple contains the following:
         (node-name, exit-code, path-to-logfile)
    """
    def mobatch(self, nodes, cmd, **kwargs):
        opts = parse_kvargs(self, kwargs)
        sitefile = None
        cmdfile = None
        rmv_sitefile = False
        rmv_cmdfile = False

        if len(nodes) == 1:
            # only one node? seems odd. possibly it is a sitefile?
            if os.path.isfile(nodes[0]):
                sitefile = nodes[0]

        # write the sitefile if required
        if not sitefile:
            rmv_sitefile = True
            sitefile = '/tmp/pymobatch.' + str(os.getpid()) + '.sitefile'
            fh = open(sitefile, 'w')
            for n in nodes:
                fh.write(n + "\n")

            fh.close()

        # write amos commands to a file
        if len(cmd) == 1 and os.path.isfile(cmd):
            cmdfile = cmd
        else:
            rmv_cmdfile = True
            cmdfile = '/tmp/pymobatch.' + str(os.getpid()) + '.mos'
            fh = open(cmdfile, 'w')
            atoms = cmd.split(';')

            for a in atoms:
                fh.write(a.strip() + "\n")

            fh.close()

        results = self.__amosbatch_runner(sitefile, cmdfile, opts)

        if rmv_sitefile:
            os.unlink(sitefile)

        if rmv_cmdfile:
            os.unlink(cmdfile)

        return results

    """
    __amosbatch_location()
    PRIVATE
    get full path to either the amosbatch or mobatch binary

    params:
        path to search(optional)
    returns:
        full path to binary | None
    """
    def __amosbatch_location(self, path):
        loc = find_possibles(self,('amosbatch','mobatch'), path)
        if not loc:
            raise
        else:
            return loc


    """
    __amos_runner()
    PRIVATE
    run a moshell/amos command subprocess against a specific node

    params:
        1. a node name or ipaddress
        2. a command string
        3. an option dict (optional)
    returns:
        A tuple. two elements.
        (return-code(0=ok, 1=fail), stdout, stderr)
    """
    def __amos_runner(self, node, cmd, opts=None):
        v = None;
        script = [self.moshellbin]
        logdir = None

        if opts:
            atoms = []
            for k, v in opts.items():
                if k == 'logdir':
                    logdir = v
                    continue
                else:
                    atoms.append("=".join((k, str(v))))

            v = "-v"
            v += ",".join(atoms)
            script.append(v)
        if logdir:
            script.append('-o')
            script.append(logdir)
        script.append(node)
        script.append(cmd)
        child = subprocess.Popen(script,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE )
        output, errors = child.communicate()
        return (child.returncode, output.decode('utf-8') , errors.decode('utf-8') )


    """
    __amosbatch_runner()
    PRIVATE
    run a moshell/amos command against a several nodes in parallel.
    the results for a node is the path to the logfile containing the
    amos results for that node.

    params:
        1. a path to a sitefile
        2. a command string
        3. an option dict (optional)

    returns:
        A list of tuples:
          [(node, rval, results-file), (node, rval, results-file)... ]

        On error, returns an empty list
    """
    def __amosbatch_runner(self, sitefile, cmdfile, opts=None):
        v = None;
        logdir = None
        script = [self.mobatchbin]
        script.append('-p')
        script.append(str(self.parallel))

        if opts:
            atoms = []
            for k, v in opts.items():
                if k == 'logdir':
                    logdir = v
                    continue
                else:
                    atoms.append("=".join((k, str(v))))

            v = "-v"
            v += ",".join(atoms)
            script.append(v)

        if logdir:
            script.append('-o')
            script.append(logdir)

        script.append(sitefile)
        script.append(cmdfile)
        child = subprocess.Popen(script,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE )
        output, errors = child.communicate()
        if child.returncode:
            sys.stderr.write(errors)
            return []

        # find results of all the logfiles
        for line in output.splitlines():
            match = re.match(r'Logfiles stored in\s+(.+)', line.decode('utf-8'))
            if match:
                return self.__amosbatch_result_parser(match.group(1))


        raise RuntimeError('could not find amosbatch result path from results')


    """
    __amosbatch_result_parser()
    PRIVATE
    Parse the directory contents of an amosbatch results dir

    params:
        a path to the amosbatch log dir

    returns:
        A list of tuples:
          [(node, rval, results), (node, rval, results)... ]
    """
    def __amosbatch_result_parser(self, path):
        results = []

        # find results text log, and pull out any nodes that failed to connect
        rlog = glob.glob(path + '/*result.txt')[0]

        if not rlog:
            raise RuntimeError('amosbatch results file not found in ' + path)

        nocontact = self.__amosbatch_nocontact_nodes(rlog)

        for n in nocontact:
            results.append((n, 1, 'no contact'))

        # store the path for each node output log
        logs = glob.glob(path + '/*log')
        for log in logs:
            nodename = None
            match = re.match(r'^.+/(\S+)\.log', log)
            if match:
                node = match.group(1)
                if node in nocontact:
                    continue

                results.append((node, 0, log))

        return results


    """
    __amosbatch_nocontact_nodes()
    PRIVATE
    Parse amosbatch results.txt log for any nodes that could not be reached

    params:
        a path to the amosbatch results text file

    returns:
        A list of node names.
        An empty list is returned if nothing is found
    """
    def __amosbatch_nocontact_nodes(self, fname):
        results = []

        """
        Look for lines like this:

        OK            0m13s   PSLEeNB04
        OK            0m13s   PSLEeNB02
        no contact    0m15s   PSLEeNB01
        """

        fh = open(fname, 'r+')
        for line in fh.readlines():
            match = re.match(r'^\s*no contact\s+\S+\s+(\S+)\s*$', line)
            if match:
                results.append(match.group(1))

        fh.close()
        return results



"""
    args:
    - parallel: max number of parallel sessions mobatch will use. default=10.
    - bin_path: path, if moshell/mobatch binaries are installed in a
                non-standard location.
    - node: address of the node which will host the session.
    - cmd: the commands to be used during startup of the session.

"""
class Open_Amos:

    def __init__(self, node, cmd='', **kwargs):
        self.bin_path = None
        self.moshellbin = None
        self.parallel = 10
        self.node = node

        allowed = ('parallel', 'bin_path')
        kw= copy.copy(kwargs)
        for k, v in kw.items():
            if k in allowed:
                setattr(self, k, v)
                del kwargs[k]

        if not self.moshellbin:
            try:
                self.moshellbin = amos_location(self,self.bin_path)
            except:
                raise RuntimeError('amos or moshell program not found')

        # Initializing the session
        v = None;
        script = [self.moshellbin]
        logdir = None
        result = []
        opts = parse_kvargs(self,kwargs)
        if opts:
            atoms = []
            for k, v in opts.items():
                if k == 'logdir':
                    logdir = v
                    continue
                else:
                    atoms.append("=".join((k, str(v))))

            v = "-v"
            v += ",".join(atoms)
            script.append(v)
        if logdir:
            script.append('-o')
            script.append(logdir)
        script.append(self.node)

        self.child = subprocess.Popen(script, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        #to prevent deadlock with stdout
        self.pwrite( "uv pre_prompt=CUSTOM_EOF_MARKER")
        result = []
        while True:
            val = self.pread()
            if val == 'CUSTOM_EOF_MARKER\n':
                break
            result.append(val)

        result.append(self.send(cmd))
        print(''.join(result))


    """
    send()

    send a command or list of commands to the open session.

    params:
        the command or commands
    returns:
        the output of the commands
    """
    def send(self, cmd):
        result = []
        if isinstance(cmd, list):
            for c in cmd:
                self.pwrite(c)
                result.append(self.node+"> "+c)
                while True:
                    val = self.pread()
                    if val == 'CUSTOM_EOF_MARKER\n':
                        break
                    result.append(val)
        else:
            self.pwrite(cmd)
            result.append(self.node+"> "+cmd)
            while True:
                val = self.pread()
                if val == 'CUSTOM_EOF_MARKER\n':
                    break
                result.append(val)
        return ''.join(result)

    """
    quit()

    quits the session

    params:
        None
    returns:
        the output of the session
    """
    def quit(self):
        result = []
        self.pwrite("quit")
        result.append(self.node+"> quit\n")
        result.append(self.pread())
        self.child.communicate()
        return ''.join(result)

    """
    pwrite()

    writes to the subprocess after checking python version_info

    params:
        the message to the subprocess
    returns:
        None
    """
    def pwrite(self, cmd):
        if sys.version_info[0] > 2:
            self.child.stdin.write((cmd+"\n").encode('utf-8'))
            self.child.stdin.flush()
        else:
            self.child.stdin.write(b''+cmd+'\n')

    """
    pread()

    reads and decodes the output from stdout

    params:
        None
    returns:
        decoded message
    """
    def pread(self):
        val = self.child.stdout.readline()
        val = val.decode('utf-8')
        return val

"""
amos_location()
PRIVATE
get full path to either the amos or moshell binary

params:
    path to search(optional)
returns:
    full path to binary | None
"""
def amos_location(self, path):
    loc = find_possibles(self,('moshell', 'amos'), path)
    if not loc:
        raise
    else:
        return loc

"""
find_possibles()
PRIVATE
return the first binary found from a list of possibles

params:
    a list of binary names
    a search path (optional)
returns:
    full path to binary | None
"""
def find_possibles(self, possibles, path):
    if not possibles or len(possibles) < 1:
        return None
    if not path:
        for p in possibles:
            target = which(self, p)
            if target:
                return target
    else:
        for p in possibles:
            target = path + "/" + p
            if os.path.isfile(target) and os.access(target, os.X_OK):
                return target

    return None


"""
which()
PRIVATE
duplicates function of unix 'which' command to find a program in the path

params:
    a program name
returns:
    full path to program | None
"""
def which(self, program):
    fpath, fname = os.path.split(program)
    if fpath:
        if os.path.isfile(program) and os.access(program, os.X_OK):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
                return exe_file

    return None


"""
parse_kvargs()
PRIVATE
parse any amos options that were passed in, and filter out invalid options.
See Ericsson Advanced Moshell Scripting user guide for variable information.

params:
    a dict
returns:
    a dict
"""
def parse_kvargs(self, kwargs):
    if not kwargs:
        return None

    opts = copy.copy(kwargs)
    valid = (
        'amos_debug',
        'ask_for_attribute_type',
        'bldebset_confirmation',
        'credential',
        'commandlog_path',
        'corba_class',
        'csnotiflist',
        'default_mom',
        'del_confirmation',
        'dontfollowlist',
        'editor',
        'fast_lh_threshold',
        'fast_cab_threshold',
        'ftp_port',
        'followlist',
        'ftp_timeout',
        'http_port',
        'inactivity_timeout',
        'include_nonpm',
        'ip_connection_timeout',
        'ip_database',
        'ip_inactivity_timeout',
        'java_settings_high',
        'java_settings_low',
        'java_settings_medium',
        'keepLmList',
        'lt_confirmation',
        'loginfo_print',
        'logdir',   # custom option, not E/// supported. see documentation
        'muteFactor',
        'nm_credential',
        'node_login',
        'print_lmid',
        'PrintProxyLDN',
        'PrintProxySilent',
        'prompt_highlight',
        'pm_wait',
        'pm_logdir',
        'sa_credential',
        'sa_password',
        'secure_ftp',
        'secure_port',
        'secure_shell',
        'set_window_title',
        'show_timestamp',
        'telnet_port',
        'transaction_timeout',
        'username',
        'xmlmomlist',
        'password',
        )

    for k, v in opts.items():
        if k not in valid:
            raise KeyError("Invalid option-key: %s" % k)

    return opts
