# Visitor
### --> MTAA BE project app - assignment

> to run BE locally:
``` hypercorn app.__main__:app --reload```

> to run in Docker:
```docker run -p 127.0.0.1:8000:8000 --env NAME=[name] --env DATABASE_HOST=gateway.docker.internal --env DATABASE_PORT=[db_port] --env DATABASE_NAME=[db_name] --env DATABASE_USER=[db_user] --env DATABASE_PASSWORD=[db_password]  --name [name-container] [name] ```

authors:
> Peter Remenár focused on developing authorization endpoints following the login process, ensuring secure access to resources. (mainly endpoints/index.py)
> Mária Matušisková was responsible for authentication and the implementation of JWT token generation, bolstering the security and integrity of user sessions. (mainly auth/authentification.py)

## Endpoints

### Status
> **GET** http://127.0.0.1:8000/status

authors:
> Peter Remenár, Mária Matušisková

### Sign up
> **POST** http://127.0.0.1:8000/api/signup/

body:
> {
  "username": "John",
  "email": "user@gmail.com",
  "password": "123",
  "confirm_password": "123"
}

author:
> Mária Matušisková

### Login
> **POST** http://127.0.0.1:8000/api/login/

body:
> {
  "username": "John",
  "password": "123"
}

author:
> Mária Matušisková

### Forgotten password
> **PUT** http://127.0.0.1:8000/api/forgotten-password/

body:

>{
  "email": "user@gmail.com",
  "password": "abc",
  "confirm_password": "abc"
}

author:
> Mária Matušisková

### Edit profile
> **PATCH** http://127.0.0.1:8000/api/edit_profile/

body:

> {
  "id": "a31a52b2-67b4-422d-bbc6-7553fa629296",
  "email": "jack@gmail.com"
}

author:
> Mária Matušisková


### Delete account
> **DELETE** http://127.0.0.1:8000/api/delete_account/

body:
>{
  "id": "a31a52b2-67b4-422d-bbc6-7553fa629296"
}

author:
> Mária Matušisková


### Get all places
> **GET** http://127.0.0.1:8000/api/get_all_places/

auth:
>Bearer Token

author:
> Peter Remenár

### place
> **GET** http://127.0.0.1:8000/api/place/

body:
> {
  "id": "2319d5ad-0346-48a9-993e-f1dd7ad233a5"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Get all favourites
> **GET** http://127.0.0.1:8000/api/get_all_favourites

auth:
>Bearer Token

author:
> Peter Remenár

### Location places
> **GET** http://127.0.0.1:8000/api/location_places

body:
>{
  "gps": "48.1405355220082, 17.115227264931488"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Place category
> **GET** http://127.0.0.1:8000/api/place_category

body:
>{
    "category": "meals"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Add favourite
> **POST** http://127.0.0.1:8000/api/add_favourite

body:
>{
    "activity_id": "f6a3b853-2f8c-4011-bf8e-5103c20a3ddc"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Delete favourite
> **POST** http://127.0.0.1:8000/api/delete_favourite

body:
>{
    "activity_id": "f6a3b853-2f8c-4011-bf8e-5103c20a3ddc"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Add edit note
> **PUT** http://127.0.0.1:8000/api/add_edit_note

body:
>{
    "activity_id": "f6a3b853-2f8c-4011-bf8e-5103c20a3ddc",
    "note": "Dobre rezne maju"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Delete note
> **DELETE** http://127.0.0.1:8000/api/delete_note

body:
>{
    "activity_id": "f6a3b853-2f8c-4011-bf8e-5103c20a3ddc"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Get note
> **GET** http://127.0.0.1:8000/api/get_note

body:
>{
    "activity_id": "f6a3b853-2f8c-4011-bf8e-5103c20a3ddc"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Add my place
> **POST** http://127.0.0.1:8000/api/add_my_place

body:
>{
    "name": "Testovacie miesto",
    "image": "t1",
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

auth:
>Bearer Token

author:
> Peter Remenár

### Edit my place
> **PUT** http://127.0.0.1:8000/api/edit_my_place

body:
>{
    "id": "5bc2a339-5c39-4cf4-bfb4-4b8bf51f17de",
    "name": "Testovacie miesto po uprave",
    "image": "t1",
    "description": "Miesto na testovanie po uprave",
    "contact": "421912345678",
    "address": "Testovacia adresa",
    "gps": "48.1405355220086, 17.115227264931488",
    "meals": "FALSE",
    "accomodation": "FALSE",
    "sport": "FALSE",
    "hiking": "FALSE",
    "fun": "FALSE",
    "events": "FALSE"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Delete my place
> **DELETE** http://127.0.0.1:8000/api/delete_my_place

body:
>{
    "id": "5bc2a339-5c39-4cf4-bfb4-4b8bf51f17de"
}

auth:
>Bearer Token

author:
> Peter Remenár

### Get my places
> **GET** http://127.0.0.1:8000/api/get_my_places

auth:
>Bearer Token

author:
> Peter Remenár

### Get my place
> **GET** http://127.0.0.1:8000/api/get_my_place

body:
>{
    "id": "5bc2a339-5c39-4cf4-bfb4-4b8bf51f17de"
}

auth:
>Bearer Token

author:
> Peter Remenár
