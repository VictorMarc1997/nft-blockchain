import base64

from flask_sqlalchemy import SQLAlchemy
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True, unique=True, nullable=False)
    email = db.Column(db.String(80), unique=True)
    password = db.Column(db.String())
    address = db.Column(db.String(), default=None)
    admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def create_address(self, blockchain):
        if self.address is None:
            address = f"0x{secrets.token_hex(32)}"
            data = {
                "sender": "0",
                "receiver": address,
                "amount": 100
            }
            success, new_block = blockchain.new_transaction(data)
            if success and not new_block:
                blockchain.build_block()

            self.address = address

    @property
    def api_key(self):
        return f"{self.email}:{self.address}"

    def to_json(self):
        return {
            "email": self.email,
            "address": self.address,
            "admin": self.admin,
            "api_key": str(base64.b64encode(self.api_key.encode("utf-8")), "utf-8"),
        }

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<User {self.id}: {self.email}>"


class NFT(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True, unique=True, nullable=False)
    image = db.Column(db.String())
    token = db.Column(db.String())

    def create_token(self):
        if self.token is None:
            self.token = f"0x{secrets.token_hex(32)}"

    def to_json(self):
        return {
            "image": self.image,
            "token": self.token,
        }

    def __repr__(self):
        return f"<Art {self.id}: {self.token}>"
