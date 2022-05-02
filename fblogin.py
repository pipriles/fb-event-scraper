#!/usr/bin/env python

import requests as rq
import re
import util
import time
import pickle

from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException

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

def restore_cookies():
    try:
        with open('./cookies.pickle', 'rb') as fp:
            return pickle.load(fp)
    except FileNotFoundError:
        return

def save_cookies(cookies):
    try:
        with open('./cookies.pickle', 'wb') as fp:
            return pickle.dump(cookies, fp)
    except FileNotFoundError:
        return

def start_login_flow(email, password):

    cookies = restore_cookies()

    if cookies:
        return cookies

    driver = webdriver.Remote('http://127.0.0.1:9515')
    driver.get(FB_URL)

    elem = driver.find_element_by_css_selector('#m_login_email')
    elem.send_keys(email)

    elem = driver.find_element_by_css_selector('#m_login_password')
    elem.send_keys(password)

    elem = driver.find_element_by_css_selector('button[name="login"]')
    elem.click()

    while True:
        try:
            if driver.get_cookie('c_user'): break
            time.sleep(.5)
        except InvalidSessionIdException as e:
            break

    cookies = driver.get_cookies()
    save_cookies(cookies)

    return cookies

def login(email, password):

    cookies = start_login_flow(email, password)

    s = FbSession()
    s.headers.update(HEADERS)

    for ck in cookies:
        s.cookies.set(ck['name'], ck['value'])

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

