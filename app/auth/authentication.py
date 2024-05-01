"""
Defines authentication functions and endpoints for API requests and related attributes.

This is a part where user in BE needs to be authenticated in the beginning of the app.
The user can sign up, login, delete account, reset his password if forgotten or edit his data.
Except of that, this module also checks accessibility of user by his automatically
generated token.

A brief overview of exported classes and their usage:
    router = APIRouter()
        in any request, example:
            @router.post("/api/signup/")

    security = HTTPBearer()
        in the authorization requests of user, example:
            async def edit_profile(request: Request, credentials: HTTPAuthorizationCredentials
                = Depends(security)):

    new_user = CreateUser()
        for the functions that validate inputs of user, example:
             new_user.validate_input(username=username, email=email, password=password,
                confirm_password=confirm_password) and new_user.validate_email(email=email)

    secure_password = Tokenization()
        for generating tokens and hashing user's password, example:
            salty_password = secure_password.password_salting()

    for handling database connection:
        pool = psycopg2.pool.SimpleConnectionPool(
                        minconn=1,
                        maxconn=10,
                        dbname=settings.DATABASE_NAME_SERVER,
                        host=settings.DATABASE_HOST,
                        port=settings.DATABASE_PORT,
                        user=settings.DATABASE_USER,
                        password=settings.DATABASE_PASSWORD
                    )
"""

import re
import uuid

import jwt
from fastapi import APIRouter, Request, HTTPException, Depends
import psycopg2.pool
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from app.auth.CreateUser import CreateUser
from app.auth.Tokenization import Tokenization
from app.config.config import settings

router = APIRouter()
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth")

pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=settings.DATABASE_NAME_SERVER,
    host=settings.DATABASE_HOST,
    port=settings.DATABASE_PORT,
    user=settings.DATABASE_USER,
    password=settings.DATABASE_PASSWORD
)


@router.post("/api/signup/")
async def signup(request: Request) -> JSONResponse:
    """
    Registers user and handles his data.

    Retrieves user's input data as username, email, password and confirmation password,
    then validate them and put into database.

    Args:
       request:
        Body of the post request. Request instance of the FastAPI.

    Returns:
       A JSONResponse of the HTTP/HTTPS status code of the request with
       description content. For example:

           If the user is created successfully:
               INFO:     127.0.0.1:61359 - "POST /api/signup/ HTTP/1.1" 201 Created
               {
                   "detail": "Created: User created successfully"
               }

           If the user is trying to register with the already existing email in the database:
               INFO:     127.0.0.1:61957 - "POST /api/signup/ HTTP/1.1" 400 Bad Request
               {
                    "detail": "Bad request: Email already exists."
               }

           If the user wrote invalid input:
               INFO:     127.0.0.1:62019 - "POST /api/signup/ HTTP/1.1" 403 Forbidden
               {
                    "detail": "Forbidden: Access forbidden."
               }

           If the user wrote invalid input, the field is missing:
               INFO:     127.0.0.1:62059 - "POST /api/signup/ HTTP/1.1" 400 Bad Request
               {
                    "detail": "Bad request: All fields are required."
               }

       Returned response is always JSON object with HTTP/HTTPS status code.

    Raises:
       HTTPException: An error occurred in the SQL query or database connection.
        psycopg2.Error instance with status code 500.
       HTTPException: An error occurred, Internal server error. Its is
            a general exception. Exception instance with status code 500.
    """
    try:
        input = await request.json()
        username = input.get("username")
        email = input.get("email")
        password = input.get("password")
        confirm_password = input.get("confirm_password")

        if not (username and email and password and confirm_password):
            return JSONResponse(status_code=400, content={"detail": "Bad request: All fields are required."})

        is_email = await email_exists(email)
        if not is_email:
            salty_password, hashed_password = await generate_hashed_password(username, email, password, confirm_password)

            if salty_password is None and hashed_password is None:
                return JSONResponse(status_code=403, content={"detail": "Forbidden: Access forbidden."})

            generated_uuid = uuid.uuid4()
            conn = pool.getconn()
            cursor = conn.cursor()
            query = ("""INSERT INTO users_auth
                        VALUES (%s, %s, %s, %s, %s)""")
            cursor.execute(query, (str(generated_uuid), username, email, salty_password, hashed_password))
            conn.commit()
            cursor.close()
            pool.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "Created: User created successfully"})
        return JSONResponse(status_code=400, content={"detail": "Bad request: Email already exists."})
    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


