import decimal
from math import radians, sin, cos, sqrt, atan2
from typing import Dict
import uuid
import base64
import jwt
from OpenSSL import crypto
from datetime import datetime, timezone
import psycopg2.pool
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import JSONResponse
from app.auth.Tokenization import Tokenization
from app.auth.authentification import token_acces
from app.config.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth")
security = HTTPBearer()


pool_server = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=settings.DATABASE_NAME_SERVER,
    host=settings.DATABASE_HOST,
    port=settings.DATABASE_PORT,
    user=settings.DATABASE_USER,
    password=settings.DATABASE_PASSWORD
)

def serialize_datetime_and_decimal(obj):
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat(timespec='milliseconds')[:-3]
    elif isinstance(obj, (float, decimal.Decimal)):
        return float(obj)
    else:
        return obj


def zip_objects_from_db(data, cursor):
    return [dict(zip((key[0] for key in cursor.description),
                     [serialize_datetime_and_decimal(value) for value in row])) for row in data]


@router.get("/server/status")
async def status() -> dict:
    conn = pool_server.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    cursor.close()
    pool_server.putconn(conn)
    return {
        'version': version
    }


@router.get("/server/get_all_places")
async def activities(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        token_access = await token_acces(credentials)

        if token_access is None:
            return JSONResponse(status_code=404, content={"Not Found": "User not found."})

        conn = pool_server.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM places""")
        cursor.execute(query)
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool_server.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

def upload_image(file_path, name):
    drawing = open(file_path, 'rb').read()
    conn = pool_server.getconn()
    cursor = conn.cursor()
    query = ("""UPDATE places
                SET image_data = %s
                WHERE name = %s""")
    cursor.execute(query, (psycopg2.Binary(drawing), name))
    conn.commit()
    cursor.close()
    pool_server.putconn(conn)

#upload_image("C:\\Users\\petor\\Downloads\\escape_room.jpg","Escape room TRAPPED")
#upload_image("C:\\Users\\petor\\Downloads\\koncert.jpg","Fajný koncert")
#upload_image("C:\\Users\\petor\\Downloads\\dostihy.jpg","Závodisko - Dostihová dráha")
#upload_image("C:\\Users\\petor\\Downloads\\kolkovna.jpg","Testovacie miesto")
#upload_image("C:\\Users\\petor\\Downloads\\hradza.jpg","Petržalská hrádza")
#upload_image("C:\\Users\\petor\\Downloads\\K2.jpg","Lezecká stena K2")
#upload_image("C:\\Users\\petor\\Downloads\\sandberg.jpg","Sandberg")
#upload_image("C:\\Users\\petor\\Downloads\\kacin.jpg","Kačín")
#upload_image("C:\\Users\\petor\\Downloads\\kart_one_arena.jpg","Kart One Arena")
#upload_image("C:\\Users\\petor\\Downloads\\sheraton.jpg","Sheraton")
#upload_image("C:\\Users\\petor\\Downloads\\carlton.jpg","Radisson Blu Carlton Hotel Bratislava")
#upload_image("C:\\Users\\petor\\Downloads\\be-about.jpg","BeAbout")
#upload_image("C:\\Users\\petor\\Downloads\\kolkovna.jpg","Koľkovňa")
