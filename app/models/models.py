import asyncio
import time
from typing import List, Optional
from pydantic import BaseModel

"""All Classes need to be revised, this bit is convoluted"""
class AnalyzeSummaryRequest(BaseModel):
    summary: str
    user_question: str

class Collaborator(BaseModel):
    email: str
    role: str

class Project(BaseModel):
    project_id: str
    created_at: str
    status: str
    project_name :str
    role: Optional[str] 
    project_description: Optional[str]
    file_source: Optional[str]
    commit_id: Optional[str]
    collaborators: List[Collaborator]


class ProjectsResponse(BaseModel):
    projects: List[Project]

class Message(BaseModel):
    role: str
    content: str

class ConversationHistoryResponse(BaseModel):
    history: List[Message]
    is_new_chat: bool

class TicketReviewRequest(BaseModel):
    project_id: str
    ticket_content: str
    ticket_id: str          
    callback_url: str

class RequirementsAnalysisRequest(BaseModel):
    project_id: str
    requirement: str
    callback_url: str  
    owner_email: str

class PRReviewRequest(BaseModel):
    project_id: str
    pr_id: str
    deep_review: str
    git_diff: str

class AsyncRateLimiter:
    def __init__(self, rate_limit):
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            while self.tokens < 1:
                self.add_new_tokens()
                await asyncio.sleep(0.1)
            self.tokens -= 1

    def add_new_tokens(self):
        now = time.monotonic()
        time_since_update = now - self.updated_at
        new_tokens = time_since_update * self.rate_limit
        if new_tokens > 1:
            self.tokens = min(self.tokens + new_tokens, self.rate_limit)
            self.updated_at = now