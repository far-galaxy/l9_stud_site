import telegram
from telegram.error import *
			
class TGbot():
	def __init__(self, token):
		self.token = token
		self.bot = telegram.Bot(token)
		self.udpate_id = None	
		
	def checkMessages(self):
		messages = []
		try:
			for update in self.bot.get_updates(offset=self.udpate_id, timeout=10):
				self.udpate_id = update.update_id + 1
				#print(self.udpate_id)
			
				if update.message:
					msg = {
					'platform' : "TG",
					'uid' : str(update.message.from_user.id),
					'name' : f'{update.message.from_user.first_name} {update.message.from_user.last_name}',					
					'text' : update.message.text
					}
					messages.append(msg)
		except TimedOut:
			return "Timed Out"
		except NetworkError:
			return "Network Error"
		except RetryAfter:
			return "Flood Stop"
		except Exception as e:
			return e
					
		return messages
	
	def keyboard(self):
		buttons = [
			[telegram.KeyboardButton("Ближайшая пара"),
			 telegram.KeyboardButton("Следующая пара")],
		[telegram.KeyboardButton("Расписание на сегодня")]
		]
		kb = telegram.ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
		#kb.add(telegram.KeyboardButton("Ближайшая пара"))
		
		return kb
	
	def confirmKeyboard(self):
		buttons = [[telegram.KeyboardButton("✅ Да"), 
				   telegram.KeyboardButton("⛔ Нет")]]
		return telegram.ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
	
	def sendMessage(self, uid, text, key=None):
		self.bot.send_message(uid, text, reply_markup=key)
				
if __name__ == "__main__":
	bot = TGbot(open("tg.txt").read())
	while True:
		msgs = bot.checkMessages()
		for msg in msgs:
			bot.sendMessage(msg['uid'], msg['text'])
