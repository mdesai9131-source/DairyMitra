from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.notification import Notification
from app.utils.responses import success_response, error_response

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')

@notifications_bp.route('', methods=['GET'])
@jwt_required()
def list_notifications():
    """List notifications for authenticated user."""
    user_id = int(get_jwt_identity())
    farm_id = request.args.get('farm_id')

    query = Notification.query.filter_by(user_id=user_id)
    if farm_id:
        query = query.filter_by(farm_id=int(farm_id))

    notifications = query.order_by(Notification.created_at.desc()).limit(50).all()
    unread_count = query.filter_by(is_read=False).count()

    return success_response(data={
        'unread_count': unread_count,
        'notifications': [n.to_dict() for n in notifications]
    })

@notifications_bp.route('/<int:id>/read', methods=['POST'])
@jwt_required()
def mark_read(id):
    """Mark a notification as read."""
    user_id = int(get_jwt_identity())
    notification = Notification.query.filter_by(id=id, user_id=user_id).first_or_404()
    notification.is_read = True
    db.session.commit()
    return success_response(message="Notification marked as read")
