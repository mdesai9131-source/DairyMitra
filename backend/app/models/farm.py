from datetime import datetime
from app.extensions import db

class Farm(db.Model):
    __tablename__ = 'farms'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    farm_name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    members = db.relationship('FarmMember', backref='farm', lazy='dynamic', cascade='all, delete-orphan')
    animals = db.relationship('Animal', backref='farm', lazy='dynamic', cascade='all, delete-orphan')
    customers = db.relationship('Customer', backref='farm', lazy='dynamic', cascade='all, delete-orphan')
    milk_prices = db.relationship('MilkPrice', backref='farm', lazy='dynamic', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='farm', lazy='dynamic', cascade='all, delete-orphan')
    inventory_items = db.relationship('Inventory', backref='farm', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'farm_name': self.farm_name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class FarmMember(db.Model):
    __tablename__ = 'farm_members'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = db.Column(db.String(30), default='WORKER', nullable=False)  # OWNER, MANAGER, WORKER
    permissions = db.Column(db.Text, nullable=True)  # JSON or comma-separated permissions
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('farm_id', 'user_id', name='uq_farm_user_membership'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'user_id': self.user_id,
            'role': self.role,
            'permissions': self.permissions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
