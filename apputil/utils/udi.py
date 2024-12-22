import hashlib

#----------------------------------------------------------------
def gen_udi(metadata_list: list) -> str:
#----------------------------------------------------------------
    _metastr = "_".join(metadata_list)
    _hash = hashlib.blake2s(bytes(_metastr,encoding='utf-8'),digest_size=12)
    return _hash.hexdigest().upper()
