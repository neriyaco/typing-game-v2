MSG_ASK_CLIENT_FOR_NICKNAME = "WhatIsYourNickname"

MSG_NICKNAME_ALREADY_TAKEN = "NameAlreadyTakenException"
MSG_NICKNAME_NOT_VALID = "InvalidNameException"

MSG_PLAYER_KICKED_BY_ADMIN = "UserKickedException"

MSG_WELCOME_TO_GAME = "WelcomeAboard"

MSG_IP_IS_BANNED = "IPBannedException"
MSG_NICKNAME_IS_BANNED = "NameBannedException"

MSG_START_GAME = "GameStarted"
MSG_PAUSE_GAME = "GamePaused"
MSG_RESUME_GAME = "GameResumed"

MSG_SERVER_QUIT = "ServerClosed"

MSG_INVALID_REQUEST = "InvalidRequestException"

MSG_GAME_TERMINATED = "GameTerminated"

MSG_PLAYER_ALREADY_HAS_NAME = "PlayerAlreadyHasNameException"

MSG_LANGUAGE_NOT_FOUND = "LanguageNotFoundException"


def get_nickname(data: bytes):
    return data.decode()
