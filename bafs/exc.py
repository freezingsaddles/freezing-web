class InvalidAuthorizationToken(RuntimeError):
    pass


class NoTeamsError(RuntimeError):
    pass


class MultipleTeamsError(RuntimeError):
    def __init__(self, teams):
        self.teams = teams


class CommandError(RuntimeError):
    pass


class DataEntryError(ValueError):
    pass