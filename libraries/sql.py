from mysql.connector import connect
import random
import datetime

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
		if query.lower().find("drop") == -1 and query.lower().find("truncate") == -1:
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
		query = f"INSERT IGNORE INTO {name} ("
		query += ", ".join(values) + ") VALUES ("
		query += ", ".join([f'"{i}"' if (i != None) else "NULL" 
							for i in values.values()]) + ");"
		self.execute(query, commit = True)
		
	def get(self, name, condition, columns = None):
		"""Get rows by simple condition
		
		:SELECT columns FROM name WHERE condition:
		
		Args:
		    :name: :class:`str` name of the table
		    :condition: :class:`str` SQL condition after WHERE
		    :columns: [optional] :class:`list` columns to return, for all columns leave None
		"""			
		query = "SELECT " + (', '.join(columns) if columns != None else "*")
		query += f" FROM `{name}` WHERE {condition};"
		return self.execute(query).fetchall()
	
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
		
		exist = result.fetchall() != []
		if not exist:
			return str(someID)
		else:
			self.newID()	

class L9LK():
	
	users_table = "l9_users"
	
	def __init__(self, sql_pass):
		self.db = Database("localhost", "root", sql_pass)
		self.db.initDatabase("l9_lk")
		self.db.initTable(L9LK.users_table, [
		["l9Id", "INTEGER", "PRIMARY KEY"],
		["groupId", "INTEGER"],
		["FOREIGN KEY", "(groupId)", "REFERENCES", f"`{Shedule_DB.groups_table}`", "(groupId)"]
		])
		
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
	
	def __init__(self, db):	
		"""Telegram Bot Databse
		
		Args:
		    :db: :class:`L9LK` database
		"""	
		self.l9lk = db
		self.l9lk.db.initTable(TG_DB.users_table, [
		["l9Id", "INTEGER", "PRIMARY KEY"],
		["tgId", "INTEGER"],
		["pos_tag", "VARCHAR(11)", "DEFAULT", "'not_started'"],
		["first_time", "INT", "DEFAULT", "45"],
		["FOREIGN KEY", "(l9Id)", "REFERENCES", f"`{L9LK.users_table}`", "(l9Id)"]
		])	
		
	def initUser(self, tgId):
		result = self.l9lk.db.get(TG_DB.users_table, f"tgId = {tgId}", ["l9Id"])
		result = result.fetchall()
		if result == []:
			l9Id = self.l9lk.initUser({"id":0})
			user = {
					"l9Id" : l9Id,
					"tgId" : tgId
				}
			self.l9lk.db.insert(TG_DB.users_table, user)
		else:
			l9Id = result[0][0]		
		
		return l9Id
	
class Shedule_DB():
	
	groups_table = 'groups'
	teachers_table = 'teachers'
	lessons_table = 'lessons'

	def __init__(self, db):	
		"""Shedule Databse

		Args:
		    :db: :class:`L9LK` database
		"""	
		self.l9lk = db
		self.l9lk.db.initTable(Shedule_DB.groups_table, [
		["groupId", "INTEGER", "PRIMARY KEY"],
		["groupNumber", "CHAR(4)"],
		["specName", "VARCHAR(45)"],
		])	
		
		self.l9lk.db.initTable(Shedule_DB.lessons_table, [
		["lessonId", "INTEGER", "PRIMARY KEY"],
		["type", "CHAR(5)", "DEFAULT", "'other'"],
		["name", "TEXT"],
		["groupId", "INTEGER"],
		["begin", "DATETIME"],
		["end", "DATETIME"],
		["teacherId", "INTEGER"],
		["place", "TEXT"],
		["add_info", "TEXT"],
		["FOREIGN KEY", "(groupId)", "REFERENCES", f"`{Shedule_DB.groups_table}`", "(groupId)"],
		["FOREIGN KEY", "(teacherId)", "REFERENCES", f"`{Shedule_DB.teachers_table}`", "(teacherId)"]
		])	
		
	def nearLesson(self, l9Id, time):
		str_time = time.isoformat(sep=' ')
	
		groupId = self.getGroup(l9Id)
		
		if groupId != None:
			lessonId = self.l9lk.db.get(Shedule_DB.lessons_table, 
							 f"groupId = {groupId} AND `end` > '{str_time}' " 
							 'ORDER BY `begin` LIMIT 1',
							 ['lessonId','begin'])
			
			if lessonId != []:
				begin = lessonId[0][1]
				return lessonId[0][0], begin
			
		return None, None
			
	def nextLesson(self, l9Id, time):
		str_time = time.isoformat(sep=' ')
	
		groupId = self.getGroup(l9Id)
		
		if groupId != None:
			lessonId = self.l9lk.db.get(Shedule_DB.lessons_table, 
							 f"groupId = {groupId} AND `begin` > '{str_time}' " 
							 'ORDER BY `begin` LIMIT 2',
							 ['lessonId','begin'])
			
			if lessonId != []:
				if len(lessonId) < 2:
					return None, None
				begin = lessonId[1][1]
				date = begin.date
				return lessonId[1][0], date
			
		return None, None
	
	def getDay(self, l9Id, time):
		str_time = time.isoformat(sep=' ')
		
		near_lesson_date = self.nearLesson(l9Id, time)[1]
		str_nld = near_lesson_date.strftime("%Y-%m-%d")
		groupId = self.getGroup(l9Id)
		if groupId != None:
			lessonsId = self.l9lk.db.get(Shedule_DB.lessons_table, 
							 f"groupId = {groupId} AND `begin` > '{str_time}' " 
							 f"AND DATE(`begin`) = '{str_nld}' "
							 'ORDER BY `begin`',
							 ['lessonId','begin'])
			date = lessonsId[0][1]
			return [i[0] for i in lessonsId], date
			
		return None, None
	def getGroup(self, l9Id):
		groupId = self.l9lk.db.get(L9LK.users_table, f'l9Id = {l9Id}',['groupId'])
		return groupId[0][0] if groupId != [] else None
	
	def getLesson(self, lessonId):
		icons = {'other' : '📙', 'lect' : '📗', 'lab' : '📘', 'pract' : '📕'}
			
		lesson = self.l9lk.db.get(Shedule_DB.lessons_table, f'lessonId = {lessonId}')
			
		if lesson != []:
			lesson = lesson[0]
				
			teacher = self.l9lk.db.get(Shedule_DB.teachers_table, f'teacherId = {lesson[6]}')
				
			if teacher != []:
				info = teacher[0] 
				teacher = f"{info[2]} {info[1][0]}.{info[3][0]}."
			else:
				teacher = "Error"
				
			json_lesson = {
				'type' : icons[lesson[1]],
				'name' : lesson[2],
				'place' : lesson[7],
				'teacher' : teacher,
				'add_info' : lesson[8]
			}
				
			return json_lesson
			
		else:
			return {'empty'}
		
		
		
	
	
if __name__ == "__main__":
	l9lk = L9LK(open("pass.txt").read())
	sh = Shedule_DB(l9lk)
	
	lesson, is_now = sh.getDay(914995387, datetime.datetime(2022, 10, 11, 17, 20))
	if lesson != None:
		for l in lesson:
			print(sh.getLesson(l))
	