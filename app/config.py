from os import getenv

DATABASE_URL = getenv("DATABASE_URL", "sqlite:///./payments.db")
