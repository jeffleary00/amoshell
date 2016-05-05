# amos
python module for interfacing with Ericsson moshell/amos/mobatch/amosbatch CLI.

# examples
	AMOS/MOSHELL
	------------
	import amos
	rval, results = amos.amos('RBS001', 'lt all; alt')
	if not rval:
		print results
		
	rval, results = amos.amos('ERBS02', 'get security', ip_database=/home/user/ip.db, corba_class=5)


	AMOSBATCH/MOBATCH
	-----------------
	import amos
	results = amos.amosbatch(('RBS001','RBS002','RBS003'), 'lt all; alt')
	for r in results:
		node, rval, payload = r
		if not rval:
			print node + ' results found in file ' + payload
		else:
			print node + ' amos error: ' + payload