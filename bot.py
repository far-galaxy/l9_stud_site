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
		
		tag, l9Id = self.getTag(msg)
		
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
			ans = self.addGroup(l9Id, text)
			if ans.find("!") != -1:
				self.changeTag(uid, 'ready', platform)
				ans.append('❗️ Внимание! Бот работает в тестовом режиме, поэтому возможны сбои в работе\nЕсли бот не отвечает на запросы, не пишите ему больше ничего: автор заметит и как можно скорее исправит ошибку, и бот обязательно вам ответит :)')
			return ans			
				
		elif tag == 'ready':
			if text == 'Ближайшая пара':
				return[self.nearLesson(l9Id)]
			elif text == 'Следующая пара':
				return[self.nextLesson(l9Id)]
			elif text == 'Расписание на сегодня':
				return[self.dayShedule(l9Id)]
			elif text[0] == '/':
				text = text.split()
				cmd = text[0]
				arg = text[1:] if len(text) > 1 else None
				if cmd == '/help':
					return [open('libraries/help', encoding='utf-8').read()]
				if cmd == '/first_time':
					if arg == None:
						self.changeTag(uid, 'first_time', platform)
						return ["Введи время в минутах, за которое тебе нужно сообщать о начале первой пары (от 20 до 240)"]
					else:
						return [self.changeFirstTime(l9Id, arg[0])]
				if cmd == '/add':
					groups_count = len(self.l9lk.db.get(Shedule_DB.gu_table, f'l9Id = {l9Id}'))
					if groups_count >= 2:
						return["Ты уже подключен к двум группам, больше нельзя. Введи команду /del, чтобы удалить ненужную группу"]
					else:
						if arg == None:
							self.changeTag(uid, 'add', platform)
							return ["Введи номер новой группы в краткой форме (например, 2305)"]
						else:
							return [self.addGroup(l9Id, arg[0])]
						
				if cmd == '/del':
					groups_count = len(self.l9lk.db.get(Shedule_DB.gu_table, f'l9Id = {l9Id}'))
					if groups_count == 0:
						return["Ты пока не подключен ни к одной группе. Введи команду /add, чтобы подключить новую группу"]	
					else:
						if arg == None:
							self.changeTag(uid, 'del', platform)
							return ["Введи номер группы, которую хочешь удалить, в краткой форме (например, 2305)"]
						else:
							return [self.delGroup(l9Id, arg[0])]
					
				if str(uid) == config["tg"]["admin"]:
					if cmd == "/mail":
						self.groupMailing(tg_bot, arg[0], " ".join(arg[1:]))
						return["Сообщения отправлены"]

			return ['Aй!']
		# Commands
		elif text == '/cancel':
			self.changeTag(uid, 'ready', platform)
			return ['Возврат в главное меню']	
		
		elif tag == 'first_time':
			ans = self.changeFirstTime(l9Id, text)
			if ans.find("!") != -1:
				self.changeTag(uid, 'ready', platform)
			return [ans]
		
		elif tag == 'add':
			ans = self.addGroup(l9Id, text)
			if ans[0].find("!") != -1:
				self.changeTag(uid, 'ready', platform)
			return ans
		
		elif tag == 'del':
			ans = self.delGroup(l9Id, text)
			if ans[0].find("!") != -1:
				self.changeTag(uid, 'ready', platform)
			return [ans]	
		
		else:
			return ['Ой!']
		
	def getTag(self, msg):
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
	
		return tag[0][0], l9Id
	
	def changeFirstTime(self, l9Id, time):
		try:
			time = int(time)
			if time > 240:
				return "Ой, а не слишком ли заранее тебе надо напоминать о парах?)\nНапиши другое время, пожалуйста"
			elif time < 20:
				return "Мне кажется, что я тебе буду слишком поздно напоминать о начале пар, ты просто не успеешь собраться и добежать до универа (ну или проснуться и подключится онлайн)\nНапиши другое время, пожалуйста"	
			else:
				self.l9lk.db.update(
					L9LK.users_table,
					f"l9Id = {l9Id}",
					f"first_time = {time}"
				)	
				return "Время установлено!"
		except ValueError:
			return "Ой, это не похоже на число ):\nНапоминаю, что тебе нужно ввести время сообщения о начале пар"
		
	def addGroup(self, l9Id, groupName):
		if Bot.group_num_format.match(groupName) is None:
			return ['❗️Группа введена неверно']
		else:
			result = self.l9lk.db.get(
						Shedule_DB.groups_table,
						f'groupNumber = {groupName}', 
						['groupId','specName']				
					)
	
			if result != []:
				result = result[0]
				exists = self.l9lk.db.get(Shedule_DB.gu_table, f'groupId = {result[0]}')
				if exists == []:
					self.l9lk.db.insert(
								Shedule_DB.gu_table,
								{'l9Id' : l9Id,
								 'groupId' : result[0]}
							)	
					return [f'Поздравляем, твоя группа {groupName}, направление "{result[1]}", подключена!']
				else:
					return ['❗️Эта группа уже подключена']
			else:
				return ['К сожалению, такой группы в моей базе ещё нет :(']	
			
	def delGroup(self, l9Id, groupName):
		if Bot.group_num_format.match(groupName) is None:
			return '❗️Группа введена неверно'
		else:
			groupId = self.l9lk.db.get(Shedule_DB.groups_table, f'groupNumber = {groupName}',['groupId'])
			
			if groupId != []:
				self.l9lk.db.execute(f"""DELETE FROM l9_lk_test.groups_users WHERE groupId = {groupId[0][0]} AND l9Id = {l9Id};""")
				return "Группа успешно удалена! (если вообще была подключена (;)"
			else:
				return "❗Ошибка: группа не найдена"
		
	def nearLesson(self, l9Id):
		now = datetime.datetime.now()
		lessonId, date = self.shedule.nearLesson(l9Id, now)
		if lessonId != None:
			lessons = [self.shedule.getLesson(i) for i in lessonId]
			
			if date.date() > now.date():
				text = f'❗️Сегодня пар нет\nБлижайшая пара '
				if date.date() - now.date() == datetime.timedelta(days=1):
					text += 'завтра:\n'
				else:
					text +=  f'{date.day} {month[date.month-1]}:\n'
				
			elif date.time() > now.time():
				text = 'Ближайшая пара сегодня:\n'	
			else: 
				text = 'Текущая пара:\n'	
				
			text += self.strLesson(lessons)
			
		else:
			text = 'Ой! Занятий не обнаружено!'

		return text
	
	def nextLesson(self, l9Id):
		now = datetime.datetime.now()
		lessonIds, date = self.shedule.nextLesson(l9Id, now)
		if lessonIds != None:
			lessons = [self.shedule.getLesson(i) for i in lessonIds]
				
			text = 'Следующая пара после ближайшей или текущей:\n'		
			text += self.strLesson(lessons)
			
		else:
			text = f'Сегодня пар больше не будет'

		return text
	
	def dayShedule(self, l9Id):
		now = datetime.datetime.now()
		lessonIds, date = self.shedule.getDay(l9Id, now)
		
		if lessonIds != None:
			if now.date() < date.date():
				text = '❗️Сегодня пар нет\nБлижайшие занятия '
				if date.date() - now.date() == datetime.timedelta(days=1):
					text += 'завтра:\n\n'
				else:
					text +=  f'{date.day} {month[date.month-1]}:\n'			
			elif now.date() == date.date():
				text = '🗓Расписание на сегодня:\n'
				
			lessons = [self.shedule.getLesson(lid) for lid in lessonIds]
			
			l = []
			p = []
			nums = [i['numInDay'] for i in lessons]
			last_num = nums[0]
			for np, i in enumerate(nums):
				if i != last_num:
					last_num = i
					l.append(p)
					p = [np]
				else:
					p.append(np)
					
				if np == len(nums) - 1:
					l.append(p)
					
			for lesson in l:
				text += self.strLesson([lessons[i] for i in lesson]) + "-"*32

		else:
			text = 'Ой! Занятий не обнаружено!'

		return text
	
	def strLesson(self, lesson):
		begin = lesson[0]['begin']
		end = lesson[0]['end']
		text = ("\n📆 %02i:%02i - %02i:%02i" % (begin.hour, begin.minute, end.hour, end.minute))
		
		for l in lesson:
			add_info = "" if l['add_info'] == None else "\n"+l['add_info']
			teacher = "" if l['teacher'] == None else "\n👤 "+l['teacher']
			text += f"\n{l['type']} {l['name']}\n🧭 {l['place']}{teacher}{add_info}\n"			
		return text
				
	def changeTag(self, uid, tag, platform = "TG"):
		table = TG_DB.users_table if platform == "TG" else ""
		self.l9lk.db.update(
			table,
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
		group = self.l9lk.db.get(Shedule_DB.gu_table, 
							f'groupId = {groupId}', 
							['l9Id'])	
		if group != []:
			for user in group:
				tg_id = self.l9lk.db.get(TG_DB.users_table, 
							f'l9Id = {user[0]}', 
							['tgId'])
				if tg_id != []:
					bot.sendMessage(tg_id[0][0], msg, tg_bot.keyboard())
					
	def firstMailing(self, bot, time):
		self.shedule.firstTimeCheck(time)
		str_time = time.isoformat(sep=' ')
		
		mail = self.l9lk.db.execute(f"""
							SELECT tgId, lessonId, u.first_time FROM first_mail AS fm 
							JOIN l9_users AS u ON fm.l9Id = u.l9Id
							JOIN tg_bot AS t ON t.l9Id = fm.l9Id
							WHERE fm.mailTime = '{str_time}';""").fetchall();
		if time.hour < 11:
			head = "Доброе утро 🌅\n"
		elif time.hour >= 11 and time.hour < 16:
			head = "Добрый день ☀️\n"
		else:
			head = "Добрый вечер 🌃\n"
		if mail != []:
			for user in mail:
				mn = user[2] % 10
				end = ""
				if mn == 1:
					end = "у"
				elif mn > 1 and mn < 5:
					end = "ы"
				text = f"{head}Через {user[2]} минут{end} начнутся занятия\n\nПервая пара:\n"
				text += self.strLesson(self.shedule.getLesson(user[1]))
				bot.sendMessage(user[0], text, tg_bot.keyboard())
				
	def nextDay(self, bot, time):
		lessons = self.shedule.checkNextDay(time)
		
		if lessons != []:
			for group, day in lessons:
				text = "❗️ Внимание!\nЗавтра будут занятия:\n\n"
				for lid in day:
					lesson = self.shedule.getLesson(lid[0])
					text += self.strLesson(lesson) + "\n\n"
				self.groupMailing(bot, group, text)
				
	
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
			tag, _ = bot.getTag(msg)
			key = tg_bot.keyboard() if tag == 'ready' else None
			if isinstance(answer, list): 
				for i in answer:
					tg_bot.sendMessage(msg['uid'], i, key)	
					
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
			#timer = datetime.datetime(2022,10,20,18,00)
			bot.firstMailing(tg_bot, timer)
			
			mail = bot.checkLesson(timer)
			for groupId, msg in mail.items():
				bot.groupMailing(tg_bot, groupId, msg)
				
			if timer.hour == 19 and timer.minute == 00:
				bot.nextDay(tg_bot, now)

