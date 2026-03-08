import telebot

class B: # bot
    def __init__(self, token : str):
        self.bot = telebot.TeleBot(token)

    def start(self, message):
        self.bot.send_message(message.chat.id, "bebra")