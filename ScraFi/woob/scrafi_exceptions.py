
"""ScraFi's custom exceptions"""


class WrongCredentialsError(Exception):
    pass


class IdNotFoundError(Exception):
    pass


class NoHistoryError(Exception):
    pass


class NoBillError(Exception):
    pass


class WebsiteError(Exception):
    pass


class DateLimitError(Exception):
    pass