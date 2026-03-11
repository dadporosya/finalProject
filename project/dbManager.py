import sqlite3 as sql3

class DbManager:
    def __init__(self, path="db.db"):
        self.path = path
        self.con = sql3.connect(self.path, check_same_thread=False)
        self.cur = self.con.cursor()
        self.createTables()

    def createTables(self):
        with self.con:
            self.con.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    sessionId INTEGER PRIMARY KEY,
                    name TEXT,
                    currentTurnPlayerId INTEGER,
                    started BOOLEAN,
                    FOREIGN KEY(currentTurnPlayerId) REFERENCES players(playerId)
                )
            ''')
            self.con.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    playerId INTEGER PRIMARY KEY,
                    name TEXT,
                    sessionId INTEGER,
                    FOREIGN KEY(sessionId) REFERENCES sessions(sessionId)
                )
            ''')
            self.con.execute('''
                CREATE TABLE IF NOT EXISTS usedWords (
                    sessionId INTEGER,
                    word TEXT,
                    FOREIGN KEY(sessionId) REFERENCES sessions(sessionId)
                )
            ''')
            self.con.commit()

    def __executemany(self, sql:str, data:tuple[tuple]) -> None:
        with self.con:
            self.con.executemany(sql, data)
            self.con.commit()

    def __execute(self, sql:str, data:tuple):
        with self.con:
            self.con.execute(sql, data)
            self.con.commit()

    def __select_data(self, sql:str, data=tuple()) -> list[tuple]:
        with self.con:
            self.cur.execute(sql, data)
            return self.cur.fetchall()

    #USER MANAGEMENT
    def addPlayer(self, userId: int, userName: str, sessionId=-1) -> None:
        query = """
            INSERT INTO players (playerId, name) VALUES (?, ?)
        """
        with self.con:
            self.con.execute(query, (userId, userName))
            self.con.commit()

        if sessionId != -1:
            self.addPlayerToSession(userId, sessionId)

    def updatePlayer(self, userId: int, userName: str, sessionId=-1) -> None:
        query = """
            UPDATE players
            SET name = ?
            WHERE playerId = ?
        """
        with self.con:
            self.con.execute(query, (userName, userId))
            self.con.commit()

        if sessionId != -1:
            self.addPlayerToSession(userId, sessionId)


    def addPlayerToSession(self, userId:int, sessionId:int) -> None:
        query = """
                UPDATE players
                SET sessionId = ?
                WHERE playerId = ?
            """
        with self.con:
            self.con.execute(query, (sessionId, userId))
            self.con.commit()


    def removePlayer(self, userId: int) -> None:
        query = """
            DELETE FROM players
            WHERE playerId = ?
        """
        with self.con:
            self.con.execute(query, (userId,))
            self.con.commit()


    def checkIfExistPlayer(self, playerId: int) -> bool:
        query = """
            SELECT EXISTS(
                SELECT 1
                FROM players
                WHERE playerId = ?
            )
        """

        with self.con:
            return bool(self.__select_data(query, (playerId,))[0][0])

    # WORD MANAGEMENT
    def checkAndAddWord(self, word:str, session:int) -> bool:
        """
            Add word to db if it is not exist
            False - such word exists. No action
            True - word has been successfully added
        """

        queryInsert = """
            INSERT INTO usedWords (word, sessionId) VALUES (?, ?)
        """
        queryCheck = """
            SELECT EXISTS(
                SELECT 1
                FROM usedWords
                WHERE word = ?
            )
        """

        with self.con:
            existing = self.__select_data(queryCheck, (word,))
            if existing[0][0]:
                return False

            self.con.execute(queryInsert, (word, session))
            self.con.commit()
            return True

    #SESSION MANAGEMENT
    def deleteSession(self, sessionId:int) -> None:
        tableTitles = [
            "sessions", "players", "usedWords"
        ]

        placeholder = "*table*"
        query = f"""
            DELETE FROM {placeholder}
            WHERE sessionId = ?
        """

        with self.con:
            for table in tableTitles:
                self.con.execute(query.replace(placeholder, table))
            self.con.commit()


    def createSession(self, hostId:int, sessionName:str):
        queryAddSession = """
            INSERT INTO sessions
            (sessionId, name, currentTurnPlayerId, started) VALUES(?,?,?,?)
        """

        with self.con:
            self.con.execute(queryAddSession, (hostId, sessionName, hostId, False))
            self.addPlayerToSession(hostId, hostId)
            self.con.commit()


    def checkIfSessionExists(self, hostId: int) -> bool:
        query = """
            SELECT EXISTS(
                SELECT 1
                FROM sessions
                WHERE sessionId = ?
            )
        """

        with self.con:
            return bool(self.__select_data(query, (hostId,))[0][0])


    def getSessionIdByName(self, sessionName : str) -> int:
        query = """
            SELECT FROM sessions
            WHERE name = ?
        """

        with self.con:
            data = self.__select_data(query, (sessionName,))
            if len(data) > 0:
                return data[0][0]
            else:
                return -1 # not found






