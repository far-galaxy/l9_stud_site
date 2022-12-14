from mysql.connector import connect
import random
import datetime

from .utils import *
import logging
logger = logging.getLogger('sql')
initLogger(logger,'sql')

class Database():
	"""Mini module for mysql connector"""
	def __init__(self, host, user, password):
		self.database = connect(host = host,
								user = user,
								password = password)
		self.cursor = self.database.cursor()
	
	def execute(self, query: str, commit = False):
		"""Execute a query
		
		Args:
		    :query: :class:`str` query string
		    :commit: [optional] :class:`bool` commit changes if any
		Returns:
		    :cursor: result of query
		"""
		if query.lower().find("drop") == -1:
			if query.lower().find('create') == -1:
				logger.info(query)
			self.cursor.execute(query)
			if commit:
				self.database.commit()
		return self.cursor
		
	def initDatabase(self, name: str):
		"""Creates a database if not exist and switch to them"""
		self.execute(f"CREATE DATABASE IF NOT EXISTS {name}")
		self.execute(f"USE {name}")		
		
	def initTable(self, name, head):
		"""Creates a table if not exist
		
		Args:
		    :name: :class:`str` name of the table
		    :head: :class:`list` of :class:`list` of column names and attributes
		"""
		query = f"CREATE TABLE IF NOT EXISTS `{name}` ("
		query += ", ".join([" ".join(i) for i in head])
		query += ");"
		self.execute(query)
		
	def insert(self, name, values):
		"""Inserts a row in the table
		
		Args:
		    :name: :class:`str` name of the table
		    :values: :class:`dict` columns name and its values
		"""		
		query = f"INSERT IGNORE INTO `{name}` ("
		query += ", ".join(values) + ") VALUES ("
		query += ", ".join([f'"{i}"' if (i != None) else "NULL" 
							for i in values.values()]) + ");"
		self.execute(query, commit = True)
		
	def get(self, name, condition = None, columns = None):
		"""Get rows by simple condition
		
		:SELECT columns FROM name WHERE condition:
		
		Args:
		    :name: :class:`str` name of the table
		    :condition: :class:`str` SQL condition after WHERE, for all rows leave None
		    :columns: [optional] :class:`list` columns to return, for all columns leave None
		"""			
		query = "SELECT " + (', '.join(columns) if columns != None else "*")
		query += f" FROM `{name}`"
		query += f" WHERE {condition};" if condition != None else ";"
		result = self.execute(query).fetchall()
		logger.info(result)
		return result
	
	def addRow(self, name, row):
		query = f"ALTER TABLE {name}"
		query += f" ADD {' '.join(row)};"
		self.execute(query)	
		
	def update(self, name, condition, new):
		query = f"UPDATE {name}"
		query += f" SET {new} WHERE {condition};"
		self.execute(query, commit = True)		
		
	def newID(self, name, id_name):
		"""Generate random 9-digits ID
		
		Args:
		    :name: :class:`str` name of the table
		    :id_name: :class:`str` name of the primary key
		Returns:
		    :someID: :class:`str` 
		"""	
		someID = random.randint(100000000,999999999)
		
		result = self.get(name, f"{id_name} = {someID}")
		
		exist = result != []
		if not exist:
			return str(someID)
		else:
			self.newID()	

class L9LK():
	
	users_table = "l9_users"
	
	def __init__(self, sql_pass):
		self.db = Database("localhost", "root", sql_pass)
		self.db.initDatabase("l9_lk_test")
		
		self.db.execute(f"""
		CREATE TABLE IF NOT EXISTS `{L9LK.users_table}` (
		`l9Id` int NOT NULL,
		`first_time` int NOT NULL DEFAULT '45',
		PRIMARY KEY (`l9Id`)
		)
		""",
		commit=True)		

		
	def initUser(self, data):
		uid = str(data['id'])
		result = self.db.get(L9LK.users_table, f"l9Id = {uid}", ["l9Id"])
		if result == []:
			l9Id = self.db.newID(L9LK.users_table, "l9Id")
			user = {
				"l9Id" : l9Id
				}
			self.db.insert(L9LK.users_table, user)
		else:
			l9Id = result[0][0]
			
		return l9Id
		
