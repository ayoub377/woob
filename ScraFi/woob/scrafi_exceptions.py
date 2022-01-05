
"""ScraFi's custom exceptions"""


class WrongCredentialsError(Exception):
    pass


class IdNotFoundError(Exception):
    pass


class NoHistoryError(Exception):
    pass


class UserLengthError(Exception):
    pass


class PassLengthError(Exception):
    pass


class WebsiteError(Exception):
    pass