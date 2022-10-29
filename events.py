import requests
import datetime
from libraries.utils import *
import time

config = loadJSON("config")

last_ddns_call = datetime.datetime(2022,1,1)

if __name__ == "__main__":
	while True:
		now = datetime.datetime.now()
		if now - last_ddns_call > datetime.timedelta(days=1):
			last_ddns_call = now
			page = requests.get(config["ddns"]);
			print(now.isoformat(), page)
		time.sleep(200)
		
