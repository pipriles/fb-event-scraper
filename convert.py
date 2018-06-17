#!/usr/bin/env python

import pandas as pd
import json
import sys
import glob
import os

def read_json(filename):

    with open(filename, encoding='utf8') as f:
        data = json.load(f)

    keys  = [ 'id', 'title', 'date', 'address', 'email', 'page', 'phone' ]
    events = [ { k: d[k] for k in keys } for d in data ]

    frame = pd.DataFrame.from_dict(events)
    hosts = pd.io.json.json_normalize(data, 
            record_path='hosts', meta=['id'], meta_prefix='event_')

    return frame, hosts

def read_hosts(filename):

    data = pd.read_json(filename, dtype=False)
    columns = [ 'id', 'url', 'email', 'phone' ]
    websites = data.websites.apply(pd.Series)
    return pd.concat([data[columns], websites], axis=1)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./convert.py [DIRECTORY]')
        return

    directory = sys.argv[1]
    efiles = glob.glob(os.path.join(directory, 'events_*.json'))
    hfiles = glob.glob(os.path.join(directory, 'hosts_*.json'))

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

    frame1.to_csv('events.csv')
    frame2.to_csv('relation.csv')

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
    s_hosts = pd.concat([hosts, info], axis=1)
    s_hosts.to_csv('hosts.csv')

if __name__ == '__main__':
    main()
