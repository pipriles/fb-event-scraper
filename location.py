#!/usr/bin/env python3
import reverse_geocoder as rg
import requests as rq
import re

#Oswaldo si quieres le cambias este nombre
def country_location(link):
	map_link = "https://places.api.here.com/places/v1/places/lookup?source=sharing&id="
	country_code = None

	#Getting app_id and app_code
	response = rq.get(link)
	if response.ok: 
		match = re.search(r'{"appCode":"([^"]*)","appId":"([^"]*)"',response.text)
		if match:
			auth = "&app_code="+match.group(1)+"&app_id="+match.group(2)

			#Getting map code
			match = re.search(r'mylocation\/([^?]*)',link)
			if match: 
				map_code = match.group(1)
				response = rq.get(map_link+map_code+auth)
				if response.ok:

					#Getting country code
					html = response.text
					match = re.search(r'position":\[([^\]]*)',html)
					if match:
						event_location = eval(match.group(1))
						location = rg.search(event_location)

						if location: 
							location = dict(location[0])
							country_code = location.get("cc")

					else:
						print(html)
				
				else:
					print(response.status_code)
		else:
			print(response.text)
	else:
		print(response.status_code)

	return country_code