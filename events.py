#!/usr/bin/env python

# I have to add random change user agent
# And maybe a way rotate ip
# Find out why script freezes
# - Maybe a facebook ban

import requests
import re
import json
import urllib

from bs4 import BeautifulSoup

TIMEOUT = 5
HEADERS = { 
    'accept-language': 'en-US,en;q=0.9', 
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', 
}

MAIL_REGEX = re.compile(r'[\w\_\.\+\-]+@[\w\-]+\.[\w\-\.]+')
URL_REGEX = re.compile(r'[-a-zA-Z0-9@:%_\+.~#?&//=]{2,256}\.[a-z]{2,4}\b(\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?')
FB_URL = "https://www.facebook.com/";

def dict_values(d, keys):
    return [ deep_get(d, k) for k in keys ]

def event_id(url):
    match = re.search(r'events\/(\d+)\/?', url)
    return match.group(1) if match else url

def deep_get(d, path, default=None):
    keys = path.split('.')
    acum = {} if d is None else d
    for k in keys:
        acum = acum.get(k, default)
        if acum is None: break
    return acum

def extract_hosts(data):
    hosts = deep_get(data, 'data.event.hosts.edges')
    keys = [ 'id', 'url', 'name', 'category', 'profilePicture.uri' ]
    result = []
    for x in hosts:
        host = x.get('node', None)
        info = dict_values(host, keys)
        result.append(info)
    return result

def extract_place(data):
    place = deep_get(data, 'data.event.place')
    keys = [ 'id', 'url', 'name', 'category', 'profilePicture.uri' ]
    info = dict_values(place, keys)
    return info

def dict_by_keys(data, keys):
    return { k: v for k, v in zip(keys, data) }

def scrape_event(url):

    s = requests.Session()
    s.headers.update(HEADERS)

    _id = event_id(url)

    api_url = 'https://www.facebook.com/api/graphql/'
    payload = { 
        'variables': '{{"eventID": {}}}'.format(_id), 
        'doc_id': 1634531006589990 
    }

    # resp = requests.post(api_url, data=payload, headers=HEADERS)    
    resp = s.post(api_url, data=payload, timeout=TIMEOUT)

    if resp.status_code != 200: 
        return None

    data = resp.json()
    hosts = extract_hosts(data)
    place = extract_place(data)

    # extract from html: title, date, start, end, address, phone
    # title -> #seo_h1_tag
    # date  -> #event_time_info ._2ycp
    event_url = '{}events/{}'.format(FB_URL, _id)
    resp = s.get(event_url, timeout=TIMEOUT)
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')

    # Title
    ttag = soup.find(id='seo_h1_tag')
    title = ttag.get_text().strip() if ttag else ''
    print(title)

    # Uncomment inside code tag
    # code = soup.select('code')
    # print(len(code))

    dtag = soup.find('code')
    text = str(dtag)
    text = re.sub(r'(?:<!--)|(?:-->)', '', text)
    summary_soup = BeautifulSoup(text, 'html.parser')

    # Date
    dtag = summary_soup.select_one('#event_time_info ._2ycp')
    date = dtag['content'] if dtag else None
    print(date)

    # Address
    atag = summary_soup.select_one('li._3xd0 div._5xhp')
    addr = atag.get_text().strip() if atag else None
    print(addr)

    # Venue
    vtag = summary_soup.select('li._3xd0 div._4bl9 > div > *')
    vtag = [ t for t in vtag if not 'ptm' in t.get('class', '') ]
    desc = ' '.join([ t.get_text() for t in vtag ])

    # Email
    match = MAIL_REGEX.search(desc)
    email = match.group() if match else None
    desc = MAIL_REGEX.sub('', desc)
    print(email)

    # Website
    match = URL_REGEX.search(desc)
    page = match.group() if match else None
    desc = URL_REGEX.sub('', desc)
    print(page)

    # Phone
    desc = re.sub(r'[^\+\d]', '', desc)
    match = re.search(r'\+?\d{4,}', desc)
    phone = match.group() if match else None
    print(phone)

    # I should probably change this to use only dict...
    keys = [ 'id', 'url', 'name', 'category', 'profilePicture' ]
    hosts = [ dict_by_keys(d, keys) for d in hosts ]

    keys = [ 'id', 'title', 'date', 'address', 'email', 'page', 'phone', 'hosts' ]
    data = dict_by_keys([ _id, title,  date, addr, email, page, phone, hosts ], keys)

    return data

