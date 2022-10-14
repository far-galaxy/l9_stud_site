import requests
from bs4 import BeautifulSoup
from ast import literal_eval
import time

def findInRasp(req):
	rasp = requests.Session() 
	hed = rasp.get("https://ssau.ru/rasp/")
	soup = BeautifulSoup(hed.text, 'lxml')
	csrf_token = soup.select_one('meta[name="csrf-token"]')['content']
	time.sleep(1)
	rasp.headers['Accept'] = 'application/json'
	rasp.headers['X-CSRF-TOKEN'] = csrf_token
	result = rasp.post("https://ssau.ru/rasp/search", data = {'text':req})
	if result.status_code == 200:
		num = literal_eval(result.text)
	else:
		return None

	if len(num) == 0:
		return None
	else:
		return num[0]
	