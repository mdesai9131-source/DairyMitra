from datetime import date, timedelta
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.animal import Animal, AnimalHealthRecord
from app.models.milk import MilkProduction
from app.models.user import User
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required
from app.services.audit_service import log_audit

animals_bp = Blueprint('animals', __name__, url_prefix='/api/v1/animals')

@animals_bp.route('', methods=['GET'])
@farm_access_required
def list_animals():
    """List all animals belonging to the farm."""
    farm_id = request.args.get('farm_id')
    status = request.args.get('status', 'ACTIVE')
    animal_type = request.args.get('animal_type')
    search = request.args.get('search', '').strip()

    query = Animal.query.filter_by(farm_id=farm_id)
    if status != 'ALL':
        query = query.filter_by(current_status=status)
    if animal_type and animal_type != 'ALL':
        query = query.filter_by(animal_type=animal_type.upper())
    if search:
        query = query.filter(db.or_(
            Animal.name.ilike(f'%{search}%'),
            Animal.animal_number.ilike(f'%{search}%'),
            Animal.breed.ilike(f'%{search}%')
        ))

    animals = query.order_by(Animal.name.asc()).all()
    return success_response(data=[a.to_dict() for a in animals])

@animals_bp.route('', methods=['POST'])
@farm_access_required
def create_animal():
    """Add a new cow or buffalo to the farm."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    animal_number = data.get('animal_number')
    name = data.get('name')

    if not farm_id or not animal_number or not name:
        return error_response("Farm ID, animal number, and name are required", status_code=400)

    # Check unique animal number within farm
    existing = Animal.query.filter_by(farm_id=farm_id, animal_number=str(animal_number).strip()).first()
    if existing:
        return error_response(f"An animal with number {animal_number} already exists on this farm", status_code=400)

    dob = date.fromisoformat(data['date_of_birth']) if data.get('date_of_birth') else None
    purchase_date = date.fromisoformat(data['purchase_date']) if data.get('purchase_date') else None

    animal = Animal(
        farm_id=farm_id,
        animal_number=str(animal_number).strip(),
        name=name.strip(),
        animal_type=data.get('animal_type', 'COW').upper(),
        breed=data.get('breed'),
        gender=data.get('gender', 'FEMALE').upper(),
        date_of_birth=dob,
        purchase_date=purchase_date,
        purchase_price=float(data.get('purchase_price', 0.0)),
        current_status=data.get('current_status', 'ACTIVE').upper(),
        notes=data.get('notes')
    )
    db.session.add(animal)
    db.session.commit()

    log_audit(action="ANIMAL_CREATED", user_id=user_id, farm_id=farm_id, entity_type="Animal", entity_id=animal.id)
    return success_response(data=animal.to_dict(), message="Animal registered successfully", status_code=201)

@animals_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_animal(id):
    """
    Get animal profile along with:
    - Today's Milk
    - 7-Day Average
    - 30-Day Average
    - Recent Health Records
    """
    animal = Animal.query.get_or_404(id)
    today = date.today()

    # Today's milk
    today_records = MilkProduction.query.filter_by(animal_id=id, date=today).all()
    today_milk = sum(r.quantity for r in today_records)

    # 7-day average
    seven_days_ago = today - timedelta(days=7)
    records_7d = MilkProduction.query.filter(
        MilkProduction.animal_id == id,
        MilkProduction.date >= seven_days_ago,
        MilkProduction.date < today
    ).all()
    avg_7d = round(sum(r.quantity for r in records_7d) / 7.0, 2) if records_7d else 0.0

    # 30-day average
    thirty_days_ago = today - timedelta(days=30)
    records_30d = MilkProduction.query.filter(
        MilkProduction.animal_id == id,
        MilkProduction.date >= thirty_days_ago,
        MilkProduction.date < today
    ).all()
    avg_30d = round(sum(r.quantity for r in records_30d) / 30.0, 2) if records_30d else 0.0

    # Recent health events
    health_records = [h.to_dict() for h in animal.health_records.order_by(AnimalHealthRecord.date.desc()).limit(10).all()]

    data = animal.to_dict()
    data['today_milk'] = round(today_milk, 2)
    data['avg_7d'] = avg_7d
    data['avg_30d'] = avg_30d
    data['recent_health'] = health_records

    return success_response(data=data)

@animals_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_animal(id):
    """Update animal details."""
    animal = Animal.query.get_or_404(id)
    data = request.get_json(silent=True) or {}

    if 'name' in data:
        animal.name = data['name'].strip()
    if 'animal_number' in data and data['animal_number']:
        new_num = str(data['animal_number']).strip()
        if new_num != animal.animal_number:
            existing = Animal.query.filter_by(farm_id=animal.farm_id, animal_number=new_num).first()
            if existing:
                return error_response(f"Animal tag/number '{new_num}' already exists on this farm", status_code=400)
            animal.animal_number = new_num
    if 'animal_type' in data and data['animal_type']:
        animal.animal_type = data['animal_type'].upper()
    if 'breed' in data:
        animal.breed = data['breed'].strip() if data['breed'] else None
    if 'gender' in data and data['gender']:
        animal.gender = data['gender'].upper()
    if 'current_status' in data and data['current_status']:
        animal.current_status = data['current_status'].upper()
    if 'purchase_price' in data:
        animal.purchase_price = float(data['purchase_price'] or 0.0)
    if 'date_of_birth' in data:
        animal.date_of_birth = date.fromisoformat(data['date_of_birth']) if data['date_of_birth'] else None
    if 'purchase_date' in data:
        animal.purchase_date = date.fromisoformat(data['purchase_date']) if data['purchase_date'] else None
    if 'notes' in data:
        animal.notes = data['notes']

    db.session.commit()
    return success_response(data=animal.to_dict(), message="Animal updated successfully")

@animals_bp.route('/<int:id>/health', methods=['GET'])
@jwt_required()
def list_health_records(id):
    """List all health records for a given animal."""
    animal = Animal.query.get_or_404(id)
    records = animal.health_records.order_by(AnimalHealthRecord.date.desc()).all()
    return success_response(data=[r.to_dict() for r in records])

@animals_bp.route('/<int:id>/health', methods=['POST'])
@jwt_required()
def add_health_record(id):
    """Record vaccination, medicine, or vet visit."""
    user_id = int(get_jwt_identity())
    animal = Animal.query.get_or_404(id)
    data = request.get_json(silent=True) or {}

    record_type = data.get('record_type', 'VACCINATION')
    record_date = date.fromisoformat(data['date']) if data.get('date') else date.today()
    next_due = date.fromisoformat(data['next_due_date']) if data.get('next_due_date') else None

    record = AnimalHealthRecord(
        animal_id=animal.id,
        record_type=record_type.upper(),
        date=record_date,
        description=data.get('description', record_type),
        medicine=data.get('medicine'),
        cost=float(data.get('cost', 0.0)),
        next_due_date=next_due,
        notes=data.get('notes')
    )
    db.session.add(record)
    db.session.commit()

    log_audit(action="HEALTH_RECORD_ADDED", user_id=user_id, farm_id=animal.farm_id, entity_type="AnimalHealthRecord", entity_id=record.id)
    return success_response(data=record.to_dict(), message="Health record saved", status_code=201)

@animals_bp.route('/<int:id>', methods=['DELETE'])
@farm_access_required
def delete_animal(id):
    """Delete or mark an animal as inactive/sold."""
    user_id = int(get_jwt_identity())
    animal = Animal.query.get_or_404(id)
    permanent = request.args.get('permanent', 'false').lower() == 'true'

    user = User.query.get(user_id)
    if permanent and user and user.role != 'ADMIN':
        return error_response("Only administrators can permanently delete animals. You can mark them as sold or inactive instead.", status_code=403)

    name = animal.name
    farm_id = animal.farm_id

    if permanent:
        db.session.delete(animal)
        action = "ANIMAL_PERMANENT_DELETED"
        msg = f"Animal '{name}' permanently deleted"
    else:
        animal.current_status = 'INACTIVE'
        action = "ANIMAL_DEACTIVATED"
        msg = f"Animal '{name}' marked as inactive"

    db.session.commit()
    log_audit(action=action, user_id=user_id, farm_id=farm_id, entity_type="Animal", entity_id=id, metadata={'name': name, 'permanent': permanent})
    return success_response(message=msg)

