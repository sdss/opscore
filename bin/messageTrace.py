#!/usr/bin/env python
"""
Command line tool for tracing how a reply message is handled.

Refer to https://trac.sdss3.org/wiki/Ops/Core for details on the message parsing
and validation process. Refer to https://trac.sdss3.org/wiki/Ops/KeysDictionary
for examples of using this tool.
"""

# Created 29-Oct-2010 by David Kirkby (dkirkby@uci.edu)

from opscore.protocols import parser,keys,types

replyParser = parser.ReplyParser()

# disable compound value wrapping (eg, PVTs)
types.CompoundValueType.WrapEnable = False

print("""\
Enter a reply message to trace how it is handled by the core parsing and validation
code. Validation is based on the current dictionaries in the actorkeys package.
Use ^C to quit this program.""")

try:
    while True:
        line = input('> ')
        if line.strip() == '':
            continue
        print('# Parsing...')
        parsed = replyParser.parse(line)
        print('Header:',parsed.header)
        print('Keywords:')
        for key in parsed.keywords:
            print('  ',key)
        actor = parsed.header.actor
        print('# Loading dictionary for actor "%s"...' % actor)
        kdict = keys.KeysDictionary.load(actor)
        print('loaded dictionary version',kdict.version)
        print('# Validating...')
        for keyword in parsed.keywords:
            keytag = '%s.%s' % (actor,keyword.name.lower())
            try:
                key = kdict[keyword.name]
                if key.consume(keyword):
                    print('found valid key',keyword)
                else:
                    print('*** Invalid keyword values for %s: %s' % (keytag,keyword.values))
            except KeyError:
                print('*** Unknown keyword',keytag)
            except Exception as e:
                print('*** Validation error for',keytag)
                print(str(e))
except KeyboardInterrupt:
    print('\nbye')
