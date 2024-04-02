# Visitor
### --> MTAA BE project app - assignment

> to run BE locally:
``` hypercorn app.__main__:app --reload```

> to run in Docker
```docker run -p 127.0.0.1:8000:8000 --env NAME=[name] --env DATABASE_HOST=gateway.docker.internal --env DATABASE_PORT=[db_port] --env DATABASE_NAME=[db_name] --env DATABASE_USER=[db_user] --env DATABASE_PASSWORD=[db_password]  --name [name-container] [name] ```

## Endpoints

### Hello
> **GET** http://127.0.0.1:8000/hello

### Status
> **GET** http://127.0.0.1:8000/status