import pytest
import os

from app import create_app
from app.extensions import db


from app.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL_TEST", "mysql+pymysql://root:84916325@127.0.0.1:3306/edms_db_test")
    JWT_SECRET_KEY = "test-jwt"
    SECRET_KEY = "test-secret"

@pytest.fixture()
def app():
    app = create_app(TestConfig)
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    import re
    from sqlalchemy import create_engine, text
    m = re.match(r"(mysql\+pymysql://[^/]+)/([^?]+)", uri)
    if m:
        base_uri, db_name = m.group(1), m.group(2)
        try:
            temp_engine = create_engine(base_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
                conn.commit()
            temp_engine.dispose()
        except Exception as e:
            print(f"Warning: failed to auto-create test database: {e}")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("SET FOREIGN_KEY_CHECKS = 0;"))
                for table_name in db.metadata.tables.keys():
                    conn.execute(db.text(f"DROP TABLE IF EXISTS `{table_name}`;"))
                conn.execute(db.text("SET FOREIGN_KEY_CHECKS = 1;"))
                conn.commit()
        except Exception as e:
            print(f"Warning: failed to drop test database tables cleanly: {e}")


@pytest.fixture()
def client(app):
    return app.test_client()
