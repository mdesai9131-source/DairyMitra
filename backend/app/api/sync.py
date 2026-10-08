from datetime import date, datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.sync import SyncRecord
from app.models.milk import MilkProduction
from app.models.customer import MilkDelivery
from app.models.expense import Expense
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

sync_bp = Blueprint('sync', __name__, url_prefix='/api/v1/sync')

@sync_bp.route('', methods=['POST'])
@farm_access_required
def process_sync_batch():
    """
    Idempotent offline batch synchronization.
    Accepts an array of offline mutations queued by Flutter client SQLite:
    [
      {
        "client_sync_id": "uuid-1234",
        "entity_type": "MILK",
        "action": "CREATE",
        "data": { ... }
      },
      ...
    ]
    Uses client_sync_id to guarantee idempotency and avoid duplicate inserts.
    """
    user_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}
    farm_id = body.get('farm_id')
    queue = body.get('queue', [])

    results = []

    for item in queue:
        sync_id = item.get('client_sync_id')
        entity_type = item.get('entity_type', '').upper()
        action = item.get('action', 'CREATE').upper()
        data = item.get('data', {})

        if not sync_id:
            continue

        # Idempotency check: has this item already been processed?
        existing_sync = SyncRecord.query.filter_by(client_sync_id=sync_id).first()
        if existing_sync:
            results.append({
                'client_sync_id': sync_id,
                'status': 'ALREADY_SYNCED',
                'backend_id': existing_sync.entity_id
            })
            continue

        status = 'APPLIED'
        error_msg = None
        created_id = None

        try:
            if entity_type == 'MILK':
                target_date = date.fromisoformat(data['date'])
                animal_id = int(data['animal_id'])
                shift = data['shift'].upper()
                qty = float(data['quantity'])

                # Check if conflict exists
                existing = MilkProduction.query.filter_by(
                    farm_id=farm_id,
                    animal_id=animal_id,
                    shift=shift,
                    date=target_date
                ).first()

                if existing:
                    existing.quantity = qty
                    created_id = existing.id
                else:
                    record = MilkProduction(
                        farm_id=farm_id,
                        animal_id=animal_id,
                        date=target_date,
                        shift=shift,
                        quantity=qty,
                        recorded_by=user_id
                    )
                    db.session.add(record)
                    db.session.flush()
                    created_id = record.id

            elif entity_type == 'DELIVERY':
                target_date = date.fromisoformat(data['date'])
                cust_id = int(data['customer_id'])
                shift = data.get('shift', 'MORNING').upper()
                qty = float(data['quantity'])
                rate = float(data['price_per_litre'])

                existing = MilkDelivery.query.filter_by(
                    customer_id=cust_id,
                    date=target_date,
                    shift=shift
                ).first()

                if existing:
                    existing.quantity = qty
                    existing.total_amount = round(qty * rate, 2)
                    created_id = existing.id
                else:
                    deliv = MilkDelivery(
                        farm_id=farm_id,
                        customer_id=cust_id,
                        date=target_date,
                        shift=shift,
                        quantity=qty,
                        price_per_litre=rate,
                        total_amount=round(qty * rate, 2),
                        delivery_status=data.get('delivery_status', 'DELIVERED'),
                        recorded_by=user_id
                    )
                    db.session.add(deliv)
                    db.session.flush()
                    created_id = deliv.id

            elif entity_type == 'EXPENSE':
                exp = Expense(
                    farm_id=farm_id,
                    category_id=int(data['category_id']),
                    amount=float(data['amount']),
                    date=date.fromisoformat(data['date']),
                    description=data.get('description'),
                    created_by=user_id
                )
                db.session.add(exp)
                db.session.flush()
                created_id = exp.id

            # Save sync record
            sync_rec = SyncRecord(
                farm_id=farm_id,
                client_sync_id=sync_id,
                entity_type=entity_type,
                entity_id=str(created_id),
                action=action,
                status='APPLIED'
            )
            db.session.add(sync_rec)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            status = 'FAILED'
            error_msg = str(e)

        results.append({
            'client_sync_id': sync_id,
            'status': status,
            'backend_id': created_id,
            'error': error_msg
        })

    return success_response(data={
        'total_processed': len(results),
        'synced_at': datetime.utcnow().isoformat(),
        'items': results
    }, message="Offline batch sync completed")
