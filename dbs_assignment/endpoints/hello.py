import psycopg2
import psycopg2.pool
from fastapi import APIRouter, Query

from dbs_assignment.config import settings

router = APIRouter()

db_name = settings.DATABASE_NAME
db_host = settings.DATABASE_HOST
db_port = settings.DATABASE_PORT
db_user = settings.DATABASE_USER
db_password = settings.DATABASE_PASSWORD


@router.get("/hello")
async def hello():
    return {
        'hello': settings.NAME
    }


@router.get("/status")
async def status():
    pom = psycopg2.connect(dbname=db_name, host=db_host, port=db_port, user=db_user, password=db_password).cursor()
    pom.execute("SELECT version();")
    verzia = pom.fetchone()[0]
    pom.close()
    return {
        'version': verzia
    }


@router.post("/api/login/{username}/{password}")
async def login(username: str, password: str):
    pom = psycopg2.connect(dbname=db_name, host=db_host, port=db_port, user=db_user, password=db_password).cursor()
    query = ("""SELECT username,password
                FROM users
                WHERE username= %s AND password= %s""")
    pom.execute(query, (username, password))
    zaznam = pom.fetchone()

    if (zaznam[0] == username and zaznam[1] == password):
        pom.close()
        return {"status": True}
    else:
        pom.close()
        return {"status": False}

@router.post("/api/signup/{username}/{password}")
async def signup(username: str, password: str):
    pom = psycopg2.connect(dbname=db_name, host=db_host, port=db_port, user=db_user, password=db_password).cursor()
    query = ("""INSERT INTO users
                VALUES (%s,%s)""")
    pom.execute(query, (username, password))

    pom.close()
    return {"status": "Done"}

global_username = ""

@router.get("/api/forgotten-password/{username}")
async def forgotten(username: str):
    pom = psycopg2.connect(dbname=db_name, host=db_host, port=db_port, user=db_user, password=db_password).cursor()
    query = ("""SELECT username,
                FROM users
                WHERE username= %s """)
    pom.execute(query, (username))

    zaznam = pom.fetchone()
    global global_username
    global_username = username

    if (zaznam[0] == username):
        pom.close()
        return {"status": True}
    else:
        pom.close()
        return {"status": False}

@router.put("/api/reset-password/{password}")
async def reset(password: str):
    pom = psycopg2.connect(dbname=db_name, host=db_host, port=db_port, user=db_user, password=db_password).cursor()
    query = ("""UPDATE users,
                SET password = %s
                WHERE username = %s """)
    pom.execute(query, (global_username, password))

    pom.close()
    return {"status": True}

@router.get("/api/activities")
async def activities():
    pom = psycopg2.connect(dbname=db_name, host=db_host, port=db_port, user=db_user, password=db_password).cursor()
    query = ("""SELECT *,
                FROM activities""")
    pom.execute(query)

    zoznam_zaznamov = []
    zaznam = pom.fetchone()

    while zaznam != None:
        id = zaznam[0]
        name = zaznam[1]
        image = zaznam[2]
        description = zaznam[3]
        data = {
                    'id': id,
                    'name': name,
                    'image': image,
                    'description': description
                }

        zoznam_zaznamov.append(data)
        zaznam = pom.fetchone()

    return {"items": zoznam_zaznamov}



##########################hypercorn dbs_assignment.__main__:app --reload##################
