from datetime import datetime
from app.extensions import db

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('customer_bills.id', ondelete='SET NULL'), nullable=True, index=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    payment_method = db.Column(db.String(30), default='CASH', nullable=False)  # CASH, UPI, RAZORPAY, BANK_TRANSFER
    gateway_order_id = db.Column(db.String(100), nullable=True, index=True)
    gateway_payment_id = db.Column(db.String(100), nullable=True, index=True)
    gateway_signature = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default='CREATED', nullable=False)  # CREATED, PENDING, SUCCESS, FAILED, REFUNDED
    receipt_number = db.Column(db.String(50), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'bill_id': self.bill_id,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'gateway_order_id': self.gateway_order_id,
            'gateway_payment_id': self.gateway_payment_id,
            'status': self.status,
            'receipt_number': self.receipt_number,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None
        }
