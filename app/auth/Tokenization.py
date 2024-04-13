import os
from hashlib import pbkdf2_hmac
import jwt
from app.config.config import settings

class Tokenization():
    access_token: str
    token_type: str

    # https://medium.com/@karthikeyan.ranasthala/build-a-jwt-based-authentication-rest-api-with-flask-and-mysql-5dc6d3d1cb82
    def password_salting(self) -> str:
        salt = os.urandom(16)
        return salt.hex()

    def password_hashing(self, original_pass: str, salty_pass: str) -> str:
        hashed_pass = pbkdf2_hmac(
            "sha256",
                b"%b" % bytes(original_pass, "utf-8"),
                b"%b" % bytes(salty_pass, "utf-8"),
            10000,
        )
        return hashed_pass.hex()

    #

    def jwt_token_generalization(self, content):
        encoded_content = jwt.encode(content, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_content




