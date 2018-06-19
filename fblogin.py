#!/usr/bin/env python

import requests as rq
import re

FB_URL = 'https://m.facebook.com/login.php'
HEADERS = { 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', 'accept-language': 'en' }

DTSG = re.compile(r'name\=\\?\"fb_dtsg\\?\"\s+value\=\\?\"([^\\\"]+)\\?\"')

class FbSession(rq.Session):

    def __init__(self, fb_dtsg=None):
        self.fb_dtsg = fb_dtsg
        super().__init__()

    def post(self, url, data=None, json=None, **kwargs):
        if self.fb_dtsg: 
            data['fb_dtsg'] = self.fb_dtsg
        resp = super().post(url, data, json, **kwargs)
        return resp

def login(email, password):

    payload = { 'email': email, 'pass': password }
    s = FbSession()
    s.headers.update(HEADERS)
    s.post(FB_URL, data=payload)

    if not s.cookies.get('c_user'):
        return None

    home = 'https://m.facebook.com/me'
    resp = s.get(home)
    html = resp.text
    s.fb_dtsg = extract_fb_dtsg(html)
    return s

# Utility function
def extract_fb_dtsg(html):

    match = DTSG.search(html)
    return match.group(1) if match else None

def main():
    pass

if __name__ == '__main__':
    main()

