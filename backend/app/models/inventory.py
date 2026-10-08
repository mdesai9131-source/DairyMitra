from datetime import datetime
from app.extensions import db

class Inventory(db.Model):
    __tablename__ = 'inventory'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    item_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # FEED, MEDICINE, GHEE, DAIRY_PACKAGING, OTHER
    unit = db.Column(db.String(20), default='KG', nullable=False)  # KG, LITRE, PIECE, PACKET
    current_stock = db.Column(db.Float, default=0.0, nullable=False)
    minimum_stock_alert = db.Column(db.Float, default=10.0, nullable=False)
    cost_per_unit = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transactions = db.relationship('InventoryTransaction', backref='item', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'item_name': self.item_name,
            'category': self.category,
            'unit': self.unit,
            'current_stock': self.current_stock,
            'minimum_stock_alert': self.minimum_stock_alert,
            'is_low_stock': self.current_stock <= self.minimum_stock_alert,
            'cost_per_unit': self.cost_per_unit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'

    id = db.Column(db.Integer, primary_key=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id', ondelete='CASCADE'), nullable=False, index=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    transaction_type = db.Column(db.String(30), nullable=False)  # PURCHASE, USAGE, PRODUCTION, SALE, ADJUSTMENT
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, default=0.0, nullable=False)
    total_cost = db.Column(db.Float, default=0.0, nullable=False)
    reference_id = db.Column(db.String(50), nullable=True)
    reference_type = db.Column(db.String(50), nullable=True)
    date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'inventory_id': self.inventory_id,
            'item_name': self.item.item_name if self.item else None,
            'farm_id': self.farm_id,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_cost': self.total_cost,
            'date': self.date.isoformat() if self.date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
