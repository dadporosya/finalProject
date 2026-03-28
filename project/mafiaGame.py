from turtledemo.clock import current_day
from project import games
import math
from typing import get_type_hints
import random
from project import _helpers as h

TEAM_IDS = {
    "civilian": 0,
    "mafia": 1
}

class Role:
    def __init__(self, session:games.Game, playerId: int = -1):
        self.name = self.__class__.__name__
        self.TEAMS = ("civilian", "mafia")
        self.teamId = None
        self.activeAtNight = False
        self.special = False
        self.maxCount = 1
        self.hideTeam = True

        self.session = session
        self.playerId = playerId
    
    def send_message(self, recipientId:int, text:str):
        return self.session.bot.bot.send_message(recipientId, text)
    
    def nightAction(self):
        print("NIGHT ACTION", self.name)

    def dayAction(self):
        print(self.playerId)
        msg = self.send_message(self.playerId, "Now, text your speech! Make it good enough!")
        return msg
        # self.session.bot.bot.register_next_step_handler(msg, self.processDayAction)

    def processDayAction(self, message):
        def sendSpeech(recipientId:int):
            text = f"Here is {self.session.playersDictIdName[self.playerId]}'s speech:"
            self.send_message(recipientId, text)
            self.send_message(recipientId, message.text)

        # self.session.doActionForUsers(h.tupleWithout(self.session.playersIds, tuple(self.playerId)), sendSpeech) #TODO: uncomm
        self.session.doActionForUsers(self.session.playersIds, sendSpeech)

        self.send_message(self.playerId, "Sent successfully!")

    def killPlayer(self, playerId):
        self.session.killPlayer(playerId)


class Mafia(Role):
    def __init__(self, session, playerId: int = -1):
        super().__init__(session, playerId)

        self.teamId = TEAM_IDS["mafia"]
        self.activeAtNight = True
        self.hideTeam = False

    def nightAction(self):
        self.session.votingState = "kill"
        def sendKillingList(recipientId: int):
            votingButtons = [self.session.skipLabel]
            votingCallbackValues = ["skip"]
            for pid in self.session.playersIds:
                if pid in self.session.deadPlayers:
                    continue
                votingButtons.append(self.session.playersDictIdName[pid])
                votingCallbackValues.append(str(pid))

            votingMarkup = self.session.bot.generateInlineMarkup(
                tuple(votingButtons),
                callbackValues=tuple(votingCallbackValues),
                callbackHeader=self.session.callbackDefaultLabel + self.session.callbackVotingLabel
            )
            text = "Vote for a player to kill! Player with the most mafia votes dies!"
            self.session.bot.bot.send_message(recipientId, text, reply_markup=votingMarkup)

        # send for mafia
        # self.session.doActionForAllUsers(sendKillingList)

        # activeMafia = self.session.getActiveMafia()
        # self.session.doActionForUsers(h.tupleWithout(self.session.playersIds, tuple(activeMafia)), sendKillingList)

        super().nightAction()
        sendKillingList(self.playerId)



class Civilian(Role):
    def __init__(self, session, playerId: int = -1):
        super().__init__(session, playerId)

        self.teamId = TEAM_IDS["civilian"]


class Commissar(Role):
    def __init__(self, session, playerId: int = -1):
        super().__init__(session, playerId)

        self.teamId = TEAM_IDS["civilian"]
        self.activeAtNight = True
        self.special = True
        self.maxCount = 1

    def nightAction(self):
        self.send_message(self.playerId, "youp, you are commisare dudeee")


