from project import games
import math
from typing import get_type_hints
import random

class Role:
    def __init__(self, session, playerId: int = -1):
        self.name = self.__class__.__name__
        self.TEAMS = ("civilian", "mafia")
        self.teamId = None
        self.activeAtNight = False
        self.special = False
        self.maxCount = 1
        self.hideTeam = True

        self.session = session
        self.playerId = playerId

    def nightAction(self):
        pass


class Mafia(Role):
    def __init__(self, session, playerId: int = -1):
        super().__init__(session, playerId)

        self.teamId = 1
        self.activeAtNight = True
        self.hideTeam = False

    def nightAction(self):
        self.session.bot.bot.send_message(self.playerId, "go fvck yourself, really")


class Civilian(Role):
    def __init__(self, session, playerId: int = -1):
        super().__init__(session, playerId)

        self.teamId = 0


class Commissar(Role):
    def __init__(self, session, playerId: int = -1):
        super().__init__(session, playerId)

        self.teamId = 0
        self.activeAtNight = True
        self.special = True
        self.maxCount = 1

    def nightAction(self):
        self.session.bot.bot.send_message(self.playerId, "youp, you are commisare dudeee")


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

        self.playersRoles = {}

        self.nightsCount = 0

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

            self.bot.bot.send_message(player_id, text)

        self.doActionForAllUsers(send_role)

    def gameRoutine(self):
        self.nightRoutine()
        self.dayRoutine()

    def nightRoutine(self):
        self.nightsCount += 1
        for role in self.ROLES.values():
            r = role(session=self)
            if not r.activeAtNight:
                continue

            activePlayers = self.getPlayersWithRoles(role.__name__)
            for player in activePlayers:
                self.playersRoles[player].nightAction()


    def dayRoutine(self):
        def helloWorld(playerId:int):
            self.bot.bot.send_message(playerId, "helloup")

        self.doActionForAllUsers(helloWorld)





