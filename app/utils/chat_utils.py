from app.constants import OPEN_AI_CLIENT
from app.db.chat import store_conversation_in_db

# Summarize early messages
async def summarize_early_exchanges(messages: list[dict], num_exchanges: int = 4) -> str:
    if len(messages) <= num_exchanges:
        return ""

    early_messages = messages[:num_exchanges * 2]
    summary_prompt = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in early_messages])
    input_text = f"Summarize the following conversation concisely:\n\n{summary_prompt}"

    response = await OPEN_AI_CLIENT.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "system", "content": "You summarize conversations concisely."},
                  {"role": "user", "content": f"Provide a brief summary. Here is the conversation: {input_text}"}],
        max_tokens=500,
        temperature=0.1
    )
    return response.choices[0].message.content

async def store_chat_in_db(email_id, project_id, user_question, raw_response_full, checklist_title, checklistAssistant=False):
    if not checklistAssistant:
        await store_conversation_in_db(email_id, project_id, "user", user_question)
        await store_conversation_in_db(email_id, project_id, "assistant", raw_response_full)
    else:
        await store_conversation_in_db(email_id, project_id, "user", f"User requested checklist creation")
        await store_conversation_in_db(email_id, project_id, "assistant", f"Checklist created: {checklist_title}. The checklist will appear in the 'Task Checklist' section after some time. If not, please refresh the page to view it.")