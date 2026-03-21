from project import botLib
from project import config
from project.dbManager import DbManager
import telebot

dbManager = DbManager(config.DBPATH)
bot = botLib.B(config.TOKEN, dbManager)

@bot.bot.message_handler(commands=["start"])
def start(message):
    bot.start(message)


@bot.bot.message_handler(commands=["register"])
def registration(message):
    bot.registration(message)


@bot.bot.message_handler(commangs=["create"])
def createSession(message):
    bot.createSession(message)

@bot.bot.message_handler(commangs=["join"])
def joinSession(message):
    pass


@bot.bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.callback(call)

bot.bot.infinity_polling()
