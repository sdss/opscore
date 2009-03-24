#!/usr/bin/env python
"""
Implements core functionality of the TUI dispatch model using opscore.protocols.

Refer to https://trac.sdss3.org/wiki/Ops/Examples#TUIMigration for details
"""

# Created 19-Dec-2008 by David Kirkby (dkirkby@uci.edu)

import sys
import traceback
import RO.AddCallback
import opscore.protocols.keys as protoKeys
import opscore.protocols.parser as protoParser
import opscore.utility.astrotime as astrotime

class KeyVarBase(RO.AddCallback.BaseMixin):
	
	def __init__(self,keyName,actor,doPrint=False):
		"""
		Processes data associated with a keyword.
		
		Inputs are:
		- keyName: the name of the keyword associated with this variable (string)
		- actor: the name of the actor issuing this keyword (string)
		- doPrint: controls whether data is printed as set (boolean)
		The value type conversions are retrieved from the actor's dictionary.
		"""
		self.actor = actor
		self.keyName = keyName
		self.doPrint = doPrint
		# lookup this actor's dictionary (or raise protoKeys.KeysDictionaryError)
		kdict = protoKeys.KeysDictionary.load(actor)
		# lookup this keyword's value types in the dictionary (or raise KeyError)
		self._converterList = kdict[keyName].typedValues
		# initialize our callback mixin
		RO.AddCallback.BaseMixin.__init__(self, defCallNow = True)
	
	def __repr__(self):
		return "%s(%r, %r, %s)" % \
			(self.__class__.__name__, self.actor, self.keyName, self._converterList)

	def __str__(self):
		return "%s(%r, %r)" % \
			(self.__class__.__name__, self.actor, self.keyName)

	def set(self,valueList,msgDict=None):
		"""
		Validates a keyword's values against its dictionary key
		"""
		if not self._converterList.consume(valueList):
			sys.stderr.write("%s.set warning: invalid types")

		# print to stderr, if requested
		if self.doPrint:
			sys.stderr.write("%s = %r\n" % (self, valueList))

		# apply callbacks, if any
		self._msgDict = msgDict
		self._valueList = valueList
		self._doCallbacks()
		
	def _doCallbacks(self):
		"""
		Specifies the callback parameters.
		
		Subclasses can override this method to implement more complex isCurrent tracking.
		"""
		self._basicDoCallbacks(self._valueList, isCurrent = True, keyVar = self)

class KeyDispatcherBase(object):

	def __init__(self):
		self.keyVarListDict = { }
		# create a reply message parser
		self.parser = protoParser.ReplyParser()
	
	def add(self,keyVar):
		"""
		Adds a keyword variable to the list of those that this dispatcher handles.
		"""
		keyName = keyVar.keyName.lower()
		dictKey = (keyVar.actor,keyName)
		keyList = self.keyVarListDict.setdefault(dictKey, [])
		keyList.append(keyVar)
	
	def dispatch(self,msgDict):
		"""
		Invokes keyword callbacks based on the supplied message data.
		
		msgDict is a parsed Reply object (opscore.protocols.messages.Reply) whose fields include:
		 - header.program: name of the program that triggered the message (string)
		 - header.commandId: command ID that triggered the message (int) 
		 - header.actor: the actor that generated the message (string)
		 - header.code: the message type code (opscore.protocols.types.Enum)
		 - string: the original unparsed message (string)
		 - keywords: an ordered dictionary of message keywords (opscore.protocols.messages.Keywords)		
		Refer to https://trac.sdss3.org/wiki/Ops/Protocols for details.
		"""
		keyActor = msgDict.header.actor
		for keyword in msgDict.keywords:
			keyName = keyword.name.lower()
			dictKey = (keyActor,keyName)
			keyVarList = self.keyVarListDict.get(dictKey, [])
			for keyVar in keyVarList:
				try:
					keyVar.set(keyword.values,msgDict)
				except:
					traceback.print_exc(file=sys.stderr)
	
	def doRead(self,msgStr):
		"""
		Parses and dispatches a hub message.
		"""
		try:
			parsed = self.parser.parse(msgStr)
		except parser.ParseError, e:
			sys.stderr.write("CouldNotParse; Msg=%r; Text=%r\n" % (msgStr,str(e)))
			return
		self.dispatch(parsed)

###################################################################
## Test drive the classes above with some sample message data
###################################################################		
if __name__ == '__main__':

	rotpos = KeyVarBase('RotPos','tcc',doPrint=True)
	spider = KeyVarBase('SpiderInstAng','tcc',doPrint=False)

	def spiderHandler(valueList,isCurrent,keyVar):
		pos,vel,tai = valueList
		# convert the TAI timestamp to UTC and print as an ISO date string
		timestamp = astrotime.AstroTime.fromMJD(tai/86400.,tz=astrotime.TAI).astimezone(astrotime.UTC)
		print 'spiderHandler: got update at',timestamp.isoformat()
		# print the full parsed reply that this keyword was found in
		print keyVar._msgDict

	spider.addCallback(spiderHandler,callNow=False)

	dispatcher = KeyDispatcherBase()
	dispatcher.add(spider)
	dispatcher.add(rotpos)

	messages = """
.tcc 0 tcc I SpiderInstAng = -25.899354, -0.004992, 4734909045.19000
.tcc 0 tcc W DeadProc="T_AUTOLOUVER"
.tcc 0 tcc I TrackAdvTime=3.51
.tcc 0 tcc I TrackAdvTime=3.55
.tcc 0 tcc I TCCStatus="TTT","NNN"; TCCPos=-31.40,53.07,154.02; AxePos=-31.40,53.07,154.02
.tcc 0 tcc I AxisErrCode="OK","OK","OK"
.tcc 0 tcc I SpiderInstAng = -25.973728, -0.004984, 4734909060.10000
.tcc 0 tcc I RotType="Obj"
.tcc 0 tcc I RotPos = -0.004347, 0.000000, 4734909045.19000
tui.operator 33 tcc I SpiderInstAng = -25.998642, -0.004982, 4734909065.10000
tui.operator 33 tcc : Cmd="show object"
tui.operator 34 tcc > Started; Cmd="offset object -0.0000118,-0.0000124"
tui.operator 34 tcc I MoveItems="NNNYNNNNN"; Moved
tui.operator 34 tcc I ObjOff = -0.000242, 0.000000, 4734909061.17000, 0.003625, 0.000000, 4734909061.17000
tui.operator 34 tcc : 
tui.operator 35 tcc > Started; Cmd="offset rotator -0.0002956"
tui.operator 35 tcc I MoveItems="NNNNNNYNN"; Moved
tui.operator 35 tcc I RotType="Obj"
tui.operator 35 tcc I RotPos = -0.004643, 0.000000, 4734909061.59000
tui.operator 35 tcc : 
"""

	for line in messages.split('\n'):
		if not line.strip(): continue
		dispatcher.doRead(line)
