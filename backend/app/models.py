from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


def ticket_id():
    return 'T-' + uuid4().hex[:10].upper()


class Ticket(Base):
    __tablename__ = 'tickets'
    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=ticket_id)
    customer_name: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20), default='email')
    status: Mapped[str] = mapped_column(String(20), default='open', index=True)
    assignee: Mapped[str] = mapped_column(String(100), default='Unassigned')
    category: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[str] = mapped_column(String(20), index=True)
    sentiment: Mapped[str] = mapped_column(String(20))
    analysis: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    draft_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {'version_id_col': version}


class Policy(Base):
    __tablename__ = 'policies'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(40), index=True)
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(240), default='Internal knowledge base')
    active: Mapped[bool] = mapped_column(default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __mapper_args__ = {'version_id_col': version}


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey('tickets.id'), index=True)
    action: Mapped[str] = mapped_column(String(60))
    actor: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
