import json
import logging
from flask import has_request_context, request
from app.extensions import db
from app.models.user import AuditLog

logger = logging.getLogger(__name__)

def log_audit(action: str, user_id=None, farm_id=None, entity_type=None, entity_id=None, metadata=None):
    """
    Records an immutable audit log entry for security and compliance.
    Safe against calling outside of request context (tests, background jobs).
    """
    try:
        ip = None
        if has_request_context():
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()

        metadata_str = None
        if metadata:
            metadata_str = json.dumps(metadata) if not isinstance(metadata, str) else metadata

        clean_user_id = None
        if user_id is not None:
            try:
                clean_user_id = int(user_id)
            except (ValueError, TypeError):
                clean_user_id = None

        clean_farm_id = None
        if farm_id is not None:
            try:
                clean_farm_id = int(farm_id)
            except (ValueError, TypeError):
                clean_farm_id = None

        entry = AuditLog(
            user_id=clean_user_id,
            farm_id=clean_farm_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            ip_address=ip,
            metadata_json=metadata_str
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Audit log recording error: {str(e)}")
        db.session.rollback()
