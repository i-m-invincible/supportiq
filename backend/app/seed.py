import json
from datetime import timedelta

from sqlalchemy import func, select

from app.models import AuditEvent, Policy, Ticket, utcnow
from app.services.drafting import extractive_draft
from app.services.intelligence import PRIORITY_HOURS
from app.services.retrieval import retrieve


def seed_database(session, settings, intelligence):
    if not session.scalar(select(func.count()).select_from(Policy)):
        for policy in json.loads((settings.data_dir / 'policies.json').read_text()):
            session.add(Policy(**policy))
        session.commit()
    if session.scalar(select(func.count()).select_from(Ticket)):
        return
    policies = session.scalars(select(Policy)).all()
    examples = json.loads((settings.data_dir / 'tickets.json').read_text())
    for i, example in enumerate(examples):
        age_hours = example.pop('age_hours')
        requested_status = example.pop('status', 'open')
        analysis = intelligence.analyze(example['subject'] + '\n' + example['body'])
        created = utcnow() - timedelta(hours=age_hours)
        ticket = Ticket(id=f'T-{1041 + i}', **example, category=analysis['category'], priority=analysis['priority'],
                        sentiment=analysis['sentiment'], analysis=analysis, created_at=created, updated_at=created,
                        due_at=created + timedelta(hours=PRIORITY_HOURS[analysis['priority']]))
        session.add(ticket)
        session.flush()
        session.add(AuditEvent(ticket_id=ticket.id, action='created', actor='Demo workspace', created_at=created,
                               details={'note': 'Synthetic sample, not a real customer.'}))
        if requested_status != 'open':
            citations = retrieve(ticket.subject + ' ' + ticket.body, policies, ticket.category, settings.retrieval_threshold)
            ticket.draft_text = extractive_draft(citations)
            ticket.draft_meta = {'provider': 'extractive', 'citations': citations, 'grounded': bool(citations),
                                 'requires_approval': True, 'fallback_reason': None,
                                 'warning': 'Demo policies only. Review relevance before approval.'}
            ticket.status = 'in_review'
            session.add(AuditEvent(ticket_id=ticket.id, action='draft_generated', actor='Demo workspace',
                                   created_at=created + timedelta(minutes=10), details={'provider': 'extractive'}))
            if requested_status in {'approved', 'resolved'} and citations:
                ticket.status = requested_status
                ticket.approved_by = 'Demo reviewer'
                ticket.approved_at = created + timedelta(minutes=30)
                session.add(AuditEvent(ticket_id=ticket.id, action='approved', actor='Demo reviewer',
                                       created_at=ticket.approved_at, details={'note': 'Synthetic workflow example.'}))
                if requested_status == 'resolved':
                    session.add(AuditEvent(ticket_id=ticket.id, action='resolved', actor='Demo reviewer',
                                           created_at=created + timedelta(hours=1), details={}))
        session.commit()
