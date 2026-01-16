# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 23:15:35 2024

@author: yberton
"""

import inspect

def retrieve_name(*args):
    frame = inspect.currentframe().f_back
    local_vars = frame.f_locals.items()
    return [
        [name for name, value in local_vars if value is arg]
        for arg in args
    ]

