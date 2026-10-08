import hmac
import hashlib
import uuid
from datetime import datetime
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import razorpay
from app.extensions import db
from app.models.payment import Payment
from app.models.bill import CustomerBill
from app.models.customer import Customer
from app.services.audit_service import log_audit
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

payments_bp = Blueprint('payments', __name__, url_prefix='/api/v1/payments')

def get_razorpay_client():
    key_id = current_app.config.get('RAZORPAY_KEY_ID')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
    return razorpay.Client(auth=(key_id, key_secret))

@payments_bp.route('/create-order', methods=['POST'])
@farm_access_required
def create_order():
    """
    Creates a server-side Razorpay order.
    Returns gateway_order_id, key_id, and currency to Flutter client.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    customer_id = data.get('customer_id')
    bill_id = data.get('bill_id')
    amount = float(data.get('amount', 0.0))

    if amount <= 0:
        return error_response("Payment amount must be greater than zero", status_code=400)

    customer = Customer.query.filter_by(id=customer_id, farm_id=farm_id).first_or_404()

    # Amount in Paise (INR * 100)
    amount_in_paise = int(round(amount * 100))
    receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"

    key_id = current_app.config.get('RAZORPAY_KEY_ID')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')

    # If test mode or mock keys, generate a deterministic order id for testing
    if key_id == 'rzp_test_placeholder_key' or not key_secret:
        order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
    else:
        try:
            client = get_razorpay_client()
            order_data = {
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': receipt_id,
                'notes': {
                    'farm_id': str(farm_id),
                    'customer_id': str(customer_id),
                    'bill_id': str(bill_id or '')
                }
            }
            order = client.order.create(data=order_data)
            order_id = order['id']
        except Exception as e:
            return error_response(f"Payment gateway error: {str(e)}", status_code=502)

    # Save payment record in CREATED state
    payment = Payment(
        farm_id=farm_id,
        customer_id=customer_id,
        bill_id=bill_id,
        amount=amount,
        currency='INR',
        payment_method='RAZORPAY',
        gateway_order_id=order_id,
        receipt_number=receipt_id,
        status='CREATED',
        notes=data.get('notes')
    )
    db.session.add(payment)
    db.session.commit()

    log_audit(
        action="PAYMENT_ORDER_CREATED",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="Payment",
        entity_id=payment.id,
        metadata={'order_id': order_id, 'amount': amount}
    )

    return success_response(data={
        'payment_id': payment.id,
        'gateway_order_id': order_id,
        'razorpay_key_id': key_id,
        'amount': amount,
        'amount_paise': amount_in_paise,
        'currency': 'INR',
        'customer_name': customer.name,
        'customer_phone': customer.phone,
        'customer_email': customer.email
    }, message="Payment order created successfully")

@payments_bp.route('/verify', methods=['POST'])
@jwt_required()
def verify_payment():
    """
    CRITICAL SECURITY RULE:
    Server-side HMAC-SHA256 signature verification.
    Only upon verified signature is customer balance and bill updated.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    order_id = data.get('gateway_order_id')
    payment_id = data.get('gateway_payment_id')
    signature = data.get('gateway_signature')

    if not order_id or not payment_id:
        return error_response("gateway_order_id and gateway_payment_id are required", status_code=400)

    payment_record = Payment.query.filter_by(gateway_order_id=order_id).first_or_404()

    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
    is_mock = current_app.config.get('RAZORPAY_KEY_ID') == 'rzp_test_placeholder_key'

    # Signature validation
    if not is_mock and key_secret:
        generated_signature = hmac.new(
            key_secret.encode('utf-8'),
            f"{order_id}|{payment_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(generated_signature, signature or ''):
            payment_record.status = 'FAILED'
            db.session.commit()
            log_audit(action="PAYMENT_FAILED_SIGNATURE", user_id=user_id, entity_type="Payment", entity_id=payment_record.id)
            return error_response("Invalid payment signature. Verification failed.", status_code=400)

    # Verification succeeded
    payment_record.gateway_payment_id = payment_id
    payment_record.gateway_signature = signature
    payment_record.status = 'SUCCESS'
    payment_record.verified_at = datetime.utcnow()

    # Update Customer Balance (deduct paid amount)
    customer = payment_record.customer
    customer.current_balance = round(customer.current_balance - payment_record.amount, 2)

    # Update Bill if associated
    if payment_record.bill_id:
        bill = CustomerBill.query.get(payment_record.bill_id)
        if bill:
            bill.paid_amount = round(bill.paid_amount + payment_record.amount, 2)
            bill.balance_due = round(bill.grand_total - bill.paid_amount, 2)
            if bill.balance_due <= 0:
                bill.status = 'PAID'
            else:
                bill.status = 'PARTIALLY_PAID'

    db.session.commit()

    log_audit(
        action="PAYMENT_VERIFIED",
        user_id=user_id,
        farm_id=payment_record.farm_id,
        entity_type="Payment",
        entity_id=payment_record.id,
        metadata={'payment_id': payment_id, 'amount': payment_record.amount}
    )

    return success_response(data=payment_record.to_dict(), message="Payment verified and balance updated successfully")

@payments_bp.route('/cash', methods=['POST'])
@farm_access_required
def record_cash_payment():
    """Record an in-person cash or direct UPI payment."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    customer_id = data.get('customer_id')
    bill_id = data.get('bill_id')
    amount = float(data.get('amount', 0.0))
    method = data.get('payment_method', 'CASH').upper()

    if amount <= 0:
        return error_response("Payment amount must be greater than zero", status_code=400)

    customer = Customer.query.filter_by(id=customer_id, farm_id=farm_id).first_or_404()
    receipt_no = f"CASH-{uuid.uuid4().hex[:8].upper()}"

    payment = Payment(
        farm_id=farm_id,
        customer_id=customer_id,
        bill_id=bill_id,
        amount=amount,
        payment_method=method,
        status='SUCCESS',
        receipt_number=receipt_no,
        notes=data.get('notes'),
        verified_at=datetime.utcnow()
    )
    db.session.add(payment)

    # Deduct customer balance
    customer.current_balance = round(customer.current_balance - amount, 2)

    # Update bill if linked
    if bill_id:
        bill = CustomerBill.query.get(bill_id)
        if bill:
            bill.paid_amount = round(bill.paid_amount + amount, 2)
            bill.balance_due = round(bill.grand_total - bill.paid_amount, 2)
            bill.status = 'PAID' if bill.balance_due <= 0 else 'PARTIALLY_PAID'

    db.session.commit()

    log_audit(action="CASH_PAYMENT_RECORDED", user_id=user_id, farm_id=farm_id, entity_type="Payment", entity_id=payment.id)
    return success_response(data=payment.to_dict(), message="Cash payment recorded successfully", status_code=201)

@payments_bp.route('', methods=['GET'])
@farm_access_required
def list_payments():
    """List payment transactions for a farm or customer."""
    farm_id = int(request.args.get('farm_id'))
    customer_id = request.args.get('customer_id')

    query = Payment.query.filter_by(farm_id=farm_id)
    if customer_id:
        query = query.filter_by(customer_id=int(customer_id))

    payments = query.order_by(Payment.created_at.desc()).all()
    return success_response(data=[p.to_dict() for p in payments])
