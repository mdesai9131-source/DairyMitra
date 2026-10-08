from datetime import date, timedelta
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.farm import Farm, FarmMember
from app.models.animal import Animal
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.milk import MilkPrice
from app.services.financial_engine import FinancialEngine
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

farms_bp = Blueprint('farms', __name__, url_prefix='/api/v1/farms')

@farms_bp.route('', methods=['GET'])
@jwt_required()
def list_farms():
    """List all farms owned or accessed by the authenticated user."""
    user_id = int(get_jwt_identity())
    owned_farms = Farm.query.filter_by(owner_id=user_id, is_active=True).all()
    member_farms = [m.farm for m in FarmMember.query.filter_by(user_id=user_id).all() if m.farm and m.farm.is_active]

    all_farms = list({f.id: f for f in (owned_farms + member_farms)}.values())
    return success_response(data=[f.to_dict() for f in all_farms])

@farms_bp.route('', methods=['POST'])
@jwt_required()
def create_farm():
    """Create a new farm under the user's account."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_name = data.get('farm_name')

    if not farm_name:
        return error_response("Farm name is required", status_code=400)

    farm = Farm(
        owner_id=user_id,
        farm_name=farm_name.strip(),
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        pincode=data.get('pincode')
    )
    db.session.add(farm)
    db.session.flush()

    # Also set default milk price
    default_price = MilkPrice(
        farm_id=farm.id,
        price_per_litre=float(data.get('milk_price', 60.0)),
        effective_from=date.today(),
        is_current=True
    )
    db.session.add(default_price)
    db.session.commit()

    return success_response(data=farm.to_dict(), message="Farm created successfully", status_code=201)

@farms_bp.route('/<int:id>', methods=['GET'])
@farm_access_required
def get_farm(id):
    """Get single farm details."""
    farm = Farm.query.get_or_404(id)
    return success_response(data=farm.to_dict())

@farms_bp.route('/<int:id>', methods=['PUT'])
@farm_access_required
def update_farm(id):
    """Update farm details."""
    farm = Farm.query.get_or_404(id)
    data = request.get_json(silent=True) or {}

    if 'farm_name' in data:
        farm.farm_name = data['farm_name'].strip()
    if 'address' in data:
        farm.address = data['address']
    if 'city' in data:
        farm.city = data['city']
    if 'state' in data:
        farm.state = data['state']
    if 'pincode' in data:
        farm.pincode = data['pincode']

    db.session.commit()
    return success_response(data=farm.to_dict(), message="Farm updated successfully")

@farms_bp.route('/<int:id>/dashboard', methods=['GET'])
@farm_access_required
def get_dashboard(id):
    """
    Farmer-friendly dashboard metrics:
    - Today's Milk (morning, evening, total)
    - Today's Revenue, Expenses, Profit
    - Active Animals & Customers
    - Pending customer payments
    - Low stock inventory alerts
    - 7-day trends
    """
    today = date.today()

    # Today's Milk
    today_milk = FinancialEngine.calculate_daily_milk_summary(id, today)

    # Today's Financials
    today_fin = FinancialEngine.calculate_farm_financials(id, start_date=today, end_date=today)

    # Monthly Financials
    month_start = today.replace(day=1)
    month_fin = FinancialEngine.calculate_farm_financials(id, start_date=month_start, end_date=today)

    # Counts
    active_cows = Animal.query.filter_by(farm_id=id, animal_type='COW', current_status='ACTIVE').count()
    active_buffaloes = Animal.query.filter_by(farm_id=id, animal_type='BUFFALO', current_status='ACTIVE').count()
    total_active_animals = active_cows + active_buffaloes
    active_customers = Customer.query.filter_by(farm_id=id, status='ACTIVE').count()

    # Total pending balance from customers
    customers = Customer.query.filter_by(farm_id=id, status='ACTIVE').all()
    pending_customer_dues = sum(c.current_balance for c in customers if c.current_balance > 0)

    # Low stock items
    low_stock_items = [
        item.to_dict() for item in Inventory.query.filter_by(farm_id=id).all()
        if item.current_stock <= item.minimum_stock_alert
    ]

    # 7-day milk trend
    seven_days_ago = today - timedelta(days=6)
    milk_trend = []
    current_d = seven_days_ago
    while current_d <= today:
        summary = FinancialEngine.calculate_daily_milk_summary(id, current_d)
        milk_trend.append({
            'date': current_d.strftime('%d %b'),
            'total_quantity': summary['total_quantity']
        })
        current_d += timedelta(days=1)

    farm = Farm.query.get(id)
    return success_response(data={
        'farm_id': id,
        'farm_name': farm.farm_name if farm else "Desai Dairy Farm",
        'location': f"{farm.city}, {farm.state}" if farm and farm.city else "Anand, Gujarat",
        'date': today.isoformat(),
        'today_milk': today_milk,
        'today_financials': today_fin,
        'monthly_financials': month_fin,
        'active_animals': {
            'total': total_active_animals,
            'cows': active_cows,
            'buffaloes': active_buffaloes
        },
        'active_customers': active_customers,
        'pending_customer_dues': round(pending_customer_dues, 2),
        'low_stock_alerts': low_stock_items,
        'milk_trend': milk_trend
    })
