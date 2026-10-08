from datetime import datetime
from app.extensions import db

class CustomerBill(db.Model):
    __tablename__ = 'customer_bills'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True)
    bill_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_milk_qty = db.Column(db.Float, default=0.0, nullable=False)
    milk_amount = db.Column(db.Float, default=0.0, nullable=False)
    previous_balance = db.Column(db.Float, default=0.0, nullable=False)
    grand_total = db.Column(db.Float, default=0.0, nullable=False)  # milk_amount + previous_balance
    paid_amount = db.Column(db.Float, default=0.0, nullable=False)
    balance_due = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(30), default='PENDING', nullable=False)  # PENDING, PARTIALLY_PAID, PAID, CANCELLED
    notes = db.Column(db.Text, nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    items = db.relationship('CustomerBillItem', backref='bill', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='bill', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'customer_phone': self.customer.phone if self.customer else None,
            'bill_number': self.bill_number,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'total_milk_qty': self.total_milk_qty,
            'milk_amount': self.milk_amount,
            'previous_balance': self.previous_balance,
            'grand_total': self.grand_total,
            'paid_amount': self.paid_amount,
            'balance_due': self.balance_due,
            'status': self.status,
            'notes': self.notes,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }

class CustomerBillItem(db.Model):
    __tablename__ = 'customer_bill_items'

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('customer_bills.id', ondelete='CASCADE'), nullable=False, index=True)
    delivery_id = db.Column(db.Integer, nullable=True)
    date = db.Column(db.Date, nullable=False)
    shift = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'delivery_id': self.delivery_id,
            'date': self.date.isoformat() if self.date else None,
            'shift': self.shift,
            'quantity': self.quantity,
            'rate': self.rate,
            'amount': self.amount
        }
