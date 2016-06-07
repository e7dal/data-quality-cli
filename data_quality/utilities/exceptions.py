# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


class SourceNotFoundError(Exception):
    
    def __init__(self, msg=None, source=None):
        default_msg = 'The source {0} was not found in \'source_file\''.format(source)
        self.msg = msg or default_msg


class DuplicateDataSourceError(Exception):

    def __init__(self, msg=None, source= None):
        default_msg = 'Different sources with the same path {0} have been found \
                       in \'source_file\''.format(source)
        self.msg = msg or default_msg