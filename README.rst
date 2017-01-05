AMOSHELL
=============
Python convenience class to interface to Ericsson's amos/moshell commands


Install
=======
::

    pip install amoshell


Synopsis
========
::

    import amoshell
    mo = amoshell.Amos()
    rval, out, err = mo.moshell('RBS003', 'lt all; alt')
    if rval:
        print err
    else:
        print out


API
===
- Amos(*kwargs*)
    - *bin_path*: keyword-arg to set a non-standard path where the moshell binaries may be installed (optional).
    - *parallel*: keyword-arg to set max number of parallel sessions that mobatch may run (defaults to 10).
    
- Amos.moshell(*name, command, kwargs*)

    Run a moshell command on a node.

    - *name*: recognized node name or node ip address.
    - *command*: command string. multiple commands are delimited with semicolon.
    - *kwargs*: any valid options that are normally set with the '-v' on the moshell command line can be entered here. See Ericsson AMOS user guide for more.

    Return value is a tuple, containing:
        - *exit code*: 0 = ok, non-zero = a failure.
        - *stdout text*:
        - *stderr text*:
    
- Amos.mobatch(*nodes, command, kwargs*)

    Run mobatch commands against many nodes simultaneously.
    
    - *nodes*: a list of node names (or ip addresses), or a string pointing to an existing sitefile.
    - *command*: command string, or a string identifying the path to an existing moshell command file.
    - *kwargs*: any valid options that are normally set with the '-v' on the moshell command line can be entered here. See Ericsson AMOS user guide for more.

    Return value is a list of tuples. Each 3 element tuple contains:
        - *node name*: node this tuple's info relates to.
        - *exit code*: 0 = ok, non-zero = a failure.
        - *path to log*: path to the file containing the moshell results for this node.

Examples
========
::

    import amoshell
    mo = amoshell.Amos()
    
    # moshell example
    rval, out, err = mo.moshell('RBS003', 'lt all; alt')
    
    # mobatch example
    results = mo.mobatch(['ERBS001', 'ERBS002'], 'lt all; get security', 
                                                    ip_database=/tmp/ipdb.dat,
                                                    corba_class=5 )
    for r in results:
        node, rval, logfile = r
        if not rval:
            print "node %s results found in log %s" % (node, logfile)      


Known Issues
============
*Node Passwords*: Some commands in moshell require a password. This tool is not
designed to have an interactive shell, and a password request will cause this
to hang indefinitely.

To prevent this, you should use a custom ip_database file containing nodes and their passwords.
The file is then referenced with the "ip_database" optional arg.

::

    Amos.moshell(node, command, ip_database='/path/to/file')
    

See Ericsson documentation for more information about these ip_database files.


To Do
=====

  
Author
======
Jeff Leary (sillymonkeysoftware -at- gmail -dot- com)

