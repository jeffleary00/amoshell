# AMOSHELL

Python module for interfacing with Ericsson moshell/amos/mobatch/amosbatch CLI.

# PLATFORM

Unix-like systems with Ericsson amos/moshell installed. NOT for Windows

# SYNOPSIS
	
moshell
---------
	from amoshell import Amos
	mo = Amos()
	rval, results = mo.moshell('RBS001', 'lt all; alt')
	if not rval:
		print results
		

mobatch
---------
	from amoshell import Amos
	mo = Amos()
	results = mo.mobatch(('RBS001','RBS002','RBS003'), 'lt all; alt')
	for r in results:
		node, rval, payload = r
		if not rval:
			print node + ' results found in file ' + payload
		else:
			print node + ' amos error: ' + payload
			
#API

moshell(node-name, command-string, [**kwargs])
-----------------
- node-name: can be either ip-address, or node name.
- command-string: a string of semicolon separated amos commands. optionally, you can pass a string containing the path to an existing command-file.
- kwargs: are any variable_name=value options that can be passed to amos with the '-v' flag. See Ericsson Advanced Moshell Scripting Guide for more variable details.
  
returns: a tuple (return-code(0 ok|1 fail), stdout text)
  
  
mobatch((list of node names), command-string, [**kwargs])
-----------------  
- node-names: should be a list or tuple of valid node names. optionally, you can pass in a list with a single element containing the path to an existing site-file.
- command-string: a string of semicolon separated amos commands. optionally, you can pass a string containing the path to an existing command-file.
- kwargs: are any variable_name=value options that can be passed to amos with the '-v' flag*. See Ericsson Advanced Moshell Scripting Guide for more variable details.
  *caveat- the 'logdir' option is set with the -o flag, but in this implementation it can be used here in kwargs, and it will be handled appropriately.
 
returns: a list of tuples. Each tuple contains exactly 3 elements.
- node name
- return-code(0 ok|1 fail)
- payload 

If node was successful, payload will contain the path to the amos log containing stdout results. otherwise, payload will contain an error message.

  
#INITITALIZATION

    from amoshell import Amos
    mo = Amos(bin_path='/path/to/binaries', parallel=5)
    
Attributes that can be set when instantiating the Amos object.
- moshellbin: full path to moshell or amos, if not found in normal location
- mobatchbin: see above.
- bin_path: path to search for amos binaries, if not in typical locations.
- parallel: used to set number of concurrent processes for mobatch. See Ericsson documentation for warnings! It is not recommended to set this value above 10 (the default value).


#LIMITATIONS, BUGS, TO-DO

- Needs proper install and test scripts.
- Does not support the -m (multi) flag that some versions of moshell have. Use mobatch for cases where this is required.
- Could use some better exception handling in a few spots.

