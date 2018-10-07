#!/usr/bin/env python3

# sudo apt-get install python3-pip
# sudo pip3 install reverse_geocoder

# I have to add random change user agent
# And maybe a way rotate ip
# Find out why script freezes
# - Maybe a facebook ban
# I have to extract image src and video [X]
# Extract event status [X]
# And extract directions page [X]

import location
import requests
import re
import json
import urllib
import fblogin as fb
import util
import getpass
import os

from bs4 import BeautifulSoup

E_OK = 0
E_ERR = 1
SEPARATOR = ';'

# user specific configuration
AUTH_EMAIL = 'MYEMAIL@MYDOMAIN.COM'
EXPAND_HOSTS = False
HOST_LIST = [ 'https://www.facebook.com/moussetofficial', \
              'https://www.facebook.com/moullinex', \
              'https://www.facebook.com/xinobimusic', \
              'https://www.facebook.com/pg/claptone.official', \
              'https://www.facebook.com/realblackcoffee', \
              'https://www.facebook.com/drpackeredits', \
              'https://www.facebook.com/MastersAtWorkOfficial', \
              'https://www.facebook.com/armandvanhelden', \
              'https://www.facebook.com/cassiusofficial/', \
              'https://www.facebook.com/fennecandwolf', \
              'https://www.facebook.com/DimitriFromParisOfficial', \
              'https://www.facebook.com/aeroplanemusiclove', \
              'https://www.facebook.com/disclosureuk', \
              'https://www.facebook.com/Nicolas-Jaar-15727540611', \
              'https://www.facebook.com/tensnake', \
            ]

