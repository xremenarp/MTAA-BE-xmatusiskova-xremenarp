"""
Defines authorization functions and endpoints for API requests and related attributes.

This is a part where user in BE needs to be authorized after authentication.
The user has access to the content of the app as searching activities for him
or making notes and so on.
Except of that, this module also checks accessibility of user by his automatically
generated token.

A brief overview of exported classes and their usage:
    router = APIRouter()
        in any request, example:
            @router.get("/status")

    security = HTTPBearer()
        in the authorization requests of user, example:
            async def activities(credentials: HTTPAuthorizationCredentials =
                Depends(security)) -> JSONResponse:

    for handling database connection for client and server:
        pool_client = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dbname=settings.DATABASE_NAME_CLIENT,
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD
        )

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

pool_client = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=settings.DATABASE_NAME_CLIENT,
    host=settings.DATABASE_HOST,
    port=settings.DATABASE_PORT,
    user=settings.DATABASE_USER,
    password=settings.DATABASE_PASSWORD
)
pool_server = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=settings.DATABASE_NAME_SERVER,
    host=settings.DATABASE_HOST,
    port=settings.DATABASE_PORT,
    user=settings.DATABASE_USER,
    password=settings.DATABASE_PASSWORD
)


def haversine(coord1: tuple, coord2: tuple) -> float:
    """
    Calculates the great-circle distance between two points on the map.

    Args:
      coord1:
          A tuple containing latitude and longitude of the first point.
      coord2:
          A tuple containing latitude and longitude of the second point.

    Returns:
        The distance between the two points in kilometers in float type.
    """
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    return 6371.0 * (2 * atan2(sqrt((sin((lat2 - lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2)**2)), sqrt(1 - (sin((lat2 - lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2)**2))))


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


def zip_objects_from_db(data: list, cursor) -> list:
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


@router.get("/status")
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
    conn = pool_client.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    cursor.close()
    pool_client.putconn(conn)
    return {
        'version': version
    }


@router.get("/api/get_all_places")
async def activities(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets all activities in the app from the databse.

    Args:
       credentials:
        Bearer token to authorize. HTTPAuthorizationCredentials instance
        with security instance of HTTPBearer.

    Returns:
       A JSONResponse of the HTTP/HTTPS status code of the request with
       description content. For example:

           If the user is not authorized:
                INFO:     127.0.0.1:57594 - "GET /api/get_all_places HTTP/1.1" 403 Forbidden
               {
                    "detail": "Internal server error: 'NoneType' object is not subscriptable"
                }

           If the database is empty then:
               INFO:     127.0.0.1:57594 - "GET /api/get_all_places HTTP/1.1" 204 No Content
               {
                    "detail": "No records found"
               }

           If the request is successful:
            INFO:     127.0.0.1:57594 - "GET /api/get_all_places HTTP/1.1" 200 OK
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
                        "events": "FALSE"
                    }
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

        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM places""")
        cursor.execute(query)

        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)

        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/place")
