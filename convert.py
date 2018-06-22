#!/usr/bin/env python

import pandas as pd
import json
import sys
import glob
import os

def read_json(filename):

    with open(filename, encoding='utf8') as f:
        data = json.load(f)

    keys  = [ 'id', 'title', 'date', 'address', 'email', 'page', 'phone', 'details', 'privacy', 'media', 'map_url' ]
    events = [ { k: d[k] for k in keys } for d in data ]

    for e, d in zip(events, data):
        e['details'] = ' '.join(d['details'].split())
        e['tags'] = ', '.join(d['tags'])

    frame = pd.DataFrame.from_dict(events)
    hosts = pd.io.json.json_normalize(data, 
            record_path='hosts', meta=['id'], meta_prefix='event_')

    return frame, hosts

def _extra_text(l):
    try:
        return ' \ '.join(l)
    except TypeError:
        return l

def read_hosts(filename):

    data = pd.read_json(filename, dtype=object)
    columns = [ 'id', 'url', 'email', 'phone', 'story', 'portraitUrl', 'extra' ]
    websites = data.websites.apply(pd.Series)
    data.extra = data.extra.apply(_extra_text)
    return pd.concat([data[columns], websites], axis=1)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./convert.py [DIRECTORY]')
        return

    directory = sys.argv[1]
    efiles = glob.glob(os.path.join(directory, 'events*.json'))
    hfiles = glob.glob(os.path.join(directory, 'hosts*.json'))

    event_frames = []
    hosts_frames = []

    for f in efiles:
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

    columns = [ 'id', 'title', 'date', 'address', 'email', 'phone', 'page', 'details', 'tags', 'privacy', 'media', 'map_url' ]
    frame1[columns].to_csv('events.csv', index=False)

    columns = [ 'event_id', 'id', 'url', 'name', 'category',
            'profilePicture' ]
    frame2[columns].to_csv('relation.csv', index=False)

    # Read each host file
    hosts = pd.concat([ read_hosts(f) for f in hfiles ], sort=False)

    # There should not be duplicates here
    hosts = hosts.drop_duplicates(subset=['id'])
    hosts.set_index('id', inplace=True)

    # Use hosts info from events and drop duplicates
    from_events = frame2.drop_duplicates(subset=['id'])
    from_events.set_index('id', inplace=True)

    columns = [ 'name', 'category', 'profilePicture' ]

    # Create new info data frame to add it after to the result
    info = pd.DataFrame(index=hosts.index, columns=columns)
    indexes = info.index

    for index in from_events.index:
        if index in indexes: # Check if index exists in info
            info.loc[index] = from_events.loc[index, columns]

    # Concat info of the hosts from the events
    websites_columns = hosts.columns[3:]
    s_hosts = pd.concat([hosts, info], axis=1)

    columns = [ 'url', 'name', 'email', 'phone', 'category', 
            'profilePicture' ] + list(websites_columns)

    s_hosts[columns].to_csv('hosts.csv')

if __name__ == '__main__':
    main()

