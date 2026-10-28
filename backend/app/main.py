import csv
import io
import secrets
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyHeader
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.config import Settings
from app.database import Base, make_database
from app.models import AuditEvent, Policy, Ticket, utcnow
from app.schemas import (AnalyzeInput, Category, DraftEdit, PolicyCreate, PolicyUpdate, Priority,
                         Review, Status, TicketCreate, TicketUpdate, Versioned)
from app.seed import seed_database
from app.services.drafting import citations_valid, generate_draft
from app.services.intelligence import Intelligence, PRIORITY_HOURS
from app.services.retrieval import retrieve


def aware(value: datetime):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def serialize(row):
    return {c.name: (aware(getattr(row, c.name)).isoformat() if isinstance(getattr(row, c.name), datetime)
                     else getattr(row, c.name)) for c in row.__table__.columns}


def verify_version(row, expected):
    if row.version != expected:
        raise HTTPException(409, 'This record changed. Refresh before saving.')


def ticket_or_404(session, ticket_id):
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, 'Ticket not found.')
    return ticket


def record(session, ticket, action, details=None, actor='Support agent'):
    session.add(AuditEvent(ticket_id=ticket.id, action=action, actor=actor, details=details or {}))
    ticket.updated_at = utcnow()


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    engine, session_factory = make_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        if settings.auto_create_schema:
            Base.metadata.create_all(engine)
        app.state.intelligence = Intelligence(settings)
        if settings.seed_demo:
            with session_factory() as session:
                seed_database(session, settings, app.state.intelligence)
        yield
        engine.dispose()

    app = FastAPI(title='SupportIQ API', version='1.0.0', description='Human-reviewed support intelligence. Demo policies are fictional.', lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.engine = engine
    app.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in settings.cors_origins.split(',') if s.strip()],
                       allow_methods=['GET', 'POST', 'PUT', 'PATCH'], allow_headers=['Content-Type', 'X-API-Key'])
    key_header = APIKeyHeader(name='X-API-Key', auto_error=False)

    def authorize(key: str | None = Depends(key_header)):
        if settings.api_key and not secrets.compare_digest(key or '', settings.api_key):
            raise HTTPException(401, 'A valid workspace API key is required.')

    def get_session():
        with session_factory() as session:
            yield session

    @app.exception_handler(StaleDataError)
    async def stale_error(_: Request, __: StaleDataError):
        return JSONResponse(status_code=409, content={'detail': 'A concurrent edit was detected. Refresh and try again.'})

    @app.middleware('http')
    async def security_headers(request, call_next):
        # Keep customer narratives and keys out of application logs and error responses.
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Request-ID'] = uuid4().hex
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/health')
    def health(session: Session = Depends(get_session)):
        session.execute(text('SELECT 1'))
        return {'status': 'ok'}

    router = APIRouter(prefix='/api/v1', dependencies=[Depends(authorize)])

    @router.get('/meta')
    def meta():
        return {'app': 'SupportIQ', 'version': '1.0.0', 'demo_data': settings.seed_demo,
                'draft_provider': settings.draft_provider, 'auth_enabled': bool(settings.api_key),
                'classifier': app.state.intelligence.metadata, 'classification_threshold': settings.classification_threshold,
                'policy_notice': 'Seed policies are fictional examples, not legal or institutional guidance.'}

    @router.get('/tickets')
    def list_tickets(q: str = Query('', max_length=200), status: Status | None = None,
                     priority: Priority | None = None, category: Category | None = None,
                     offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                     session: Session = Depends(get_session)):
        statement = select(Ticket)
        if q:
            escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            pattern = f'%{escaped}%'
            statement = statement.where(or_(*[column.ilike(pattern, escape='\\') for column in [Ticket.subject, Ticket.body, Ticket.customer_name, Ticket.id]]))
        for column, value in [(Ticket.status, status), (Ticket.priority, priority), (Ticket.category, category)]:
            if value:
                statement = statement.where(column == value)
        total = session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = session.scalars(statement.order_by(Ticket.created_at.desc()).offset(offset).limit(limit)).all()
        return {'items': [serialize(t) for t in rows], 'total': total, 'offset': offset, 'limit': limit}

    @router.post('/tickets', status_code=201)
    def create_ticket(payload: TicketCreate, session: Session = Depends(get_session)):
        analysis = app.state.intelligence.analyze(payload.subject + '\n' + payload.body)
        ticket = Ticket(**payload.model_dump(), analysis=analysis, category=analysis['category'],
                        priority=analysis['priority'], sentiment=analysis['sentiment'],
                        due_at=utcnow() + timedelta(hours=PRIORITY_HOURS[analysis['priority']]))
        session.add(ticket)
        session.flush()
        record(session, ticket, 'created', {'category': ticket.category, 'priority': ticket.priority})
        session.commit()
        return serialize(ticket)

    @router.get('/tickets/{ticket_id}')
    def get_ticket(ticket_id: str, session: Session = Depends(get_session)):
        return serialize(ticket_or_404(session, ticket_id))

    @router.patch('/tickets/{ticket_id}')
    def update_ticket(ticket_id: str, payload: TicketUpdate, session: Session = Depends(get_session)):
        ticket = ticket_or_404(session, ticket_id)
        verify_version(ticket, payload.expected_version)
        changes = payload.model_dump(exclude={'expected_version'}, exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise HTTPException(422, 'Provide at least one non-null field to update.')
        if changes.get('status') == 'resolved' and ticket.status != 'approved':
            raise HTTPException(409, 'Approve a reviewed response before resolving the ticket.')
        category_changed = 'category' in changes and changes['category'] != ticket.category
        if category_changed and changes.get('status') == 'resolved':
            raise HTTPException(409, 'Review the new category before resolving.')
        for field, value in changes.items():
            setattr(ticket, field, value)
        if category_changed:
            ticket.analysis = {**ticket.analysis, 'human_category_override': ticket.category, 'needs_review': False}
            ticket.draft_text, ticket.draft_meta = None, None
            ticket.status = 'open'
        if category_changed or changes.get('status') == 'open':
            ticket.approved_by, ticket.approved_at = None, None
        if 'priority' in changes:
            ticket.due_at = aware(ticket.created_at) + timedelta(hours=PRIORITY_HOURS[ticket.priority])
        record(session, ticket, 'updated', changes)
        session.commit()
        return serialize(ticket)

    @router.post('/tickets/{ticket_id}/draft')
    def draft_ticket(ticket_id: str, payload: Versioned, session: Session = Depends(get_session)):
        ticket = ticket_or_404(session, ticket_id)
        verify_version(ticket, payload.expected_version)
        if ticket.status == 'resolved':
            raise HTTPException(409, 'Reopen this ticket before generating another draft.')
        policies = session.scalars(select(Policy).where(Policy.active.is_(True))).all()
        citations = retrieve(ticket.subject + ' ' + ticket.body, policies, ticket.category, settings.retrieval_threshold)
        draft, metadata = generate_draft(ticket.subject + '\n' + ticket.body, citations, settings)
        ticket.draft_text, ticket.draft_meta = draft, metadata
        ticket.status, ticket.approved_by, ticket.approved_at = 'in_review', None, None
        record(session, ticket, 'draft_generated', {'provider': metadata['provider'], 'sources': [c['policy_id'] for c in citations]})
        session.commit()
        return serialize(ticket)

    @router.put('/tickets/{ticket_id}/draft')
    def edit_draft(ticket_id: str, payload: DraftEdit, session: Session = Depends(get_session)):
        ticket = ticket_or_404(session, ticket_id)
        verify_version(ticket, payload.expected_version)
        if ticket.status == 'resolved' or not ticket.draft_meta:
            raise HTTPException(409, 'Generate a draft on an open ticket first.')
        if ticket.draft_meta['citations'] and not citations_valid(payload.text, ticket.draft_meta['citations']):
            raise HTTPException(422, 'Keep at least one valid policy citation and remove unknown citation IDs.')
        ticket.draft_text = payload.text
        ticket.status, ticket.approved_by, ticket.approved_at = 'in_review', None, None
        record(session, ticket, 'draft_edited')
        session.commit()
        return serialize(ticket)

    @router.post('/tickets/{ticket_id}/review')
    def review_draft(ticket_id: str, payload: Review, session: Session = Depends(get_session)):
        ticket = ticket_or_404(session, ticket_id)
        verify_version(ticket, payload.expected_version)
        if ticket.status != 'in_review' or not ticket.draft_text or not ticket.draft_meta:
            raise HTTPException(409, 'Only a draft awaiting review can be approved or rejected.')
        if payload.decision == 'approve':
            citations = ticket.draft_meta.get('citations', [])
            if not citations or not citations_valid(ticket.draft_text, citations):
                raise HTTPException(409, 'No valid policy citation. Add a relevant policy and regenerate the draft.')
            for citation in citations:
                policy = session.scalar(select(Policy).where(Policy.id == citation['policy_id']).with_for_update(read=True))
                if not policy or not policy.active or policy.version != citation['version']:
                    raise HTTPException(409, 'A cited policy changed. Regenerate and review the draft.')
            ticket.status = 'approved'
            ticket.approved_by, ticket.approved_at = payload.reviewer, utcnow()
        else:
            ticket.status, ticket.approved_by, ticket.approved_at = 'open', None, None
        record(session, ticket, 'approved' if payload.decision == 'approve' else 'rejected', {'note': payload.note}, payload.reviewer)
        session.commit()
        return serialize(ticket)

    @router.get('/tickets/{ticket_id}/audit')
    def audit(ticket_id: str, session: Session = Depends(get_session)):
        ticket_or_404(session, ticket_id)
        return [serialize(e) for e in session.scalars(select(AuditEvent).where(AuditEvent.ticket_id == ticket_id).order_by(AuditEvent.created_at, AuditEvent.id))]

    @router.post('/analyze')
    def analyze(payload: AnalyzeInput):
        return app.state.intelligence.analyze(payload.text)

    @router.get('/policies')
    def policies(q: str = Query('', max_length=500), session: Session = Depends(get_session)):
        rows = session.scalars(select(Policy).order_by(Policy.title)).all()
        if q.strip():
            return {'items': [serialize(p) for p in rows], 'matches': retrieve(q, rows, threshold=settings.retrieval_threshold, limit=5)}
        return {'items': [serialize(p) for p in rows], 'matches': []}

    @router.post('/policies', status_code=201)
    def create_policy(payload: PolicyCreate, session: Session = Depends(get_session)):
        policy = Policy(id='POL-' + uuid4().hex[:8].upper(), **payload.model_dump())
        session.add(policy)
        session.commit()
        return serialize(policy)

    @router.put('/policies/{policy_id}')
    def update_policy(policy_id: str, payload: PolicyUpdate, session: Session = Depends(get_session)):
        policy = session.get(Policy, policy_id)
        if not policy:
            raise HTTPException(404, 'Policy not found.')
        verify_version(policy, payload.expected_version)
        for field, value in payload.model_dump(exclude={'expected_version'}).items():
            setattr(policy, field, value)
        policy.updated_at = utcnow()
        session.commit()
        return serialize(policy)

    @router.get('/analytics')
    def analytics(session: Session = Depends(get_session)):
        rows = session.scalars(select(Ticket)).all()
        now = utcnow()
        active = [t for t in rows if t.status not in {'approved', 'resolved'}]
        trend = []
        for days in range(6, -1, -1):
            day = (now - timedelta(days=days)).date()
            on_day = [t for t in rows if aware(t.created_at).date() == day]
            trend.append({'date': day.isoformat(), 'total': len(on_day),
                          'negative': sum(t.sentiment == 'negative' for t in on_day)})
        return {'total': len(rows), 'active': len(active),
                'awaiting_review': sum(t.status == 'in_review' for t in rows),
                'critical': sum(t.priority == 'critical' for t in active),
                'overdue': sum(aware(t.due_at) < now for t in active),
                'approved': sum(t.status == 'approved' for t in rows),
                'resolved': sum(t.status == 'resolved' for t in rows),
                'mean_confidence': round(sum(t.analysis['confidence'] for t in rows) / len(rows), 4) if rows else 0,
                'categories': dict(Counter(t.category for t in rows)),
                'priorities': dict(Counter(t.priority for t in rows)),
                'sentiments': dict(Counter(t.sentiment for t in rows)),
                'statuses': dict(Counter(t.status for t in rows)), 'trend': trend}

    @router.get('/export/tickets.csv')
    def export_tickets(session: Session = Depends(get_session)):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['id', 'subject', 'customer_name', 'category', 'priority', 'status', 'created_at'])
        for ticket in session.scalars(select(Ticket).order_by(Ticket.created_at.desc())):
            values = [ticket.id, ticket.subject, ticket.customer_name, ticket.category, ticket.priority, ticket.status, aware(ticket.created_at).isoformat()]
            # Spreadsheet formula injection protection, including leading whitespace.
            writer.writerow(["'" + v if v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else v for v in values])
        return Response(stream.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="supportiq-tickets.csv"'})

    app.include_router(router)
    return app


app = create_app()
