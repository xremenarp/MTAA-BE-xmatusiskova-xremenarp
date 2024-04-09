# Visitor
### --> MTAA BE project app - assignment

> to run BE locally:
``` hypercorn app.__main__:app --reload```

> to run in Docker:
```docker run -p 127.0.0.1:8000:8000 --env NAME=[name] --env DATABASE_HOST=gateway.docker.internal --env DATABASE_PORT=[db_port] --env DATABASE_NAME=[db_name] --env DATABASE_USER=[db_user] --env DATABASE_PASSWORD=[db_password]  --name [name-container] [name] ```

## Endpoints

### Hello
> **GET** http://127.0.0.1:8000/hello

### Status
> **GET** http://127.0.0.1:8000/status

### Sign up
> **POST** http://127.0.0.1:8000/api/signup/

body:
> {
  "username": "John",
  "email": "user@gmail.com",
  "password": "123",
  "confirm_password": "123"
}

### Login
> **POST** http://127.0.0.1:8000/api/login/

body:
> {
  "username": "John",
  "password": "123"
}

### Forgotten password
> **PUT** http://127.0.0.1:8000/api/forgotten-password/

body:

>{
  "email": "user@gmail.com",
  "password": "abc",
  "confirm_password": "abc"
}

### Edit profile
> **PATCH** http://127.0.0.1:8000/api/edit_profile/

body:

> {
  "id": "a31a52b2-67b4-422d-bbc6-7553fa629296",
  "email": "jack@gmail.com"
}


### Delete account
> **DELETE** http://127.0.0.1:8000/api/delete_account/

body:
>{
  "id": "a31a52b2-67b4-422d-bbc6-7553fa629296"
}
