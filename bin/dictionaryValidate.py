#!/usr/bin/env python
"""
Command line tool for validating dictionaries in the actorkeys package.

Refer to https://trac.sdss3.org/wiki/Ops/KeysDictionary for details.
"""

# Created 29-Oct-2010 by David Kirkby (dkirkby@uci.edu)

import os,sys
import http.client,socket
from opscore.protocols import keys,types

if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] == '--help'):
    print('usage: %s [ <ArchiverHost> | --offline ]' % sys.argv[0])
    sys.exit(-1)

# try to load the server's latest actor info
archiverHost = 'sdss-archiver.apo.nmsu.edu'
if len(sys.argv) > 1:
    archiverHost = sys.argv[1]

actorInfo = { }
if archiverHost != '--offline':
    try:
        server = http.client.HTTPConnection(archiverHost)
        server.request('GET','/static/data/actors.txt')
        response = server.getresponse()
        if response.status != 200:
            print('unable to get actor info from %s (%d,%s)' % (
                archiverHost,response.status,response.reason))
            sys.exit(-2)
        for line in response.read().split('\n'):
            if line.strip() == '' or line[0] == '#':
                continue
            actorname,info = line.split(' ',1)
            if len(info.split()) == 2:
                print(actorname,'has no dictionary')
            else:
                actorInfo[actorname] = info.split()
        server.close()
    except http.client.InvalidURL as e:
        print('Invalid archiver URL::',str(e))
        sys.exit(-2)
    except socket.gaierror as e:
        print('HTTP socket error::',str(e))
        sys.exit(-2)

try:
    # find the directory containing the active dictionary files
    import actorkeys
    keyspath = sys.modules['actorkeys'].__path__[0]
    # loop over the directory contents
    for filename in os.listdir(keyspath):
        (actorname,ext) = os.path.splitext(filename)
        # ignore things that are obviously not dictionary files
        if actorname == '__init__' or ext != '.py':
            continue
        # try to load this dictionary
        try:
            kdict = keys.KeysDictionary.load(actorname)
            # is this dictionary already being used?
            if actorname in actorInfo:
                (major,minor,cksum) = actorInfo[actorname]
                major = int(major)
                minor = int(minor)
                if kdict.version == (major,minor):
                    # test that the checksum has not changed
                    if kdict.checksum != cksum:
                        print('%s %d.%d has changed and needs a version bump' % (
                            actorname,kdict.version[0],kdict.version[1]))
                    else:
                        print('%s %d.%d already in use and unchanged' % (
                            actorname,kdict.version[0],kdict.version[1]))
                else:
                    if major > kdict.version[0] or (
                        major == kdict.version[0] and minor > kdict.version[1]):
                        print('%s %d.%d has invalid version, should be >= %d.%d' % (
                            actorname,kdict.version[0],kdict.version[1],major,minor))
                    else:
                        print('%s %d.%d replaces %d.%d' % (
                            actorname,kdict.version[0],kdict.version[1],major,minor))
            else:
                print('%s %d.%d is new' % (
                    actorname,kdict.version[0],kdict.version[1]))
        except keys.KeysDictionaryError as e:
            print(str(e))
        except types.ValueTypeError as e:
            print(str(e))
except ImportError:
    print("Cannot import 'actorkeys' module. Is your PYTHONPATH correct?")
    sys.exit(-3)
except IndexError:
    print("No path associated with actorkeys module?")
    sys.exit(-4)
except OSError as e:
    print(str(e))
