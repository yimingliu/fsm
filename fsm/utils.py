from zlib import adler32

def first_value(l):
    if not l:
        return None
    else:
        return l[0]

def etag_hash(txt):
    return adler32(txt) & 0xffffffff
