import decimal
from math import radians, sin, cos, sqrt, atan2
from OpenSSL import crypto
from datetime import datetime, timezone
import psycopg2.pool
from fastapi import APIRouter
from app.config.config import settings

router = APIRouter()

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

##chatgpt
def generate_ssl_cert_and_key(key_length=2048, days_valid=365):
    # Generate a key pair
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, key_length)

    # Create a self-signed certificate
    cert = crypto.X509()
    cert.get_subject().C = "SK"  # Country Name
    cert.get_subject().ST = "BA"  # State or Province Name
    cert.get_subject().L = "BA"  # Locality Name
    cert.get_subject().O = "MTAA"  # Organization Name
    cert.get_subject().CN = "localhost"  # Common Name
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(days_valid * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')

    # Write certificate and private key to files
    with open('cert.pem', "wb") as certfile:
        certfile.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    with open('key.pem', "wb") as keyfile:
        keyfile.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    print("SSL certificate and key generated successfully.")

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

@router.get("/hello")
async def hello() -> dict:
    return {
        'hello': settings.DATABASE_NAME
    }


generate_ssl_cert_and_key()


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


@router.get("/api/activities")
async def activities() -> dict:
    conn = pool.getconn()
    cursor = conn.cursor()
    query = ("""SELECT *
                FROM activities""")
    cursor.execute(query)

    data = cursor.fetchall()
    records = zip_objects_from_db(data, cursor)

    cursor.close()
    pool.putconn(conn)
    return {"items": records}


@router.get("/api/activita/{id}")
async def activities(id : int) -> dict:
    conn = pool.getconn()
    cursor = conn.cursor()
    query = ("""SELECT *
                FROM places
                where id=%s""")
    cursor.execute(query, [id])

    data = cursor.fetchall()
    records = zip_objects_from_db(data, cursor)

    cursor.close()
    pool.putconn(conn)
    return {"items": records}


@router.get("/api/favourites")
async def favourites() -> dict:
    conn = pool.getconn()
    cursor = conn.cursor()
    query = ("""SELECT *
                FROM favourites""")
    cursor.execute(query)

    data = cursor.fetchall()
    records = zip_objects_from_db(data, cursor)

    cursor.close()
    pool.putconn(conn)
    return {"items": records}


@router.get("/api/location-activities/{gps}")
async def location_activities(gps: str) -> dict:
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
    return {"items": records}

# @router.get("/api/{username}")
# async def favourites(username: str) -> dict:
#     conn = pool.getconn()
#     cursor = conn.cursor()
#     query = ("""SELECT *
#                 FROM users_auth
#                 WHERE username= %s""")
#     cursor.execute(query, (username,))
#
#     data = cursor.fetchall()
#     #vypocet radiusu podla gps
#
#     records = zip_objects_from_db(data, cursor)
#
#     cursor.close()
#     pool.putconn(conn)
#     return {"items": records}



@router.get("/api/activity/{category}")
async def category(category: str) -> dict:
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
        return {"items": "Nothing was found"}

    cursor.execute(query, category)

    data = cursor.fetchall()
    records = zip_objects_from_db(data, cursor)

    cursor.close()
    pool.putconn(conn)
    return {"items": records}

@router.post("/api/add_favourit/{activity_id}")
async def edit_profile(actiactivity_id: int) -> dict:
    conn = pool.getconn()
    cursor = conn.cursor()
    query = ("""SELECT *
                FROM favourites
                WHERE id = %s""")
    cursor.execute(query, [actiactivity_id])
    data = cursor.fetchone()
    cursor.close()
    pool.putconn(conn)
    if not data:
        conn = pool.getconn()
        cursor = conn.cursor()

        query = ("""SELECT *
                    FROM places
                    WHERE id = %s""")
        cursor.execute(query, [actiactivity_id])
        data = cursor.fetchone()
        query = ("""INSERT INTO favourites
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""")
        cursor.execute(query, (data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11], data[12]))
        conn.commit()
        cursor.close()
        pool.putconn(conn)
        return {"status": "Done"}
    else:
        return {"status": "Already in favourites"}


