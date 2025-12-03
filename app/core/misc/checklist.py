# checklist_operations.py
import os
import json
from datetime import datetime
from openai import AsyncOpenAI
from app.db.checklist import delete_checklist_from_db, get_checklists_from_db, insert_checklist, update_checklist_in_db

# OpenAI client
OPEN_AI_CLIENT = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --------------------------
# BUSINESS LOGIC
# --------------------------

async def create_checklist(project_id: str, checklist_description: str):
    """
    Creates a new checklist using OpenAI, then stores it in Postgres.
    """
    final_prompt = [
        {"role": "system", "content": "You are a checklist assistant. Generate structured checklists. Important: Always respond ONLY with valid JSON in the format: {title, steps:[{step_number, description, details, status}]}"},
        {"role": "user", "content": f"Create a new checklist with following details: {checklist_description}"}
    ]

    model_response = await OPEN_AI_CLIENT.chat.completions.create(
        model="gpt-4.1-nano",
        messages=final_prompt,
        max_tokens=2000
    )

    checklist_content = json.loads(model_response.choices[0].message.content)
    checklist_title = checklist_content.get("title")

    checklist_id = await insert_checklist(project_id, checklist_title, {"content": checklist_content})

    return {"id": checklist_id, "title": checklist_title, "content": checklist_content}


async def update_checklist(project_id: str, title: str, modification: str):
    """
    Modifies an existing checklist using OpenAI and updates DB.
    """
    existing_checklists = await get_checklists_from_db(project_id)

    parsed_checklists = []
    for row in existing_checklists:
        raw_content = row["content"]

        # Ensure JSON is parsed
        if isinstance(raw_content, str):
            try:
                raw_content = json.loads(raw_content)
            except Exception:
                print(f"Invalid JSON in checklist {row['id']}")
                continue

        # If wrapped inside {"content": "..."} unwrap it
        if isinstance(raw_content, dict) and "content" in raw_content:
            inner = raw_content["content"]
            if isinstance(inner, str):
                try:
                    inner = json.loads(inner)
                except Exception:
                    pass
            if isinstance(inner, dict):
                raw_content = inner

        parsed_checklists.append({
            "id": row["id"],
            "project_id": row["project_id"],
            "title": row["title"],
            "content": raw_content,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        })

    checklist = next((c for c in parsed_checklists if c["content"]["title"] == title), None)
    if not checklist:
        raise ValueError(f"Checklist with title '{title}' not found for project {project_id}")

    existing_content = checklist["content"]

    final_prompt = [
        {"role": "system", "content": "You are a checklist assistant. Modify existing checklists based on instructions. Important: Always respond ONLY with valid JSON in the format: {title, steps:[{step_number, description, details, status}]}"},
        {"role": "user", "content": f"Here is the existing checklist: {existing_content}.\nApply the following modification: {modification}"}
    ]

    model_response = await OPEN_AI_CLIENT.chat.completions.create(
        model="gpt-4.1-nano",
        messages=final_prompt,
        max_tokens=2000
    )

    updated_content = model_response.choices[0].message.content

    await update_checklist_in_db(project_id, title, {"content": updated_content})
    return {"title": title, "content": updated_content}


async def delete_checklist(project_id: str, title: str):
    """
    Deletes a checklist from DB.
    """
    await delete_checklist_from_db(project_id, title)
    return {"status": "deleted", "title": title}


async def fetch_checklists(project_id: str):
    """
    Fetches all checklists for a project from DB.
    """
    rows = await get_checklists_from_db(project_id)
    checklists = []
    for row in rows:
        try:
            # Parse JSONB into dict
            raw_content = row["content"]

            # Step 1: ensure it's a dict
            if isinstance(raw_content, str):
                try:
                    raw_content = json.loads(raw_content)
                except Exception:
                    print(f"Row {row['id']} has invalid JSON string")
                    continue

            # Step 2: unwrap "content" if nested
            if isinstance(raw_content, dict) and "content" in raw_content:
                inner = raw_content["content"]
                if isinstance(inner, str):
                    try:
                        inner = json.loads(inner)
                    except Exception:
                        pass
                if isinstance(inner, dict):
                    raw_content = inner

            # Step 3: build final structure
            checklist_obj = {
                "title": raw_content.get("title", row["title"]),
                "steps": raw_content.get("steps", [])
            }
            checklists.append(checklist_obj)
        except Exception as e:
            print(f"Error parsing checklist content for row {row['id']}: {e}")
    return {"checklist": checklists}
