# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import tempfile

def write_string_to_disk(string):
    # get random file
    tf = tempfile.NamedTemporaryFile(mode='w+')

    # write text
    tf.write(string)
    tf.flush()
    # return file descriptor
    return tf
