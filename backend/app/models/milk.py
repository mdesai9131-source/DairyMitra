from datetime import datetime
from app.extensions import db

class MilkPrice(db.Model):
    __tablename__ = 'milk_prices'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    price_per_litre = db.Column(db.Float, nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'price_per_litre': self.price_per_litre,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'is_current': self.is_current,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MilkProduction(db.Model):
    __tablename__ = 'milk_production'

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farms.id', ondelete='CASCADE'), nullable=False, index=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    shift = db.Column(db.String(20), nullable=False)  # MORNING, EVENING
    quantity = db.Column(db.Float, nullable=False)  # in Litres
    fat_content = db.Column(db.Float, nullable=True)  # optional FAT %
    notes = db.Column(db.String(255), nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('farm_id', 'animal_id', 'date', 'shift', name='uq_farm_animal_date_shift'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'farm_id': self.farm_id,
            'animal_id': self.animal_id,
            'animal_name': self.animal.name if self.animal else None,
            'animal_number': self.animal.animal_number if self.animal else None,
            'date': self.date.isoformat() if self.date else None,
            'shift': self.shift,
            'quantity': self.quantity,
            'fat_content': self.fat_content,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
