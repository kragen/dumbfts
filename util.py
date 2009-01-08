import os

def commit(file_object):
    file_object.flush()
    os.fsync(file_object.fileno())
    file_object.close()
