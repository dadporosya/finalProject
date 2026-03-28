import telebot
# from pygame.examples.audiocapture import callback
from telebot import types
from project.dbManager import DbManager
from project import games
from project import _helpers as h
from project import mafiaGame

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
        self.callGameNameHeader = "game" + self.callbackGap

        self.activeGames: dict[int, games.Game] = dict()

    def checkIfSessionExistsByMessage(self, message) -> bool:
        return self.checkIfSessionExists(message.chat.id)

    def checkIfSessionExists(self, chatId:int) -> bool:
        exist = self.dbManager.checkIfSessionExists(chatId)
        if not exist:
            text = "You haven't created a lobby yet. Please you cmd /create in the first place."
            self.bot.send_message(chatId,text)

        return exist

    def getPlayerSessionByMessage(self, message) -> int:
        return self.getPlayerSession(message.chat.id)

    def getPlayerSession(self, playerId:int) -> int:
        sessionId = self.dbManager.getPlayerSession(playerId)
        if not sessionId:
            text = "You haven't created of joined a lobby yet. Please you cmd /create or /join in the first place."
            self.bot.send_message(playerId, text)

        return sessionId

    def generateInlineMarkup(self, buttons: tuple[str, ...], callbackHeader="", callbackValues:tuple=None, rowWidth=2):
        """Generate inline keyboard markup with callback data values.

        :param buttons: Button labels.
        :param callbackHeader: Prefix for callback_data.
        :param rowWidth: Buttons per row.
        :return: TeleBot InlineKeyboardMarkup object.
        """
        markup = types.InlineKeyboardMarkup(row_width=rowWidth)

        for i in range(len(buttons)):
            btn = buttons[i]
            callbackData = callbackHeader + btn.lower()
            try:
                callbackData = callbackHeader + callbackValues[i]
            except:
                pass
            markup.add(types.InlineKeyboardButton(btn, callback_data=callbackData))

        return markup

    def generateKeyboardMarkup(self, buttons: tuple[str, ...], rowWidth=2):
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
        print("Callback: ", call.data)

        for game in self.activeGames.values():
            game.callback(call)

        if call.data == self.callbackReplaceSessionHeader + "yes":
            self.replaceSession(call.message)
        elif call.data == self.callbackReplaceSessionHeader + "no":
            self.bot.send_message(call.message.chat.id, "okey dokey")

    def start(self, message):
        """Handle /start command by forwarding to registration flow if player exists.

        :param message: Telegram message object.
        :return: None
        """
        if self.dbManager.checkIfExistPlayer(playerId=message.from_user.id):
            self.registration(message)

    def registration(self, message):
        """Ask user for username and start username processing.

        :param message: Telegram message object.
        :return: None
        """
        exist = self.dbManager.checkIfExistPlayer(playerId=message.from_user.id)
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
            self.dbManager.updatePlayer(
                userId=message.from_user.id,
                chatId=message.chat.id,
                userName=username
            )
            self.bot.send_message(message.chat.id, "Username has been changed successfully!")
        else:
            self.dbManager.addPlayer(
                userId=message.from_user.id,
                chatId=message.chat.id,
                userName=username
            )
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
            self.processReplaceSession(message)
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
        self.bot.send_message(message.chat.id, f"Successfully created lobby {'"' + sessionName + '"'}!")

        self.chooseGameForSession(message)

    def processReplaceSession(self, message):
        """Prompt user to confirm creating a new session when one already exists.

        :param message: Telegram message object.
        :return: None
        """
        markup = self.generateInlineMarkup(("Yes", "No",), callbackHeader=self.callbackReplaceSessionHeader)
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

        self.dbManager.addPlayerToSession(message.from_user.id, lobbyId)
        self.bot.send_message(lobbyId, f"{self.dbManager.getPlayerNameById(message.chat.id)} joined!")
        self.bot.send_message(message.chat.id, "Successfully added")

    def showGamesList(self, message):
        self.bot.send_message(message.chat.id, ', '.join(self.dbManager.getAllGames()))

    def chooseGameForSession(self, message):
        markup = self.generateKeyboardMarkup(self.dbManager.getAllGames())
        msg = self.bot.send_message(message.chat.id, "Choose a game:", reply_markup=markup)
        print("choose game")
        self.bot.register_next_step_handler(msg, self.setGameToSession)

    def setGameToSession(self, message):
        gameId = self.dbManager.getGameIdByName(message.text)
        if gameId == -1:
            self.bot.send_message(message.chat.id, "Invalid game name")
            return

        exist = self.dbManager.checkIfSessionExists(message.chat.id)
        if not exist:
            self.bot.send_message(message.chat.id,
                                  "You haven't created a lobby yet. Please you cmd /create in the first place.")
            return

        self.dbManager.setGameToSession(message.chat.id, gameId)
        self.bot.send_message(message.chat.id, f"You have changed game to {message.text} successfully!")

    def showSessionInfo(self, message):
        sessionId = self.getPlayerSessionByMessage(message)
        if not sessionId:
            return
        print(sessionId)
        self.bot.send_message(message.chat.id, "Current session info:")
        self.bot.send_message(message.chat.id,f"Name: \"{self.dbManager.getSessionNameById(sessionId)}\"")
        self.showPlayers(userId=message.chat.id, sessionId=sessionId)
        currentGame = self.dbManager.getGameBySessionId(sessionId)
        text = f"Current game: {currentGame}"

        self.bot.send_message(message.chat.id, text)


    def showPlayers(self, message=None, userId=None, sessionId=None):

        if message:
            exist = self.checkIfSessionExistsByMessage(message)
            if not exist:
                return

        if not userId:
            userId = message.chat.id
        if not sessionId:
            sessionId = message.chat.id

        players = self.dbManager.getAllPlayersNamesInSession(sessionId)
        if len(players) > 0:
            self.bot.send_message(userId, f"Players: \n {h.joinNested(', ', players)}")
        else:
            self.bot.send_message(userId, "No players!")

    def startGame(self, message):
        exist = self.checkIfSessionExistsByMessage(message)
        if not exist:
            return

        gameType = self.dbManager.getGameIdBySessionId(message.chat.id)
        if gameType == -1:
            self.bot.send_message(message.chat.id, "You haven't chosen a game yet!")
            self.chooseGameForSession(message)
            return

        self.dbManager.startSession(message.chat.id)
        gameName = self.dbManager.getGameNameById(gameType)
        print(gameName)
        if gameName == "Cities":
            self.activeGames[message.chat.id] = games.WordGame(self, message.chat.id)
        elif gameName == "Mafia":
            self.activeGames[message.chat.id] = mafiaGame.MafiaGame(self, message.chat.id)
        else:
            self.bot.send_message(message.chat.id, "Invalid game name!")
            return

        self.activeGames[message.chat.id].start()

        print("started")

    def callEndGameWithMessage(self, message):
        self.endGame(message.chat.id)

    def endGame(self, chatId:int):
        exist = self.checkIfSessionExists(chatId)
        if not exist:
            return

        if not chatId in self.activeGames.keys():
            self.bot.send_message(chatId, "You haven't started a game yet! Use cmd /startGame")
            return

        self.dbManager.endSession(chatId)
        # del self.activeGames[chatId]
        text = "Your session has been finished. Would you like to create a new one? Use cmd /create!"
        self.bot.send_message(chatId, text)
        print("ended")

    def deleteSessionByMessage(self, message):
        self.deleteSession(message.chat.id)
        self.bot.send_message(message.chat.id, "Lobby was deleted successfully!")

    def deleteSession(self, sessionId):
        self.dbManager.deleteSession(sessionId)

    def copyPlayer(self, message):
        msg = self.bot.send_message(message.chat.id, "Copy count")


    def processCopy(self, message, copyCount: int = 1):
        self.dbManager.copyPlayer(message.from_user.id, int(message.text))

    def clearDB(self, message, sequentialInit=True):
        self.dbManager.clearAll()
        self.bot.send_message(message.chat.id, "DB cleared")
        if sequentialInit:
            self.initDB()

    def initDB(self):
        self.dbManager.createTables()

    def showCmds(self, message):
        text = """
        List of possible commands:
        /info - shows the list of possible commands
        /register - register in the bot (essential to participate in games)
        /create - create lobby
        /join - join lobby
        /show - shows information of current lobby
        /deleteLobby - deletes current lobby (if you are the host)
        /startGame - starts chosen game in the current lobby (only if you are the host of the lobby)
        /endGame - ends current game session (only if you are the host of the lobby)
        """
        self.bot.send_message(message.chat.id, text)

