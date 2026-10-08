import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

import pytest
from datetime import date
from app import create_app
from app.extensions import db
from app.models.user import User, EmailOTP
from app.models.farm import Farm
from app.models.animal import Animal
from app.models.milk import MilkProduction, MilkPrice
from app.models.customer import Customer, MilkDelivery
from app.models.expense import Expense, ExpenseCategory
from app.services.financial_engine import FinancialEngine
from app.services.auth_service import AuthService, hash_otp

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_otp_generation_and_hashing(client):
    """Test OTP creation, SHA-256 hashing, and verification."""
    email = "testfarmer@gmail.com"
    success, msg = AuthService.send_otp(email, purpose='REGISTER')
    assert success is True

    otp_record = EmailOTP.query.filter_by(email=email, is_used=False).first()
    assert otp_record is not None
    assert len(otp_record.otp_hash) == 64  # SHA-256 hex string length

    # Attempt wrong OTP
    verified, error_msg = AuthService.verify_otp(email, "000000", purpose='REGISTER')
    assert verified is False
    assert "Incorrect OTP" in error_msg

def test_user_registration_and_login(client):
    """Test full registration and JWT login."""
    email = "farmer_auth_test@gmail.com"
    user, msg = AuthService.register_user("Gopal", email, "secret12345", phone="9988776655")
    assert user is not None
    assert user.check_password("secret12345") is True

    # Login via API
    res = client.post('/api/v1/auth/login', json={
        'email': email,
        'password': 'secret12345'
    })
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert 'access_token' in json_data['data']

def test_financial_engine_calculations(client):
    """Test Revenue - Expense = Net Profit formula."""
    user = User(email="farmtest@gmail.com", full_name="Farmer Test", role="FARMER")
    user.set_password("pass")
    db.session.add(user)
    db.session.commit()

    farm = Farm(owner_id=user.id, farm_name="Profit Test Farm")
    db.session.add(farm)
    db.session.commit()

    cust = Customer(farm_id=farm.id, name="Test Cust", phone="1234567890", daily_quantity=2.0, price_per_litre=60.0)
    db.session.add(cust)
    db.session.commit()

    # Delivery of 2L at 60 = 120 INR
    deliv = MilkDelivery(
        farm_id=farm.id,
        customer_id=cust.id,
        date=date.today(),
        shift="MORNING",
        quantity=2.0,
        price_per_litre=60.0,
        total_amount=120.0,
        delivery_status="DELIVERED"
    )
    db.session.add(deliv)

    # Expense of 50 INR
    cat = ExpenseCategory(name="Feed", code="FEED", is_default=True)
    db.session.add(cat)
    db.session.flush()

    exp = Expense(farm_id=farm.id, category_id=cat.id, amount=50.0, date=date.today())
    db.session.add(exp)
    db.session.commit()

    # Financial check
    fin = FinancialEngine.calculate_farm_financials(farm.id)
    assert fin['total_revenue'] == 120.0
    assert fin['total_expenses'] == 50.0
    assert fin['net_profit'] == 70.0
    assert fin['is_profitable'] is True

def test_admin_add_customer_and_milk(client):
    """Test that an ADMIN user can add customers and record milk seamlessly."""
    # 1. Create Admin
    admin = User(email="admin_test@dairymitra.com", full_name="Admin Test", role="ADMIN", is_active=True, is_verified=True)
    admin.set_password("DairyMitra@2026")
    db.session.add(admin)
    db.session.commit()

    # 2. Create Farm
    farm = Farm(owner_id=admin.id, farm_name="Admin Test Farm")
    db.session.add(farm)
    db.session.commit()

    # 3. Create Animal
    animal = Animal(farm_id=farm.id, animal_number="A01", name="Ganga", animal_type="COW")
    db.session.add(animal)
    db.session.commit()

    # 4. Login as Admin
    login_res = client.post('/api/v1/auth/login', json={'email': 'admin_test@dairymitra.com', 'password': 'DairyMitra@2026'})
    assert login_res.status_code == 200
    token = login_res.get_json()['data']['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 5. Add Customer as Admin (with farm_id)
    cust_res = client.post('/api/v1/customers', json={
        'farm_id': farm.id,
        'name': 'Ramesh Bhai',
        'phone': '9876543210',
        'daily_quantity': 2.5,
        'price_per_litre': 62.0
    }, headers=headers)
    assert cust_res.status_code == 201
    assert cust_res.get_json()['data']['name'] == 'Ramesh Bhai'

    # 6. Add Milk Record as Admin (with farm_id)
    milk_res = client.post('/api/v1/milk', json={
        'farm_id': farm.id,
        'animal_id': animal.id,
        'shift': 'MORNING',
        'quantity': 8.5
    }, headers=headers)
    assert milk_res.status_code == 201
    assert milk_res.get_json()['data']['quantity'] == 8.5

    # 7. List Customers without farm_id in query (Admin auto-resolves to primary farm)
    list_cust_res = client.get('/api/v1/customers', headers=headers)
    assert list_cust_res.status_code == 200
    assert len(list_cust_res.get_json()['data']) == 1

    # 8. Get Daily Milk without farm_id in query (Admin auto-resolves to primary farm)
    daily_milk_res = client.get('/api/v1/milk', headers=headers)
    assert daily_milk_res.status_code == 200
    assert daily_milk_res.get_json()['data']['morning_total'] == 8.5

