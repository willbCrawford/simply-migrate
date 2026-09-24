from enum import Enum


class SimplyMigrateValidFolders(str, Enum):
    CURRENT_DIRECTORY = ""
    MIGRATIONS = "migrations"
    DATA = "data"
    HOTFIX = "hotfix"