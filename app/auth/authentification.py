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


async def generate_hashed_password(username: str, email: str, password: str, confirm_password: str) -> (str, str):
    try:
        if check_signup_input(username, email, password, confirm_password):
            secure_password = Tokenization()
            salty_password = secure_password.password_salting()
            hashed_password = secure_password.password_hashing(password, salty_password)
            return salty_password, hashed_password
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


def check_signup_input(username:str, email:str, password: str, confirm_password: str) -> bool:
    new_user = CreateUser()
    return check_passwords_equality(password, confirm_password) and new_user.validate_input(username=username, email=email, password=password,
                                                                confirm_password=confirm_password) and new_user.validate_email(email=email)


def check_passwords_equality(password: str, confirm_password: str) -> bool:
    return password == confirm_password


async def email_exists(email: str) -> bool:
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
    try:
        user_input = await request.json()
        username = user_input.get("username")
        password = user_input.get("password")
        if not username or not password:
            raise HTTPException(status_code=400, detail={"Bad request"})

        user_token = await get_user(username, password)

        if user_token and user_token is not False:
            return {"jwt_token": user_token}
        else:
            raise HTTPException(status_code=401, detail={"Unauthorized"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={f"Internal server error: {e}"})


async def get_user(username: str, password: str):
    conn = pool.getconn()
    cursor = conn.cursor()
    query = ("""SELECT *
                   FROM users_auth
                   WHERE username= %s""")
    cursor.execute(query, (username,))
    record = cursor.fetchone()
    cursor.close()
    pool.putconn(conn)

    if len(record) == 5:
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
    try:
        input = await request.json()
        email = input.get("email")
        password = input.get("password")
        confirm_password = input.get("confirm_password")

        if not (email and password and confirm_password):
            return JSONResponse(status_code=400, content={"detail": "Bad request: All fields are required."})

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT email
                    FROM users_auth
                    WHERE email= %s""")
        cursor.execute(query, (email,))

        record = cursor.fetchone()
        cursor.close()
        pool.putconn(conn)

        if check_email(record, email):
            JSONResponse(status_code=200, content={"detail": "OK: User found"})
        else:
            raise HTTPException(status_code=404, detail={"Not found: User not found"})

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


def check_email(record, email: str) -> bool:
    return record[0] == email


async def generate_new_hashed_password(password: str, confirm_password: str) -> (str, str):
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
    try:
        await token_acces(credentials)

        input = await request.json()
        id = input.get("id")
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
            raise HTTPException(status_code=500, detail="Username is not updated, check id.")
        elif edit_only_username_or_email(email, username, password, confirm_password):
            is_changed = await edit_email(email, id)
            if is_changed:
                return JSONResponse(status_code=200, content={"detail": "OK: Email updated successfully."})
            raise HTTPException(status_code=500, detail="Email is not updated, check id or email.")
        elif edit_only_password(password, confirm_password, username, email):
            is_changed = await edit_password(password, confirm_password, id)
            if is_changed:
                return JSONResponse(status_code=200, content={"detail": "OK: Password updated successfully."})
            raise HTTPException(status_code=500, detail="Password is not updated, check id.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


def edit_only_username_or_email(attribute_to_change: str, stay_attribute: str, password: str, confirm_password: str) -> bool:
    return attribute_to_change is not None and not stay_attribute and not password and not confirm_password


async def edit_username(username: str, id: str) -> bool:
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
    return password is not None and confirm_password is not None and not username and not email


async def edit_password(password: str, confirm_password: str, id: str) -> bool:
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
async def delete_account(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        await token_acces(credentials)

        input_data = await request.json()
        user_id = input_data.get("id")

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


async def token_acces(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        decoded_token = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])

        user_id = decoded_token.get("id")
        if user_id:
            db_user_id = await get_user_id(user_id)

            if db_user_id is None:
                raise HTTPException(status_code=404, detail="Could not find user")

            if user_id == db_user_id:
                return {"detail": "Access allowed!"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid token")


async def get_user_id(id: str):
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
            raise HTTPException(status_code=404, detail="Not Found: User not found.")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={f"Internal server error: {e}"})
