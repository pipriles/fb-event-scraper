#!/usr/bin/env python

import pandas as pd
import json
import sys

def read_json(filename):

    with open(filename, encoding='utf8') as f:
        data = json.load(f)

    keys  = [ 'id', 'title', 'date', 'address', 'email', 'page', 'phone' ]
    events = [ { k: d[k] for k in keys } for d in data ]

    frame = pd.DataFrame.from_dict(events)
    hosts = pd.io.json.json_normalize(data, 
            record_path='hosts', meta=['id'], meta_prefix='event_')

    return frame, hosts

def main():

    if len(sys.argv) < 2:
        print('Usage: ./convert.py [FILANAME] [FILENAME]...')
        return

    files = sys.argv[1:]

    event_frames = []
    hosts_frames = []

    for f in files:
        events, hosts = read_json(f) 

        keys = list(hosts.columns)
        if keys: keys[5], keys[0] = keys[0], keys[5]

        hosts = hosts[keys]
        event_frames.append(events)
        hosts_frames.append(hosts)
    
    frame1 = pd.concat(event_frames)
    frame1 = frame1.drop_duplicates(subset=['id'])

    frame2 = pd.concat(hosts_frames)
    frame2 = frame2.drop_duplicates(subset=['id', 'event_id'])

    frame1.to_csv('events.csv')
    frame2.to_csv('hosts.csv')


if __name__ == '__main__':
    main()
