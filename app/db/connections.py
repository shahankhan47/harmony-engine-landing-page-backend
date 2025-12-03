import os
import asyncpg


VECTOR_DB_PARAMS = {
    'database': os.environ.get('DB_VECTOR'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST'),
    'port': os.environ.get('DB_PORT')
}

CORE_DB_PARAMS = {
    'database': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST'),
    'port': os.environ.get('DB_PORT')
}

async def  get_vector_db_connection():
    return await asyncpg.connect(**VECTOR_DB_PARAMS)

async def  get_db_connection():
    return await asyncpg.connect(**CORE_DB_PARAMS)