import asyncio
import json
from app.db.connections import get_db_connection


async def insert_checklist(project_id: str, title: str, content: dict):
    conn = await get_db_connection()
    try:
        query = """
            INSERT INTO checklist_table (project_id, title, content)
            VALUES ($1, $2, $3)
            RETURNING id;
        """
        return await conn.fetchval(query, project_id, title, json.dumps(content))
    finally:
        await conn.close()

async def update_checklist_in_db(project_id: str, title: str, content: dict):
    conn = await get_db_connection()
    try:
        query = """
            UPDATE checklist_table
            SET content = $3, updated_at = NOW()
            WHERE project_id = $1 AND title = $2
            RETURNING id;
        """
        return await conn.fetchval(query, project_id, title, json.dumps(content))
    finally:
        await conn.close()

async def delete_checklist_from_db(project_id: str, title: str):
    conn = await get_db_connection()
    try:
        query = """
            DELETE FROM checklist_table
            WHERE project_id = $1 AND title = $2;
        """
        await conn.execute(query, project_id, title)
    finally:
        await conn.close()

async def get_checklists_from_db(project_id: str):
    conn = await get_db_connection()
    try:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS checklist_table (
            id SERIAL PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (project_id, title)
        );
        """)

        query = """
            SELECT id, project_id, title, content, created_at, updated_at
            FROM checklist_table
            WHERE project_id = $1;
        """
        rows = await conn.fetch(query, project_id)
        return rows
    finally:
        await conn.close()