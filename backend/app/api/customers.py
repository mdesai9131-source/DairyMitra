from datetime import date
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.customer import Customer, MilkDelivery
from app.models.user import User
from app.services.audit_service import log_audit
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

customers_bp = Blueprint('customers', __name__, url_prefix='/api/v1/customers')

@customers_bp.route('', methods=['GET'])
@farm_access_required
def list_customers():
    """List all customers for the farm with their balances."""
    farm_id = int(request.args.get('farm_id') or request.environ.get('dairy_farm_id'))
    status = request.args.get('status', 'ACTIVE')
    search = request.args.get('search', '').strip()

    query = Customer.query.filter_by(farm_id=farm_id)
    if status != 'ALL':
        query = query.filter_by(status=status)
    if search:
        query = query.filter(db.or_(
            Customer.name.ilike(f'%{search}%'),
            Customer.phone.ilike(f'%{search}%'),
            Customer.address.ilike(f'%{search}%')
        ))

    customers = query.order_by(Customer.name.asc()).all()
    return success_response(data=[c.to_dict() for c in customers])

@customers_bp.route('', methods=['POST'])
@farm_access_required
def create_customer():
    """Register a new dairy customer."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id') or request.environ.get('dairy_farm_id')
    name = data.get('name')
    phone = data.get('phone')

    if not farm_id or not name or not phone:
        return error_response("Farm ID, customer name, and phone are required", status_code=400)
    farm_id = int(farm_id)

    customer = Customer(
        farm_id=farm_id,
        name=name.strip(),
        email=data.get('email'),
        phone=str(phone).strip(),
        address=data.get('address'),
        daily_quantity=float(data.get('daily_quantity', 1.0)),
        price_per_litre=float(data.get('price_per_litre', 60.0)),
        delivery_time=data.get('delivery_time', 'MORNING').upper(),
        current_balance=float(data.get('initial_balance', 0.0)),
        status=data.get('status', 'ACTIVE').upper()
    )
    db.session.add(customer)
    db.session.commit()

    log_audit(
        action="CUSTOMER_CREATED",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="Customer",
        entity_id=customer.id,
        metadata={'name': customer.name, 'phone': customer.phone}
    )
    return success_response(data=customer.to_dict(), message="Customer registered successfully", status_code=201)

@customers_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_customer(id):
    """Customer profile, delivery history, and recent bills."""
    customer = Customer.query.get_or_404(id)
    recent_deliveries = [
        d.to_dict() for d in customer.deliveries.order_by(MilkDelivery.date.desc()).limit(30).all()
    ]
    recent_bills = [
        b.to_dict() for b in customer.bills.order_by(db.desc('generated_at')).limit(10).all()
    ]

    data = customer.to_dict()
    data['recent_deliveries'] = recent_deliveries
    data['recent_bills'] = recent_bills
    return success_response(data=data)

@customers_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_customer(id):
    """Update customer details."""
    customer = Customer.query.get_or_404(id)
    data = request.get_json(silent=True) or {}

    if 'name' in data:
        customer.name = data['name'].strip()
    if 'phone' in data:
        customer.phone = str(data['phone']).strip()
    if 'email' in data:
        customer.email = data['email']
    if 'address' in data:
        customer.address = data['address']
    if 'daily_quantity' in data:
        customer.daily_quantity = float(data['daily_quantity'])
    if 'price_per_litre' in data:
        customer.price_per_litre = float(data['price_per_litre'])
    if 'delivery_time' in data:
        customer.delivery_time = data['delivery_time'].upper()
    if 'status' in data:
        customer.status = data['status'].upper()

    db.session.commit()
    return success_response(data=customer.to_dict(), message="Customer updated successfully")

@customers_bp.route('/deliveries', methods=['GET'])
@farm_access_required
def get_daily_deliveries():
    """Get the daily customer delivery register for a given date."""
    farm_id = int(request.args.get('farm_id'))
    date_str = request.args.get('date')
    target_date = date.fromisoformat(date_str) if date_str else date.today()

    customers = Customer.query.filter_by(farm_id=farm_id, status='ACTIVE').order_by(Customer.name.asc()).all()
    deliveries = MilkDelivery.query.filter_by(farm_id=farm_id, date=target_date).all()
    del_map = {d.customer_id: d for d in deliveries}

    results = []
    total_delivered_qty = 0.0

    for c in customers:
        existing = del_map.get(c.id)
        if existing:
            status = existing.delivery_status
            qty = existing.quantity
            rate = existing.price_per_litre
            amount = existing.total_amount
            del_id = existing.id
        else:
            status = 'PENDING'
            qty = c.daily_quantity
            rate = c.price_per_litre
            amount = round(qty * rate, 2)
            del_id = None

        if status == 'DELIVERED':
            total_delivered_qty += qty

        results.append({
            'delivery_id': del_id,
            'customer_id': c.id,
            'customer_name': c.name,
            'customer_phone': c.phone,
            'quantity': qty,
            'price_per_litre': rate,
            'total_amount': amount,
            'delivery_status': status,
            'balance': c.current_balance
        })

    return success_response(data={
        'date': target_date.isoformat(),
        'total_delivered_qty': round(total_delivered_qty, 2),
        'deliveries': results
    })

@customers_bp.route('/deliveries', methods=['POST'])
@farm_access_required
def record_delivery():
    """Record customer daily delivery, skipped, or cancelled."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    customer_id = data.get('customer_id')
    shift = data.get('shift', 'MORNING').upper()
    status = data.get('delivery_status', 'DELIVERED').upper()
    target_date = date.fromisoformat(data['date']) if data.get('date') else date.today()

    customer = Customer.query.filter_by(id=customer_id, farm_id=farm_id).first_or_404()
    qty = float(data.get('quantity', customer.daily_quantity)) if status == 'DELIVERED' else 0.0
    rate = float(data.get('price_per_litre', customer.price_per_litre))
    total_amount = round(qty * rate, 2)

    existing = MilkDelivery.query.filter_by(
        customer_id=customer_id,
        date=target_date,
        shift=shift
    ).first()

    if existing:
        existing.quantity = qty
        existing.price_per_litre = rate
        existing.total_amount = total_amount
        existing.delivery_status = status
        existing.notes = data.get('notes')
        db.session.commit()
        return success_response(data=existing.to_dict(), message="Delivery record updated")

    record = MilkDelivery(
        farm_id=farm_id,
        customer_id=customer_id,
        date=target_date,
        shift=shift,
        quantity=qty,
        price_per_litre=rate,
        total_amount=total_amount,
        delivery_status=status,
        notes=data.get('notes'),
        recorded_by=user_id
    )
    db.session.add(record)
    db.session.commit()

    return success_response(data=record.to_dict(), message="Delivery recorded successfully", status_code=201)

