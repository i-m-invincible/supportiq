from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal['credit_card', 'bank_account', 'money_transfer', 'credit_reporting', 'debt_collection', 'loan', 'other']
Priority = Literal['critical', 'high', 'medium', 'low']
Status = Literal['open', 'in_review', 'approved', 'resolved']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class TicketCreate(StrictModel):
    customer_name: str = Field(min_length=2, max_length=100)
    subject: str = Field(min_length=5, max_length=180)
    body: str = Field(min_length=20, max_length=10000)
    channel: Literal['email', 'chat', 'web', 'phone'] = 'email'


class Versioned(StrictModel):
    expected_version: int = Field(ge=1)


class TicketUpdate(Versioned):
    assignee: str | None = Field(default=None, min_length=2, max_length=100)
    category: Category | None = None
    priority: Priority | None = None
    status: Literal['open', 'resolved'] | None = None


class DraftEdit(Versioned):
    text: str = Field(min_length=20, max_length=10000)


class Review(Versioned):
    decision: Literal['approve', 'reject']
    reviewer: str = Field(min_length=2, max_length=100)
    note: str = Field(default='', max_length=2000)


class PolicyCreate(StrictModel):
    title: str = Field(min_length=5, max_length=180)
    category: Category
    body: str = Field(min_length=40, max_length=12000)
    source: str = Field(default='Internal knowledge base', min_length=2, max_length=240)


class PolicyUpdate(PolicyCreate, Versioned):
    active: bool = True


class AnalyzeInput(StrictModel):
    text: str = Field(min_length=10, max_length=10000)