FB_URL = 'https://www.facebook.com/'
API_URL = 'https://www.facebook.com/api/graphql/'
TIMEOUT = 5
HEADERS = { 
    'accept-language': 'en', 
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

@util.safe_mode
def scrape_event(url, session=requests.Session()):

    session.headers.update(HEADERS)
    _id = event_id(url)

    payload = { 
        'variables': '{{"eventID": {}}}'.format(_id), 
        'doc_id': 1634531006589990 
    }

    resp = session.post(API_URL, data=payload, timeout=TIMEOUT)

    if resp.status_code != 200: 
        return None

    data = resp.json()
    hosts = extract_hosts(data)
    place = extract_place(data)

    # extract from html: title, date, start, end, address, phone
    # title -> #seo_h1_tag
    # date  -> #event_time_info ._2ycp
    event_url = '{}events/{}'.format(FB_URL, _id)
    resp = session.get(event_url, timeout=TIMEOUT)
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')

    # Title
    ttag = soup.find(id='seo_h1_tag')
    title = ttag.get_text().strip() if ttag else ''
    #print(title)

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
    #print(date)

    # Address
    atag = summary_soup.select_one('li._3xd0 div._5xhp')
    addr = atag.get_text().strip() if atag else None
    #print(addr)

    # Venue
    vtag = summary_soup.select('li._3xd0 div._4bl9 > div > *')
    vtag = [ t for t in vtag if not 'ptm' in t.get('class', '') ]
    desc = ' '.join([ t.get_text() for t in vtag ])

    # Email
    match = MAIL_REGEX.search(desc)
    email = match.group() if match else None
    desc = MAIL_REGEX.sub('', desc)
    #print(email)

    # Website
    match = URL_REGEX.search(desc)
    page = match.group() if match else None
    desc = URL_REGEX.sub('', desc)
    #print(page)

    # Phone
    desc = re.sub(r'[^\+\d]', '', desc)
    match = re.search(r'\+?\d{4,}', desc)
    phone = match.group() if match else None
    #print(phone)

    # Extract tags
    scripts = soup('script')
    keyword_regex = re.compile(r'\{\s*name\:\s*\"([^\"]*)\"\s*\,\s*token')
    for script in scripts:
        text = script.get_text()
        match = keyword_regex.findall(text)
        if match: break
    tags = match

    # Request details
    payload['doc_id'] = 1640160956043533
    details = None

    resp = session.post(API_URL, data=payload, timeout=TIMEOUT)
    if resp.status_code == 200: 
        details = deep_get(resp.json(), 'data.event.details.text')

    # Map Url
    map_url = None
    CC = None
    map_anchor = summary_soup.find("a", class_='_42ft')
    if map_anchor: 
        map_url = map_anchor["href"]
        map_url = urllib.parse.unquote(map_url)
        match = re.search(r'u\=(.+)', map_url)
        if match:
            map_url = match.group(1)
            CC = location.country_location(map_url) 
            
        
    #Extract video
    media = None
    match = re.search(r'"hd_src":"([^"]*)"', html)
    media = match.group(1).replace('\\','') if match else media

    # Extract img
    if media is None:
        images = soup.select("#event_header_primary img")
        if images: media = images[0]["src"]

    # Privacy
    privacy = 'Private'
    spans = soup.select("span[data-testid='event_permalink_privacy']")
    if spans: privacy = spans[0].get_text()

    # I should probably change this to use only dict...
    keys = [ 'id', 'url', 'name', 'category', 'profilePicture' ]
    hosts = [ dict_by_keys(d, keys) for d in hosts ]

    keys = [ 'id', 'title', 'date', 'address', 'email', 'page', 'phone', 'hosts', 'details', 'tags', 'media', 'privacy', 'map_url', "CC" ]
    data = dict_by_keys([ _id, title,  date, addr, email, page, phone, hosts, details, tags, media, privacy, map_url, CC ], keys)

    return data

@util.safe_mode
def scrape_host(_id, session=requests.Session()):

    session.headers.update(HEADERS)

    url = 'https://www.facebook.com/{}/'.format(_id)
    result = { 'id': _id, 'url': url, 'events': [] }
    variables = { 'pageID': _id } 

    payload = { 'variables': json.dumps(variables), 
        'doc_id': 1934177766626784 }

    next_page = True
    while next_page:

        resp = session.post(API_URL, data=payload, timeout=TIMEOUT)
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
    info = scrape_host_about(_id, session)
    result.update(info)

    return result

def _extract_about(container, session=requests.Session()):

    info = None
    uregex = re.compile(r'u\=([^&]+)\&')
    pregex = re.compile(r'Call (.+)')

    websites = set()
    elems = container.select('._4bl9')

    default = { 
        'websites': [], 
        'email': None, 
        'phone': None, 
        'extra': [],
        'story': None
    }

    if elems:
        info = default
        info['story'] = extract_history(container, session)

    for e in elems:
        # Get anchor tags inside ._4bl9 class tags
        anchor = e.find('a')
        if anchor:
            href = anchor['href']

            # Find emails
            match = MAIL_REGEX.search(href)
            if match:
                info['email'] = match.group()
                continue

            # Find Websites
            match = uregex.search(href)
            if match: 
                url = match.group(1)
                url = urllib.parse.unquote(url)
                url = url.lower()
                websites.add(url)
                continue

        text  = e.get_text(' | ', strip=True)
        match = pregex.match(text)

        # Match Phone Number
        if match:
            info['phone'] = match.group(1)
            continue

        info['websites'] = list(websites)
        info['extra'].append(text)

    return info

def scrape_host_about(_id, session=requests.Session()):
    
    session.headers.update(HEADERS)
    extracted = {}

    url = 'https://www.facebook.com/pg/{}/about/'.format(_id)
    resp = session.get(url, timeout=TIMEOUT)

    if resp.status_code != 200:
        return extracted
    
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.find(id='content_container')

    if container:
        extracted = _extract_about(container)

    if not extracted:
        extracted = {}

        codes = soup.select('code')
        for code in codes:
            # Code string should be a comment
            inner = code.string
            inner = inner if inner else ''
            comment = BeautifulSoup(inner, 'html.parser')
            about = _extract_about(comment, session)
            if about: 
                extracted = about
                break

    # Extract extra data
    portrait_video_url = scrape_host_video(html, session)
    if portrait_video_url:
        extracted['portraitUrl'] = portrait_video_url
    else:
        extracted['portraitUrl'] = extract_portrait(html)

    return extracted

# Format string instead of concatenate
# And use urljoin to safe concatenate url
# Use resp.json if you can
def scrape_host_video(html, session=requests.Session()):
    video_url= None
    data = {'__a':'1'}
    url = 'https://www.facebook.com/pages/profile/cover_video_data/?video_id='
    match = re.search(r'videoID:"([0-9][^"]*)',html)
    if match:
        video_id = match.group(1)
        url = url + video_id
        response = session.post(url, data)
        match = re.search(r'"hd_src":"([^"]*)', response.text)
        if match:
            video_url = match.group(1)
            video_url = video_url.replace('\\','')
    return video_url

def extract_history(container, session=requests.Session()):
    story_link = None
    story_achor = container.select_one("#story-card a");
    if story_achor: 
        story_href = story_achor['href']
        json = session.get("https://www.facebook.com"+story_href+"&__a=1")
        story_link = re.search(r'"permalinkURI":"([^"]+)', json.text)
        if story_link: story_link = "https://www.facebook.com" + story_link.group(1).replace('\\','')
    return story_link

def extract_portrait(html):
    match = re.search(r'original:[^"]*"(https?[^"]*)',html)
    return match.group(1) if match else None

def extract_place_id(url, session=requests.Session()):

    session.headers.update(HEADERS)

    resp = session.get(url, timeout=TIMEOUT)
    html = resp.text

    # I believe we don't have to do this
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.find('head')
    match = re.search(r'fb:\/\/page\/(\d+)', str(head))

    return match.group(1) if match else None

def write_json(filename, data):
    if not data: return
    with open(filename, 'w', encoding='utf8') as f:
        json.dump(data, f, indent=4)

class EventSpider:

    def __init__(self, pending_host=[], 
            pending_events=[], fb_s=requests.Session(), scrape_tag='DEFAULT_TAG'):

        self.pending_hosts = set(pending_host)
        self.pending_events = set(pending_events)

        self.scraped_hosts = set()
        self.scraped_events = set()

        self.rotation = 1
        self.r_events = []
        self.r_hosts = []

        self.fb_s = fb_s
        self.fb_s.headers.update(HEADERS)

        self.scrape_tag = scrape_tag

    def scrape_pendings(self, limit=50):

        self.r_events = []
        self.r_hosts = []

        print('Extracting events...')
        hosts = tuple(self.pending_hosts)
        count = len(hosts)
        for host in hosts:
            print('Extracting host:', host, count)
            data = scrape_host(host, self.fb_s)
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
            data = scrape_event(e, self.fb_s)
            hosts_id = []

            if data:
                self.r_events.append(data)
                if EXPAND_HOSTS: # get new hosts recursively
                    hosts_id = [ host['id'] for host in data.get('hosts', []) ]
                else: # or stick to events at the host we are at
                    hosts_id = hosts

            self.pending_hosts |= set(hosts_id) - self.scraped_hosts
            self.pending_events.discard(e)
            self.scraped_events.add(e)
            count -= 1

            if len(events) - count >= limit:
                break
            
    def expand_search(self):

        self.rotation = 1
        keep = True

        efile = 'results/events_{}.json'
        hfile = 'results/hosts_{}.json'

        while keep and \
            ( self.pending_hosts or \
                self.pending_events ): # Sad face

            try:
                self.scrape_pendings()
            except Exception as e:
                raise(e)
                # keep = False
            except KeyboardInterrupt:
                keep = False
            finally:
                filename1 = efile.format(self.scrape_tag)
                filename2 = hfile.format(self.scrape_tag)
                write_json(filename1, self.r_events)
                write_json(filename2, self.r_hosts)
                self.rotation += 1
                # I should probably save state here too...

        return self.r_events

# Move to fb module
def login_flow():

    auth = AUTH_EMAIL, \
            getpass.getpass('Can i haz pass plz?\n')
    fb_s = fb.login(*auth)
    if fb_s is None:
        print('Login fail!')
        exit (E_ERR)
    print('Success!')
    return fb_s

def render_result( json_list, csv = False ):

    # process and present
    json_list.sort(key=lambda k: k['date'], reverse=False)
    print ('')
    print ('Sorted list of events')
    print ('')
    print
    for json_entry in json_list:
        # format is from ... to, but we just want the initial date
        mydate = json_entry['date'].split(' ')[0]
        ev_title, ev_host, ev_address, ev_link, ev_date = extract_fields (json_entry)
        if not csv:
            print ('-------------------------------------------------------------------------------------')
            print ('Title:    ' , ev_title)
            print ('Host:     ' , ev_host)
            print ('Address:  ' , ev_address)
            print ('Link:     ' , ev_link)
            print ('Date:     ' , ev_date)
            print ('')
        else:
            print (ev_title,   SEPARATOR, \
               ev_host,    SEPARATOR, \
               ev_address, SEPARATOR, \
               ev_link,    SEPARATOR, \
               ev_date )

def extract_fields ( json_entry ):

    # extract fields handling cases where they are not present
    try:
        ev_title   = json_entry['title']
    except Exception as e:
        ev_title   = ''

    try:
        ev_host    = json_entry['hosts'][0]['name']
    except Exception as e:
        ev_host    = ''

    try:
        ev_address = json_entry['address']
    except Exception as e:
        ev_address = ''

    try:
        ev_link    = json_entry['hosts'][0]['url']
    except Exception as e:
        ev_link    = ''

    try:
        ev_date    = json_entry['date'].split(' ')[0]
    except Exception as e:
        ev_date    = ''

    return ev_title, ev_host, ev_address, ev_link, ev_date

def main():

    fb_s = login_flow()
    json_list = []

    # get json results
    for url in HOST_LIST:
        print('Extracting place id...')
        print (url)
        host_name = os.path.basename(url)
        _id = extract_place_id(url, fb_s)
        spider = EventSpider(pending_host=(_id,), scrape_tag=host_name)
        json_list = json_list + spider.expand_search()

    # resulting output on screen friendly version
    render_result( json_list, False )

    # resulting output on CSV format
    render_result( json_list, True )

if __name__ == '__main__':
    main()

