import telebot
# from pygame.examples.audiocapture import callback
from telebot import types
from project.dbManager import DbManager


class B: # bot
    def __init__(self, token : str, dbManager : DbManager):
        self.bot = telebot.TeleBot(token)
        self.dbManager = dbManager

        # callbacks
        self.callbackGap = '_'
        self.callbackReplaceSessionHeader = "repSes" + self.callbackGap

    def generateInlineMarkup(self, buttons : list[str], callbackHeader="", rowWidth=2): # -> markup
        markup = types.ReplyKeyboardMarkup(row_width=rowWidth, resize_keyboard=True)

        for btn in buttons:
            markup.add(types.InlineKeyboardButton(btn, callback_data=callbackHeader+btn.lower()))

        return markup

    def generateKeyboardMarkup(self, buttons : list[str], rowWidth=2): # -> markup
        markup = types.ReplyKeyboardMarkup(row_width=rowWidth, resize_keyboard=True)

        for btn in buttons:
            markup.add(types.KeyboardButton(btn))

        return markup


    def callback(self, call):
        if   call.data == self.callbackReplaceSessionHeader + "yes":
            self.replaceSession(call.message)
        elif call.data == self.callbackReplaceSessionHeader + "no":
            pass


    def start(self, message):
        if self.dbManager.checkIfExistPlayer(playerId=message.chat.id):
            self.registration(message)


    def registration(self, message):
        exist = self.dbManager.checkIfExistPlayer(playerId=message.chat.id)
        if exist:
            answer = "You have already been registered! Enter new username:"
        else:
            answer = "Enter your username:"

        msg = self.bot.send_message(message.chat.id, answer)
        self.bot.register_next_step_handler(msg, self.processUsername, exist)


    def processUsername(self, message, exist:bool):
        username = message.text
        if exist:
            self.dbManager.updatePlayer(userId=message.chat.id, userName=username)
            self.bot.send_message(message.chat.id, "Username has been changed successfully!")
        else:
            self.dbManager.addPlayer(userId=message.chat.id, userName=username)
            self.bot.send_message(message.chat.id, "Successfully registered!")


    def createSession(self, message):
        exist = self.dbManager.checkIfSessionExists(message.chat.id)
        if exist:
            answer = "You have already been created a lobby."
            msg = self.bot.send_message(message.chat.id, answer)
            self.bot.register_next_step_handler(msg, self.processReplaceSession)
        else:
            answer = "Enter lobby's name"
            msg = self.bot.send_message(message.chat.id, answer)
            self.bot.register_next_step_handler(msg, self.processAddSession)


    def replaceSession(self, message):
        self.dbManager.deleteSession(message.chat.id)
        answer = "Enter lobby's name:"
        msg = self.bot.send_message(message.chat.id, answer)
        self.bot.register_next_step_handler(msg, self.processAddSession)


    def processAddSession(self, message):
        hostId = message.chat.id
        sessionName = message.text
        self.dbManager.createSession(hostId, sessionName)


    def processReplaceSession(self, message):
        markup = self.generateInlineMarkup(["Yes", "No"], callbackHeader=self.callbackReplaceSessionHeader)
        self.bot.send_message(message.chat.id, "Would you like to create a new one?", reply_markup=markup)


    def joinSession(self, message):
        answer = "Enter lobby's name:"
        msg = self.bot.send_message(message.chat.id, answer)
        self.bot.register_next_step_handler(msg, self.processJoinSession)


    def processJoinSession(self, message):
        lobbyName = message.text
        lobbyId = self.dbManager.getSessionIdByName(lobbyName)
        if lobbyId == -1:
            self.bot.send_message(message.chat.id, "Lobby is not found :(")
            return

        self.dbManager.addPlayerToSession(message.chat.id, lobbyId)
        self.bot.send_message(message.chat.id, "Successfully added")





