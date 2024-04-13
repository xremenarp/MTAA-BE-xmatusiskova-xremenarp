import re


class CreateUser():
    username: str
    email: str
    password: str

    def validate_input(self, **kwargs) -> bool:
        return True if self.check_length_input(**kwargs) else False

    def check_length_input(self, **kwargs) -> bool:
        return len(kwargs['username']) <= 255 and len(kwargs['email']) <= 255 and len(kwargs['password']) <= 255 and len(kwargs['confirm_password']) <= 255

    def validate_email(self, **kwargs) -> bool:
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        return bool(re.fullmatch(regex, kwargs['email']))