class MafiaGame(games.Game):
    def __init__(self, bot, sessionId: int):
        super().__init__(bot, sessionId)
        '''
            self.bot : bot
            self.sessionId : int
            self.playersIds : tuple[int]
            self.playersNames : tuple[str]
            self.playerCount : int
        '''
        self.MAFIA_DISTRIBUTION = 0.25

        rawRoles = [Mafia, Civilian, Commissar]
        self.ROLES = {}
        for role in rawRoles:
            self.ROLES[role.__name__] = role

        self.rolesDistribution = {}
        for role in rawRoles:
            self.rolesDistribution[role.__name__] = 0

        self.playersRoles: dict[int, Role] = {}

        self.nightsCount = 0

        self.startingPlayerInd = random.randint(0, self.playerCount - 1)

        self.callbackDefaultLabel = str(self.sessionId) + self.bot.callbackGap + "MafiaGame" + self.bot.callbackGap
        self.callbackVotingLabel = "voting" + self.bot.callbackGap
        self.callbackExecutionLabel = "execution" + self.bot.callbackGap
        self.callbackKillingLabel = "killing" + self.bot.callbackGap
        self.callbackAllVotingLabels = [
            self.callbackKillingLabel, self.callbackExecutionLabel, self.callbackVotingLabel
        ]

        self.currentVoting: dict[str, int] = {"skip":0,}
        self.deadPlayers:list[int] = []
        self.alivePlayers:list[int] = []
        self.clearVoting()

        self.skipLabel = "skip"

        self.neededVoteCount=0
        self.votingState="execution"

        self.activeRoleInd = 0
        self.activePlayers:list[int] = []


        self.createVoting()


    def killPlayer(self, playerId, alertMessage=False):
        self.deadPlayers.append(playerId)
        # if alertMessage:
        #     self.bot.bot.send_message(playerId, "You have been killed!")
        # try:
        #     self.alivePlayers.remove(playerId)
        # except:
        #     pass

        self.sendForAllUsers(f"{self.playersDictIdName[playerId]} was violently murdered!")


        self.checkWinCondition()

    def checkWinCondition(self) -> bool:
        teams = self.getAllAlivePlayersInTeam()
        alivePlayers = self.playerCount - len(self.deadPlayers)
        civilianCount = 0
        mafiaCount = 0
        try:
            civilianCount = len(teams[TEAM_IDS["civilian"]])
        except:
            pass
        try:
            mafiaCount = len(teams[TEAM_IDS["mafia"]])
        except:
            pass

        winner:int|None = None
        print("checkwin:", civilianCount, mafiaCount, alivePlayers)
        if mafiaCount == 0:
            # civilians win
            winner = TEAM_IDS["civilian"]
        # if mafiaCount >= alivePlayers - mafiaCount:
        #     # mafia win
        #     winner = TEAM_IDS["mafia"]

        if winner is None:
            return False

        print(winner)
        self.win(winner)
        return True


    def win(self, winnerTeamId:int):
        print(f"winnerTeamId: {winnerTeamId}")
        key = h.getKey(TEAM_IDS, winnerTeamId)
        print(key)
        if TEAM_IDS.get(key) is None:
            print("invalidId")
            return
        self.sendForAllUsers(f"{key} team wins!".upper())
        for pid, role in self.playersRoles.items():
            text = "You lose!"
            if role.teamId == winnerTeamId:
                text = "You win!"
            self.bot.bot.send_message(pid, text)

        self.end()

    def end(self):
        self.sendForAllUsers("Game was finished!")
        self.bot.endGame(self.sessionId)

        self.bot.activeGames[self.sessionId] = MafiaGame(self.bot, self.sessionId)
        del self


    def createVoting(self):
        for pid in self.playersIds:
            self.currentVoting[pid] = 0

    def clearVoting(self):
        for k in self.currentVoting.keys():
            self.currentVoting[k] = 0

    def nextRoleTurn(self, newRoleInd:int=None):
        if newRoleInd is not None:
            self.activeInd = newRoleInd
        else:
            self.activeRoleInd += 1
        print(self.activeRoleInd)
        self.nightActionRoutine()

    def getAllPlayersOfRole(self, role) -> tuple[int, ...]:
        selected = []
        for pid in self.playersIds:
            if pid in self.deadPlayers:
                continue
            if type(self.playersRoles[pid]) != role:
                continue
            selected.append(pid)
        return tuple(selected)

    def getAllPlayersInTeams(self) -> dict[int, list[int]]:
        teams: dict[int, list[int]] = {}

        for player_id, role in self.playersRoles.items():
            team_id = role.teamId

            if team_id is None:
                continue  # skip roles without team

            if team_id not in teams:
                teams[team_id] = []

            teams[team_id].append(player_id)

        return teams

    def getAllAlivePlayersInTeam(self) -> dict[int, list[int]]:
        teams: dict[int, list[int]] = {}

        for player_id, role in self.playersRoles.items():
            if player_id in self.deadPlayers:
                continue
            team_id = role.teamId

            if team_id is None:
                continue  # skip roles without team

            if team_id not in teams:
                teams[team_id] = []


            teams[team_id].append(player_id)

        return teams



    def getActiveMafia(self) -> tuple[int, ...]:
        return self.getAllPlayersOfRole(Mafia)

    def callback(self, call):
        data = call.data

        if not data.startswith(self.callbackDefaultLabel):
            return
        data:str = data[len(self.callbackDefaultLabel):]

        for label in self.callbackAllVotingLabels:
            if data.startswith(label):
                proces = label
                self.voteCallback(call, str(data[len(self.callbackVotingLabel):]))


        self.bot.bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

    def voteCallback(self, call, data):


        if self.currentVoting.get(data) is None:
            return

        if data == self.skipLabel:
            text = "You voted for skipping the voting..."
        else:
            text = f"You voted for {self.playersDictIdName[data]}!"

        self.currentVoting[data] += 1
        self.bot.bot.send_message(call.message.chat.id, text)
        print(self.currentVoting.values())
        if sum(self.currentVoting.values()) < self.neededVoteCount:
            return
        print(data, self.votingState)
        if self.votingState == "execution":
            self.dayRoutineProcessVoting()
        elif self.votingState == "kill":
            self.killActionProcessVoting()

    def dayRoutineProcessVoting(self):
        voted = h.maxFromDict(self.currentVoting)
        if self.skipLabel in voted or len(voted) < 1:
            self.sendForAllUsers("Voting was canceled")
        elif len(voted) > 1:
            self.sendForAllUsers("Tie! Voting was canceled!")
        else:
            executedId = voted[0]
            self.sendForAllUsers(f"{self.playersDictIdName[executedId]} was executed! He was a {self.playersRoles[executedId].name}!")
            self.killPlayer(executedId, alertMessage=True)

        self.gameRoutine()

    def killActionProcessVoting(self):
        voted = h.maxFromDict(self.currentVoting)
        victim = random.choice(voted)
        if victim == self.skipLabel:
            self.sendForUsers(tuple(self.activePlayers), "Voting skipped")
        else:
            self.sendForUsers(tuple(self.activePlayers), f"{self.playersDictIdName[victim]} has been killed!")
            self.killPlayer(victim)
            #TODO: append to list, that would be shown after night

        self.nextRoleTurn()


    def getPlayersWithRoles(self, roleName: str) -> list[int]:
        return [
            player_id
            for player_id, role in self.playersRoles.items()
            if role.name == roleName
        ]


    def createDistribution(self, mafiaCount=-1, mafiaDistribution=-1):
        if mafiaDistribution <= 0:
            mafiaDistribution = self.MAFIA_DISTRIBUTION
        if mafiaCount <= 0:
            _ = self.playerCount * mafiaDistribution
            mafiaCount = round(_) if random.random() > 0.5 else math.ceil(_)

        mafiaCount = max(1, mafiaCount)

        self.rolesDistribution[Civilian.__name__] = self.playerCount - mafiaCount
        self.rolesDistribution[Mafia.__name__] = mafiaCount


    def start(self):
        if sum(self.rolesDistribution.values()) <= 0:
            self.createDistribution()
        self.assignRoles()
        self.roleReveal()
        self.gameRoutine()

    def assignRoles(self) -> None:
        # Step 1: build a list of roles according to distribution
        roles_list = []

        for role_name, count in self.rolesDistribution.items():
            role_class = self.ROLES[role_name]
            roles_list.extend([role_class] * count)

        # Step 2: safety check
        if len(roles_list) != self.playerCount:
            raise ValueError("Roles count does not match number of players")

        # Step 3: shuffle roles randomly
        random.shuffle(roles_list)

        # Step 4: assign roles to players
        self.playersRoles = {}

        for player_id, role_class in zip(self.playersIds, roles_list):
            role_instance = role_class(self, player_id)
            role_instance.session = self
            self.playersRoles[player_id] = role_instance

        print(self.playersRoles)

    def roleReveal(self) -> None:
        def send_role(player_id: int) -> None:
            role = self.playersRoles.get(player_id)

            if role is None:
                return  # safety check

            text = f"Your role is: {role.name}"

            # Optional: include team info if not hidden
            if not role.hideTeam:
                # Find all players with the same team
                teammates = []

                for pid, r in self.playersRoles.items():
                    if r.teamId == role.teamId:
                        # get index to access name
                        try:
                            idx = self.playersIds.index(pid)
                            teammates.append(self.playersNames[idx])
                        except ValueError:
                            continue

                if len(teammates) > 0:
                    text += "\nYour team is:\n"
                    text += ", ".join(teammates)

            self.bot.bot.send_message(player_id, text)

        self.doActionForAllUsers(send_role)

    def gameRoutine(self):
        if self.checkWinCondition():
            return

        self.startNightRoutine()

    def startDayRoutine(self):
        self.clearVoting()
        self.sendForAllUsers("It's day time buddies!")

        self.dayRoutineSpeeches()

    def startNightRoutine(self):
        self.nightsCount += 1
        self.sendForAllUsers(f"It's night number {self.nightsCount}")
        self.activeRoleInd = -1
        self.nextRoleTurn()


    def nightActionRoutine(self):
        if self.activeRoleInd >= len(self.ROLES):
            self.startDayRoutine()
            return

        role = tuple(self.ROLES.values())[self.activeRoleInd]
        r = role(session=self)
        print("Role night::::", r.name)
        if not r.activeAtNight:
            self.nextRoleTurn()
            return

        self.clearVoting()

        self.activePlayers = self.getPlayersWithRoles(role.__name__)
        self.neededVoteCount = len(self.activePlayers)
        self.clearVoting()
        if self.neededVoteCount <= 0:
            self.nextRoleTurn()
            return
        for player in self.activePlayers:
            if player in self.deadPlayers:
                continue
            self.playersRoles[player].nightAction()


    def speechRoutine(self, playerInd:int, cycleCount:int):
        if cycleCount >= self.playerCount:
            #continue day routine
            self.dayRoutineVoting()
            return

        def sendSpeechProcess(message):
            self.playersRoles[activePlayerId].processDayAction(message)
            self.speechRoutine((playerInd + 1) % self.playerCount, cycleCount + 1)

        activePlayerId = self.playersIds[playerInd]

        if activePlayerId in self.deadPlayers:
            self.speechRoutine((playerInd + 1) % self.playerCount, cycleCount + 1)
            print(self)
            return

        msg = self.playersRoles[activePlayerId].dayAction()
        (self.playersRoles[activePlayerId].
        session.bot.bot.register_next_step_handler(
            msg, sendSpeechProcess))


    def dayRoutineSpeeches(self):
        # every player will send their speech
        self.startingPlayerInd = (self.startingPlayerInd + 1) % self.playerCount
        self.speechRoutine(self.startingPlayerInd, 0)


    def dayRoutineVoting(self):
        self.clearVoting()
        self.neededVoteCount = self.playerCount - len(self.deadPlayers)
        self.votingState = "execution"

        def sendVoting(recipientId: int):
            votingButtons = [self.skipLabel]
            votingCallbackValues = ["skip"]
            for pid in self.playersIds:
                if pid in self.deadPlayers:
                    continue
                votingButtons.append(self.playersDictIdName[pid])
                votingCallbackValues.append(str(pid))

            votingMarkup = self.bot.generateInlineMarkup(
                tuple(votingButtons),
                callbackValues=tuple(votingCallbackValues),
                callbackHeader=self.callbackDefaultLabel + self.callbackVotingLabel
            )
            self.bot.bot.send_message(recipientId, "Select a player to vote!", reply_markup=votingMarkup)

        # self.doActionForAllUsers(sendVoting)
        self.doActionForUsers(h.tupleWithout(self.playersIds, tuple(self.deadPlayers)), sendVoting)





