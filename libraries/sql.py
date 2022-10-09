from mysql.connector import connect
import random

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
		query = f"CREATE TABLE IF NOT EXISTS {name} ("
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
		query += f" FROM {name} WHERE {condition};"
		return self.execute(query)
	
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
		["userName", "TEXT"],
		["userSurname", "TEXT"],
		["userPhotoUrl", "TEXT"],
		["sessionToken", "TEXT"],
		])
		
	def initUser(self, data):
		uid = str(data['id'])
		result = self.db.get(L9LK.users_table, f"l9Id = {uid}", ["l9Id"])
		result = result.fetchall()
		if result == []:
			l9Id = self.db.newID(L9LK.users_table, "l9Id")
			user = {
				"l9Id" : l9Id,
				"userName" : data['first_name'] if 'first_name' in data else None,
				"userSurname" : data['last_name'] if 'last_name' in data else None,
				"userPhotoUrl" : data['photo_big'] if 'photo_big' in data else None
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
		["FOREIGN KEY", "(l9Id)", "REFERENCES", L9LK.users_table, "(l9Id)"]
		])	
		
	def initUser(self, tgId):
		result = self.l9lk.db.get(TG_DB.users_table, f"tgId = {tgId}", ["l9Id"])
		result = result.fetchall()
		print(result)
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
	
if __name__ == "__main__":
	l9lk = L9LK(open("pass.txt").read())
	TG_DB = TG_DB(l9lk)
	print(TG_DB.initUser("12345689"))
	