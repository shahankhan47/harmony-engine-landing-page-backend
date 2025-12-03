import json
from typing import Optional, List, Dict

from asyncpg import Connection
from app.db.connections import get_db_connection, get_vector_db_connection
from app.utils.path_utils import encode_path, decode_path

async def store_summary_in_db(emails: str, project_id: str, summary: str, status: str, executive_summary: str, project_diagrams: str):
    conn: Optional[Connection] = None
    try:
        conn = await get_db_connection()
        email_list = json.loads(emails)

        for email_info in email_list:
            email = email_info['email'].replace('@', '_').replace('.', '_')
            table_name = f"summaries_{email}"
            update_query = f"""
                UPDATE {table_name}
                SET summary = $2,
                status = $3,
                executive_summary = $4,
                project_diagrams = $5
                WHERE project_id = $1;
            """
            
            await conn.execute(update_query, project_id, summary, status, executive_summary, project_diagrams)

    except Exception as e:
        print(f"An error occurred while storing the summary: {e}")
    
    finally:
        if conn:
            await conn.close()

async def get_summary_from_db(email: str, project_id: str) -> Optional[str]:
    conn = None
    try:
        conn = await get_db_connection()
        
        table_name = f"summaries_{email.replace('@', '_').replace('.', '_')}"
        select_query = f"""
            SELECT summary FROM {table_name}
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await conn.fetchrow(select_query, project_id)
        return result['summary'] if result else None

    except Exception as e:
        print(f"An error occurred while retrieving the summary: {e}")
        return None
    finally:
        if conn:
            await conn.close()

async def get_executive_summary_from_db(email: str, project_id: str) -> Optional[str]:
    conn = None
    try:
        conn = await get_db_connection()
        
        table_name = f"summaries_{email.replace('@', '_').replace('.', '_')}"
        select_query = f"""
            SELECT  executive_summary FROM {table_name}
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await conn.fetchrow(select_query, project_id)
        return result['executive_summary'] if result else None

    except Exception as e:
        print(f"An error occurred while retrieving the executive_summary: {e}")
        return None
    
    finally:
        if conn:
            await conn.close()

async def get_project_diagrams_from_db(email: str, project_id: str) -> Optional[str]:
    conn = None
    try:
        conn = await get_db_connection()
        
        table_name = f"summaries_{email.replace('@', '_').replace('.', '_')}"
        select_query = f"""
            SELECT  project_diagrams FROM {table_name}
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await conn.fetchrow(select_query, project_id)
        return result['project_diagrams'] if result else None

    except Exception as e:
        print(f"An error occurred while retrieving the project_diagrams: {e}")
        return None
    
    finally:
        if conn:
            await conn.close()

async def ensure_context_summaries_table_exists(conn: Connection):
    create_table_query = """
    CREATE TABLE IF NOT EXISTS context_summaries (
        project_id VARCHAR PRIMARY KEY,
        full_summaries TEXT
    );
    """
    await conn.execute(create_table_query)

async def insert_or_update_summary_in_context_summaries(project_id: str, full_summaries: str) -> None:
    conn: Optional[Connection] = None
    try:
        conn = await get_db_connection()
        
        # Ensure the table exists
        await ensure_context_summaries_table_exists(conn)
        
        # Use an upsert query to insert or update
        upsert_query = """
        INSERT INTO context_summaries (project_id, full_summaries)
        VALUES ($1, $2)
        ON CONFLICT (project_id) DO UPDATE 
        SET full_summaries = EXCLUDED.full_summaries;
        """
        
        # Execute the upsert query
        await conn.execute(upsert_query, project_id, full_summaries)

    except Exception as e:
        print(f"An error occurred while inserting or updating the summary: {e}")
    
    finally:
        if conn:
            await conn.close()

async def get_files_list(project_id: str) -> List[Dict[str, str]]:
    """
    Retrieve a list of files with summary snippets for a given project.

    Args:
        project_id: The unique identifier of the project.

    Returns:
        A list of dictionaries, each containing:
            - file_path: path relative to the project root.
            - file_name: name of the file.
            - summary_snippet: a concise snippet from file summary or content.
        If no embeddings are found, returns an empty list.
    """
    conn = None
    try:
        conn = await get_vector_db_connection()

        # Step 1: Check if any embeddings exist for this project
        count_query = "SELECT COUNT(*) FROM embeddings WHERE project_id = $1"
        embeddings_count = await conn.fetchval(count_query, project_id)
        if embeddings_count == 0:
            # No embeddings found for the project, return empty list
            return []

        # Step 2: Retrieve file details
        files_query = """
            SELECT file_path, file_name, summary, content
            FROM embeddings
            WHERE project_id = $1
            ORDER BY file_path ASC
        """
        records = await conn.fetch(files_query, project_id)

        result = []
        for record in records:
            file_path = (record.get("file_path", "") or "")
            file_name = record.get("file_name", "") or ""
            summary = record.get("summary", "") or ""
            content = record.get("content", "") or ""

            # Prepare summary snippet: prefer summary, fallback to truncated content
            if summary.strip():
                snippet = summary.strip()
            else:
                snippet = (content[:200] + "...") if len(content) > 200 else content

            try:
                encoded_id = encode_path(file_path)
            except Exception as enc_e:
                print(f"Warning: Could not encode path '{file_path}'. Skipping. Error: {enc_e}")
                continue # Skip files with paths that fail to encode

            result.append({
                "id": encoded_id, # Add the encoded ID
                "file_path": file_path, # Keep original path if needed internally or for display
                "file_name": file_name,
                "summary_snippet": snippet
            })

        return result

    except Exception as e:
        # Consider logging the exception here
        print(f"Error in get_files_list for project_id={project_id}: {str(e)}")
        return []

    finally:
        if conn:
            await conn.close()
            
async def get_file_summary(project_id: str, file_id: str) -> str:
    """
    Retrieve the latest content or summary for a specific file in a project
    from the embeddings table, filtered by project_id and file_path.
    """
    conn = None
    try:
        try:
            file_path = decode_path(file_id)
        except ValueError as dec_e:
            print(f"Error decoding file_id '{file_id}': {dec_e}")
            return f"Error: Invalid file ID format."
        
        conn = await get_vector_db_connection()

        query = """
            SELECT content, summary, metadata
            FROM embeddings
            WHERE project_id = $1 AND file_path = $2
            ORDER BY created_at DESC
            LIMIT 1
        """

        file_path = file_path
        row = await conn.fetchrow(query, project_id, file_path)

        if row:
            # Return a dictionary containing both fields.
            # Use .get() to safely handle cases where a column might be null.
            return {
                "content": row.get('content'),
                "summary": row.get('summary')
            }
        else:
            return "No data found for the specified file."

    except Exception as e:
        print(f"Error in get_file_content_or_summary: {e}")
        return f"Error: {e}"

    finally:
        if conn:
            await conn.close()