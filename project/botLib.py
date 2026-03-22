import telebot
# from pygame.examples.audiocapture import callback
from telebot import types
from project.dbManager import DbManager


class B:  # bot
    def __init__(self, token: str, dbManager: DbManager):
        """Initialize bot wrapper with TeleBot and database manager.

        :param token: Telegram bot token.
        :param dbManager: DbManager instance for persistence.
        :return: None
        """
        self.bot = telebot.TeleBot(token)
        self.dbManager = dbManager

        # callbacks
        self.callbackGap = '_'
        self.callbackReplaceSessionHeader = "repSes" + self.callbackGap

    def generateInlineMarkup(self, buttons: list[str], callbackHeader="", rowWidth=2):
        """Generate inline keyboard markup with callback data values.

        :param buttons: Button labels.
        :param callbackHeader: Prefix for callback_data.
        :param rowWidth: Buttons per row.
        :return: TeleBot InlineKeyboardMarkup object.
        """
        markup = types.ReplyKeyboardMarkup(row_width=rowWidth, resize_keyboard=True)

        for btn in buttons:
            markup.add(types.InlineKeyboardButton(btn, callback_data=callbackHeader + btn.lower()))

        return markup

    def generateKeyboardMarkup(self, buttons: list[str], rowWidth=2):
        """Generate keyboard markup with regular reply buttons.

        :param buttons: Button labels.
        :param rowWidth: Buttons per row.
        :return: TeleBot ReplyKeyboardMarkup object.
        """
        markup = types.ReplyKeyboardMarkup(row_width=rowWidth, resize_keyboard=True)

        for btn in buttons:
            markup.add(types.KeyboardButton(btn))

        return markup

    def callback(self, call):
        """Handle callback queries from inline buttons.

        :param call: Callback query object.
        :return: None
        """
        if call.data == self.callbackReplaceSessionHeader + "yes":
            self.replaceSession(call.message)
        elif call.data == self.callbackReplaceSessionHeader + "no":
            pass

    def start(self, message):
        """Handle /start command by forwarding to registration flow if player exists.

        :param message: Telegram message object.
        :return: None
        """
        if self.dbManager.checkIfExistPlayer(playerId=message.chat.id):
            self.registration(message)

    def registration(self, message):
        """Ask user for username and start username processing.

        :param message: Telegram message object.
        :return: None
        """
        exist = self.dbManager.checkIfExistPlayer(playerId=message.chat.id)
        if exist:
            answer = "You have already been registered! Enter new username:"
        else:
            answer = "Enter your username:"

        msg = self.bot.send_message(message.chat.id, answer)
        self.bot.register_next_step_handler(msg, self.processUsername, exist)

    def processUsername(self, message, exist: bool):
        """Create or update player record based on existing state.

        :param message: Telegram message object.
        :param exist: Existing user flag.
        :return: None
        """
        username = message.text
        if exist:
            self.dbManager.updatePlayer(userId=message.chat.id, userName=username)
            self.bot.send_message(message.chat.id, "Username has been changed successfully!")
        else:
            self.dbManager.addPlayer(userId=message.chat.id, userName=username)
            self.bot.send_message(message.chat.id, "Successfully registered!")

    def createSession(self, message):
        """Initiate session creation flow; ask for lobby name or ask to replace existing.

        :param message: Telegram message object.
        :return: None
        """
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
        """Delete existing session and ask for a new lobby name.

        :param message: Telegram message object.
        :return: None
        """
        self.dbManager.deleteSession(message.chat.id)
        answer = "Enter lobby's name:"
        msg = self.bot.send_message(message.chat.id, answer)
        self.bot.register_next_step_handler(msg, self.processAddSession)

    def processAddSession(self, message):
        """Create a session using the message chat ID and text as name.

        :param message: Telegram message object.
        :return: None
        """
        hostId = message.chat.id
        sessionName = message.text
        self.dbManager.createSession(hostId, sessionName)
        self.bot.send_message(message.chat.id, f"Successfully created lobby {'"'+sessionName+'"'}!")

    def processReplaceSession(self, message):
        """Prompt user to confirm creating a new session when one already exists.

        :param message: Telegram message object.
        :return: None
        """
        markup = self.generateInlineMarkup(["Yes", "No"], callbackHeader=self.callbackReplaceSessionHeader)
        self.bot.send_message(message.chat.id, "Would you like to create a new one?", reply_markup=markup)

    def joinSession(self, message):
        """Ask user for lobby name to join.

        :param message: Telegram message object.
        :return: None
        """
        answer = "Enter lobby's name:"
        msg = self.bot.send_message(message.chat.id, answer)
        self.bot.register_next_step_handler(msg, self.processJoinSession)

    def processJoinSession(self, message):
        """Add user to lobby if lobby is found by name.

        :param message: Telegram message object.
        :return: None
        """
        lobbyName = message.text
        lobbyId = self.dbManager.getSessionIdByName(lobbyName)
        if lobbyId == -1:
            self.bot.send_message(message.chat.id, "Lobby is not found :(")
            return

        self.dbManager.addPlayerToSession(message.chat.id, lobbyId)
        self.bot.send_message(message.chat.id, "Successfully added")





