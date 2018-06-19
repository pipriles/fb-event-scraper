#!/usr/bin/env python

import time

def safe_mode(func):
    def wrapper(*args, **kwargs):
        resp = None
        retries = 1 # Number of attempts
        while retries > 0:
            try:
                resp = func(*args, **kwargs)
                retries = 0
            except Exception as e:
                print(e)
                retries -= 1
                time.sleep(3)
        return resp
    return wrapper

