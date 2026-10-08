from datetime import datetime
from app.extensions import db

class Animal(db.Model):
    __tablename__ = 'animals'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    animal_number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    animal_type = db.Column(db.String(30), default='COW', nullable=False)  # COW, BUFFALO, OTHER
    breed = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.String(20), default='FEMALE', nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_price = db.Column(db.Float, default=0.0, nullable=False)
    current_status = db.Column(db.String(30), default='ACTIVE', nullable=False)  # ACTIVE, SOLD, DECEASED, INACTIVE
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    health_records = db.relationship('AnimalHealthRecord', backref='animal', lazy='dynamic', cascade='all, delete-orphan')
    milk_records = db.relationship('MilkProduction', backref='animal', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('farm_id', 'animal_number', name='uq_farm_animal_number'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'animal_number': self.animal_number,
            'name': self.name,
            'animal_type': self.animal_type,
            'breed': self.breed,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'purchase_price': self.purchase_price,
            'current_status': self.current_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AnimalHealthRecord(db.Model):
    __tablename__ = 'animal_health_records'

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id', ondelete='CASCADE'), nullable=False, index=True)
    record_type = db.Column(db.String(50), nullable=False)  # VACCINATION, MEDICINE, VET_VISIT, CALVING, CHECKUP
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    medicine = db.Column(db.String(150), nullable=True)
    cost = db.Column(db.Float, default=0.0, nullable=False)
    next_due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'animal_id': self.animal_id,
            'record_type': self.record_type,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'medicine': self.medicine,
            'cost': self.cost,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
