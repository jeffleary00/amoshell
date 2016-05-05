#!/usr/bin/env python

"""
-------------------------------------------------------------------------------
A Python interface to Ericsson moshell/amos CLI.
See included README for usage examples.

AUTHOR:
	Jeff Leary
	jeffleary00@gmail.com
	
See included LICENSE information (BSD 3-clause license)
-------------------------------------------------------------------------------
"""

import os
import sys
import re
import glob
import copy
import subprocess

__version_info__ = ('1','0','0')
__version__ = '.'.join(__version_info__)


# global variables
amosbin = __find_amos()
amosbatchbin = __find_amosbatch()


"""
amos()
-----------------------------
Run an amos/moshell command

params:
    1. node name
    2. commands, as quoted string
    3. kwargs, to be added as options to the command-line variables.
       see Ericsson Advanced Moshell Scripting documentation for more details
       about variables.
       Some examples, like;
        - ip_database=/home/user/ipdatabase.dat
        - corba_class=5

returns:
    A tuple. two elements. (see __amos_runner())
    (return-code(0=ok, non-zero=error), text-results)

"""
def amos(node, command, **kwargs):
    opts = __parse_kwargs(kwargs)
    return __amos_runner(node, command, opts)


"""
amosbatch()
-----------------------------
Run an amosbatch/mobatch command, for parallel collection from multiple nodes
at one time.

params:
    1. a list of nodes
    2. a command string
    3. kwargs, to be added as options to the command-line variables

returns:
    A list of tuples:
      [(node, return-code, log-path), (node, return-code, log-path)... ]
"""
def amosbatch(nodes, command, **kwargs):
    opts = __parse_kwargs(kwargs)
    sitefile = '/tmp/pymobatch.' + str(os.getpid()) + '.sitefile'
    cmdfile = '/tmp/pymobatch.' + str(os.getpid()) + '.mos'
    
    # open a temp sitefile for listing the nodes
    try:
        fh = open(sitefile, 'w')
    except IOError:
        sys.stderr.write("failed to open temp sitefile for writing\n")
        return []

    for n in nodes:
        fh.write(n + "\n")

    fh.close()

    
    # write amos commands to a file
    try:
        fh = open(cmdfile, 'w')
    except IOError:
        sys.stderr.write("failed to open temp command file for writing\n")
        return []

    atoms = command.split(';')
    for a in atoms:
        fh.write(a.strip() + "\n")
    
    fh.close()
    
    results = __amosbatch_runner(sitefile, cmdfile, opts)
    os.unlink(sitefile)
    os.unlink(cmdfile)
    
    return results


"""
__parse_kwargs()

parse any options that were passed in, and filter out invalid options
See Ericsson Advanced Moshell Scripting user guide for variable information.

params:
    a dict
returns:
    a dict
"""
def __parse_kwargs(kwargs):
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
        'xmlmomlist'
    )
    for k, v in opts.items():
        if k not in valid:
            sys.stderr.write(k + " not a valid option\n")
            try:
                del opts[k]
            except KeyError:
                pass

    return opts


"""
__amos_runner()

run a moshell/amos command subprocess against a specific node

params:
    1. a node name or ipaddress
    2. a command string
    3. an option dict (optional)
returns:
    A tuple. two elements.
    (return-code(0=ok, 1=fail), text-results)
"""
def __amos_runner(node, command, opts=None):
    v = None;
    moshell = [amosbin]

    if opts:
        atoms = []
        for k, v in opts.items():
            atoms.append("=".join((k, str(v))))

        v = "-v"
        v += ",".join(atoms)
        moshell.append(v)

    moshell.append(node)
    moshell.append("'" + command + "'")
    child = subprocess.Popen(moshell,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE )
    output, errors = child.communicate()
    if child.returncode or errors:
        return [1, errors]

    return [0, output]


"""
__amosbatch_runner()
=============================
*PRIVATE*
=============================
run a moshell/amos command against a several nodes in parallel.
the results for a node is the path to the logfile containing the
amos results for that node.

The amosbatch 'parallel' feature (-p) is hard-coded to 10 for safety, to 
prevent overloading system resources.

params:
    1. a path to a sitefile
    2. a command string
    3. an option dict (optional)

returns:
    A list of tuples:
      [(node, rval, results-file), (node, rval, results-file)... ]

    On error, returns an empty list
"""
def __amosbatch_runner(sitefile, cmdfile, opts=None):
    v = None;
    mobatch = [amosbatchbin, '-p', '10']
    logpath = None

    if opts:
        atoms = []
        for k, v in opts.items():
            atoms.append("=".join( (k, str(v) )))

        v = "-v"
        v += ",".join(atoms)
        mobatch.append(v)

    mobatch.append(sitefile)
    mobatch.append(cmdfile)
    child = subprocess.Popen(mobatch,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE )
    output, errors = child.communicate()
    if errors:
        sys.stderr.write(errors)
        return []

    # find results of all the logfiles
    for line in output.splitlines():
        match = re.match(r'Logfiles stored in\s+(.+)', line)
        if match:
            return __amosbatch_result_parser(match.group(1))


    sys.stderr.write("could not find amosbatch result path\n")
    return []


"""
__amosbatch_result_parser()
=============================
*PRIVATE*
=============================
Parse the directory contents of an amosbatch results dir

params:
    1. a path to the amosbatch log dir

returns:
    A list of tuples:
      [(node, rval, results), (node, rval, results)... ]
"""
def __amosbatch_result_parser(path):
    results = []

    # find results text log, and pull out any nodes that failed to connect
    rlog = glob.glob(path + '/*result.txt')[0]

    if not rlog:
        sys.stderr.write('amosbatch results text file not found in ' + path)
        return []

    nocontact = __amosbatch_nocontact_nodes(rlog)

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

            results.append( (node, 0, log) )

    return results


"""
__amosbatch_nocontact_nodes()
=============================
*PRIVATE*
=============================
Parse amosbatch results.txt log for any nodes that could not be reached

params:
    1. a path to the amosbatch results text file

returns:
    A list of node names.
    An empty list is returned if nothing is found
"""
def __amosbatch_nocontact_nodes(fname):
    results = []

    """
    Look for lines like this:

    OK            0m13s   PSLEeNB04
    OK            0m13s   PSLEeNB02
    no contact    0m15s   PSLEeNB01
    """

    try:
        fh = open(fname, 'r+')
    except IOError:
        sys.stderr.write("failed to open " + fname + "\n")
        return []

    for line in fh.readlines():
        match = re.match(r'^\s*no contact\s+\S+\s+(\S+)\s*$', line)
        if match:
            results.append(match.group(1))

    fh.close()
    return results

"""
__find_amos()
=============================
*PRIVATE*
=============================
find the path to either the amos or moshell cli binary

params:
	none

returns:
	path to amos/moshell on success
	None on failure
"""
def __find_amos:
	target = None
	possibles = ('amos', 'moshell')
	for p in possibles:
		target = __which(p)
		if target:
			return target

	return target

	
"""
__find_amosbatch()
=============================
*PRIVATE*
=============================
find the path to either the amos or moshell cli binary

params:
	none

returns:
	path to amosbatch/mobatch on success
	None on failure
"""
def __find_amosbatch():
	target = None
	possibles = ('amosbatch', 'mobatch')
	for p in possibles:
		target = __which(p)
		if target:
			return target

	return target


"""
__which()
=============================
*PRIVATE*
=============================
mimic the function of Unix which command.

params:
	executable name

returns:
	full path to the executable
	None on failure
"""	
def __which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None
