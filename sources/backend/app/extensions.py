from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode="gevent")

class BaseModel(db.Model):
    __abstract__ = True
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

