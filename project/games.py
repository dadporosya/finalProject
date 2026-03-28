from random import randint
from typing import Callable

from project import botLib
from project import dbManager
from project import _helpers as h

class Game:
    def __init__(self, bot, sessionId: int):
        self.bot: botLib.B = bot
        self.sessionId = sessionId

        self.playersIds = h.unnest(bot.dbManager.getAllPlayersChatIdsInSession(sessionId))
        self.playersNames = h.unnest(bot.dbManager.getAllPlayersNamesInSession(sessionId))

        self.playerCount = len(self.playersIds)

        self.playersDictIdName = {}
        for i in range(self.playerCount):
            self.playersDictIdName[self.playersIds[i]] = self.playersNames[i]

        print(self.playersIds)
        print(self.playersNames)



        self.activeInd = randint(0, self.playerCount - 1)

    def start(self):
        pass

    def end(self):
        pass

    def showSettings(self, message):
        pass

    def callback(self, call):
        pass

    def doActionForUsers(self, users: tuple[int, ...], action: Callable[[int], None]) -> None:
        for user in users:
            action(user)

    def doActionForAllUsers(self, action : Callable[[int], None]) -> None:
        self.doActionForUsers(self.playersIds, action)

    def sendForUsers(self, users:tuple[int, ...], text:str):
        def sendMessage(recipientId:int):
            self.bot.bot.send_message(recipientId, text)
        self.doActionForUsers(users, sendMessage)

    def sendForAllUsers(self, text:str=""):
        def sendMessage(recipientId:int):
            self.bot.bot.send_message(recipientId, text)
        self.doActionForAllUsers(sendMessage)


class WordGame(Game):
    def __init__(self, bot, sessionId: int):
        super().__init__(bot, sessionId)

        self.previousWord = ''

        self.maxMistakesCount = 3

    def showSettings(self, message):
        text = f"""
            Settings:\n
            Max Mistakes Count: {self.maxMistakesCount}
        """
        

    def nextPlayer(self):
        self.activeInd = (self.activeInd + 1) % self.playerCount

    def start(self):
        super().start()
        self.gameTurnCoroutine()

    def gameTurnCoroutine(self):
        activePlayerId = self.playersIds[self.activeInd]
        if self.previousWord:
            self.bot.bot.send_message(activePlayerId, f"Previous word: {self.previousWord}")

        text = "Type a new word!"
        if not self.previousWord:
            text = "Type a start word!"

        msg = self.bot.bot.send_message(activePlayerId, text)
        self.bot.bot.register_next_step_handler(msg, self.processWord, activePlayerId)

    def processWord(self, message, playerId:int):
        exist = self.bot.dbManager.checkWord(message.text, self.sessionId)
        if exist:
            self.bot.bot.send_message(playerId, "This word has been already used!")
        elif self.previousWord and message.text[0].lower() != self.previousWord[-1].lower():
            self.bot.bot.send_message(playerId, "Word must start with the first letter of previous word!")
        else:
            self.bot.dbManager.addWord(message.text, self.sessionId)
            self.previousWord = message.text
            self.nextPlayer()

        self.gameTurnCoroutine()
        return






