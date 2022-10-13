from libraries.sql import *
from libraries.utils import *
import datetime
import re
from time import sleep

import logging
logger = logging.getLogger(__name__)


month = ("января", "февраля", "марта", "апреля", "мая", "июня", 
		 "июля", "августа", "сентября", "октября", "ноября", "декабря")

class Bot():
	
	platforms = {"VK":"vkId","TG":"tgId"}
	group_num_format = re.compile('\d{4}')
	
	def __init__(self, db, shedule):
		self.l9lk = db
		self.users_id = {"VK":{}, "TG":{}}
		self.users_db = {}
		self.shedule = shedule
		
	def checkMessage(self, msg):
		
		platform = msg['platform']
		uid = msg['uid']
		text = msg['text']
		name = msg['name']
		
		if uid not in self.users_id[platform]:
			if platform == 'TG':
				l9Id = tg_db.initUser(uid, name)
				self.users_id[platform][uid] = l9Id
		else:
			l9Id = self.users_id[platform][uid]
		
		tag = self.l9lk.db.get(TG_DB.users_table, 
					f"{Bot.platforms[platform]} = {uid}", 
					["pos_tag"])
		
		tag = tag[0][0]
		
		if tag == 'not_started':
			if text != '/start':
				return ['Нажми /start, чтобы начать']
			else:
				self.changeTag(uid, 'started', platform)
				return ['Приветствую тебя!',
						'Я буду напоминать тебе о ближайших парах!',
						'Для начала определимся, откуда ты\n' 
						'Введи свой номер группы в краткой форме (например, 2305)']
			
		elif tag == 'started':
			if Bot.group_num_format.match(text) is None:
				return ['Группа введена неверно!']
			else:
				result = self.l9lk.db.get(
					Shedule_DB.groups_table,
					f'groupNumber = {text}', 
					['groupId','specName']				
				)
				
				if result != []:
					result = result[0]
					self.l9lk.db.insert(
						Shedule_DB.gu_table,
						{'l9Id' : l9Id,
						 'groupId' : result[0]}
					)	
					self.changeTag(uid, 'ready', platform)
					return [f'Поздравляем, твоя группа {text}, направление "{result[1]}", уже есть в моей базе!',
							'❗️ Внимание! Бот работает в тестовом режиме, поэтому возможны сбои в работе\nЕсли бот не отвечает на запросы, не пишите ему больше ничего: автор заметит и как можно скорее исправит ошибку, и бот обязательно вам ответит :)']
				else:
					return ['К сожалению, такой группы в моей базе ещё нет :(']
				
		elif tag == 'ready':
			if text == 'Ближайшая пара':
				return[self.nearLesson(l9Id)]
			elif text == 'Следующая пара':
				return[self.nextLesson(l9Id)]
			elif text == 'Расписание на сегодня':
				return[self.dayShedule(l9Id)]			
			return ['Aй!']
		else:
			return ['Ой!']
		
	def nearLesson(self, l9Id):
		now = datetime.datetime.now()
		lessonId, date = self.shedule.nearLesson(l9Id, now)
		if lessonId != None:
			lesson = self.shedule.getLesson(lessonId)
			
			if date.date() > now.date():
				text = f'❗️ Сегодня пар нет\nБлижайшая пара '
				if date.date() - now.date() == datetime.timedelta(days=1):
					text += 'завтра:\n\n'
				else:
					text +=  f'{date.day} {month[date.month-1]}:\n\n'
				
			elif date.time() > now.time():
				text = 'Ближайшая пара сегодня:\n\n'	
			else: 
				text = 'Текущая пара:\n\n'	
				
			text += self.strLesson(lesson)
			
		else:
			text = 'Ой! Занятий не обнаружено!'

		return text
	
	def nextLesson(self, l9Id):
		now = datetime.datetime.now()
		lessonId, date = self.shedule.nextLesson(l9Id, now)
		if lessonId != None:
			lesson = self.shedule.getLesson(lessonId)
			
			if date.date() > now.date():
				text = f'❗️ Сегодня пар дальше не будет\nСледующая пара после ближайшей '
				if date.date() - now.date() == datetime.timedelta(days=1):
					text += 'завтра:\n\n'
				else:
					text +=  f'{date.day} {month[date.month-1]}:\n\n'
				
			elif date.time() > now.time():
				text = 'Следующая пара сегодня:\n\n'	
				
			text += self.strLesson(lesson)
			
		else:
			text = 'Ой! Занятий не обнаружено!'

		return text
	
	def dayShedule(self, l9Id):
		now = datetime.datetime.now()
		lessonIds, date = self.shedule.getDay(l9Id, now)
		
		if lessonIds != None:
			if now.date() < date.date():
				text = '❗️ Сегодня пар нет\nБлижайшие занятия '
				if date.date() - now.date() == datetime.timedelta(days=1):
					text += 'завтра:\n\n'
				else:
					text +=  f'{date.day} {month[date.month-1]}:\n\n'			
			elif now.date() == date.date():
				text = '🗓 Расписание на сегодня:\n\n'
				
			for lid in lessonIds:
				lesson = self.shedule.getLesson(lid)
				text += self.strLesson(lesson) + "\n\n"
		else:
			text = 'Ой! Занятий не обнаружено!'

		return text
	
	def strLesson(self, lesson):
		begin = lesson['begin']
		end = lesson['end']
		text = ("📆 %02i:%02i - %02i:%02i\n" % (begin.hour, begin.minute, end.hour, end.minute))
		add_info = "" if lesson['add_info'] == None else "\n"+lesson['add_info']
		teacher = "" if lesson['teacher'] == None else "\n👤 "+lesson['teacher']
		text += f"{lesson['type']} {lesson['name']}\n🧭 {lesson['place']}{teacher}{add_info}"
		return text
				
	def changeTag(self, uid, tag, platform = "TG"):
		table = TG_DB.users_table if platform == "TG" else ""
		self.l9lk.db.update(
			TG_DB.users_table,
			f"{Bot.platforms[platform]} = {uid}",
			f"pos_tag = '{tag}'"
			)	
		
	def checkLesson(self, time):
		lessons, first_lessons = self.shedule.checkLesson(time)
		last_lessons = self.shedule.lastLesson(time)
		
		mailing = {}
		
		for groupId, lesson in lessons:
			text = "❗️ Следующая пара: \n\n"
			text += self.strLesson(lesson)
			mailing[groupId] = text
			
		for groupId, lesson in first_lessons:
			text = "❗️ Первая пара: \n\n"
			text += self.strLesson(lesson)
			mailing[groupId] = text
			
		for groupId, lesson in last_lessons:
			text = "❗️ Сегодня пар больше нет"	
			mailing[groupId] = text
			
		return mailing
			
	def groupMailing(self, bot, groupId, msg):
		group = self.l9lk.db.get(L9LK.users_table, 
							f'groupId = {groupId}', 
							['l9Id'])	
		if group != []:
			for user in group:
				tg_id = self.l9lk.db.get(TG_DB.users_table, 
							f'l9Id = {user[0]}', 
							['tgId'])
				if tg_id != []:
					bot.sendMessage(tg_id[0][0], msg, tg_bot.keyboard())
	
