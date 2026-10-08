from datetime import datetime
from app.extensions import db

class ExpenseCategory(db.Model):
    __tablename__ = 'expense_categories'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=True, index=True) # Null means global default
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    expenses = db.relationship('Expense', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'name': self.name,
            'code': self.code,
            'is_default': self.is_default
        }

class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    payment_method = db.Column(db.String(50), default='CASH', nullable=False)  # CASH, UPI, BANK_TRANSFER
    receipt_image_url = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'amount': self.amount,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'payment_method': self.payment_method,
            'receipt_image_url': self.receipt_image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
