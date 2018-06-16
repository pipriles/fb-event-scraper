#!/usr/bin/env python

import requests
import re
import json

from bs4 import BeautifulSoup

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
    resp = s.post(api_url, data=payload)
    data = resp.json()

    hosts = extract_hosts(data)
    place = extract_place(data)

    # extract from html: title, date, start, end, address, phone
    # title -> #seo_h1_tag
    # date  -> #event_time_info ._2ycp
    event_url = '{}events/{}'.format(FB_URL, _id)
    resp = s.get(event_url)
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

def scrape_events(_id):

    s = requests.Session()
    s.headers.update(HEADERS)

    extracted = []
    variables = { 'pageID': _id } 

    api_url = 'https://www.facebook.com/api/graphql/' 
    payload = { 'variables': json.dumps(variables), 'doc_id': 1934177766626784 }

    next_page = True
    while next_page:

        resp = s.post(api_url, data=payload)
        resp.raise_for_status()

        data = resp.json()

        events = deep_get(data, 'data.page.upcoming_events')
        if events is None: break

        edges = events['edges']

        for e in edges:
            extracted.append(deep_get(e, 'node.id'))

        page_info = events['page_info']
        end_cursor = page_info['end_cursor']
        next_page = page_info.get('has_next_page', False)

        variables['count'] = 9
        variables['cursor'] = end_cursor

        payload['variables'] = json.dumps(variables)
        payload['doc_id'] = 1595001790625344 

    return extracted

def extract_place_id(url):

    s = requests.Session()
    s.headers.update(HEADERS)

    resp = requests.get(url)
    html = resp.text

    # I believe we don't have to do this
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.find('head')
    match = re.search(r'fb:\/\/page\/(\d+)', str(head))

    return match.group(1) if match else None

def write_json(filename, data):
    with open(filename, 'w', encoding='utf8') as f:
        json.dump(data, f, indent=4)

def main():

    print('Extracting place id...')
    url = 'https://www.facebook.com/umbrellabarattherock/'
    _id = extract_place_id(url)

    pending_hosts = set((_id,))
    scraped_hosts = set()

    pending_events = set()
    scraped_events = set()

    rotation = 1
    while pending_hosts or pending_events:

        result = []

        print('Extracting events...')
        hosts = tuple(pending_hosts)
        count = len(hosts)
        for host in hosts:
            print('Extracting host:', host, count)
            pending_events |= set(scrape_events(host)) - scraped_events
            pending_hosts.discard(_id)
            scraped_hosts.add(_id)
            count -= 1

        print('Scraping events...')
        events = tuple(pending_events)
        count = len(events)
        for e in events:
            print('Scraping event', e, count)
            data = scrape_event(e)
            result.append(data)
            h_id = [ host['id'] for host in data['hosts'] ]
            pending_hosts |= set(h_id) - scraped_hosts
            pending_events.discard(e)
            scraped_events.add(e)
            count -= 1

        filename = 'results/{}.json'.format(rotation)
        write_json(filename, result)
        # I should probably save state here too...

        rotation += 1

if __name__ == '__main__':
    main()

