import os
import sys
import base64
from itertools import izip, cycle

sys.path.append(os.path.abspath(__file__))

# Key should be in `key` file
with open('key', 'r') as keyfile:
    KEY = keyfile.read()
    

def encrypt(data):
    """
    Encrypts the `data` string using and XOR operation and
    returns the result encoded using base64.
    
    :param data: String to be encrypted
    """
    
    encrypted = _do_xor(data)

    return base64.b64encode(encrypted)
    
def decrypt(data):
    """
    Decrypts the `data` string using and XOR after decoding 
    it using base64. The `data` string should have been encrypted
    with the `encrypt` function in this module.
    
    :param data: String to be decrypted
    """

    decrypted = base64.b64decode(data)
    
    return _do_xor(decrypted)
    
def _do_xor(data):
    """
    Performs a XOR operation between `data` and `KEY`
    strings.
    Returns the encoded result.
    
    :param data: String to be encoded
    """
    
    # Recipe for xoring two strings. 
    xored = ''.join(chr(ord(x) ^ ord(y)) for (x,y) in izip(data, cycle(KEY)))

    return xored