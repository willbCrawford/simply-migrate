from sqlalchemy import create_engine

class DatabaseConnectionManager:
    """Manages database connections for tenants"""

    def __init__(self, connection_string: str):
        self.connections = {}
        self.connection_string = connection_string

    def create_engine(self):
        return create_engine(self.connection_string)