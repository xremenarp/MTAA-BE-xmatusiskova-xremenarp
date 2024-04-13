import decimal
from math import radians, sin, cos, sqrt, atan2
from typing import Dict
import uuid

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

pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=settings.DATABASE_NAME,
    host=settings.DATABASE_HOST,
    port=settings.DATABASE_PORT,
    user=settings.DATABASE_USER,
    password=settings.DATABASE_PASSWORD
)

def haversine(coord1, coord2):
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    return 6371.0 * (2 * atan2(sqrt((sin((lat2 - lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2)**2)), sqrt(1 - (sin((lat2 - lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2)**2))))


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


@router.get("/status")
async def status() -> dict:
    conn = pool.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    cursor.close()
    pool.putconn(conn)
    return {
        'version': version
    }


@router.get("/api/get_all_places")
async def activities(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM places""")
        cursor.execute(query)

        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)

        cursor.close()
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/place")
async def activities(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        id = input.get("id")
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM places
                    where id= %s""")
        cursor.execute(query, [id])
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/get_all_favourites")
async def favourites(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM favourites""")
        cursor.execute(query)
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/location_places")
async def location_activities(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        gps = input.get("gps")
        gps = str(gps)
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
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
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/api/place_category")
async def category(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        category = input.get("category")
        conn = pool.getconn()
        cursor = conn.cursor()
        if category == "meals":
            query = ("""SELECT *
                        FROM places
                        WHERE meals='TRUE' """)
        elif category == "accomodation":
            query = ("""SELECT *
                        FROM places
                        WHERE accomodation='TRUE' """)
        elif category == "sport":
            query = ("""SELECT *
                        FROM places
                        WHERE sport='TRUE' """)
        elif category == "hiking":
            query = ("""SELECT *
                        FROM places
                        WHERE hiking='TRUE' """)
        elif category == "fun":
            query = ("""SELECT *
                        FROM places
                        WHERE fun='TRUE' """)
        elif category == "events":
            query = ("""SELECT *
                        FROM places
                        WHERE events='TRUE' """)
        else:
            cursor.close()
            pool.putconn(conn)
            return JSONResponse(status_code=204, content={"detail": "Category does not exist"})

        cursor.execute(query, category)
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=200, content={"items": records})
        else:
            return JSONResponse(status_code=204, content={"detail": "No records found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/api/add_favourite")
async def add_favourit(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        activity_id = input.get("activity_id")
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM favourites
                    WHERE id = %s""")
        cursor.execute(query, [activity_id])
        data = cursor.fetchone()
        cursor.close()
        pool.putconn(conn)
        if not data:
            conn = pool.getconn()
            cursor = conn.cursor()

            query = ("""SELECT *
                        FROM places
                        WHERE id = %s""")
            cursor.execute(query, [activity_id])
            data = cursor.fetchone()
            query = ("""INSERT INTO favourites
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
            cursor.execute(query, (data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8],
                                   data[9], data[10], data[11], data[12], data[13]))
            conn.commit()
            cursor.close()
            pool.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place added to favourites."})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place already in favourites"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/api/delete_favourite")
async def delete_favourit(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        activity_id = input.get("activity_id")
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
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
            pool.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place deleted from favourites."})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place not in favourites"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.put("/api/add_edit_note")
async def add_note(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        activity_id = input.get("activity_id")
        note = input.get("note")
        conn = pool.getconn()
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
        pool.putconn(conn)
        return JSONResponse(status_code=201, content={"detail": "OK: Note added to place."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/api/delete_note")
async def add_note(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        activity_id = input.get("activity_id")
        conn = pool.getconn()
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
            pool.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Note deleted."})
        else:
            cursor.close()
            pool.putconn(conn)
            return JSONResponse(status_code=205, content={"detail": "FAIL: Note does not exist."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/api/get_note")
async def get_note(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        activity_id = input.get("activity_id")
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM notes
                    WHERE id = %s""")
        cursor.execute(query, [activity_id])
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=201, content={"note": records})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place does not have notes"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.post("/api/add_my_place")
async def add_place(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

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

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""INSERT INTO my_places
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
        cursor.execute(query,(str(gen_uuid), name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
        conn.commit()
        query = ("""INSERT INTO places
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
        cursor.execute(query, (str(gen_uuid), name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
        conn.commit()
        cursor.close()
        pool.putconn(conn)
        return JSONResponse(status_code=201, content={"detail": "OK: Place created."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.put("/api/edit_my_place")
async def edit_place(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

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

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
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
            query = ("""INSERT INTO my_places
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
            cursor.execute(query,(place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun, events))
            conn.commit()
            query = ("""INSERT INTO places
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
            cursor.execute(query, (place_id, name, image, description, contact, address, gps, meals, accomodation, sport, hiking, fun,events))
            conn.commit()
            cursor.close()
            pool.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place edited."})
        else:
            cursor.close()
            pool.putconn(conn)
            return JSONResponse(status_code=205, content={"detail": "OK: Place not found."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/api/delete_my_place")
async def edit_place(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        place_id = input.get("id")
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
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
            pool.putconn(conn)
            return JSONResponse(status_code=201, content={"detail": "OK: Place deleted."})
        else:
            cursor.close()
            pool.putconn(conn)
            return JSONResponse(status_code=205, content={"detail": "OK: Place not found."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/api/get_my_places")
async def get_created_places(credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM my_places""")
        cursor.execute(query)
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=201, content={"note": records})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place not found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/api/get_my_place")
async def get_created_places(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JSONResponse:
    try:
        await token_acces(credentials)

        input = await request.json()
        place_id = input.get("id")
        conn = pool.getconn()
        cursor = conn.cursor()
        query = ("""SELECT *
                    FROM my_places
                    WHERE id = %s""")
        cursor.execute(query, [place_id])
        data = cursor.fetchall()
        records = zip_objects_from_db(data, cursor)
        cursor.close()
        pool.putconn(conn)
        if data:
            return JSONResponse(status_code=201, content={"note": records})
        else:
            return JSONResponse(status_code=205, content={"detail": "Place not found"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
