import os
import json
import re
import asyncio
import time
from app.constants import OPEN_AI_CLIENT
from app.core.codebase.truncator import open_ai_truncator
from app.core.embeddings.query_embeddings import query_vectorDB
from app.core.misc.checklist import create_checklist
from app.db.chat import get_conversation_history_from_db
from app.utils.chat_utils import store_chat_in_db, summarize_early_exchanges

async def chat(email_id: str, project_id: str, summary: str, user_question: str, checklistAssistant: bool, uploaded_files: list, on_stream: callable) -> str:
    try:
        t0 = time.monotonic()

        # Parallelize all async calls
        conversation_task = get_conversation_history_from_db(email_id, project_id)
        summary_task = open_ai_truncator(text=summary, max_tokens=10000, model="gpt-4.1-mini")
        conversation_messages, summary = await asyncio.gather(conversation_task, summary_task)

        system_message = [
            {"role": "system", "content": "You are a senior software architect expert in code analysis."},
            {"role": "system", "content": f"Codebase summary: {summary}"},
            {"role": "system", "content": "Checklist = call CHECKLIST_ASSISTANT. Missing code = call Querycodebase."}
        ]
        t1 = time.monotonic()

        api_messages = []
        if conversation_messages:
            early_summary_task = summarize_early_exchanges(conversation_messages[:-2])
            last_msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": msg["content"]}
                         for i, msg in enumerate(conversation_messages[-2:])]
            api_messages.extend(last_msgs)
            early_summary = await early_summary_task
            if early_summary:
                system_message.append({"role": "system", "content": f"Earlier summary: {early_summary}"})
        api_messages.append({"role": "user", "content": user_question})

        # Step 1: Generate a ChromaDB search query
        query_prompt = system_message + api_messages + [
            {"role": "system", "content": "Generate a vector search query to retrieve code snippets or documents."}
        ]
        query_response = await OPEN_AI_CLIENT.chat.completions.create(
            model="gpt-4.1-nano",
            messages=query_prompt,
            max_tokens=500,
            temperature=0.1
        )
        t2 = time.monotonic()
        rag_query = query_response.choices[0].message.content

        # Step 2: Query DB and format result
        db_result = await query_vectorDB(project_id, rag_query)
        retrieved_context = await open_ai_truncator(text=db_result, max_tokens=20000, model="gpt-4.1-mini")

        t3 = time.monotonic()
        system_message.extend([
            {"role": "system", "content": f"Search query: {rag_query}"},
            {"role": "system", "content": f"Retrieved codebase info: {retrieved_context}"},
            {"role": "system", "content": f"Original User question: {user_question}"}
        ])

        if uploaded_files:
            system_message.extend([
                {"role": "system", "content": f"""The user has also uploaded one or more files. 
                Here are the names and summaries of the files (Each object contains a fileName and fileSummary):
                {uploaded_files}
                """},
            ])

        final_prompt = system_message + api_messages + [
            {"role": "system", "content": """
                Analyze all context and provide a precise, implementation-ready answer to the question.
                If explaining multiple items (components, files, functions, etc.):
                - List each explicitly in a structured format (numbered list or table)
                - Explain purpose, functionality, dependencies, and key implementation details of each
                - Don’t skip or merge items, even minor ones
                - Include examples, configs, code-snippets, relationships, and usage considerations where relevant
                Make the answer exhaustive and developer-friendly.
            """},
        ]

        if "No relevant codebase content found" in db_result:
            final_prompt.append({"role": "user", "content": f"Call Querycodebase with query: {rag_query}."})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "Querycodebase",
                    "description": "Run a code-level search using a specific query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "Query": {"type": "string", "description": "The query to run."}
                        },
                        "required": ["Query"]
                    }
                }
            }
        ]

        t4 = time.monotonic()
        # Step 3: Tool interaction loop
        while True:
            model_response = await OPEN_AI_CLIENT.chat.completions.create(
                model="gpt-4.1-nano",
                messages=final_prompt,
                max_tokens=2000,
                tool_choice="auto",
                tools=tools
            )
            finish_reason = model_response.choices[0].finish_reason

            if finish_reason == "tool_calls":
                for tool_call in model_response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    if tool_name == "Querycodebase":
                        query = tool_args.get("Query", "")
                        tool_result = await query_vectorDB(project_id, query)
                        formatted_result = await open_ai_truncator(tool_result, max_tokens=20000, model="gpt-4.1-mini")
                        final_prompt.append({"role": "user", "content": formatted_result})
            else:
                break

        t5 = time.monotonic()
        print(f"Initial setup time: {t1 - t0:.2f} sec")
        print(f"Early summary and query generation time: {t2 - t1:.2f} sec")
        print(f"ChromaDB search time: {t3 - t2:.2f} sec")
        print(f"Variables time: {t4 - t3:.2f} sec")
        print(f"Tools run time: {t5 - t4:.2f} sec")
        print(f"Total time: {t5 - t0:.2f} sec")

        raw_response_full = ""
        checklist_title = ""
        if not checklistAssistant:
            final_response_stream = await OPEN_AI_CLIENT.chat.completions.create(
                model="gpt-4.1-mini",
                messages=final_prompt,
                max_tokens=10000,
                stream=True
            )

            async for chunk in final_response_stream:
                delta = chunk.choices[0].delta
                content = delta.content
                if content:
                    raw_response_full += content
                    await on_stream(content)

        else:
            checklist = await create_checklist(project_id, user_question)
            checklist_title = checklist.get("title")
            res = f"Checklist created: {checklist_title}. The checklist will appear in the 'Task Checklist' section after some time. If not, please refresh the page to view it."
            for content in res:
                await on_stream(content)

        asyncio.create_task(store_chat_in_db(email_id, project_id, user_question, raw_response_full, checklist_title, checklistAssistant))

    except Exception as e:
        await on_stream(f"[ERROR] {str(e)}")