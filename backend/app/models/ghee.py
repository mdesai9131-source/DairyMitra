from datetime import datetime
from app.extensions import db

class GheeProduction(db.Model):
    __tablename__ = 'ghee_production'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    milk_used_litres = db.Column(db.Float, nullable=False)
    ghee_produced_kg = db.Column(db.Float, nullable=False)
    production_cost = db.Column(db.Float, default=0.0, nullable=False)
    selling_price_per_kg = db.Column(db.Float, default=900.0, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'date': self.date.isoformat() if self.date else None,
            'milk_used_litres': self.milk_used_litres,
            'ghee_produced_kg': self.ghee_produced_kg,
            'production_cost': self.production_cost,
            'selling_price_per_kg': self.selling_price_per_kg,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class GheeSale(db.Model):
    __tablename__ = 'ghee_sales'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    quantity_kg = db.Column(db.Float, nullable=False)
    price_per_kg = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(30), default='PAID', nullable=False)  # PAID, PENDING
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'customer_id': self.customer_id,
            'date': self.date.isoformat() if self.date else None,
            'quantity_kg': self.quantity_kg,
            'price_per_kg': self.price_per_kg,
            'total_amount': self.total_amount,
            'payment_status': self.payment_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
