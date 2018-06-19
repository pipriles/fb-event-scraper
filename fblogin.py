#!/usr/bin/env python

import requests as rq

FB_URL = 'https://m.facebook.com/login.php'
HEADERS = { 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', 'accept-language': 'en' }

def login(email, password):

    payload = { 'email': email, 'pass': password }
    s = rq.Session()
    s.headers.update(HEADERS)
    resp = s.post(FB_URL, data=payload)
    return s if s.cookies.get('c_user') else None

def main():
    pass

if __name__ == '__main__':
    main()
