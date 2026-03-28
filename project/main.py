from project import botLib
from project import config
from project.dbManager import DbManager
import telebot

dbManager = DbManager(config.DBPATH)
bot = botLib.B(config.TOKEN, dbManager)

@bot.bot.message_handler(commands=["start"])
def start(message):
    """Handle /start command from Telegram.

    :param message: Telegram message object.
    :return: None
    """
    bot.showCmds(message)
    bot.registration(message)


@bot.bot.message_handler(commands=["info"])
def info(message):
    bot.showCmds(message)


@bot.bot.message_handler(commands=["register"])
def registration(message):
    """Handle /register command, delegating to bot registration flow.

    :param message: Telegram message object.
    :return: None
    """
    bot.registration(message)


@bot.bot.message_handler(commands=["create"])
def createSession(message):
    """Handle /create command to start session creation.

    :param message: Telegram message object.
    :return: None
    """
    bot.createSession(message)


@bot.bot.message_handler(commands=["join"])
def joinSession(message):
    """Handle /join command to start join-session flow.

    :param message: Telegram message object.
    :return: None
    """
    bot.joinSession(message)

@bot.bot.message_handler(commands=["startGame"])
def startGame(message):
    bot.startGame(message)

@bot.bot.message_handler(commands=["endGame"])
def endGame(message):
    bot.callEndGameWithMessage(message)

@bot.bot.message_handler(commands=["games"])
def showGamesList(message):
    bot.showGamesList(message)

@bot.bot.message_handler(commands=["show"])
def showSessionInfo(message):
    bot.showSessionInfo(message)

@bot.bot.message_handler(commands=["showPlayers"])
def showPlayers(message):
    bot.showPlayers(message)

@bot.bot.message_handler(commands=["resetDB"])
def resetDB(message):
    bot.clearDB(message, True)

@bot.bot.message_handler(commands=["deleteLobby"])
def deleteLobby(message):
    bot.deleteSessionByMessage(message)

@bot.bot.callback_query_handler(func=lambda call: True)
def callback(call):
    """Handle callback queries from inline keyboard buttons.

    :param call: Callback query object.
    :return: None
    """
    bot.callback(call)




bot.bot.infinity_polling()
