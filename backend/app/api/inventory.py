from datetime import date
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.inventory import Inventory, InventoryTransaction
from app.services.audit_service import log_audit
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/v1/inventory')

@inventory_bp.route('', methods=['GET'])
@farm_access_required
def list_inventory():
    """List all stock inventory items with low-stock status."""
    farm_id = int(request.args.get('farm_id'))
    category = request.args.get('category')

    query = Inventory.query.filter_by(farm_id=farm_id)
    if category:
        query = query.filter_by(category=category.upper())

    items = query.order_by(Inventory.item_name.asc()).all()
    return success_response(data=[item.to_dict() for item in items])

@inventory_bp.route('', methods=['POST'])
@farm_access_required
def create_item():
    """Add a new inventory item (Cattle feed, Medicine, etc.)."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    item_name = data.get('item_name')

    if not farm_id or not item_name:
        return error_response("Farm ID and item name are required", status_code=400)

    item = Inventory(
        farm_id=farm_id,
        item_name=item_name.strip(),
        category=data.get('category', 'FEED').upper(),
        unit=data.get('unit', 'KG').upper(),
        current_stock=float(data.get('opening_stock', 0.0)),
        minimum_stock_alert=float(data.get('minimum_stock_alert', 10.0)),
        cost_per_unit=float(data.get('cost_per_unit', 0.0))
    )
    db.session.add(item)
    db.session.commit()

    return success_response(data=item.to_dict(), message="Item created successfully", status_code=201)

@inventory_bp.route('/transaction', methods=['POST'])
@farm_access_required
def record_transaction():
    """
    Log an inventory transaction (PURCHASE, USAGE, ADJUSTMENT).
    Automatically updates the inventory item's current stock level.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    inventory_id = data.get('inventory_id')
    tx_type = data.get('transaction_type', 'USAGE').upper()
    quantity = float(data.get('quantity', 0.0))
    unit_price = float(data.get('unit_price', 0.0))
    tx_date = date.fromisoformat(data['date']) if data.get('date') else date.today()

    if quantity <= 0:
        return error_response("Quantity must be greater than zero", status_code=400)

    item = Inventory.query.filter_by(id=inventory_id, farm_id=farm_id).first_or_404()

    # Calculate stock adjustment
    if tx_type in ('PURCHASE', 'PRODUCTION'):
        item.current_stock += quantity
    elif tx_type in ('USAGE', 'SALE'):
        item.current_stock -= quantity
    elif tx_type == 'ADJUSTMENT':
        item.current_stock = quantity

    total_cost = round(quantity * unit_price, 2)

    transaction = InventoryTransaction(
        inventory_id=item.id,
        farm_id=farm_id,
        transaction_type=tx_type,
        quantity=quantity,
        unit_price=unit_price,
        total_cost=total_cost,
        reference_id=data.get('reference_id'),
        reference_type=data.get('reference_type'),
        date=tx_date,
        notes=data.get('notes')
    )
    db.session.add(transaction)
    db.session.commit()

    log_audit(
        action="INVENTORY_TRANSACTION",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="Inventory",
        entity_id=item.id,
        metadata={'type': tx_type, 'quantity': quantity, 'new_stock': item.current_stock}
    )

    return success_response(data={
        'item': item.to_dict(),
        'transaction': transaction.to_dict()
    }, message="Inventory updated successfully", status_code=201)