async def activities(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets one specific activity in the app from the database, according to user request.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
             INFO:     127.0.0.1:57973 - "GET /api/place HTTP/1.1" 403 Forbidden
             {
                  "detail": "Internal server error: 'NoneType' object is not subscriptable"
              }

         If the database is empty then:
             INFO:     127.0.0.1:57973 - "GET /api/place HTTP/1.1" 204 No Content
             {
                  "detail": "No records found"
             }

         If the request is successful:
          INFO:     127.0.0.1:57973 - "GET /api/place HTTP/1.1" 200 OK
          {
            "items": [
                {
                    "id": "2319d5ad-0346-48a9-993e-f1dd7ad233a5",
                    "name": "BeAbout",
                    "image_name": "img1",
                    "description": "Najlepšia burgráreň.",
                    "contact": "421912000001",
                    "address": "Prešernova 4, 811 02 Bratislava",
                    "gps": "48.1405355220085, 17.115227264931487",
                    "meals": "TRUE",
                    "accomodation": "FALSE",
                    "sport": "FALSE",
                    "hiking": "FALSE",
                    "fun": "FALSE",
                    "events": "FALSE"
                }
            ]
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
        id = input.get("id")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM places
                    where id= %s""")
        cursor.execute(query, [id])
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/get_all_favourites")
async def favourites(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets all user's favourites activities in the app from the database.

    Args:
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
              INFO:     127.0.0.1:58071 - "GET /api/get_all_favourites HTTP/1.1" 403 Forbidden
             {
                  "detail": "Internal server error: 'NoneType' object is not subscriptable"
              }

         If the database is empty then:
             INFO:     127.0.0.1:58071 - "GET /api/get_all_favourites HTTP/1.1" 204 No Content
             {
                  "detail": "No records found"
             }

         If the request is successful:
          INFO:     127.0.0.1:58071 - "GET /api/get_all_favourites HTTP/1.1" 200 OK
          {
            "items": [
                 "items": [
                        {
                            "id": "dad61774-5515-4d1e-8da6-a27fb5bc13f5",
                            "name": "Petržalská hrádza",
                            "image": "img5",
                            "description": "Miesto v prírode ideálne na bicyklovanie.",
                            "contact": "421912000005",
                            "address": "34RM+99, 851 07 Bratislava",
                            "gps": "48.091041411663475, 17.13336239814964",
                            "meals": "FALSE",
                            "accomodation": "FALSE",
                            "sport": "TRUE",
                            "hiking": "TRUE",
                            "fun": "FALSE",
                            "events": "FALSE"
                        }
                    ]
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

        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM favourites""")
        cursor.execute(query)
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/location_places")
async def location_activities(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets activities in the app for user according to his gps location.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
              INFO:     127.0.0.1:58208 - "GET /api/location_places HTTP/1.1" 403 Forbidden
             {
                  "detail": "Internal server error: 'NoneType' object is not subscriptable"
              }

         If the database is empty then:
             INFO:     127.0.0.1:58208 - "GET /api/location_places HTTP/1.1" 204 No Content
             {
                  "detail": "No records found"
             }

         If the request is successful, then the result will be
         according to user location:
          INFO:     127.0.0.1:58208 - "GET /api/location_places HTTP/1.1" 200 OK
          {
            "items": [
                  {
                        "id": "c584e467-1e9e-45d5-a617-4ae772a1407a",
                        "name": "Sheraton",
                        "image_name": "img4",
                        "description": "Hotel s ideálnou polohou.",
                        "contact": "421912000004",
                        "address": "Pribinova 12, 811 09 Bratislava",
                        "gps": "48.14061834357159, 17.12233203794686",
                        "meals": "TRUE",
                        "accomodation": "TRUE",
                        "sport": "FALSE",
                        "hiking": "FALSE",
                        "fun": "FALSE",
                        "events": "FALSE"
                  }
            ]
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
        gps = input.get("gps")
        gps = str(gps)
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM places""")
        cursor.execute(query)
        data = cursor.fetchall()
        new_data = []
        for i in data:
            coord = i[6].split(", ")
            coord_user = gps.split(", ")
            if haversine((float(coord_user[0]), float(coord_user[1])), (float(coord[0]), float(coord[1]))) <= 2:#############radius in km
                new_data.append(i)

        records = zip_objects_from_db(new_data, cursor)
        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/place_category")
async def category(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets activities in the app for user according to chosen category.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
              INFO:     127.0.0.1:59286 - "GET /api/place_category HTTP/1.1" 403 Forbidden
             {
                  "detail": "Internal server error: 'NoneType' object is not subscriptable"
              }

         If the database is empty then:
             INFO:     127.0.0.1:59286 - "GET /api/place_category HTTP/1.1" 204 No Content
             {
                  "detail": "No records found"
             }

         If the request is successful, then the result will be
         according to chosen category, in this case meals:
          INFO:     127.0.0.1:59286 - "GET /api/place_category HTTP/1.1" 200 OK
          {
            "items": [
                  {
                        "id": "c584e467-1e9e-45d5-a617-4ae772a1407a",
                        "name": "Sheraton",
                        "image_name": "img4",
                        "description": "Hotel s ideálnou polohou.",
                        "contact": "421912000004",
                        "address": "Pribinova 12, 811 09 Bratislava",
                        "gps": "48.14061834357159, 17.12233203794686",
                        "meals": "TRUE",
                        "accomodation": "TRUE",
                        "sport": "FALSE",
                        "hiking": "FALSE",
                        "fun": "FALSE",
                        "events": "FALSE"
                  }
            ]
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
        category = input.get("category")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        if category == "meals":
            query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                        FROM places
                        WHERE meals='TRUE' """)
        elif category == "accomodation":
            query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                        FROM places
                        WHERE accomodation='TRUE' """)
        elif category == "sport":
            query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                        FROM places
                        WHERE sport='TRUE' """)
        elif category == "hiking":
            query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                        FROM places
                        WHERE hiking='TRUE' """)
        elif category == "fun":
            query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                        FROM places
                        WHERE fun='TRUE' """)
        elif category == "events":
            query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                        FROM places
                        WHERE events='TRUE' """)
        else:
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=204, content={"detail": "Category does not exist"})

        cursor.execute(query, category)
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/api/add_favourite")
async def add_favourit(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Posts user's favourite activity into favourites list.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
             INFO:     127.0.0.1:59752 - "POST /api/add_favourite HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the place is already in favourites:
             INFO:     127.0.0.1:60040 - "POST /api/add_favourite HTTP/1.1" 205 Reset Content
             {
                "detail": "Place already in favourites"
             }

         If the request is successful:
          INFO:      127.0.0.1:60040 - "POST /api/add_favourite HTTP/1.1" 200 OK
           {
                "detail": "OK: Place added to favourites."
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
        activity_id = input.get("activity_id")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM favourites
                    WHERE id = %s""")
        cursor.execute(query, [activity_id])
        data = cursor.fetchone()
        cursor.close()
        pool_client.putconn(conn)
        if not data:
            conn = pool_client.getconn()
            cursor = conn.cursor()
            query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                        FROM places
                        WHERE id = %s""")
            cursor.execute(query, [activity_id])
            place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events = cursor.fetchone()
            query = ("""INSERT INTO favourites (id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
            cursor.execute(query, (place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
            conn.commit()
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place added to favourites."})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place already in favourites"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/api/delete_favourite")
async def delete_favourit(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Deletes user's favourite activity from the favourites list.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
            INFO:     127.0.0.1:60420 - "POST /api/delete_favourite HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the place is not in favourites:
             INFO:     127.0.0.1:60543 - "POST /api/delete_favourite HTTP/1.1" 205 Reset Content
            {
                "detail": "Place not in favourites"
            }

         If the request is successful:
          INFO:     127.0.0.1:60519 - "POST /api/delete_favourite HTTP/1.1" 201 Created
           {
                "detail": "OK: Place deleted from favourites."
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
        activity_id = input.get("activity_id")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM favourites
                    WHERE id = %s""")
        cursor.execute(query, [activity_id])
        data = cursor.fetchone()
        if data:
            query = ("""DELETE FROM favourites
                        WHERE id = %s""")
            cursor.execute(query, [activity_id])
            conn.commit()
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place deleted from favourites."})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place not in favourites"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.put("/api/add_edit_note")
async def add_note(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    User can put his note into the app.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
            INFO:     127.0.0.1:60645 - "PUT /api/add_edit_note HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the request is successful:
            INFO:     127.0.0.1:60672 - "PUT /api/add_edit_note HTTP/1.1" 201 Created
           {
                "detail": "OK: Note added to place."
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
        activity_id = input.get("activity_id")
        note = input.get("note")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""INSERT INTO notes
                    VALUES (%s,%s)
                    ON CONFLICT(id)
                    DO UPDATE
                    SET note = %s
                    WHERE notes.id = %s""")
        cursor.execute(query, (activity_id, note, note, activity_id))
        conn.commit()
        cursor.close()
        pool_client.putconn(conn)
        return JSONResponse(status_code=201, content={"detail": "OK: Note added to place."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.delete("/api/delete_note")
async def add_note(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
     User can delete his note from the app.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
             INFO:     127.0.0.1:60951 - "DELETE /api/delete_note HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the note is already deleted:
             INFO:     127.0.0.1:61026 - "DELETE /api/delete_note HTTP/1.1" 205 Reset Content
            {
                "detail": "FAIL: Note does not exist."
            }

         If the request is successful:
            INFO:     127.0.0.1:61008 - "DELETE /api/delete_note HTTP/1.1" 201 Created
            {
                "detail": "OK: Note deleted."
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
        activity_id = input.get("activity_id")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM notes
                    WHERE id=%s""")
        cursor.execute(query, [activity_id])
        data = cursor.fetchone()
        if data:
            query = ("""DELETE FROM notes
                        WHERE id= %s""")
            cursor.execute(query, [activity_id])
            conn.commit()
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Note deleted."})
        else:
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=205, content={"detail": "FAIL: Note does not exist."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/get_note")
async def get_note(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets note from the system for user.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
             INFO:     127.0.0.1:61113 - "GET /api/get_note HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the note is not found:
             INFO:     127.0.0.1:61162 - "GET /api/get_note HTTP/1.1" 205 Reset Content
            {
                "detail": "Place does not have notes"
            }

         If the request is successful:
            INFO:     127.0.0.1:61232 - "GET /api/get_note HTTP/1.1" 201 Created
            {
                "note": [
                    {
                        "id": "f6a3b853-2f8c-4011-bf8e-5103c20a3ddc",
                        "note": "Dobre rezne maju"
                    }
                ]
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
        activity_id = input.get("activity_id")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM notes
                    WHERE id = %s""")
        cursor.execute(query, [activity_id])
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=201, content={"note": records})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place does not have notes"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/api/add_my_place")
async def add_place(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    User can place into the system.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
            INFO:     127.0.0.1:61393 - "POST /api/add_my_place HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the request is successful:
            INFO:     127.0.0.1:61430 - "POST /api/add_my_place HTTP/1.1" 201 Created
           {
                "detail": "OK: Place created."
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
        name = input.get("name")
        image = input.get("image")
        description = input.get("description")
        contact = input.get("contact")
        address = input.get("address")
        gps = input.get("gps")
        meals = input.get("meals")
        accomodation = input.get("accomodation")
        sport = input.get("sport")
        hiking = input.get("hiking")
        fun = input.get("fun")
        events = input.get("events")
        #image_data = input.get("image_data")
        gen_uuid = uuid.uuid4()

        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""INSERT INTO my_places (id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
        cursor.execute(query,(str(gen_uuid), name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
        conn.commit()
        query = ("""INSERT INTO places (id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
        cursor.execute(query, (str(gen_uuid), name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
        conn.commit()
        cursor.close()
        pool_client.putconn(conn)
        return JSONResponse(status_code=201, content={"detail": "OK: Place created."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.put("/api/edit_my_place")
async def edit_place(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    User can edit his place in the system.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
            INFO:     127.0.0.1:61505 - "PUT /api/edit_my_place HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the request is successful:
            INFO:     127.0.0.1:61521 - "PUT /api/edit_my_place HTTP/1.1" 201 Created
            {
                "detail": "OK: Place edited."
            }

         If the place is not found:
            INFO:     127.0.0.1:61521 - "PUT /api/edit_my_place HTTP/1.1" 205 Reset Content
            {
                "detail": "OK: Place not found."
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
        place_id = input.get("id")
        name = input.get("name")
        image = input.get("image")
        description = input.get("description")
        contact = input.get("contact")
        address = input.get("address")
        gps = input.get("gps")
        meals = input.get("meals")
        accomodation = input.get("accomodation")
        sport = input.get("sport")
        hiking = input.get("hiking")
        fun = input.get("fun")
        events = input.get("events")
        #image_data = input.get("image_data")

        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM my_places
                    WHERE id = %s""")
        cursor.execute(query, [place_id])
        data = cursor.fetchall()
        if data:
            query = ("""DELETE FROM my_places
                        WHERE id=%s""")
            cursor.execute(query, [place_id])
            conn.commit()
            query = ("""DELETE FROM places
                        WHERE id=%s""")
            cursor.execute(query, [place_id])
            conn.commit()
            query = ("""INSERT INTO my_places (id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
            cursor.execute(query,(place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
            conn.commit()
            query = ("""INSERT INTO places (id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
            cursor.execute(query, (place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun,events))
            conn.commit()
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place edited."})
        else:
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=205, content={"detail": "OK: Place not found."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.delete("/api/delete_my_place")
async def edit_place(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    User can delete his place from the system.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
            INFO:     127.0.0.1:61661 - "DELETE /api/delete_my_place HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the request is successful:
            INFO:     127.0.0.1:61689 - "DELETE /api/delete_my_place HTTP/1.1" 201 Created
            {
                "detail": "OK: Place deleted."
            }

         If the place is not found:
            INFO:     127.0.0.1:61689 - "DELETE /api/delete_my_place HTTP/1.1" 205 Reset Content
            {
                "detail": "OK: Place not found."
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
        place_id = input.get("id")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM my_places
                    WHERE id = %s""")
        cursor.execute(query, [place_id])
        data = cursor.fetchone()
        if data:
            query = ("""DELETE FROM my_places
                        WHERE id=%s""")
            cursor.execute(query, [place_id])
            conn.commit()
            query = ("""DELETE FROM places
                        WHERE id=%s""")
            cursor.execute(query, [place_id])
            conn.commit()
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place deleted."})
        else:
            cursor.close()
            pool_client.putconn(conn)
            return JSONResponse(status_code=205, content={"detail": "OK: Place not found."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/get_my_places")
async def get_created_places(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets all user's places.

    Args:
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
            INFO:     127.0.0.1:62063 - "GET /api/get_my_places HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the request is successful:
            INFO:     127.0.0.1:62091 - "GET /api/get_my_places HTTP/1.1" 201 Created
           {
                "note": [
                    {
                        "id": "3a360180-7205-40f3-a600-6eb69520a06c",
                        "name": "Testovacie miesto",
                        "image_name": "t1",
                        "description": "Miesto na testovanie",
                        "contact": "421912345678",
                        "address": "Testovacia adresa",
                        "gps": "48.1405355220086, 17.115227264931488",
                        "meals": "TRUE",
                        "accomodation": "TRUE",
                        "sport": "TRUE",
                        "hiking": "TRUE",
                        "fun": "TRUE",
                        "events": "TRUE"
                    }
                ]
            }

         If the place is not found:
            INFO:     127.0.0.1:62091 - "GET /api/get_my_places HTTP/1.1" 205 Reset Content
            {
                "detail": "Place not found"
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

        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM my_places""")
        cursor.execute(query)
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=201, content={"note": records})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place not found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/api/get_my_place")
async def get_created_places(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Gets chosen by user his place.

    Args:
        request:
            Body of the post request. Request instance of the FastAPI.
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
             INFO:     127.0.0.1:62292 - "GET /api/get_my_place HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the request is successful:
            INFO:     127.0.0.1:62314 - "GET /api/get_my_place HTTP/1.1" 201 Created
           {
                "note": [
                    {
                        "id": "3a360180-7205-40f3-a600-6eb69520a06c",
                        "name": "Testovacie miesto",
                        "image_name": "t1",
                        "description": "Miesto na testovanie",
                        "contact": "421912345678",
                        "address": "Testovacia adresa",
                        "gps": "48.1405355220086, 17.115227264931488",
                        "meals": "TRUE",
                        "accomodation": "TRUE",
                        "sport": "TRUE",
                        "hiking": "TRUE",
                        "fun": "TRUE",
                        "events": "TRUE"
                    }
                ]
            }

         If the place is not found:
            INFO:     127.0.0.1:62314 - "GET /api/get_my_place HTTP/1.1" 205 Reset Content
            {
                "detail": "Place not found"
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
        place_id = input.get("id")
        conn = pool_client.getconn()
        cursor = conn.cursor()
        query = ("""SELECT id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events
                    FROM my_places
                    WHERE id = %s""")
        cursor.execute(query, [place_id])
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool_client.putconn(conn)
        if data:
            return JSONResponse(status_code=201, content={"note": records})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place not found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/api/update_databse")
async def update_databse(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    """
    Request to update database.

    Args:
        credentials:
            Bearer token to authorize. HTTPAuthorizationCredentials instance
            with security instance of HTTPBearer.

    Returns:
     A JSONResponse of the HTTP/HTTPS status code of the request with
     description content. For example:

         If the user is not authorized:
             INFO:     127.0.0.1:62687 - "PUT /api/update_databse HTTP/1.1" 403 Forbidden
             {
                "detail": "Not authenticated"
             }

         If the request is successful:
            INFO:     127.0.0.1:62724 - "PUT /api/update_databse HTTP/1.1" 201 Created
            {
                "note": "Records updated"
            }

         If the place is not found:
            INFO:     127.0.0.1:62724 - "PUT /api/update_databse HTTP/1.1" 205 Reset Content
            {
                "detail": "Records not found"
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

        conn = pool_client.getconn()
        cursor = conn.cursor()
        conn_server = pool_server.getconn()
        cursor_server = conn_server.cursor()

        query = ("""DELETE FROM places""")
        cursor.execute(query)
        conn.commit()

        query = ("""SELECT * FROM places""")
        cursor_server.execute(query)

        pom = 0
        while True:
            row = cursor_server.fetchone()
            if row is None:
                break
            place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events, image_data = row
            query = ("""INSERT INTO places (id, name, image_name, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
            cursor.execute(query, (place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
            conn.commit()
            pom = 1

        cursor.close()
        cursor_server.close()
        pool_client.putconn(conn)
        pool_server.putconn(conn_server)

        if pom == 1:
            return JSONResponse(status_code=201, content={"note": "Records updated"})
        else:
            return JSONResponse(status_code=205, content={"detail": "Records not found"})
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
    conn = pool_client.getconn()
    cursor = conn.cursor()
    query = ("""UPDATE places
                SET image_data = %s
                WHERE name = %s""")
    cursor.execute(query, (psycopg2.Binary(drawing), name))
    conn.commit()
    cursor.close()
    pool_client.putconn(conn)

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
