#!/usr/bin/env python
import subprocess, sys, getopt





def _run(argv):

	

	try:

		opts, args = getopt.getopt(argv, 'j:n:')

	except getopt.GetoptError:

		print 'Wrong command line args'
		exit(2)

	optDict = dict(opts)

	DEFAULT_TRIALS, DEFAULT_JUMP_LIMIT = 5, 100

	NUM_TRIALS = int(optDict['-n']) if '-n' in optDict else DEFAULT_TRIALS

	JUMP_LIMIT = int(optDict['-j']) if '-j' in optDict else DEFAULT_JUMP_LIMIT

	for trialNum in xrange(NUM_TRIALS):

		try:
			subprocess.check_call(['./wikicrawl.py', '-n', str(JUMP_LIMIT)])

			print '\n' * 3

		except OSError as e:

			print "wikicrawl.py does not exist autorun.py's directory"
			exit(127)

		except subprocess.CalledProcessError as e:

			print 'wikicrawl.py experienced an error'
			exit(1)


				


_run(sys.argv[1:])


