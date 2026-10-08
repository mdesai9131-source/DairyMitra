from datetime import date
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.expense import Expense, ExpenseCategory
from app.services.audit_service import log_audit
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

expenses_bp = Blueprint('expenses', __name__, url_prefix='/api/v1/expenses')

DEFAULT_CATEGORIES = [
    ("Cattle Feed", "FEED"),
    ("Medicine", "MEDICINE"),
    ("Vaccination", "VACCINATION"),
    ("Labour", "LABOUR"),
    ("Transport", "TRANSPORT"),
    ("Electricity", "ELECTRICITY"),
    ("Water", "WATER"),
    ("Farm Maintenance", "MAINTENANCE"),
    ("Animal Purchase", "ANIMAL_PURCHASE"),
    ("Equipment", "EQUIPMENT"),
    ("Ghee Production", "GHEE_PROD"),
    ("Other", "OTHER")
]

def ensure_categories_exist():
    """Ensure default expense categories exist."""
    for name, code in DEFAULT_CATEGORIES:
        if not ExpenseCategory.query.filter_by(code=code, farm_id=None).first():
            cat = ExpenseCategory(name=name, code=code, is_default=True)
            db.session.add(cat)
    db.session.commit()

@expenses_bp.route('/categories', methods=['GET'])
@jwt_required()
def list_categories():
    """List available expense categories."""
    ensure_categories_exist()
    farm_id = request.args.get('farm_id')
    query = ExpenseCategory.query.filter(
        db.or_(ExpenseCategory.is_default == True, ExpenseCategory.farm_id == farm_id)
    )
    categories = query.order_by(ExpenseCategory.name.asc()).all()
    return success_response(data=[c.to_dict() for c in categories])

@expenses_bp.route('', methods=['GET'])
@farm_access_required
def list_expenses():
    """List expenses with date range and category filtering."""
    farm_id = int(request.args.get('farm_id'))
    category_id = request.args.get('category_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Expense.query.filter_by(farm_id=farm_id)
    if category_id:
        query = query.filter_by(category_id=int(category_id))
    if start_date:
        query = query.filter(Expense.date >= date.fromisoformat(start_date))
    if end_date:
        query = query.filter(Expense.date <= date.fromisoformat(end_date))

    expenses = query.order_by(Expense.date.desc(), Expense.id.desc()).all()
    total_amount = sum(e.amount for e in expenses)

    return success_response(data={
        'total_amount': round(total_amount, 2),
        'count': len(expenses),
        'expenses': [e.to_dict() for e in expenses]
    })

@expenses_bp.route('', methods=['POST'])
@farm_access_required
def create_expense():
    """Record a farm expense."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    category_id = data.get('category_id')
    amount = float(data.get('amount', 0.0))
    expense_date = date.fromisoformat(data['date']) if data.get('date') else date.today()

    if not farm_id or not category_id or amount <= 0:
        return error_response("Farm ID, category ID, and a valid amount are required", status_code=400)

    category = ExpenseCategory.query.get_or_404(category_id)

    expense = Expense(
        farm_id=farm_id,
        category_id=category.id,
        amount=amount,
        date=expense_date,
        description=data.get('description'),
        payment_method=data.get('payment_method', 'CASH').upper(),
        receipt_image_url=data.get('receipt_image_url'),
        created_by=user_id
    )
    db.session.add(expense)
    db.session.commit()

    log_audit(
        action="EXPENSE_CREATED",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="Expense",
        entity_id=expense.id,
        metadata={'category': category.name, 'amount': amount}
    )
    return success_response(data=expense.to_dict(), message="Expense recorded successfully", status_code=201)

@expenses_bp.route('/<int:id>', methods=['DELETE'])
@farm_access_required
def delete_expense(id):
    """Delete a farm expense entry."""
    user_id = int(get_jwt_identity())
    expense = Expense.query.get_or_404(id)
    amt = expense.amount
    farm_id = expense.farm_id

    db.session.delete(expense)
    db.session.commit()
    log_audit(
        action="EXPENSE_DELETED",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="Expense",
        entity_id=id,
        metadata={'amount': amt}
    )
    return success_response(message="Expense record deleted successfully")

