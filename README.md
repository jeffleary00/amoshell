# AMOS
python module for interfacing with Ericsson moshell/amos/mobatch/amosbatch CLI.

# EXAMPLES
	
amos/moshell
------------
	import amos
	rval, results = amos.amos('RBS001', 'lt all; alt')
	if not rval:
		print results
		
	rval, results = amos.amos('ERBS02', 'get security', ip_database=/home/user/ip.db, corba_class=5)


amosbatch/mobatch
-----------------
	import amos
	results = amos.amosbatch(('RBS001','RBS002','RBS003'), 'lt all; alt')
	for r in results:
		node, rval, payload = r
		if not rval:
			print node + ' results found in file ' + payload
		else:
			print node + ' amos error: ' + payload
			
#API

amos(node-name, command-string, [**kwargs])
-----------------
kwargs are any variable_name=value options that can be passed to amos.
See Ericsson Advanced Moshell Scripting Guide for more details.
  
returns: a tuple (result(0 ok|1 fail), stdout text)
  
  
amosbatch((list-or-tuple of node names), command-string, [**kwargs])
-----------------  
returns: list of result objects (node-name, return-code(0|1), payload)
in the case of a success, the payload contains the path to the logfile
containing the output. otherwise, payload will probably contain the error
message.
  
  