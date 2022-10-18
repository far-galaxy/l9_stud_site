import requests
from bs4 import BeautifulSoup
from ast import literal_eval
import time
import datetime

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
	
def connect(groupId, week):
	site = requests.get(f'https://ssau.ru/rasp?groupId={groupId}&selectedWeek={week}')
	contents = site.text.replace("\n", " ")	
	
	soup = BeautifulSoup(contents, 'html.parser')
	return soup
	
def getGroupInfo(groupId):
	soup = connect(groupId, 1)
	
	group_spec_soup = soup.find("div", {"class": "body-text info-block__description"}) 
	group_spec = group_spec_soup.find("div").contents[0].text[1:]
	
	group_name_soup = soup.find("h2", {"class": "h2-text info-block__title"}) 
	group_name = group_name_soup.text[1:5]
	
	info = {'groupId' : groupId, 'groupNumber' : group_name, 'specName' : group_spec}
	
	return info

lesson_types = ('lect','lab','pract','other')
teacher_columns = ('surname','name','midname','teacherId')
	
def parseWeek(groupId, week):
	
	soup = connect(groupId, week)
		
	dates_soup = soup.find_all("div", {"class": "schedule__head-date"})
	dates = []
	for date in dates_soup:
		date = datetime.datetime.strptime(date.contents[0].text,' %d.%m.%Y').date()
		dates.append(date)
		
	blocks = soup.find("div", {"class": "schedule__items"})
	
	blocks = [item for item in blocks if "schedule__head" not in item.attrs["class"]]
	
	numInDay = 0
	weekday = 0
	times = []
	shedule = []
	week = []
	teachers = []
	for block in blocks:
		if block.attrs['class'] == ['schedule__time']:
			begin = datetime.datetime.strptime(block.contents[0].text,' %H:%M ').time()
			end = datetime.datetime.strptime(block.contents[1].text,' %H:%M ').time()
			times.append((begin, end))	
			numInDay += 1
			weekday = 0
			
			if numInDay != 1:
				#shedule.append(week)
				week = []
		else:
			begin_dt = datetime.datetime.combine(dates[weekday], begin)
			end_dt = datetime.datetime.combine(dates[weekday], end)
			
			sub_pairs = block.find_all("div", {"class": "schedule__lesson"})
			
			pair = []
			for sub_pair in sub_pairs:
				if sub_pair != []:
					name = sub_pair.select_one('div.schedule__discipline')	
					lesson_type = lesson_types[int(name['class'][-1][-1]) - 1]
					name = name.text
					
					place = sub_pair.select_one('div.schedule__place').text
					place = place if place.lower().find("on") == -1 else "ONLINE"
					place = place if place != "" else None
					
					teacher = sub_pair.select_one('.schedule__teacher a')
					teacherId = teacher['href'][14:] if teacher != None else None
					if teacher != None:
						teacher_name = teacher.text[:-4]
						t_info = findInRasp(teacher_name)['text'].split()
						t_info.append(teacherId)
						teachers.append(dict(zip(teacher_columns, t_info)))
											
					groups = sub_pair.select_one('div.schedule__groups').text
					groups = groups if groups.find('группы') != -1 else ""
					
					comment = sub_pair.select_one('div.schedule__comment').text
					
					full_name = f'{name} {groups} {comment}'		
					
					lesson = {
						'numInDay' : numInDay,
						'type' : lesson_type,
						'name' : full_name,
						'groupId' : groupId,
						'begin' : begin_dt,
						'end' : end_dt,
						'teacherId' : teacherId,
						'place' : place}

					shedule.append(lesson)
					
			weekday += 1
		
	shedule = sorted(shedule, key=lambda d: d['begin'])	
	return shedule, teachers

if __name__ == "__main__":	
	import sql
	lessons, teachers = parseWeek(530996168,8)
	l9lk = sql.L9LK(open("pass.txt").read())
	sh = sql.Shedule_DB(l9lk)
	
	g = getGroupInfo(530996168)
	l9lk.db.insert(sql.Shedule_DB.groups_table, g)
	
	for t in teachers:
		l9lk.db.insert(sql.Shedule_DB.teachers_table, t)	
		
	for l in lessons:	
		l9lk.db.insert(sql.Shedule_DB.lessons_table, l)