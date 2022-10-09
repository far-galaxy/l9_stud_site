import telegram
			
class TGbot():
	def __init__(self, token):
		self.token = token
		self.bot = telegram.Bot(token)
		self.udpate_id = None	
		
	def checkMessages(self):
		messages = []
		for update in self.bot.get_updates(offset=self.udpate_id, timeout=10):
			self.udpate_id = update.update_id + 1
		
			if update.message:
				msg = {
				'uid' : update.message.from_user.id,
				'text' : update.message.text
				}
				messages.append(msg)
		return messages
	
	def sendMessage(self, uid, text):
		self.bot.send_message(uid, text)
				
if __name__ == "__main__":
	bot = TGbot(open("tg.txt").read())
	while True:
		msgs = bot.checkMessages()
		for msg in msgs:
			bot.sendMessage(msg['uid'], msg['text'])