async def generate_hashed_password(username: str, email: str, password: str, confirm_password: str):
    """
    Generating a hash password according to input user's password.

    Retrieves user's input data as username, email, password and confirmation password,
    and validate this data. Then generate password by Tokenization class functions.

    Args:
       username:
        User's input of username.
       email:
        User's input of email.
       password:
        User's input of password.
       confirm_password:
        User's input of confirm_password.

    Returns:
       A tuple of salty_password and hashed_password or if not successful then None and None.
       For example:
            user password is: "125"

            the salty_password is: "c188d9111ecd9c8310c4775afdb2f166"
            the hashed_password is: "bb1ca6e6c5ce37d2020c62097d43734baa6ea3f0d99b978b624b9c98fea23d25"


       Returned response is always tuple. The salty password is important due to security of
       the user's data.

    Raises:
       HTTPException: An error occurred, Internal server error. Its is
            a general exception. Exception instance with status code 500.
    """
    try:
        if check_signup_input(username, email, password, confirm_password):
            secure_password = Tokenization()
            salty_password = secure_password.password_salting()
            hashed_password = secure_password.password_hashing(password, salty_password)
            return salty_password, hashed_password
        return (None, None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


def check_signup_input(username:str, email:str, password: str, confirm_password: str) -> bool:
    """
    Validates user input and checks equality of passwords.

    Retrieves user's input data as username, email, password and confirmation password,
    and validate this data.

    Args:
      username:
       User's input of username.
      email:
       User's input of email.
      password:
       User's input of password.
      confirm_password:
       User's input of confirm_password.

    Returns:
      A boolean value (True or False).

      If is everything correct then True. If not then False.

      Returned response is always boolean.
    """
    new_user = CreateUser()
    return check_passwords_equality(password, confirm_password) and new_user.validate_input(username=username, email=email, password=password,
                                                                confirm_password=confirm_password) and new_user.validate_email(email=email)


def check_passwords_equality(password: str, confirm_password: str) -> bool:
    """
    Checks passwords equality between argument password and confirm_password.
    They should be the same.

    Retrieves user's input data of password and confirmation password.

    Args:
      password:
       User's input of password.
      confirm_password:
       User's input of confirm_password.

    Returns:
      A boolean value (True or False).

      If the passwords are equal then True. If not then False.

      Returned response is always boolean.
    """
    return password == confirm_password


async def email_exists(email: str) -> bool:
    """
    Checking if the email is already in the database.

    Retrieves user's input data of an email and searching
    email in the database by SQL query.

    Args:
       email:
        User's input of email.

    Returns:
       A boolean value (True or False).

       If the email is not in the database then False. If does exist then True.

       Returned response is always boolean.

    Raises:
       HTTPException: An error occurred, Internal server error. Its is
            a general exception. Exception instance with status code 500.
    """
    try:
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT EXISTS(SELECT 1 FROM users_auth WHERE email=%s)""")
        cursor.execute(query, (email, ))
        result = cursor.fetchone()[0]
        cursor.close()
        pool.putconn(conn)
        if result == 0:
            return False
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail={f"Internal server error: {e}"})

@router.post("/api/login/")
async def login(request: Request):
    """
    Logins user into the system and generates jwt bearer token for authorization.

    Retrieves user's input data as username and password to login into system.

    Args:
       request:
        Body of the post request. Request instance of the FastAPI.

    Returns:
       A JSONResponse of the HTTP/HTTPS status code of the request with
       description content or jwt token with status code 200 OK. For example:

           If the user is login successfully:
               INFO:     127.0.0.1:56045 - "POST /api/login/ HTTP/1.1" 200 OK
               {
                    "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjBmYmIwNmQzLThlMjEtNDdmOC1hYjhiLWZiYjFkZWMxOGI0NCJ9.56AYBki0mTphIyHpYnQqh1Agc-070KynBIl9Zlsiy5M"
                }

          If the user is not login successfully:
            INFO:     127.0.0.1:56097 - "POST /api/login/ HTTP/1.1" 401 Unauthorized
            {
                "detail": "Unauthorized"
            }

          If the one of the inputs (username, password) is misssing:
            INFO:     127.0.0.1:57299 - "POST /api/login/ HTTP/1.1" 400 Bad Request
            {
                "detail": "Bad request"
            }

        Returned response is always JSON object with HTTP/HTTPS status code.

    Raises:
       HTTPException: An error occurred, Internal server error. Its is
        a general exception. Exception instance with status code 500.
    """
    try:
        user_input = await request.json()
        username = user_input.get("username")
        password = user_input.get("password")
        if not username or not password:
            return JSONResponse(status_code=400, content={"detail": "Bad request"})

        user_token = await get_user(username, password)

        if user_token and user_token is not False:
            return {"jwt_token": user_token}

        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={f"Internal server error: {e}"})


async def get_user(username: str, password: str):
    """
    Function from the login process to find user in the system
    according to his name and password by SQL query.

    Retrieves user's input data as username and password to login into system.

    Args:
      username:
        User's input of username.
      password:
        User's input of password.

    Returns:
        A generated jwt token or boolean. For example:

        If the user is found in the database:
          jwt token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjBmYmIwNmQzLThlMjEtNDdmOC1hYjhiLWZiYjFkZWMxOGI0NCJ9.56AYBki0mTphIyHpYnQqh1Agc-070KynBIl9Zlsiy5M
        else:
            False

    Returned response is a boolean value or generate jwt token
    as a response to the login function.
    """
    conn = pool.getconn()
    cursor = conn.cursor()
    query = ("""SELECT *
                   FROM users_auth
                   WHERE username= %s""")
    cursor.execute(query, (username,))
    record = cursor.fetchone()
    cursor.close()
    pool.putconn(conn)

    if record is not None and len(record) == 5:
        hashed_password = record[4]
        salty_password = record[3]
        get_password = Tokenization()
        new_hashed_password = get_password.password_hashing(password, salty_password)

        if check_passwords_equality(hashed_password, new_hashed_password):
            user_id = record[0]
            jwt_token = get_password.jwt_token_generalization({"id": user_id})
            return jwt_token
        else:
            return False
    else:
        return False


@router.put("/api/forgotten-password/")
async def forgotten_password(request: Request) -> JSONResponse:
    """
    If the user forgotten password, this function can change/update his password
    and generate new hashed password.

    Retrieves user's input data as email, password, confirm_password into system.

    Args:
       request:
        Body of the post request. Request instance of the FastAPI.

   Returns:
       A JSONResponse of the HTTP/HTTPS status code of the request with
       description content. For example:

       If the password is changed successfully:
           INFO:     127.0.0.1:58563 - "PUT /api/forgotten-password/ HTTP/1.1" 200 OK
           {
                "detail": "OK: Password updated successfully"
           }

       If one of the input values are missing:
            INFO:     127.0.0.1:58751 - "PUT /api/forgotten-password/ HTTP/1.1" 400 Bad Request
            {
               "detail": "Bad request: All fields are required."
            }

       If the email is invalid:
            INFO:     127.0.0.1:58876 - "PUT /api/forgotten-password/ HTTP/1.1" 403 Forbidden
            {
                "detail": "Forbidden: Access forbidden."
            }

    Returned response is always JSON object with HTTP/HTTPS status code.

   Raises:
       HTTPException: An error occurred in the SQL query or database connection.
        psycopg2.Error instance with status code 500.
       HTTPException: An error occurred, Internal server error. Its is
            a general exception. Exception instance with status code 500.
    """
    try:
        input = await request.json()
        email = input.get("email")
        password = input.get("password")
        confirm_password = input.get("confirm_password")

        if not (email and password and confirm_password):
            return JSONResponse(status_code=400, content={"detail": "Bad request: All fields are required."})

        is_email = await email_exists(email)
        if not is_email:
            return JSONResponse(status_code=403, content={"detail": "Forbidden: Access forbidden."})

        salty_password, hashed_password = await generate_new_hashed_password(password, confirm_password)

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""UPDATE users_auth
                      SET password_salt = %s, password_hash = %s
                      WHERE email = %s """)
        cursor.execute(query, (salty_password, hashed_password, email))
        conn.commit()
        cursor.close()
        pool.putconn(conn)
        return JSONResponse(status_code=200, content={"detail": "OK: Password updated successfully"})
    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


