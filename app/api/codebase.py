import json
from fastapi import APIRouter, Form, HTTPException, Query, Response
import time
import asyncio
from typing import Dict, Any

from app.db.codebase import get_executive_summary_from_db, get_project_diagrams_from_db
from app.db.codebase import get_files_list, get_file_summary
from app.db.connections import get_vector_db_connection
from app.utils.path_utils import decode_path, encode_path

router = APIRouter()

#$~ API 1 ~$############################################################################################################################
#$~ Description ~$#
"""
This API retrieves Executive Summary of the project, this replaces the previous generate summary api - API 6
"""
@router.get("/executive-summary", description="This API retrieves the Executive Summary of the project and user.")
async def get_executive_summary(
    email: str = Query(..., description="The email address of the user"),
    project_id: str = Query(..., description="The unique identifier for the project")
):
    try:
        executive_summary = await get_executive_summary_from_db(email, project_id)
        return  executive_summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#$~ API 2 ~$############################################################################################################################
#$~ Description ~$#
"""
This API retrieves project diagrams this replaces the previous generate mermaid api - API 7 
"""
@router.get("/project_diagrams", description="This API retrieves the project's mermaid diagrams.")
async def get_project_diagram(
    email: str = Query(..., description="The email address of the user"),
    project_id: str = Query(..., description="The unique identifier for the project")
):
    try:
        project_diagrams = await get_project_diagrams_from_db(email, project_id)
        return  project_diagrams
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#$~ API 3 ~$############################################################################################################################
#$~ Description ~$#
"""
    Retrieve a list of files with summaries for the specified project_id.
"""
_PROJECT_FILES_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = asyncio.Lock()

# Set to None for infinite cache (recommended for your case)
_CACHE_TTL_SECONDS = None  # or e.g. 300

@router.get(
    "/projects/{project_id}/files",
    description="Retrieve all files for a project including summary, content, and snippet"
)
async def get_project_files_with_details(project_id: str):
    now = time.time()

    # -----------------------------
    # CACHE HIT (FAST PATH)
    # -----------------------------
    cached = _PROJECT_FILES_CACHE.get(project_id)
    if cached:
        if cached["expires_at"] is None or cached["expires_at"] > now:
            return cached["data"]

    # -----------------------------
    # CACHE MISS (LOCKED)
    # -----------------------------
    async with _CACHE_LOCK:

        # Double-check cache after acquiring lock
        cached = _PROJECT_FILES_CACHE.get(project_id)
        if cached:
            if cached["expires_at"] is None or cached["expires_at"] > now:
                return cached["data"]

        conn = None
        try:
            conn = await get_vector_db_connection()

            # Step 1: Check if embeddings exist
            count_query = "SELECT COUNT(*) FROM embeddings WHERE project_id = $1"
            embeddings_count = await conn.fetchval(count_query, project_id)

            if embeddings_count == 0:
                result = {
                    "project_id": project_id,
                    "files": []
                }
            else:
                # Step 2: Fetch latest version of each file
                files_query = """
                    SELECT DISTINCT ON (file_path)
                        file_path,
                        file_name,
                        summary,
                        content
                    FROM embeddings
                    WHERE project_id = $1
                    ORDER BY file_path ASC, created_at DESC
                """

                records = await conn.fetch(files_query, project_id)

                files = []
                for record in records:
                    file_path = record.get("file_path") or ""
                    file_name = record.get("file_name") or ""
                    summary = record.get("summary") or ""
                    content = record.get("content") or ""

                    # Summary snippet logic
                    if summary.strip():
                        snippet = summary.strip()
                    else:
                        snippet = (
                            content[:200] + "..."
                            if len(content) > 200
                            else content
                        )

                    try:
                        encoded_id = encode_path(file_path)
                    except Exception:
                        # Skip invalid paths safely
                        continue

                    files.append({
                        "id": encoded_id,
                        "file_path": file_path,
                        "file_name": file_name,
                        "summary_snippet": snippet,
                        "summary": summary or None,
                        "content": content or None
                    })

                result = {
                    "project_id": project_id,
                    "files": files
                }

            # -----------------------------
            # STORE IN CACHE
            # -----------------------------
            _PROJECT_FILES_CACHE[project_id] = {
                "data": result,
                "expires_at": (
                    None if _CACHE_TTL_SECONDS is None
                    else now + _CACHE_TTL_SECONDS
                )
            }

            return result

        except Exception as e:
            print(
                f"Error in get_project_files_with_details "
                f"(project_id={project_id}): {e}"
            )
            return {
                "project_id": project_id,
                "files": []
            }

        finally:
            if conn:
                await conn.close()
