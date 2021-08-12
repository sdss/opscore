#!/usr/bin/env python
"""
Encrypts secret configuration data
"""

# Created 9-Apr-2009 by David Kirkby (dkirkby@uci.edu)

from opscore.utility import config

if __name__ == "__main__":

    import getpass
    from Crypto.Hash import MD5 as hasher
    from Crypto.Cipher import AES as cipher

    passphrase = getpass.getpass("Enter a pass phrase: ")
    key = hasher.new(passphrase).digest()
    assert len(key) in [16, 24, 32]
    engine = cipher.new(key, cipher.MODE_ECB)

    while True:
        plaintext = input("Enter text to encrypt or RETURN to quit: ")
        if not plaintext:
            break
        npad = cipher.block_size - (len(plaintext) % cipher.block_size)
        assert npad > 0
        data = plaintext + "\x00" * (npad - 1) + chr(npad)
        assert len(data) % cipher.block_size == 0
        print(config.ConfigOptionParser.bin2hex(engine.encrypt(data)))
