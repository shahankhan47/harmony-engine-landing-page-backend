import json
from fastapi import APIRouter, Form, HTTPException, Query, Response

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
@router.get(
    "/projects/{project_id}/files",
    description="Retrieve all files for a project including summary, content, and snippet"
)
async def get_project_files_with_details(project_id: str):
    conn = None
    try:
        conn = await get_vector_db_connection()

        # Step 1: Check project embeddings existence
        count_query = "SELECT COUNT(*) FROM embeddings WHERE project_id = $1"
        embeddings_count = await conn.fetchval(count_query, project_id)
        if embeddings_count == 0:
            return {"project_id": project_id, "files": []}

        # Step 2: Fetch latest version of each file with full data
        # DISTINCT ON ensures we get only the newest entry per file_path
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
            file_path = record.get("file_path", "") or ""
            file_name = record.get("file_name", "") or ""
            summary = record.get("summary", "") or ""
            content = record.get("content", "") or ""

            # Prepare summary snippet
            if summary.strip():
                snippet = summary.strip()
            else:
                snippet = (content[:200] + "...") if len(content) > 200 else content

            try:
                encoded_id = encode_path(file_path)
            except Exception as enc_e:
                print(f"Warning: Could not encode path '{file_path}'. Skipping. Error: {enc_e}")
                continue

            files.append({
                "id": encoded_id,
                "file_path": file_path,
                "file_name": file_name,
                "summary_snippet": snippet,
                "summary": summary or None,
                "content": content or None
            })

        return {
            "project_id": project_id,
            "files": files
        }

    except Exception as e:
        print(f"Error in get_project_files_with_details for project_id={project_id}: {str(e)}")
        return {"project_id": project_id, "files": []}

    finally:
        if conn:
            await conn.close()
