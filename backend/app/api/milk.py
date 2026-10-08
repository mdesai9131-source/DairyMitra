from datetime import date
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.milk import MilkProduction, MilkPrice
from app.models.animal import Animal
from app.services.financial_engine import FinancialEngine
from app.services.audit_service import log_audit
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

milk_bp = Blueprint('milk', __name__, url_prefix='/api/v1/milk')

@milk_bp.route('', methods=['GET'])
@farm_access_required
def get_daily_milk():
    """
    Get animal-wise milk entries for a selected date.
    Returns:
    [
      {
        animal_id: ...,
        animal_name: ...,
        animal_number: ...,
        morning: 6.2,
        evening: 5.8,
        total: 12.0
      }, ...
    ]
    """
    farm_id = int(request.args.get('farm_id') or request.environ.get('dairy_farm_id'))
    date_str = request.args.get('date')
    target_date = date.fromisoformat(date_str) if date_str else date.today()

    animals = Animal.query.filter_by(farm_id=farm_id, current_status='ACTIVE').order_by(Animal.animal_number.asc()).all()
    productions = MilkProduction.query.filter_by(farm_id=farm_id, date=target_date).all()

    prod_map = {}
    for p in productions:
        if p.animal_id not in prod_map:
            prod_map[p.animal_id] = {'morning': 0.0, 'evening': 0.0, 'morning_id': None, 'evening_id': None}
        if p.shift == 'MORNING':
            prod_map[p.animal_id]['morning'] = p.quantity
            prod_map[p.animal_id]['morning_id'] = p.id
        elif p.shift == 'EVENING':
            prod_map[p.animal_id]['evening'] = p.quantity
            prod_map[p.animal_id]['evening_id'] = p.id

    result = []
    total_morning = 0.0
    total_evening = 0.0

    for a in animals:
        entry = prod_map.get(a.id, {'morning': 0.0, 'evening': 0.0, 'morning_id': None, 'evening_id': None})
        m = entry['morning']
        e = entry['evening']
        t = round(m + e, 2)
        total_morning += m
        total_evening += e

        result.append({
            'animal_id': a.id,
            'animal_name': a.name,
            'animal_number': a.animal_number,
            'breed': a.breed,
            'animal_type': a.animal_type,
            'morning': m,
            'morning_id': entry['morning_id'],
            'evening': e,
            'evening_id': entry['evening_id'],
            'total': t
        })

    return success_response(data={
        'date': target_date.isoformat(),
        'morning_total': round(total_morning, 2),
        'evening_total': round(total_evening, 2),
        'grand_total': round(total_morning + total_evening, 2),
        'animals': result
    })

@milk_bp.route('', methods=['POST'])
@farm_access_required
def record_milk():
    """
    Record or update a milk production record.
    Prevents accidental duplicates by updating existing if shift already exists.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id') or request.environ.get('dairy_farm_id')
    animal_id = data.get('animal_id')
    shift = data.get('shift', 'MORNING').upper()
    quantity = float(data.get('quantity', 0.0))
    target_date = date.fromisoformat(data['date']) if data.get('date') else date.today()

    if not farm_id or not animal_id:
        return error_response("Farm ID and Animal ID are required", status_code=400)
    farm_id = int(farm_id)

    # Check existing record for that animal, shift, date
    existing = MilkProduction.query.filter_by(
        farm_id=farm_id,
        animal_id=animal_id,
        shift=shift,
        date=target_date
    ).first()

    if existing:
        old_qty = existing.quantity
        existing.quantity = quantity
        existing.notes = data.get('notes', existing.notes)
        existing.fat_content = float(data['fat_content']) if data.get('fat_content') else existing.fat_content
        db.session.commit()
        log_audit(
            action="MILK_UPDATED",
            user_id=user_id,
            farm_id=farm_id,
            entity_type="MilkProduction",
            entity_id=existing.id,
            metadata={'old_quantity': old_qty, 'new_quantity': quantity, 'shift': shift}
        )
        return success_response(data=existing.to_dict(), message="Milk record updated successfully")

    record = MilkProduction(
        farm_id=farm_id,
        animal_id=animal_id,
        date=target_date,
        shift=shift,
        quantity=quantity,
        fat_content=float(data['fat_content']) if data.get('fat_content') else None,
        notes=data.get('notes'),
        recorded_by=user_id
    )
    db.session.add(record)
    db.session.commit()

    log_audit(
        action="MILK_ADDED",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="MilkProduction",
        entity_id=record.id,
        metadata={'quantity': quantity, 'shift': shift, 'date': target_date.isoformat()}
    )
    return success_response(data=record.to_dict(), message="Milk recorded successfully", status_code=201)

@milk_bp.route('/price', methods=['GET'])
@farm_access_required
def get_milk_prices():
    """Get milk price history and current effective price."""
    farm_id = int(request.args.get('farm_id'))
    prices = MilkPrice.query.filter_by(farm_id=farm_id).order_by(MilkPrice.effective_from.desc()).all()
    current_price = FinancialEngine.get_current_milk_price(farm_id)
    return success_response(data={
        'current_price': current_price,
        'history': [p.to_dict() for p in prices]
    })

@milk_bp.route('/price', methods=['POST'])
@farm_access_required
def set_milk_price():
    """
    Set a new milk price.
    Historical prices are NEVER overwritten; the previous price is archived with effective_to.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    new_price = float(data.get('price_per_litre', 0.0))
    effective_from = date.fromisoformat(data['effective_from']) if data.get('effective_from') else date.today()

    if new_price <= 0:
        return error_response("Price per litre must be greater than 0", status_code=400)

    # Deactivate current price
    current_active = MilkPrice.query.filter_by(farm_id=farm_id, is_current=True).first()
    if current_active:
        current_active.is_current = False
        current_active.effective_to = effective_from

    # Create new effective price record
    new_record = MilkPrice(
        farm_id=farm_id,
        price_per_litre=new_price,
        effective_from=effective_from,
        is_current=True
    )
    db.session.add(new_record)
    db.session.commit()

    log_audit(
        action="MILK_PRICE_UPDATED",
        user_id=user_id,
        farm_id=farm_id,
        metadata={'new_price': new_price, 'effective_from': effective_from.isoformat()}
    )
    return success_response(data=new_record.to_dict(), message="Milk price updated successfully", status_code=201)
