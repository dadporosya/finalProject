import sqlite3 as sql3
from project import _helpers as h

class DbManager:
    """Database manager for players, sessions, and used words."""

    def __init__(self, path="db.db"):
        """Initialize SQLite connection and ensure required tables exist.

        :param path: Path to SQLite file (default 'db.db').
        :return: None
        """
        self.path = path
        self.con = sql3.connect(self.path, check_same_thread=False)
        self.cur = self.con.cursor()
        self.createTables()

        games = self.getAllGames()
        if "Mafia" not in games:
            self.addGame("Mafia")



    def createTables(self):
        """Create sessions, players, and usedWords tables if missing.

        :return: None
        """
        with self.con:
            self.con.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    gameId INTEGER PRIMARY KEY,
                    name TEXT
                )
            ''')
            self.con.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    sessionId INTEGER PRIMARY KEY,
                    name TEXT,
                    currentTurnPlayerId INTEGER,
                    started BOOLEAN,
                    gameId INTEGER DEFAULT NULL,
                    FOREIGN KEY(currentTurnPlayerId) REFERENCES players(playerId),
                    FOREIGN KEY(gameId) REFERENCES games(gameId)
                )
            ''')
            self.con.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    playerId INTEGER PRIMARY KEY,
                    chatId INTEGER,
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

    def executemany(self, sql: str, data: tuple[tuple]) -> None:
        """Execute many prepared statements with data tuples.

        :param sql: SQL query with placeholders.
        :param data: Tuples of parameter values.
        :return: None
        """
        with self.con:
            self.con.executemany(sql, data)
            self.con.commit()

    def execute(self, sql: str, data: tuple):
        """Execute a single SQL command with parameters.

        :param sql: SQL query with placeholders.
        :param data: Parameters to bind.
        :return: None
        """
        with self.con:
            self.con.execute(sql, data)
            self.con.commit()

    def select_data(self, sql: str, data=tuple()) -> list[tuple]:
        """Execute a select query and return all results.

        :param sql: SELECT query string.
        :param data: Parameters for query.
        :return: Rows as list of tuples.
        """
        with self.con:
            self.cur.execute(sql, data)
            return self.cur.fetchall()

    # USER MANAGEMENT
    def getPlayerNameById(self, playerId: int) -> str | None:
        """Return player name by ID or -1 if not found.

        :param playerId: Player ID.
        :return: Player name or -1.
        """

        query = """
            SELECT name
            FROM players
            WHERE playerId = ?
            LIMIT 1
        """

        with self.con:
            data = self.select_data(query, (playerId,))
            if len(data) > 0:
                return data[0][0]
            return None  # not found

    def addPlayer(self, userId: int, chatId: int, userName: str, sessionId=-1) -> None:
        """Insert a player record; optionally assign to a session.

        :param userId: Player ID.
        :param chatId: Player chat ID.
        :param userName: Player username.
        :param sessionId: Optional session ID (default -1).
        :return: None
        """
        query = """
            INSERT INTO players (playerId, chatId, name) VALUES (?, ?, ?)
        """
        with self.con:
            self.con.execute(query, (userId, chatId, userName))
            self.con.commit()

        if sessionId != -1:
            self.addPlayerToSession(userId, sessionId)

    def updatePlayer(self, userId: int, chatId: int, userName: str, sessionId=-1) -> None:
        """Update a player's chat ID and name; optionally assign to a session.

        :param userId: Player ID.
        :param chatId: New chat ID.
        :param userName: New username.
        :param sessionId: Optional session ID (default -1).
        :return: None
        """
        query = """
            UPDATE players
            SET chatId = ?, name = ?
            WHERE playerId = ?
        """
        with self.con:
            self.con.execute(query, (chatId, userName, userId))
            self.con.commit()

        if sessionId != -1:
            self.addPlayerToSession(userId, sessionId)

    def addPlayerToSession(self, userId: int, sessionId: int) -> None:
        """Assign an existing player to a session.

        :param userId: Player ID.
        :param sessionId: Target session ID.
        :return: None
        """
        query = """
                UPDATE players
                SET sessionId = ?
                WHERE playerId = ?
            """
        with self.con:
            self.con.execute(query, (sessionId, userId))
            self.con.commit()

    def removePlayer(self, userId: int) -> None:
        """Remove player record by ID.

        :param userId: Player ID.
        :return: None
        """
        query = """
            DELETE FROM players
            WHERE playerId = ?
        """
        with self.con:
            self.con.execute(query, (userId,))
            self.con.commit()

    def checkIfExistPlayer(self, playerId: int) -> bool:
        """Return True if player exists, else False.

        :param playerId: Player ID to check.
        :return: Boolean existence flag.
        """
        query = """
            SELECT EXISTS(
                SELECT 1
                FROM players
                WHERE playerId = ?
            )
        """

        with self.con:
            return bool(self.select_data(query, (playerId,))[0][0])

    def getAllPlayersNamesInSession(self, sessionId: int) -> tuple[str, ...]:
        """Return all player names in a given session.

        :param sessionId: Session ID.
        :return: Tuple of player names.
        """
        query = """
            SELECT name
            FROM players
            WHERE sessionId = ?
        """

        with self.con:
            data = self.select_data(query, (sessionId,))
            return h.unnest(data)

    def getAllPlayersChatIdsInSession(self, sessionId: int) -> tuple[int, ...]:
        """Return all player chat IDs in a given session.

        :param sessionId: Session ID.
        :return: Tuple of player chat IDs.
        """
        query = """
            SELECT chatId
            FROM players
            WHERE sessionId = ?
        """

        with self.con:
            data = self.select_data(query, (sessionId,))
            return data

    def copyPlayer(self, playerId: int, times: int) -> None:
        """Copy a player N times with new IDs.

        :param playerId: ID of the player to copy.
        :param times: Number of copies to create.
        :return: None
        """
        query_get = """
            SELECT chatId, name, sessionId
            FROM players
            WHERE playerId = ?
        """
        data = self.select_data(query_get, (playerId,))

        if not data:
            raise ValueError("Player not found")

        chatId, name, sessionId = data[0]

        new_players = []
        for i in range(times):
            new_players.append((playerId+i+1, chatId, name, sessionId))

        query_insert = """
            INSERT INTO players (playerId, chatId, name, sessionId)
            VALUES (?, ?, ?, ?)
        """
        self.executemany(query_insert, tuple(new_players))


    def getPlayerSession(self, playerId: int) -> int | None:
        """Return the sessionId the player is currently in, or None if not in any session.

        :param playerId: Player ID.
        :return: Session ID or None.
        """

        query = """
            SELECT sessionId
            FROM players
            WHERE playerId = ?
            LIMIT 1
        """

        with self.con:
            data = self.select_data(query, (playerId,))
            if len(data) > 0:
                return data[0][0]  # can be None if not assigned
            return None  # player not found

    # WORD MANAGEMENT
    def checkWord(self, word: str, session: int) -> bool:
        """Return True if word was already used in a session, else False.

        :param word: Word to check.
        :param session: Session ID.
        :return: True if already used, False otherwise.
        """
        word = word.lower()

        queryCheck = """
            SELECT EXISTS(
                SELECT 1
                FROM usedWords
                WHERE word = ? AND sessionId = ?
            )
        """

        with self.con:
            existing = self.select_data(queryCheck, (word, session))
            if existing[0][0]:
                return True
            return False

    def addWord(self, word: str, session: int):
        """Add a word to usedWords for a session.

        :param word: Word to add.
        :param session: Session ID.
        :return: None
        """
        queryInsert = """
                    INSERT INTO usedWords (word, sessionId) VALUES (?, ?)
                """

        with self.con:
            self.con.execute(queryInsert, (word, session))
            self.con.commit()

    # SESSION MANAGEMENT
    def deleteSession(self, sessionId: int) -> None:
        """Delete a session and clean up related data.

        - Unassign all players from this session (set sessionId = NULL)
        - Delete all used words for this session
        - Delete the session itself

        :param sessionId: Session ID to delete.
        :return: None
        """
        unsignPlayersQuery = """
            UPDATE players
            SET sessionId = NULL
            WHERE sessionId = ?
        """

        deleteWordsQuery = """
            DELETE FROM usedWords
            WHERE sessionId = ?
        """

        deleteSessionQuery = """
            DELETE FROM sessions
            WHERE sessionId = ?
        """

        with self.con:
            self.con.execute(unsignPlayersQuery,(sessionId,))
            self.con.execute(deleteWordsQuery,(sessionId,))

            # 3. Delete the session
            self.con.execute(deleteSessionQuery,(sessionId,))
            self.con.commit()

    def createSession(self, hostId: int, sessionName: str):
        """Create a new session and assign host player to it.

        :param hostId: Host player ID.
        :param sessionName: Session name.
        :return: None
        """
        queryAddSession = """
            INSERT INTO sessions
            (sessionId, name, currentTurnPlayerId, started) VALUES(?,?,?,?)
        """

        with self.con:
            self.con.execute(queryAddSession, (hostId, sessionName, hostId, False))
            self.addPlayerToSession(hostId, hostId)
            self.con.commit()

    def checkIfSessionExists(self, hostId: int) -> bool:
        """Check whether a session with given hostId exists.

        :param hostId: Candidate session ID.
        :return: Boolean existence flag.
        """
        query = """
            SELECT EXISTS(
                SELECT 1
                FROM sessions
                WHERE sessionId = ?
            )
        """

        with self.con:
            return bool(self.select_data(query, (hostId,))[0][0])

    def getSessionIdByName(self, sessionName: str) -> int:
        """Return sessionId by name or -1 if not found.

        :param sessionName: Session name to look up.
        :return: Session ID or -1.
        """
        query = """
            SELECT sessionId
            FROM sessions
            WHERE name = ?
        """

        with self.con:
            data = self.select_data(query, (sessionName,))
            if len(data) > 0:
                return data[0][0]
            return -1  # not found

    def getSessionIdByChatId(self, chatId: int) -> int:
        """Return sessionId for a given player chat ID, or -1 if not found.

        :param chatId: Player chat ID.
        :return: Session ID or -1.
        """
        query = """
            SELECT sessionId
            FROM players
            WHERE chatId = ?
        """
        with self.con:
            data = self.select_data(query, (chatId,))
            if len(data) > 0:
                return data[0][0]
            return -1  # not found

    def startSession(self, sessionId: int):
        """Mark a session as started.

        :param sessionId: Session ID.
        :return: None
        """
        self.changeSessionsState(sessionId, 1)

    def endSession(self, sessionId: int):
        """Mark a session as ended.

        :param sessionId: Session ID.
        :return: None
        """
        self.changeSessionsState(sessionId, 0)

    def changeSessionsState(self, sessionId: int, state: int):
        """Update the started state of a session.

        :param sessionId: Session ID.
        :param state: New state value (1 = started, 0 = ended).
        :return: None
        """
        query = """
            UPDATE sessions
            SET started = ?
            WHERE sessionId = ?
        """

        with self.con:
            self.execute(query, (state, sessionId,))


    def getSessionNameById(self, sessionId: int) -> str:
        """Return session name by ID or -1 if not found.

        :param sessionId: Session ID.
        :return: Session name or -1.
        """

        query = """
            SELECT name
            FROM sessions
            WHERE sessionId = ?
            LIMIT 1
        """

        with self.con:
            data = self.select_data(query, (sessionId,))
            if len(data) > 0:
                return data[0][0]
            return -1  # not found

    # GAMES
    def getAllGames(self) -> tuple[str]:
        """Return all game names.

        :return: Tuple of game name strings.
        """
        query = """
            SELECT name
            FROM games
        """

        with self.con:
            data = self.select_data(query)
            print(data)
            if len(data) > 0:
                return h.unnest(tuple(data))
            return ("No games found",)

    def addGame(self, name: str):
        """Insert a new game with an auto-incremented ID.

        :param name: Game name.
        :return: None
        """
        query_max = "SELECT MAX(gameId) FROM games"
        with self.con:
            max_id = self.select_data(query_max)[0][0]
            next_id = 0 if max_id is None else max_id + 1
            query_insert = "INSERT INTO games (gameId, name) VALUES (?, ?)"
            self.con.execute(query_insert, (next_id, name))
            self.con.commit()

    def getGameIdByName(self, name: str) -> int:
        """Return gameId by name or -1 if not found.

        :param name: Game name.
        :return: Game ID or -1.
        """
        query = """
            SELECT gameId
            FROM games
            WHERE name = ?
            LIMIT 1
        """
        with self.con:
            data = self.select_data(query, (name,))
            if len(data) > 0:
                return data[0][0]
            return -1  # not found

    def getGameNameById(self, gameId: int) -> str:
        """Return game name by ID or -1 if not found.

        :param gameId: Game ID.
        :return: Game name or -1.
        """
        query = """
            SELECT name
            FROM games
            WHERE gameId = ?
            LIMIT 1
        """
        with self.con:
            data = self.select_data(query, (gameId,))
            if len(data) > 0:
                return data[0][0]
            return -1  # not found

    def setGameToSession(self, sessionId: int, gameId: int) -> None:
        """Assign a game to a session.

        :param sessionId: Target session ID.
        :param gameId: Game ID to assign.
        :return: None
        """
        query = """
            UPDATE sessions
            SET gameId = ?
            WHERE sessionId = ?
        """
        with self.con:
            self.con.execute(query, (gameId, sessionId))
            self.con.commit()

    def getGameIdBySessionId(self, sessionId: int) -> int:
        """Return the game ID assigned to a session, or -1 if none.

        :param sessionId: Session ID.
        :return: Game ID or -1.
        """
        query = """
            SELECT gameId
            FROM sessions
            WHERE sessionId = ?
            LIMIT 1
        """

        with self.con:
            data = self.select_data(query, (sessionId,))
            if len(data) > 0:
                return data[0][0]
            return -1  # not found

    def getGameBySessionId(self, sessionId: int) -> str:
        """Return the game name for a given session, or -1 if not found."""

        query = """
            SELECT g.name
            FROM sessions s
            JOIN games g ON s.gameId = g.gameId
            WHERE s.sessionId = ?
            LIMIT 1
        """

        with self.con:
            data = self.select_data(query, (sessionId,))
            if len(data) > 0:
                return data[0][0]
            return -1  # not found

    # OTHER
    def clearAll(self) -> None:
        """Drop all tables in the database."""
        tables = ["usedWords", "players", "sessions"]

        with self.con:
            for table in tables:
                self.con.execute(f"DROP TABLE IF EXISTS {table}")
            self.con.commit()


if __name__ == "__main__":
    dbManager = DbManager()

