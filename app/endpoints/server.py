"""
Defines authorization functions and endpoints for API requests and related attributes.

It is similar to client file, but these endpoints are meant for server database.

A brief overview of exported classes and their usage:
    router = APIRouter()
        in any request, example:
            @router.get("/status")

    security = HTTPBearer()
        in the authorization requests of user, example:
            async def activities(credentials: HTTPAuthorizationCredentials =
                Depends(security)) -> JSONResponse:

    for handling database connection of server:

        pool_server = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dbname=settings.DATABASE_NAME_SERVER,
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD
        )
"""

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
from app.auth.authentication import token_access
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
    """
    Serializes datetime and decimal objects.

    Args:
      obj:
          The object to be serialized.

    Returns:
        String or float value of serialized object.
    """
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat(timespec='milliseconds')[:-3]
    elif isinstance(obj, (float, decimal.Decimal)):
        return float(obj)
    else:
        return obj


def zip_objects_from_db(data, cursor):
    """
     Zips objects retrieved from the database with cursor metadata.

     Args:
       data:
         Data to in the list of tuples (colum - value) from database
       cursor:
         The cursor object containing metadata about the retrieved data.

     Returns:
         A list of dictionaries, where each dictionary has a row of data.
     """
    return [dict(zip((key[0] for key in cursor.description),
                     [serialize_datetime_and_decimal(value) for value in row])) for row in data]


@router.get("/server/status")
async def status() -> dict:
    """
    Function status is only for testing purpose.

    Returns:
        A JSON object which defines a current version of postgreSQL:

            If the user is created successfully:
                INFO:     127.0.0.1:56979 - "GET /status HTTP/1.1" 200 OK
                {
                    "version": "PostgreSQL 14.4 on x86_64-apple-darwin20.6.0,
                    compiled by Apple clang version 12.0.0 (clang-1200.0.32.29), 64-bit"
                }

    Returned response is always JSON object with HTTP/HTTPS status code.
    """
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
    """
       Gets chosen by user his place.

       Args:
           credentials:
               Bearer token to authorize. HTTPAuthorizationCredentials instance
               with security instance of HTTPBearer.

       Returns:
        A JSONResponse of the HTTP/HTTPS status code of the request with
        description content. For example:

            If the user is not authorized:
                INFO:     127.0.0.1:63240 - "GET /server/get_all_places HTTP/1.1" 403 Forbidden
                {
                   "detail": "Not authenticated"
                }

            If the request is successful:
               INFO:     127.0.0.1:63275 - "GET /server/get_all_places HTTP/1.1" 200 OK
              {
                    "items": [
                        {
                            "id": "dad61774-5515-4d1e-8da6-a27fb5bc13f5",
                            "name": "Petržalská hrádza",
                            "image_name": "img5",
                            "description": "Miesto v prírode ideálne na bicyklovanie.",
                            "contact": "421912000005",
                            "address": "34RM+99, 851 07 Bratislava",
                            "gps": "48.091041411663475, 17.13336239814964",
                            "meals": "FALSE",
                            "accomodation": "FALSE",
                            "sport": "TRUE",
                            "hiking": "TRUE",
                            "fun": "FALSE",
                            "events": "FALSE",
                            "image_data": null
                        }
                    ]
               }

            If the database is empty then:
               INFO:     127.0.0.1:63275 - "GET /server/get_all_places HTTP/1.1" 204 No Content
               {
                    "detail": "No records found"
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
    """
    Uploads image.

    Args:
      file_path:
          Path to source of image.
      name:
          Name of the image.
    """
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