class TG_DB():
	
	users_table = "tg_bot"
	msg_table = "temp_msg"
	
	def __init__(self, db):	
		"""Telegram Bot Databse
		
		Args:
		    :db: :class:`L9LK` database
		"""	
		self.l9lk = db
		self.l9lk.db.execute(f"""
							 CREATE TABLE IF NOT EXISTS `{TG_DB.users_table}` (
							 `l9Id` int NOT NULL,
							 `tgId` bigint NOT NULL,
							 `pos_tag` varchar(30) DEFAULT 'not_started',
							 `name` TEXT,
							 PRIMARY KEY (`l9Id`),
							 CONSTRAINT `l9_tg` FOREIGN KEY (`l9Id`) REFERENCES `{L9LK.users_table}` (`l9Id`) ON DELETE CASCADE ON UPDATE CASCADE
							 )""",
							 commit=True)	
		
		self.l9lk.db.execute(f"""
								 CREATE TABLE IF NOT EXISTS `{TG_DB.msg_table}` (
								 `msgId` bigint NOT NULL AUTO_INCREMENT,
								 `chatId` bigint NOT NULL,
								 `messageId` bigint NOT NULL,
								 `msgDate` datetime NOT NULL,
								 `msgType` varchar(5),
								 PRIMARY KEY (`msgId`))""",
								 commit=True)		
		
	def initUser(self, tgId, name):
		result = self.l9lk.db.get(TG_DB.users_table, f"tgId = {tgId}", ["l9Id"])
		if result == []:
			l9Id = self.l9lk.initUser({"id":0})
			user = {
					"l9Id" : l9Id,
					"tgId" : tgId,
					"name" : name
				}
			self.l9lk.db.insert(TG_DB.users_table, user)
		else:
			l9Id = result[0][0]		
		
		return l9Id
	