@customers_bp.route('/<int:id>', methods=['DELETE'])
@farm_access_required
def delete_customer(id):
    """Delete or deactivate a dairy customer."""
    user_id = int(get_jwt_identity())
    customer = Customer.query.get_or_404(id)
    permanent = request.args.get('permanent', 'false').lower() == 'true'

    user = User.query.get(user_id)
    if permanent and user and user.role != 'ADMIN':
        return error_response("Only administrators can permanently delete customer records. You can deactivate them instead.", status_code=403)

    name = customer.name
    farm_id = customer.farm_id

    if permanent:
        from app.models.sale import Sale
        from app.models.ghee import GheeSale
        Sale.query.filter_by(customer_id=customer.id).update({'customer_id': None})
        GheeSale.query.filter_by(customer_id=customer.id).update({'customer_id': None})
        db.session.delete(customer)
        action = "CUSTOMER_PERMANENT_DELETED"
        msg = f"Customer '{name}' permanently deleted"
    else:
        customer.status = 'INACTIVE'
        action = "CUSTOMER_DEACTIVATED"
        msg = f"Customer '{name}' deactivated successfully"

    db.session.commit()
    log_audit(
        action=action,
        user_id=user_id,
        farm_id=farm_id,
        entity_type="Customer",
        entity_id=id,
        metadata={'name': name, 'permanent': permanent}
    )
    return success_response(message=msg)
