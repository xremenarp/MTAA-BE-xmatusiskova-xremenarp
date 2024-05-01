"""
This file is focused on password security and jwt token generalization.
"""

import os
from hashlib import pbkdf2_hmac
import jwt
from app.config.config import settings


class Tokenization():
    """
    Tokenization class for handling token-related operations.

    This class provides methods for password salting, password hashing,
    and JWT token generalization.

    Attributes:
        access_token: The access token string.
        token_type: The type of token.
    """
    access_token: str
    token_type: str

    # https://medium.com/@karthikeyan.ranasthala/build-a-jwt-based-authentication-rest-api-with-flask-and-mysql-5dc6d3d1cb82
    def password_salting(self) -> str:
        """
        Generate a random salt for password salting.

        Returns:
            string: The generated salt in hexadecimal format.
        """
        salt = os.urandom(16)
        return salt.hex()

    def password_hashing(self, original_pass: str, salty_pass: str) -> str:
        """
        Generate a hashed password using PBKDF2-HMAC.

        Args:
            original_pass: The original password from user's input.
            salty_pass: The salted password generated from password_salting function.

        Returns:
            string: The hashed password in hexadecimal format.
        """
        hashed_pass = pbkdf2_hmac(
            "sha256",
                b"%b" % bytes(original_pass, "utf-8"),
                b"%b" % bytes(salty_pass, "utf-8"),
            10000,
        )
        return hashed_pass.hex()

    #

    def jwt_token_generalization(self, content: dict) -> str:
        """
        Generate a JWT token with the provided content.
        The content representing JSON object, in this case user id.

        Args:
            content: The content to be encoded into the token.

        Returns:
            string: The encoded JWT token.
        """
        encoded_content = jwt.encode(content, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_content




