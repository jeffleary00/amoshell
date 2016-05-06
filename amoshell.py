"""
-------------------------------------------------------------------------------
AMOSHELL:

    A Python OO interface to the Ericsson moshell/amos CLI.


API:

    moshell(node, command, **opts)
    mobatch(node-list, command, **opts)
    
EXAMPLES:

    ** moshell usage **
    *******************
    
    from amoshell import Amos
    mo = Amos()
    rval, results = mo.moshell('RBS003', 'lt all; alt')
    if rval:
        print 'error: ' + results
    else:
        print results


    ** mobatch usage **
    *******************
    
    from amoshell import Amos
    mo = Amos(parallel=5, log_dir=/var/tmp/mylogs)
    results = mo.mobatch(['ERB001', 'ERBS002'], 'lt all; get security', 
                                                    ip_database=/tmp/ipdb.dat,
                                                    corba_class=5 )
    for r in results:
        node, rval, logfile = r
        if not rval:
            print node + " results found in " + logfile                                             

    
AUTHOR:

    Jeff Leary
    jeffleary00@gmail.com


LICENSE:

Copyright (c) 2016, Jeff Leary
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of amos nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

-------------------------------------------------------------------------------
"""

import os
import sys
import re
import glob
import copy
import subprocess


__version_info__ = ('1','1','0')
__version__ = '.'.join(__version_info__)


class Amos:
    
    def __init__(self, **kwargs):
        self.bin_path = None
        self.moshellbin = None
        self.mobatchbin = None
        self.parallel = 10
    
        for k,v in kwargs.items():
            setattr(self, k, v)
        
        if not self.moshellbin:
            try:
                self.moshellbin = self.amos_location(self.bin_path)
            except:
                raise RuntimeError('amos or moshell binary not found')
            
        if not self.mobatchbin:
            try:
                self.mobatchbin = self.amosbatch_location(self.bin_path)
            except:
                raise RuntimeError('amosbatch or mobatch binary not found')
            
    
    """
    moshell()
    send amos command to node, and get stdout results
    
    params:
        node name (or ip address)
        command string
        optional keyword-args (valid amos optional variables only)
    returns:
        tuple (return-code[0 ok|1 fail], stdout text)
    """                 
    def moshell(self, node, cmd, **kwargs):
        opts = self.__parse_kwargs(kwargs)
        return self.__amos_runner(node, cmd, opts)


    """
    mobatch()
    send amosbatch(mobatch) commands to nodes, and get result logs.
    
    this can take a very, very long time to complete, depending on number of
    nodes and commands to be run. mobatch commands against thousands of nodes
    may take 4-8 hours(or more) to complete!!
    
    params:
        node list (or path to existing sitefile)
        command string (or path to existing mos command file)
        optional keyword-args (valid amos optional variables only)
        
    returns:
        list-of-tuples. Each result tuple contains the following:
         (node-name, return-code, path-to-logfile)
    """
    def mobatch(self, nodes, cmd, **kwargs):
        opts = self.__parse_kwargs(kwargs)
        sitefile = None
        cmdfile = None
        
        if len(nodes) == 1:
            # only one node? seems odd. possibly it is a sitefile
            if os.path.isfile(nodes[0]):
                sitefile = nodes[0]         
        
        # write the sitefile if required    
        if not sitefile:    
            sitefile = '/tmp/pymobatch.' + str(os.getpid()) + '.sitefile'
        
            try:
                fh = open(sitefile, 'w')
            except IOError:
                sys.stderr.write("failed to open temp sitefile for writing\n")
                return []

            for n in nodes:
                fh.write(n + "\n")

            fh.close()

        # write amos commands to a file
        if os.path.isfile(cmd):
            cmdfile = cmd
        else:
            cmdfile = '/tmp/pymobatch.' + str(os.getpid()) + '.mos'
            try:
                fh = open(cmdfile, 'w')
            except IOError:
                sys.stderr.write("failed to open temp command file for writing\n")
                return []

            atoms = cmd.split(';')
            for a in atoms:
                fh.write(a.strip() + "\n")
    
            fh.close()

    
        results = self.__amosbatch_runner(sitefile, cmdfile, opts)
        os.unlink(sitefile)
        os.unlink(cmdfile)
    
        return results
    
        
    """
    amos_location()
    get full path to either the amos or moshell binary
    
    params:
        path to search(optional)
    returns:
        full path to binary | None
    """
    def amos_location(self, path):
        loc = self.__find_possibles(('amos','moshell'), path)
        if not loc:
            raise
        else:
            return loc  
    

    """
    amosbatch_location()
    get full path to either the amosbatch or mobatch binary
    
    params:
        path to search(optional)
    returns:
        full path to binary | None
    """
    def amosbatch_location(self, path):
        loc = self.__find_possibles(('amosbatch','mobatch'), path)
        if not loc:
            raise
        else:
            return loc


    """
    __find_possibles()
    PRIVATE
    return the first binary found from a list of possibles
    
    params:
        a list of binary names
        a search path (optional)
    returns:
        full path to binary | None
    """
    def __find_possibles(self, possibles, path):

        if not possibles or len(possibles) < 1:
            pass
            
        if not path:
            for p in possibles:
                target = self.__which(p)
                if target:
                    return target
        else:
            for p in possibles:
                target = path + "/" + p
                if os.path.isfile(target) and os.access(fpath, os.X_OK):
                    return target
                    
        return None
        
        
    """
    __which()
    PRIVATE
    duplicates function of unix 'which' command to find a program in the path
    
    params:
        a program name
    returns:
        full path to program | None
    """     
    def __which(self, program):
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
    __parse_kwargs()
    PRIVATE
    parse any amos options that were passed in, and filter out invalid options.
    See Ericsson Advanced Moshell Scripting user guide for variable information.

    params:
        a dict
    returns:
        a dict
    """
    def __parse_kwargs(self, kwargs):
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
            'logdir',   # special case. see ericsson documentation
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
            'xmlmomlist', )
            
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
    PRIVATE
    run a moshell/amos command subprocess against a specific node

    params:
        1. a node name or ipaddress
        2. a command string
        3. an option dict (optional)
    returns:
        A tuple. two elements.
        (return-code(0=ok, 1=fail), text-results)
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
        script.append("'" + cmd + "'")
        child = subprocess.Popen(script,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE )
        output, errors = child.communicate()
        if child.returncode or errors:
            return (1, errors)

        return (0, output)


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
        script = [mobatchbin]
        script.append('-p')
        script.append(str(parallel))

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
        if errors:
            sys.stderr.write(errors)
            return []

        # find results of all the logfiles
        for line in output.splitlines():
            match = re.match(r'Logfiles stored in\s+(.+)', line)
            if match:
                return self.__amosbatch_result_parser(match.group(1))


        sys.stderr.write("could not find amosbatch result path\n")
        return []


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
            sys.stderr.write('amosbatch results text file not found in ' + path)
            return []

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

                results.append( (node, 0, log) )

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


