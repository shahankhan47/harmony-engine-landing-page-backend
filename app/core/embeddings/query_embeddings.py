import json
from app.constants import OPEN_AI_CLIENT
from app.db.connections import get_vector_db_connection


query_cache = {}
async def query_vectorDB(project_id: str, query: str, top_k: int = 4, similarity_threshold: float | None = None):
    """
    Improved query:
      - caches by project_id + query
      - uses cosine distance (embedding <=> $2)
      - returns structured, numbered entries including filename and similarity score
      - filters by optional distance threshold (lower is more similar)
    """

    cache_key = f"{project_id}:{query}"
    if cache_key in query_cache:
        return query_cache[cache_key]

    # 1) Embed the query
    embedding_resp = await OPEN_AI_CLIENT.embeddings.create(
        model="text-embedding-3-large",
        input=query
    )
    embed_list = embedding_resp.data[0].embedding
    if not embed_list:
        return "No embedding generated for query."

    # convert to pgvector literal string
    query_embedding = "[" + ",".join(str(x) for x in embed_list) + "]"

    # 2) Run DB query using cosine distance (lower = better)
    conn = await get_vector_db_connection()
    rows = await conn.fetch(
        """
        SELECT
            id,
            file_name,
            file_path,
            summary,
            content,
            document,
            metadata,
            (embedding <=> $2::vector) AS distance
        FROM embeddings
        WHERE project_id = $1
        ORDER BY distance ASC
        LIMIT $3
        """,
        project_id, query_embedding, top_k
    )

    if not rows:
        output = "No relevant codebase content found for the generated query."
        query_cache[cache_key] = output
        return output

    # 3) Filter by threshold (if provided) and build nicely formatted output
    entries = []
    for i, r in enumerate(rows):
        dist = r['distance']
        if dist is None:
            continue
        # If threshold provided, skip entries with larger distance.
        if similarity_threshold is not None and dist > similarity_threshold:
            continue

        # metadata may be stored as JSON string
        meta = r['metadata']
        if isinstance(meta, str):
            try:
                meta_obj = json.loads(meta)
            except Exception:
                meta_obj = None
        else:
            meta_obj = meta

        fname = meta_obj.get("file_name") if meta_obj and meta_obj.get("file_name") else r.get("file_name") or "unknown"
        fpath = meta_obj.get("file_path") if meta_obj and meta_obj.get("file_path") else r.get("file_path") or "unknown"
        summary = r.get("summary") or (meta_obj.get("summary") if meta_obj else "") or ""
        document = r.get("document") or ""

        if any(token in document for token in ["def ", "class ", "import ", "{", "=>", ";"]):
            code_block = f"```py\n{document}\n```"
            content_display = code_block
        else:
            content_display = document

        entries.append(
            f"Document {i+1} — File: {fname} (path: {fpath})\n"
            f"Similarity distance (lower=better): {dist:.4f}\n"
            f"Summary: {summary}\n\n"
            f"Content:\n{content_display}"
        )

    if not entries:
        output = "No sufficiently similar content found for the generated query."
    else:
        output = "\n\n---\n\n".join(entries)

    # cache by project+query
    query_cache[cache_key] = output
    return output