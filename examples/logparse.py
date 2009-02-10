"""
Processes a TCC logfile as a stream of reply messages

Refer to https://trac.sdss3.org/wiki/Ops/Examples#TCCLogfileParser for details
"""

# Created 17-Dec-2008 by David Kirkby (dkirkby@uci.edu)

import re

import ops.core.utility.astrotime as atime
import ops.core.protocols.parser as parser
import ops.core.protocols.keys as keys
import ops.core.protocols.types as types

def parseTCCLog(stream):
	"""
	Processes a stream TCC logfile lines as reply messages
	"""
	parseEngine = parser.ReplyParser()
	# regexp for a TCC reply as it appears in the telrun log
	fields = re.compile('(0|[1-9][0-9]*) (0|[1-9][0-9]*) ([>iIwW:fF!])(.*)')

	# Declare a callback for the TCCPos keyword
	def tccPosHandler(keyword,reply,mjd):
		# Reconstruct a TAI timestamp from the MJD seconds provided
		timestamp = atime.AstroTime.fromMJD(mjd/86400.,tz=atime.TAI)
		# Special handling of invalid values
		if types.InvalidValue in keyword.values:
			print '%s: Axes halted or positions not available' % timestamp
			return
		# Extract our values, which have been typed according to the TCC keys dictionary as
		# Float(units='deg',invalid='NaN',strFmt='%+07.2f')*3
		az,alt,rot = keyword.values
		# Print our values: %s uses the value type's strFmt.
		print ('%s: Az = %s %s, Alt = %s %s, Rot = %s %s'
			% (timestamp,az,az.units,alt,alt.units,rot,rot.units))
	
	# Build a simple callback dispatch dictionary
	callbacks = {
		'tcc.TCCPos': tccPosHandler
	}

	for line in stream:
		#################################################################################
		## Step 1: Convert a TCC log message to a hub-style reply message
		#################################################################################
		try:
			# Parse an initial ISO timestamp of the form YYYY-MM-DD HH:MM:SS.SSSZ
			# strptime() cannot handle fractional seconds so we add them by hand.
			timestamp = atime.AstroTime.strptime(line[:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=atime.UTC)
			timestamp = timestamp.replace(microsecond=1000*int(line[20:23]))
			# Convert from UTC to TAI MJD seconds
			mjd = timestamp.astimezone(atime.TAI).MJD()*86400
			# Does the text following the timestamp look like a TCC reply of the form %d %d %c ... ?
			matched = fields.match(line[25:])
			if not matched:
				continue
			# Reformat the message to look like it came via the hub
			(commandId,userNum,replyCode,replyText) = matched.groups()
			msg = 'telrun.user%s %s tcc %s%s' % (userNum,commandId,replyCode,replyText)
		except Exception:
			print 'Conversion error on line:',line
			raise
		
		#################################################################################
		## Step 2: Parse the reply message and lookup its actor's dictionary
		#################################################################################
		try:
			parsed = parseEngine.parse(msg)
			# we always have actor=tcc here but, in general, each message can be
			# from a different actor so we need to look up its dictionary now
			actor = parsed.header.actor
			kdict = keys.KeysDictionary.load(actor)
		except parser.ParseError:
			print 'Unable to parse line:',line
			continue
		except keys.KeysDictionaryError:
			print 'Unknown actor:',actor
			continue

		#################################################################################
		## Step 3: Validate each keyword in the message against the actor's dictionary
		#################################################################################
		for keyword in parsed.keywords:
			try:
				key = kdict[keyword.name]
				if not key.consume(keyword):
					print 'Invalid values for keyword:',keyword
				try:
					keytag = '%s.%s' % (actor,keyword.name)
					handler = callbacks[keytag]
					handler(keyword,parsed,mjd)
				except:
					pass
			except KeyError:
				print 'Ignorning unknown %s keyword: %s' % (actor,keyword.name)
			except Exception:
				raise

if __name__ == '__main__':
	import fileinput
	parseTCCLog(fileinput.input())