if __name__ == "__main__":
	initLogger(logger)
	logger.info("Restart bot")
	
	config = loadJSON("config")
	l9lk = L9LK(config['sql'])
	tg_db = TG_DB(l9lk)
	sh_db = Shedule_DB(l9lk)
	bot = Bot(l9lk, sh_db)
	
	from libraries.tg_bot import TGbot
	
	tg_bot = TGbot(config['tg']['token'])
	
	timer = datetime.datetime(2022,1,1)
	
	logger.info("Bot ready!")
	
	while True:
		msgs = tg_bot.checkMessages()
		for msg in msgs:
			logger.info(msg.values())
			answer = bot.checkMessage(msg)
			if isinstance(answer, list): 
				for i in answer:
					tg_bot.sendMessage(msg['uid'], i, tg_bot.keyboard())	
					
			elif isinstance(answer, Exception): 
				logger.error(answer, exc_info=True)
			else:
				if answer == "Flood Stop":
					sleep(5)
				else:
					logger.warning(answer)
		
		now = datetime.datetime.now()		
		if now - timer > datetime.timedelta(minutes=5):
			timer = now.replace(minute=now.minute//5*5, second=0, microsecond=0)
			logger.debug("check "+now.isoformat())
			#timer = datetime.datetime(2022,10,11,21,55)
			mail = bot.checkLesson(timer)
			
			for groupId, msg in mail.items():
				bot.groupMailing(tg_bot, groupId, msg)			

