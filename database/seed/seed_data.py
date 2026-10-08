import sys
import os
from datetime import date, timedelta
import random

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.farm import Farm, FarmMember
from app.models.animal import Animal, AnimalHealthRecord
from app.models.milk import MilkPrice, MilkProduction
from app.models.customer import Customer, MilkDelivery
from app.models.expense import Expense, ExpenseCategory
from app.models.ghee import GheeProduction, GheeSale
from app.models.inventory import Inventory
from app.api.expenses import ensure_categories_exist

def seed_all():
    app = create_app('development')
    with app.app_context():
        print("Creating tables...")
        db.create_all()
        ensure_categories_exist()

        # 1. Create or Update Admin User (Mahesh Desai)
        admin_email = "admin@dairymitra.com"
        user = User.query.filter((User.email == admin_email) | (User.email == "farmer@dairymitra.com")).first()
        if not user:
            user = User(
                email=admin_email,
                full_name="Mahesh Desai",
                phone="9825012345",
                role="ADMIN",
                is_active=True,
                is_verified=True
            )
            user.set_password("DairyMitra@2026")
            db.session.add(user)
            db.session.commit()
            print(f"Created admin farmer: {admin_email} (Password: DairyMitra@2026)")
        else:
            user.full_name = "Mahesh Desai"
            user.role = "ADMIN"
            user.email = admin_email
            user.phone = "9825012345"
            user.set_password("DairyMitra@2026")
            db.session.commit()
            print(f"Updated user to Admin Mahesh Desai: {admin_email}")

        # Also ensure farmer@dairymitra.com exists or can be used
        alt_user = User.query.filter_by(email="farmer@dairymitra.com").first()
        if not alt_user and user.email != "farmer@dairymitra.com":
            alt_user = User(
                email="farmer@dairymitra.com",
                full_name="Mahesh Desai",
                phone="9825012345",
                role="ADMIN",
                is_active=True,
                is_verified=True
            )
            alt_user.set_password("DairyMitra@2026")
            db.session.add(alt_user)
            db.session.commit()

        # 2. Create or Update Farm
        farm = Farm.query.filter_by(owner_id=user.id).first()
        if not farm:
            farm = Farm(
                owner_id=user.id,
                farm_name="Desai Dairy Farm",
                address="Plot No. 18, National Highway 48, Near Amul Dairy, Anand",
                city="Anand",
                state="Gujarat",
                pincode="388001"
            )
            db.session.add(farm)
            db.session.flush()
        else:
            farm.farm_name = "Desai Dairy Farm"
            farm.address = "Plot No. 18, National Highway 48, Near Amul Dairy, Anand"
            farm.city = "Anand"
            farm.state = "Gujarat"
            db.session.commit()

            price = MilkPrice(
                farm_id=farm.id,
                price_per_litre=60.0,
                effective_from=date.today() - timedelta(days=90),
                is_current=True
            )
            db.session.add(price)
            db.session.commit()
            print(f"Created Farm: {farm.farm_name}")

        # Ensure alt_user has FarmMember access to this farm
        if alt_user and not FarmMember.query.filter_by(farm_id=farm.id, user_id=alt_user.id).first():
            member = FarmMember(farm_id=farm.id, user_id=alt_user.id, role='OWNER')
            db.session.add(member)
            db.session.commit()

        # 3. Create Animals (5 cows, 5 buffaloes)
        if farm.animals.count() == 0:
            cows = [
                ("Gauri", "C001", "Gir", 12.5),
                ("Kaveri", "C002", "Kankrej", 11.0),
                ("Laxmi", "C003", "Sahiwal", 14.0),
                ("Kamdhenu", "C004", "Gir", 13.0),
                ("Radha", "C005", "Red Sindhi", 10.5)
            ]
            buffaloes = [
                ("Kali", "B001", "Murrah", 9.5),
                ("Yamuna", "B002", "Mehsana", 10.0),
                ("Ganga", "B003", "Murrah", 11.2),
                ("Narmada", "B004", "Surti", 8.5),
                ("Champa", "B005", "Jaffarabadi", 9.0)
            ]

            all_animals = []
            for name, num, breed, avg_qty in cows:
                a = Animal(
                    farm_id=farm.id,
                    animal_number=num,
                    name=name,
                    animal_type="COW",
                    breed=breed,
                    gender="FEMALE",
                    purchase_date=date.today() - timedelta(days=300),
                    purchase_price=55000.0,
                    current_status="ACTIVE"
                )
                db.session.add(a)
                all_animals.append((a, avg_qty))

            for name, num, breed, avg_qty in buffaloes:
                a = Animal(
                    farm_id=farm.id,
                    animal_number=num,
                    name=name,
                    animal_type="BUFFALO",
                    breed=breed,
                    gender="FEMALE",
                    purchase_date=date.today() - timedelta(days=200),
                    purchase_price=70000.0,
                    current_status="ACTIVE"
                )
                db.session.add(a)
                all_animals.append((a, avg_qty))

            db.session.commit()
            print("Added 5 cows and 5 buffaloes.")

            # Health records
            for a, _ in all_animals[:4]:
                h = AnimalHealthRecord(
                    animal_id=a.id,
                    record_type="VACCINATION",
                    date=date.today() - timedelta(days=45),
                    description="Foot & Mouth Disease (FMD) Vaccination",
                    medicine="Raksha Ovac",
                    cost=150.0,
                    next_due_date=date.today() + timedelta(days=135)
                )
                db.session.add(h)
            db.session.commit()

            # Milk History for last 14 days
            print("Generating 14 days of milk records...")
            today = date.today()
            for day_offset in range(14, -1, -1):
                rec_date = today - timedelta(days=day_offset)
                for a, target_qty in all_animals:
                    # Morning shift
                    m_qty = round((target_qty * 0.55) + random.uniform(-0.5, 0.5), 1)
                    # Evening shift
                    e_qty = round((target_qty * 0.45) + random.uniform(-0.4, 0.4), 1)

                    db.session.add(MilkProduction(
                        farm_id=farm.id,
                        animal_id=a.id,
                        date=rec_date,
                        shift="MORNING",
                        quantity=max(1.0, m_qty),
                        fat_content=random.choice([4.2, 4.5, 4.8, 6.2, 6.5])
                    ))
                    db.session.add(MilkProduction(
                        farm_id=farm.id,
                        animal_id=a.id,
                        date=rec_date,
                        shift="EVENING",
                        quantity=max(1.0, e_qty),
                        fat_content=random.choice([4.3, 4.6, 4.9, 6.3, 6.7])
                    ))
            db.session.commit()

        # 4. Create 20 Customers
        if farm.customers.count() == 0:
            print("Creating 20 customers...")
            names = [
                "Rajesh Patel", "Suresh Shah", "Kishore Solanki", "Dinesh Joshi", "Pravin Joshi",
                "Amit Sharma", "Kiran Varma", "Prakash Solanki", "Mukesh Mehta", "Hitesh Trivedi",
                "Jignesh Chauhan", "Pooja Gupta", "Anil Barot", "Sanjay Vyas", "Nitin Rathod",
                "Vijay Prajapati", "Manish Rajput", "Alok Sengupta", "Deepak Verma", "Chetan Modi"
            ]
            for i, name in enumerate(names, 1):
                c = Customer(
                    farm_id=farm.id,
                    name=name,
                    phone=f"98250{i:05d}",
                    email=f"customer{i}@gmail.com",
                    address=f"House No. {10 + i}, Green Park Society, Anand",
                    daily_quantity=random.choice([1.0, 1.5, 2.0, 2.5, 3.0]),
                    price_per_litre=60.0,
                    delivery_time="MORNING",
                    current_balance=random.choice([0.0, 300.0, 600.0, 1200.0])
                )
                db.session.add(c)
            db.session.commit()

            # Record deliveries for today and yesterday
            customers = farm.customers.all()
            for d_date in [date.today() - timedelta(days=1), date.today()]:
                for c in customers:
                    db.session.add(MilkDelivery(
                        farm_id=farm.id,
                        customer_id=c.id,
                        date=d_date,
                        shift="MORNING",
                        quantity=c.daily_quantity,
                        price_per_litre=c.price_per_litre,
                        total_amount=round(c.daily_quantity * c.price_per_litre, 2),
                        delivery_status="DELIVERED"
                    ))
            db.session.commit()

        # 5. Create Expenses
        if farm.expenses.count() == 0:
            print("Creating demo expenses...")
            feed_cat = ExpenseCategory.query.filter_by(code='FEED').first()
            med_cat = ExpenseCategory.query.filter_by(code='MEDICINE').first()
            lab_cat = ExpenseCategory.query.filter_by(code='LABOUR').first()
            trans_cat = ExpenseCategory.query.filter_by(code='TRANSPORT').first()

            expenses_data = [
                (feed_cat, 4500.0, "Cottonseed cake (Kapasiya khol) 2 bags", date.today() - timedelta(days=10)),
                (feed_cat, 3200.0, "Dry fodder & maize silage", date.today() - timedelta(days=5)),
                (med_cat, 850.0, "Mineral mixture packets & calcium tonic", date.today() - timedelta(days=8)),
                (lab_cat, 4000.0, "Weekly farm helper wages", date.today() - timedelta(days=7)),
                (trans_cat, 600.0, "Milk distribution fuel", date.today() - timedelta(days=2)),
            ]
            for cat, amt, desc, exp_date in expenses_data:
                if cat:
                    db.session.add(Expense(
                        farm_id=farm.id,
                        category_id=cat.id,
                        amount=amt,
                        date=exp_date,
                        description=desc,
                        payment_method="CASH",
                        created_by=user.id
                    ))
            db.session.commit()

        # 6. Ghee Production
        if GheeProduction.query.filter_by(farm_id=farm.id).count() == 0:
            print("Creating ghee production & sale batch...")
            g_batch = GheeProduction(
                farm_id=farm.id,
                date=date.today() - timedelta(days=6),
                milk_used_litres=25.0,
                ghee_produced_kg=3.0,
                production_cost=1500.0,
                selling_price_per_kg=900.0,
                notes="Bilona method desi cow ghee batch"
            )
            db.session.add(g_batch)

            g_sale = GheeSale(
                farm_id=farm.id,
                customer_id=farm.customers.first().id if farm.customers.first() else None,
                date=date.today() - timedelta(days=3),
                quantity_kg=2.0,
                price_per_kg=900.0,
                total_amount=1800.0,
                payment_status="PAID",
                notes="Sold to regular customer"
            )
            db.session.add(g_sale)
            db.session.commit()

        # 7. Inventory Items
        if farm.inventory_items.count() == 0:
            print("Creating inventory items...")
            inv_items = [
                ("Cottonseed Feed (Khol)", "FEED", "KG", 150.0, 40.0, 38.0),
                ("Maize Silage", "FEED", "KG", 500.0, 100.0, 8.0),
                ("Mineral Mixture", "MEDICINE", "KG", 8.0, 10.0, 120.0), # Low stock alert!
                ("Glass Ghee Jars (1 KG)", "DAIRY_PACKAGING", "PIECE", 25.0, 10.0, 35.0)
            ]
            for iname, icat, iunit, istock, ialert, icost in inv_items:
                db.session.add(Inventory(
                    farm_id=farm.id,
                    item_name=iname,
                    category=icat,
                    unit=iunit,
                    current_stock=istock,
                    minimum_stock_alert=ialert,
                    cost_per_unit=icost
                ))
            db.session.commit()

        print("\n=======================================================")
        print(" DairyMitra realistic seed data successfully created!")
        print(" Admin Farmer:   Mahesh Desai")
        print(" Farm Name:      Desai Dairy Farm (Anand, Gujarat)")
        print(" Login Email:    admin@dairymitra.com (or farmer@dairymitra.com)")
        print(" Login Password: DairyMitra@2026")
        print(" Role:           ADMIN")
        print("=======================================================\n")

if __name__ == '__main__':
    seed_all()
