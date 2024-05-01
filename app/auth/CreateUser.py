"""
This file is focused on user's input to validates it.
"""

import re


class CreateUser:
    """
    class CreateUser specifies user's input

    Attributes:
        username: A string representing a name of user.
        email: A string representing an email of user.
        password: A string representing a password of user.
    """
    username: str
    email: str
    password: str

    def validate_input(self, **kwargs) -> bool:
        """
        Checks user's input length.

        Args:
          kwargs:
            Represents keywords arguments.

        Returns:
          A boolean value (True or False).

          If the function check_length_input return True, then return True.
          Else return False.

          Returned response is always boolean.
        """
        return True if self.check_length_input(**kwargs) else False

    def check_length_input(self, **kwargs) -> bool:
        """
        Checks user's input length, if they meet database requirements.

        Args:
         kwargs:
           Represents keywords arguments of user's input.

        Returns:
         A boolean value (True or False).

         If the kwargs arguments are all true, then return True.
         Else return False.

         Returned response is always boolean.
        """
        return len(kwargs['username']) <= 255 and len(kwargs['email']) <= 255 and len(kwargs['password']) <= 255 and len(kwargs['confirm_password']) <= 255

    def validate_email(self, **kwargs) -> bool:
        """
        Checks if the email looks as email. If the input meets requirements for email.

        Args:
         kwargs:
           Represents keywords arguments of user's input.
           Should be an email.

        Returns:
         A boolean value (True or False).

         By using re library it will check regex with value and decide
         if it is true or not.

         Returned response is always boolean.
        """
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        return bool(re.fullmatch(regex, kwargs['email']))