class Shedule_DB():
	
	groups_table = 'groups'
	teachers_table = 'teachers'
	lessons_table = 'lessons'
	fm_table = 'first_mail'
	gu_table = 'groups_users'
	s_table = 'session'

	def __init__(self, db):	
		"""Shedule Databse

		Args:
		    :db: :class:`L9LK` database
		"""	
		self.l9lk = db
		
		self.l9lk.db.execute(f"""
		CREATE TABLE IF NOT EXISTS `{Shedule_DB.groups_table}` (
		`groupId` bigint NOT NULL,
		`groupNumber` char(4) DEFAULT '0000',
		`specName` text,
		PRIMARY KEY (`groupId`)
		)""",
		commit=True)
		
		self.l9lk.db.execute(f"""
		CREATE TABLE IF NOT EXISTS `{Shedule_DB.gu_table}` (
		`guId` int NOT NULL AUTO_INCREMENT,
		`l9Id` int NOT NULL,
		`groupId` bigint NOT NULL,
		`firstTime` int DEFAULT '45',
		`firstNote` tinyint DEFAULT '1',
		`nextNote` tinyint DEFAULT '1',
		PRIMARY KEY (`guId`),
		KEY `guid_idx` (`l9Id`),
		KEY `gid_idx` (`groupId`),
		CONSTRAINT `gr_gu` FOREIGN KEY (`groupId`) REFERENCES `{Shedule_DB.groups_table}` (`groupId`) ON DELETE CASCADE ON UPDATE CASCADE,
		CONSTRAINT `l9_gu` FOREIGN KEY (`l9Id`) REFERENCES `{L9LK.users_table}` (`l9Id`) ON DELETE CASCADE ON UPDATE CASCADE
		)""",
		commit=True)			
		
		self.l9lk.db.execute(f"""
		CREATE TABLE IF NOT EXISTS `{Shedule_DB.teachers_table}` (
		`teacherId` int NOT NULL,
		`name` varchar(45) DEFAULT '????????',
		`surname` varchar(45) DEFAULT '????????????',
		`midname` varchar(45) DEFAULT '????????????????',
		PRIMARY KEY (`teacherId`)
		)""",
		commit=True)		
		
		self.l9lk.db.execute(f"""
		CREATE TABLE IF NOT EXISTS `{Shedule_DB.lessons_table}` (
		`lessonId` int NOT NULL AUTO_INCREMENT,
		`numInDay` int DEFAULT '1',
		`type` char(5) DEFAULT 'other',
		`name` text,
		`groupId` bigint NOT NULL,
		`begin` datetime NOT NULL,
		`end` datetime NOT NULL,
		`teacherId` int DEFAULT NULL,
		`place` text,
		`add_info` text,
		PRIMARY KEY (`lessonId`),
		KEY `gr_l_idx` (`groupId`),
		KEY `teach_l_idx` (`teacherId`),
		CONSTRAINT `gr_l` FOREIGN KEY (`groupId`) REFERENCES `{Shedule_DB.groups_table}` (`groupId`) ON DELETE RESTRICT ON UPDATE RESTRICT,
		CONSTRAINT `teach_l` FOREIGN KEY (`teacherId`) REFERENCES `{Shedule_DB.teachers_table}` (`teacherId`) ON DELETE SET NULL ON UPDATE CASCADE
		)""",
		commit=True)
		
		self.l9lk.db.execute(f"""
		CREATE TABLE IF NOT EXISTS `first_mail` (
		`mailId` int NOT NULL AUTO_INCREMENT,
		`l9Id` int NOT NULL,
		`lessonId` int NOT NULL,
		`mailTime` datetime NOT NULL,
		PRIMARY KEY (`mailId`),
		KEY `l9_fm_idx` (`l9Id`),
		KEY `lesson_fm_idx` (`lessonId`),
		CONSTRAINT `l9_fm` FOREIGN KEY (`l9Id`) REFERENCES `{L9LK.users_table}` (`l9Id`),
		CONSTRAINT `lesson_fm` FOREIGN KEY (`lessonId`) REFERENCES `lessons` (`lessonId`) ON DELETE CASCADE ON UPDATE CASCADE
		)""",
		commit=True)	
		
		self.l9lk.db.execute(f"""
		CREATE TABLE IF NOT EXISTS `{Shedule_DB.s_table}` (
		`sessionId` int NOT NULL AUTO_INCREMENT,
		`type` char(5) DEFAULT 'exam',
		`subject` text,
		`groupId` bigint NOT NULL,
		`date` datetime NOT NULL,
		`teacherId` bigint DEFAULT NULL,
		`place` text,
		`add_info` text,
		PRIMARY KEY (`sessionId`),
		KEY `gr_s_idx` (`groupId`),
		KEY `teach_s_idx` (`teacherId`)
		)""",
		commit=True)		
		
	def nearLesson(self, l9Id, time, groupId = None):
		print(groupId)
		str_time = time.isoformat(sep=' ')
	
		if groupId == None:
			groupId = self.getGroup(l9Id)
		
		if groupId != None:
			second_gr = f' OR groupId = {groupId[1][0]}' if len(groupId) == 2 else ""
			lessonId = self.l9lk.db.get(Shedule_DB.lessons_table, 
							 f"(groupId = {groupId[0][0]}{second_gr}) AND `end` > '{str_time}' " 
							 'ORDER BY `begin` LIMIT 2',
							 ['lessonId','begin','numInDay'])
			
			if lessonId != []:
				begin = lessonId[0][1]
				if len(lessonId) == 2 and lessonId[0][1] == lessonId[1][1]:
					return [lessonId[0][0], lessonId[1][0]], begin				
				return [lessonId[0][0]], begin
			
		return None, None
			
	def nextLesson(self, l9Id, time):
		str_time = time.isoformat(sep=' ')
		str_date = time.strftime("%Y-%m-%d")
	
		groupId = self.getGroup(l9Id)
		
		if groupId != None:
			second_gr = f' OR groupId = {groupId[1][0]}' if len(groupId) == 2 else ""
			lessonId = self.l9lk.db.get(Shedule_DB.lessons_table, 
							 f"(groupId = {groupId[0][0]}{second_gr}) AND `end` > '{str_time}' "
							 f"AND DATE(`begin`) = '{str_date}' "
							 'ORDER BY `begin` LIMIT 3',
							 ['lessonId','begin','numInDay'])
			
			if lessonId != []:
				if len(lessonId) < 2:
					return None, None
				begin = lessonId[1][1]
				if len(lessonId) == 3 and lessonId[1][2] == lessonId[2][2]:
					return [lessonId[1][0], lessonId[2][0]], begin
				return [lessonId[1][0]], begin
			
		return None, None
	
	def getDay(self, l9Id, time, groupId = None):
		str_time = time.isoformat(sep=' ')
		
		near_lesson_date = self.nearLesson(l9Id, time, groupId)[1]
		if near_lesson_date != None:
			str_nld = near_lesson_date.strftime("%Y-%m-%d")
			if groupId == None:
				groupId = self.getGroup(l9Id)
			if groupId != None:
				second_gr = f' OR groupId = {groupId[1][0]}' if len(groupId) == 2 else ""
				lessonsId = self.l9lk.db.get(Shedule_DB.lessons_table, 
								 f"(groupId = {groupId[0][0]}{second_gr})"# AND `begin` > '{str_time}' " 
								 f"AND DATE(`begin`) = '{str_nld}' "
								 'ORDER BY `begin`',
								 ['lessonId','begin'])
				if lessonsId != []:
					date = lessonsId[0][1]
					return [i[0] for i in lessonsId], date
			
		return None, None
	
	def checkLesson(self, time):
		time = time.replace(second=0, microsecond=0)
		str_time = time.isoformat(sep=' ')
		str_date = time.strftime("%Y-%m-%d")
		lessons = []
		prev_groupsIds = self.l9lk.db.get(Shedule_DB.lessons_table, 
										 f"`end` = '{str_time}' " 
										 f"AND DATE(`end`) = '{str_date}' ",
										 #'AND `numInDay` != 1',
										 ['groupId','numInDay'])
		
		if prev_groupsIds != []:
			prev_groupsIds = set(prev_groupsIds)
			for i in prev_groupsIds:
				num = i[1]
				next_lessonId = self.l9lk.db.get(Shedule_DB.lessons_table, 
													 f"`numInDay` = '{num+1}' " 
													 f"AND DATE(`end`) = '{str_date}' "
													 f"AND groupId = {i[0]}",
													 ['lessonId'])
				if next_lessonId != []:
					lessons.append((i[0], 
									[self.getLesson(lid[0]) for lid in next_lessonId]))
				
		
		first_groupsIds = self.l9lk.db.get(Shedule_DB.lessons_table, 
										 f"DATE(`begin`) = '{str_date}' "
										 'AND `numInDay` = 1',
										 ['groupId'])
		first_lessons = []
		if first_groupsIds != []:
			first_groupsIds = set(first_groupsIds)
			for i in first_groupsIds:
				first_lessonIds = self.l9lk.db.get(Shedule_DB.lessons_table, 
													   f"DATE(`begin`) = '{str_date}' "
													   'AND `numInDay` = 1 '
													   f'AND `groupId` = {i[0]}',
													   ['lessonId', 'begin'])
				if first_lessonIds[0][1] - datetime.timedelta(minutes=10) == time:
					first_lessons.append((i[0], [self.getLesson(l[0]) for l in first_lessonIds]))
					
		return lessons, first_lessons
	
	def lastLesson(self, time):
		time = time.replace(second=0, microsecond=0)
		str_time = time.isoformat(sep=' ')
		str_date = time.strftime("%Y-%m-%d")
		lessons = []
		last_lessonIds = self.l9lk.db.get(Shedule_DB.lessons_table, 
											 f"DATE(`end`) = '{str_date}' "
											 'ORDER BY `end` DESC',
											 ['groupId'])
		if last_lessonIds != []:
			last_lessonIds = set(last_lessonIds)
			for i in last_lessonIds:
				lesson = self.l9lk.db.get(Shedule_DB.lessons_table, 
											 f"DATE(`end`) = '{str_date}' "
											 f"AND groupId = {i[0]} "
											 'ORDER BY `end` DESC LIMIT 1',
											 ['lessonId','end'])
				if lesson != []:
					if lesson[0][1] == time:
						lessons.append(i[0])
	
		return lessons		
		
	def getGroup(self, l9Id):
		groupId = self.l9lk.db.get(Shedule_DB.gu_table, f'l9Id = {l9Id}',['groupId'])
		return groupId if groupId != [] else None
	
	def firstTimeCheck(self, time):
		str_time = time.isoformat(sep=' ')
		str_data = time.strftime("%Y-%m-%d")
		
		query = f"DELETE FROM first_mail"# WHERE mailTime <= '{str_time}';"
		
		self.l9lk.db.execute(query, commit=True)
		
		query = f"""#
		INSERT IGNORE INTO first_mail (l9Id, lessonId, mailTime) 
		SELECT u.l9Id, l.lessonId, DATE_SUB(l.begin, INTERVAL g.firstTime MINUTE) as `time` FROM groups_users AS g 
		JOIN l9_users AS u ON u.l9Id = g.l9Id
		JOIN lessons AS l ON l.groupId = g.groupId WHERE DATE(l.begin) = '{str_data}' AND l.numInDay = 1 AND l.begin > '{str_time}' AND g.firstNote = 1 ORDER BY l.begin;"""
		
		self.l9lk.db.execute(query, commit=True)
		
	def checkNextDay(self, time):
		str_time = time.strftime("%Y-%m-%d")
		
		groups = self.l9lk.db.execute(f"""
		SELECT groupId FROM lessons 
		WHERE DATE(DATE_SUB(begin, INTERVAL 1 DAY)) = '{str_time}' AND numInDay = 1;""").fetchall()
		
		mail = []
		for gr in groups:
			lessonIds = self.l9lk.db.execute(f"""
			SELECT lessonId FROM lessons 
			WHERE DATE(DATE_SUB(begin, INTERVAL 1 DAY)) = '{str_time}' AND groupId = {gr[0]}""").fetchall()		
			mail.append([gr[0], lessonIds])
		return mail
					
	
	def getLesson(self, lessonId):
		icons = {'other' : '????', 'lect' : '????', 'lab' : '????', 'pract' : '????'}
			
		lesson = self.l9lk.db.get(Shedule_DB.lessons_table, f'lessonId = {lessonId}')
			
		if lesson != []:
			lesson = lesson[0]
			
			teacher = None
			if lesson[7] != None:	
				teacher = self.l9lk.db.get(Shedule_DB.teachers_table, f'teacherId = {lesson[7]}')
				
			if teacher != None and teacher != []:
				info = teacher[0] 
				teacher = f"{info[2]} {info[1][0]}.{info[3][0]}."
				
			json_lesson = {
				'numInDay': lesson[1],
				'type' : icons[lesson[2]],
				'name' : lesson[3],
				'place' : lesson[8],
				'teacher' : teacher,
				'add_info' : lesson[9],
				'begin': lesson[5],
				'end': lesson[6],
			}
				
			return json_lesson
			
		else:
			return {'empty'}
		
		
		
	
	
if __name__ == "__main__":
	l9lk = L9LK(open("pass.txt").read())
	sh = Shedule_DB(l9lk)
	
	
	print(sh.firstTimeCheck(datetime.datetime(2022, 10, 14, 20, 15)))
	
	#lesson, is_now = sh.getDay(914995387, datetime.datetime(2022, 10, 11, 17, 20))

	