def scraped_hosts(_id):

    s = requests.Session()
    s.headers.update(HEADERS)

    url = 'https://www.facebook.com/{}/'.format(_id)
    result = { 'id': _id, 'url': url, 'events': [] }
    variables = { 'pageID': _id } 

    api_url = 'https://www.facebook.com/api/graphql/' 
    payload = { 'variables': json.dumps(variables), 
        'doc_id': 1934177766626784 }

    next_page = True
    while next_page:

        resp = s.post(api_url, data=payload, timeout=TIMEOUT)
        if resp.status_code != 200: 
            break

        data = resp.json()
        events = deep_get(data, 'data.page.upcoming_events')
        if events is None: break

        edges = events['edges']

        for e in edges:
            result['events'].append(deep_get(e, 'node.id'))

        page_info = events['page_info']
        end_cursor = page_info['end_cursor']
        next_page = page_info.get('has_next_page', False)

        variables['count'] = 9
        variables['cursor'] = end_cursor

        payload['variables'] = json.dumps(variables)
        payload['doc_id'] = 1595001790625344

    # Extract extra info from the host url
    info = scrape_host_info(_id)
    result.update(info)

    return result

def scrape_host_info(_id):

    info = {}

    s = requests.Session()
    s.headers.update(HEADERS)

    url = 'https://www.facebook.com/pg/{}/about/'.format(_id)
    resp = s.get(url, timeout=TIMEOUT)

    if resp.status_code != 200:
        return info

    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.find(id='content_container')
    anchors = container.select('._4bl9 a')
    
    uregex = re.compile(r'u\=([^&]+)\&')
    pregex = re.compile(r'Call (.+)')

    websites = set()
    info['websites'] = []
    info['email'] = None
    info['phone'] = None

    # Find emails
    for a in anchors:
        href = a['href']
        match = MAIL_REGEX.search(href)
        if match:
            info['email'] = match.group()
            break

    # Find Websites
    for a in anchors:
        href = a['href']
        match = uregex.search(href)
        if match: 
            url = match.group(1)
            url = urllib.parse.unquote(url)
            url = url.lower()
            websites.add(url)

    info['websites'] = list(websites)

    items = container.select('._4bl9')
    for i in items:
        text = i.get_text()
        match = pregex.match(text)
        if match:
            info['phone'] = match.group(1)
            break

    return info

def extract_place_id(url):

    s = requests.Session()
    s.headers.update(HEADERS)

    resp = requests.get(url, timeout=TIMEOUT)
    html = resp.text

    # I believe we don't have to do this
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.find('head')
    match = re.search(r'fb:\/\/page\/(\d+)', str(head))

    return match.group(1) if match else None

def write_json(filename, data):
    with open(filename, 'w', encoding='utf8') as f:
        json.dump(data, f, indent=4)

class EventSpider:

    def __init__(self, pending_host=[], pending_events=[]):

        self.pending_hosts = set(pending_host)
        self.pending_events = set(pending_events)

        self.scraped_hosts = set()
        self.scraped_events = set()

        self.rotation = 1
        self.r_events = []
        self.r_hosts = []

    def scrape_pendings(self, limit=50):

        self.r_events = []
        self.r_hosts = []

        print('Extracting events...')
        hosts = tuple(self.pending_hosts)
        count = len(hosts)
        for host in hosts:
            print('Extracting host:', host, count)
            data = scraped_hosts(host)
            events = []

            if data:
                self.r_hosts.append(data)
                events = data.get('events', [])

            self.pending_events |= set(events) - self.scraped_events
            self.pending_hosts.discard(host)
            self.scraped_hosts.add(host)
            count -= 1

            if len(host) - count >= limit:
                break

        print('Scraping events...')
        events = tuple(self.pending_events)
        count = len(events)
        for e in events:
            print('Scraping event', e, count)
            data = scrape_event(e)
            hosts_id = []

            if data:
                self.r_events.append(data)
                hosts_id = [ host['id'] for host in data.get('hosts', []) ]

            self.pending_hosts |= set(hosts_id) - self.scraped_hosts
            self.pending_events.discard(e)
            self.scraped_events.add(e)
            count -= 1

            if len(events) - count >= limit:
                break
            
    def expand_search(self):

        self.rotation = 1
        keep = True

        while keep and \
            ( self.pending_hosts or \
                self.pending_events ): # Sad face

            try:
                self.scrape_pendings()
            except Exception as e:
                raise(e)
                keep = False
            finally:
                filename1 = 'results/events_{}.json'.format(self.rotation)
                filename2 = 'results/hosts_{}.json'.format(self.rotation)
                write_json(filename1, self.r_events)
                write_json(filename2, self.r_hosts)
                self.rotation += 1
                # I should probably save state here too...

def main():

    print('Extracting place id...')
    url = 'https://www.facebook.com/umbrellabarattherock/'
    _id = extract_place_id(url)

    spider = EventSpider(pending_host=(_id,))
    spider.expand_search() # Keep searching until the end of the world

if __name__ == '__main__':
    main()

