from datetime import datetime
from app.extensions import db

class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True, index=True)
    product_type = db.Column(db.String(50), default='MILK', nullable=False)  # MILK, GHEE, CATTLE, OTHER
    date = db.Column(db.Date, nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(30), default='PAID', nullable=False)  # PAID, PENDING
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'customer_id': self.customer_id,
            'product_type': self.product_type,
            'date': self.date.isoformat() if self.date else None,
            'total_amount': self.total_amount,
            'payment_status': self.payment_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
