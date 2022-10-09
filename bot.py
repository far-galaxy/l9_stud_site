from libraries.sql import *
from libraries.utils import *
import datetime
import re

class User():
	def __init__(self, l9Id):
		self.l9Id = l9Id
		self.timestamp = datetime.now()
		
	def isStart():
		pass

class Bot():
	
	platforms = {"VK":"vkId","TG":"tgId"}
	group_num_format = re.compile('\d{4}')
	
	def __init__(self, db):
		self.l9lk = db
		self.users_id = {"VK":{}, "TG":{}}
		self.users_db = {}
		
	def checkMessage(self, msg):
		
		platform = msg['platform']
		uid = msg['uid']
		text = msg['text']
		
		if uid not in self.users_id[platform]:
			if platform == 'TG':
				l9Id = tg_db.initUser(uid)
				self.users_id[platform][uid] = l9Id
		
		tag = self.l9lk.db.get(TG_DB.users_table, 
					f"{Bot.platforms[platform]} = {uid}", 
					["pos_tag"])
		
		tag = tag.fetchall()
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
				result = result.fetchall()
				
				if result != []:
					result = result[0]
					self.changeTag(uid, 'ready', platform)
					self.l9lk.db.update(
						L9LK.users_table,
						f"l9Id = {l9Id}",
						f"groupId = '{result[0]}'"
					)						
					return [f'Поздравляем, твоя группа {text}, направление "{result[1]}", уже есть в моей базе!']
				else:
					return ['К сожалению, такой группы в моей базе ещё нет :(']
				
	def changeTag(self, uid, tag, platform = "TG"):
		table = TG_DB.users_table if platform == "TG" else ""
		self.l9lk.db.update(
			TG_DB.users_table,
			f"{Bot.platforms[platform]} = {uid}",
			f"pos_tag = '{tag}'"
			)		
		
	def answer(self, user, text):
		pass
	
if __name__ == "__main__":
	config = loadJSON("config")
	l9lk = L9LK(config['sql'])
	tg_db = TG_DB(l9lk)
	bot = Bot(l9lk)
	
	from libraries.tg_bot import TGbot
	
	tg_bot = TGbot(config['tg']['token'])
	
	while True:
		msgs = tg_bot.checkMessages()
		for msg in msgs:
			answer = bot.checkMessage(msg)
			for i in answer:
				tg_bot.sendMessage(msg['uid'], i)	
	
