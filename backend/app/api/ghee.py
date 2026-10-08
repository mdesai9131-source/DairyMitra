from datetime import date
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.ghee import GheeProduction, GheeSale
from app.services.audit_service import log_audit
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

ghee_bp = Blueprint('ghee', __name__, url_prefix='/api/v1/ghee')

@ghee_bp.route('/production', methods=['GET'])
@farm_access_required
def list_production():
    """List ghee manufacturing batches."""
    farm_id = int(request.args.get('farm_id'))
    records = GheeProduction.query.filter_by(farm_id=farm_id).order_by(GheeProduction.date.desc()).all()
    total_ghee_produced = sum(r.ghee_produced_kg for r in records)
    total_milk_used = sum(r.milk_used_litres for r in records)

    return success_response(data={
        'total_ghee_produced_kg': round(total_ghee_produced, 2),
        'total_milk_used_litres': round(total_milk_used, 2),
        'batches': [r.to_dict() for r in records]
    })

@ghee_bp.route('/production', methods=['POST'])
@farm_access_required
def record_production():
    """Record a ghee production batch from milk."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    milk_used = float(data.get('milk_used_litres', 0.0))
    ghee_produced = float(data.get('ghee_produced_kg', 0.0))
    prod_date = date.fromisoformat(data['date']) if data.get('date') else date.today()

    if not farm_id or milk_used <= 0 or ghee_produced <= 0:
        return error_response("Farm ID, milk used, and ghee produced must be greater than zero", status_code=400)

    record = GheeProduction(
        farm_id=farm_id,
        date=prod_date,
        milk_used_litres=milk_used,
        ghee_produced_kg=ghee_produced,
        production_cost=float(data.get('production_cost', 0.0)),
        selling_price_per_kg=float(data.get('selling_price_per_kg', 900.0)),
        notes=data.get('notes')
    )
    db.session.add(record)
    db.session.commit()

    log_audit(
        action="GHEE_PRODUCED",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="GheeProduction",
        entity_id=record.id,
        metadata={'milk_used': milk_used, 'ghee_produced': ghee_produced}
    )
    return success_response(data=record.to_dict(), message="Ghee production recorded successfully", status_code=201)

@ghee_bp.route('/sales', methods=['GET'])
@farm_access_required
def list_sales():
    """List ghee sales and total revenue."""
    farm_id = int(request.args.get('farm_id'))
    sales = GheeSale.query.filter_by(farm_id=farm_id).order_by(GheeSale.date.desc()).all()
    total_sales_kg = sum(s.quantity_kg for s in sales)
    total_revenue = sum(s.total_amount for s in sales)

    return success_response(data={
        'total_sales_kg': round(total_sales_kg, 2),
        'total_revenue': round(total_revenue, 2),
        'sales': [s.to_dict() for s in sales]
    })

@ghee_bp.route('/sales', methods=['POST'])
@farm_access_required
def record_sale():
    """Record a ghee sale to customer."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    qty_kg = float(data.get('quantity_kg', 0.0))
    price_per_kg = float(data.get('price_per_kg', 0.0))
    sale_date = date.fromisoformat(data['date']) if data.get('date') else date.today()

    if not farm_id or qty_kg <= 0 or price_per_kg <= 0:
        return error_response("Quantity and price per kg are required", status_code=400)

    total_amount = round(qty_kg * price_per_kg, 2)

    sale = GheeSale(
        farm_id=farm_id,
        customer_id=data.get('customer_id'),
        date=sale_date,
        quantity_kg=qty_kg,
        price_per_kg=price_per_kg,
        total_amount=total_amount,
        payment_status=data.get('payment_status', 'PAID').upper(),
        notes=data.get('notes')
    )
    db.session.add(sale)
    db.session.commit()

    log_audit(
        action="GHEE_SOLD",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="GheeSale",
        entity_id=sale.id,
        metadata={'qty_kg': qty_kg, 'total_amount': total_amount}
    )
    return success_response(data=sale.to_dict(), message="Ghee sale logged successfully", status_code=201)