async def generate_new_hashed_password(password: str, confirm_password: str) -> (str, str):
    """
    Generates new hashed password after signup or forgotten password.

    Retrieves user's input data as password and confirm_password into system.

    Args:
      password:
        User's input of password.
      confirm_password:
        User's input of confirm_password.

    Returns:
      Tuple of salty_password and hashed_password or unsuccessful status.
      For example:

      If successful:
        (4ab5a6eeb8c11c58158b5b91880f6bd3, ff17345a32fe7cdfe1b47b8ac37c4979cc5f6e9a0487448c082b5a83d4164fa0)
      else:
        "status": "Passwords are not equal." error 500


    Returned response is tuple or JSON object

    Raises:
      HTTPException: An error occurred, Internal server error. Its is
           a general exception. Exception instance with status code 500.
    """
    try:
        if check_passwords_equality(password, confirm_password):
            secure_password = Tokenization()
            salty_password = secure_password.password_salting()
            hashed_password = secure_password.password_hashing(password, salty_password)
            return salty_password, hashed_password
        else:
            return {"status": "Passwords are not equal."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.patch("/api/edit_profile/")
async def edit_profile(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Edits profile of user, by updating his data from the user input.
    Always can be change only one data at once of user.

    Retrieves user's input data as username, email, password and confirmation password,
    then validate them and update in database.

    Args:
       request:
        Body of the post request. Request instance of the FastAPI.
       credentials:
        Bearer token to authorize. HTTPAuthorizationCredentials instance
        with security instance of HTTPBearer.

    Returns:
       A JSONResponse of the HTTP/HTTPS status code of the request with
       description content. For example:

           If the token is wrong:
               INFO:     127.0.0.1:60478 - "PATCH /api/edit_profile/ HTTP/1.1"" 403 Forbidden
               {
                    "Forbidden: Invalid token"
               }

           if the input is missing, nothing is updated:
                INFO:     127.0.0.1:60478 - "PATCH /api/edit_profile/ HTTP/1.1" 200 OK
                {
                    "status": "No changes were made."
                }

           If the input is correct and user is authorized, as example email:
                INFO:     127.0.0.1:60599 - "PATCH /api/edit_profile/ HTTP/1.1" 200 OK
                {
                    "detail": "OK: Email updated successfully."
                }

           If the input is correct and user is authorized, but email already exists,
            as example email:
                INFO:     127.0.0.1:60652 - "PATCH /api/edit_profile/ HTTP/1.1" 500 Internal Server Error
                {
                    "detail": "Email is not updated, check id or email."
                }

       Returned response is always JSON object with HTTP/HTTPS status code.

    Raises:
       HTTPException: An error occurred, Internal server error. Its is
            a general exception. Exception instance with status code 500.
    """
    try:
        token_access_value = await token_access(credentials)

        if token_access_value is None:
            return JSONResponse(status_code=404, content={"Not Found": "User not found."})

        input = await request.json()
        id = token_access_value
        username = input.get("username")
        email = input.get("email")
        password = input.get("password")
        confirm_password = input.get("confirm_password")

        if not (username or email or password or confirm_password):
            return {"status": "No changes were made."}

        if edit_only_username_or_email(username, email, password, confirm_password):
            is_changed = await edit_username(username, id)
            if is_changed:
                return JSONResponse(status_code=200, content={"detail": "OK: Username updated successfully."})
            return JSONResponse(status_code=500, content={"detail": "Username is not updated, check id."})
        elif edit_only_username_or_email(email, username, password, confirm_password):
            is_changed = await edit_email(email, id)
            if is_changed:
                return JSONResponse(status_code=200, content={"detail": "OK: Email updated successfully."})
            return JSONResponse(status_code=500, content={"detail": "Email is not updated, check id or email."})
        elif edit_only_password(password, confirm_password, username, email):
            is_changed = await edit_password(password, confirm_password, id)
            if is_changed:
                return JSONResponse(status_code=200, content={"detail": "OK: Password updated successfully."})
            return JSONResponse(status_code=500, content={"detail": "Password is not updated, check id."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


def edit_only_username_or_email(attribute_to_change: str, stay_attribute: str, password: str, confirm_password: str) -> bool:
    """
    Checks if the user wants to change username or email.

    Args:
      attribute_to_change:
        User's input of username or email.
      stay_attribute:
        User's input of username or email.
        If is in the attribute_to_change username then in this will be email and vice versa.
        The wanted value is None.
      password:
        User's input of password, the wanted value is None.
      confirm_password:
        User's input of confirm_password, the wanted value is None.

    Returns:
      A boolean value (True or False).

      If the attribute_to_change is True an others are False, then return True.
      Else return False.

      Returned response is always boolean.
    """
    return attribute_to_change is not None and not stay_attribute and not password and not confirm_password


async def edit_username(username: str, id: str) -> bool:
    """
    If the user choose to edit username, then this function handles it
    by SQL query updating database data of user.

    Args:
     username:
        User's input of username  to change/update.
     id:
        Id of user from the token.

    Returns:
     A boolean value. For example:

     If the username is changed successfully:
        Then returns True.
     Else:
        Returns False.

    Returned response is always boolean.

    Raises:
     HTTPException: An error occurred in the SQL query or database connection.
      psycopg2.Error instance with status code 500.
     HTTPException: An error occurred, Internal server error. Its is
          a general exception. Exception instance with status code 500.
    """
    try:
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""UPDATE users_auth
                    SET username = %s
                    WHERE id = %s""")
        cursor.execute(query, (username, id))
        conn.commit()
        cursor.close()
        pool.putconn(conn)

        if cursor.rowcount > 0:
            return True
        else:
            return False

    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


async def edit_email(email: str, id: str) -> bool:
    """
    If the user choose to edit email, then this function handles it
    by SQL query updating database data of user.

    Args:
     email:
        User's input of email  to change/update.
     id:
        Id of user from the token.

    Returns:
     A boolean value. For example:

     If the email is changed successfully:
        Then returns True.
     Else:
        Returns False.

    Returned response is always boolean.

    Raises:
     HTTPException: An error occurred in the SQL query or database connection.
      psycopg2.Error instance with status code 500.
     HTTPException: An error occurred, Internal server error. Its is
          a general exception. Exception instance with status code 500.
    """
    try:
        new_user = CreateUser()
        is_email = await email_exists(email)
        if not is_email and new_user.validate_email(email=email):
            conn = pool.getconn()
            cursor = conn.cursor()
            query = ("""UPDATE users_auth
                        SET email = %s
                        WHERE id = %s""")
            cursor.execute(query, (email, id))
            conn.commit()
            cursor.close()
            pool.putconn(conn)

            if cursor.rowcount > 0:
                return True
            else:
                return False
        return False
    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


def edit_only_password(password: str, confirm_password: str, username: str, email: str) -> bool:
    """
    Checks if the user wants to change password.

    Args:
     password:
       User's input of password.
     confirm_password:
       User's input of confirm_password.
     username:
       User's input of username, the wanted value is None.
     email:
       User's input of email, the wanted value is None.

    Returns:
     A boolean value (True or False).

     If the password and confirm_password is True an others are False, then return True.
     Else return False.

     Returned response is always boolean.
    """
    return password is not None and confirm_password is not None and not username and not email


async def edit_password(password: str, confirm_password: str, id: str) -> bool:
    """
    If the user choose to edit password, then this function handles it
    by SQL query updating database data of user.

    Args:
     password:
        User's input of password to change/update.
     confirm_password:
        User's input of confirm_password to check equality with password.
     id:
        Id of user from the token.

    Returns:
     A boolean value. For example:

     If the password is changed successfully:
        Then returns True.
     Else:
        Returns False.

    Returned response is always boolean.

    Raises:
     HTTPException: An error occurred in the SQL query or database connection.
      psycopg2.Error instance with status code 500.
     HTTPException: An error occurred, Internal server error. Its is
          a general exception. Exception instance with status code 500.
    """
    try:
        salty_password, hashed_password = await generate_new_hashed_password(password, confirm_password)

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""UPDATE users_auth
                              SET password_salt = %s, password_hash = %s
                              WHERE id = %s""")
        cursor.execute(query, (salty_password, hashed_password, id))
        conn.commit()
        cursor.close()
        pool.putconn(conn)

        if cursor.rowcount > 0:
            return True
        else:
            return False

    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.delete("/api/delete_account/")
async def delete_account(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Deletes whole user's data from the system.

    Args:
       credentials:
        Bearer token to authorize. HTTPAuthorizationCredentials instance
        with security instance of HTTPBearer.

    Returns:
       A JSONResponse of the HTTP/HTTPS status code of the request with
       description content. For example:

           If the token is wrong:
               INFO:     127.0.0.1:62356 - "DELETE /api/delete_note HTTP/1.1" 500 Internal Server Error
               {
                    "detail": "Internal server error: cannot access local variable 'token_access'
                    where it is not associated with a value"
               }

           If the user is deleted successfully:
                INFO:     127.0.0.1:62476 - "DELETE /api/delete_account/ HTTP/1.1" 200 OK
                {
                    "detail": "OK: Account deleted successfully."
                }

       Returned response is always JSON object with HTTP/HTTPS status code.

    Raises:
       HTTPException: An error occurred in the SQL query or database connection.
            psycopg2.Error instance with status code 500.
       HTTPException: An error occurred, Internal server error. Its is
            a general exception. Exception instance with status code 500.
    """
    try:
        token_access_value = await token_access(credentials)

        if token_access_value is None:
            return JSONResponse(status_code=404, content={"Not Found": "User not found."})


        user_id = token_access_value

        if not user_id:
            raise HTTPException(status_code=400, detail="Bad Request: User ID is required.")

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""DELETE FROM users_auth
                        WHERE id = %s""")
        cursor.execute(query, (user_id,))
        conn.commit()
        cursor.close()
        pool.putconn(conn)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not Found: User not found.")

        return JSONResponse(status_code=200, content={"detail": "OK: Account deleted successfully."})

    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


async def token_access(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
   Check if the user is authorized.

   Args:
      credentials:
       Bearer token to authorize. HTTPAuthorizationCredentials instance
       with security instance of HTTPBearer.

   Returns:
      Value of the user_id or value None. For example:

          If the user_id is not found in the token, then return None.

          If the user_id is found in the token, then return its value.

   Raises:
      HTTPException: Token expired or is no longer available.
           jwt.ExpiredSignatureError instance with status code 401.
      HTTPException: Forbidden: Invalid token.
           jwt.InvalidTokenError instance with status code 403.
   """
    try:
        token = credentials.credentials
        decoded_token = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])

        user_id = decoded_token.get("id")
        if user_id:
            db_user_id = await get_user_id(user_id)
            if db_user_id[0] is None:
                return None

            if user_id == db_user_id[0]:
                return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid token")


async def get_user_id(id: str):
    """
    Finds user_id in the database according to user id from the token in the sent parameter.

    Args:
       id:
        User id from the bearer token.

    Returns:
        Value of the user_id as a result variable or value None. For example:

          If the user_id is not found in the database, then return None.

          If the user_id is found in the database, then return its value.

    Raises:
       HTTPException: An error occurred, Internal server error. Its is
            a general exception. Exception instance with status code 500.
    """
    try:
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                       FROM users_auth
                       WHERE id= %s""")
        cursor.execute(query, (id,))
        result = cursor.fetchone()
        cursor.close()
        pool.putconn(conn)

        if cursor.rowcount == 0:
            return None
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={f"Internal server error: {e}"})
