from datetime import datetime
from app.extensions import db

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    daily_quantity = db.Column(db.Float, default=1.0, nullable=False)  # default Litres per day
    price_per_litre = db.Column(db.Float, default=60.0, nullable=False)  # specific price agreement
    delivery_time = db.Column(db.String(20), default='MORNING', nullable=False)  # MORNING, EVENING, BOTH
    current_balance = db.Column(db.Float, default=0.0, nullable=False)  # Pending due (positive = owes money, negative = advance)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)  # ACTIVE, INACTIVE
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    deliveries = db.relationship('MilkDelivery', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    bills = db.relationship('CustomerBill', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='customer', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'daily_quantity': self.daily_quantity,
            'price_per_litre': self.price_per_litre,
            'delivery_time': self.delivery_time,
            'current_balance': self.current_balance,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MilkDelivery(db.Model):
    __tablename__ = 'milk_deliveries'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    shift = db.Column(db.String(20), default='MORNING', nullable=False)  # MORNING, EVENING
    quantity = db.Column(db.Float, nullable=False)  # Litres
    price_per_litre = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    delivery_status = db.Column(db.String(20), default='DELIVERED', nullable=False)  # DELIVERED, SKIPPED, CANCELLED
    notes = db.Column(db.String(255), nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('customer_id', 'date', 'shift', name='uq_customer_delivery_date_shift'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'date': self.date.isoformat() if self.date else None,
            'shift': self.shift,
            'quantity': self.quantity,
            'price_per_litre': self.price_per_litre,
            'total_amount': self.total_amount,
            'delivery_status': self.delivery_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
