from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Инициализация ORM без привязки к конкретному экземпляру приложения (паттерн Application Factory)
db = SQLAlchemy(model_class=Base)
