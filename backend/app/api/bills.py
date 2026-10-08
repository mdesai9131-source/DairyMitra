import io
import uuid
from datetime import date
from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from app.extensions import db
from app.models.bill import CustomerBill, CustomerBillItem
from app.models.customer import Customer, MilkDelivery
from app.services.financial_engine import FinancialEngine
from app.services.audit_service import log_audit
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

bills_bp = Blueprint('bills', __name__, url_prefix='/api/v1/bills')

@bills_bp.route('/generate', methods=['POST'])
@farm_access_required
def generate_bill():
    """
    Generates a formal bill for a customer based on actual deliveries.
    Bill Total = Milk Amount + Previous Balance.
    Customer's current balance is updated to reflect the new grand total.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    customer_id = data.get('customer_id')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    if not farm_id or not customer_id or not start_date_str or not end_date_str:
        return error_response("Farm ID, customer ID, start date, and end date are required", status_code=400)

    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)

    customer = Customer.query.filter_by(id=customer_id, farm_id=farm_id).first_or_404()

    # Calculate via central financial engine
    calc = FinancialEngine.calculate_customer_bill(farm_id, customer_id, start_date, end_date)

    bill_number = f"DM-BILL-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

    bill = CustomerBill(
        farm_id=farm_id,
        customer_id=customer_id,
        bill_number=bill_number,
        start_date=start_date,
        end_date=end_date,
        total_milk_qty=calc['total_milk_qty'],
        milk_amount=calc['milk_amount'],
        previous_balance=calc['previous_balance'],
        grand_total=calc['grand_total'],
        paid_amount=0.0,
        balance_due=calc['grand_total'],
        status='PENDING' if calc['grand_total'] > 0 else 'PAID',
        notes=data.get('notes')
    )
    db.session.add(bill)
    db.session.flush()

    # Link delivery items
    deliveries = MilkDelivery.query.filter(
        MilkDelivery.farm_id == farm_id,
        MilkDelivery.customer_id == customer_id,
        MilkDelivery.date >= start_date,
        MilkDelivery.date <= end_date,
        MilkDelivery.delivery_status == 'DELIVERED'
    ).all()

    for d in deliveries:
        item = CustomerBillItem(
            bill_id=bill.id,
            delivery_id=d.id,
            date=d.date,
            shift=d.shift,
            quantity=d.quantity,
            rate=d.price_per_litre,
            amount=d.total_amount
        )
        db.session.add(item)

    # Update customer balance to the grand total due
    customer.current_balance = calc['grand_total']
    db.session.commit()

    log_audit(
        action="BILL_CREATED",
        user_id=user_id,
        farm_id=farm_id,
        entity_type="CustomerBill",
        entity_id=bill.id,
        metadata={'bill_number': bill.bill_number, 'amount': bill.grand_total}
    )

    return success_response(data=bill.to_dict(), message="Bill generated successfully", status_code=201)

@bills_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_bill(id):
    """Retrieve bill details and individual item lines."""
    bill = CustomerBill.query.get_or_404(id)
    items = [item.to_dict() for item in bill.items.order_by(CustomerBillItem.date.asc()).all()]
    data = bill.to_dict()
    data['items'] = items
    return success_response(data=data)

@bills_bp.route('/<int:id>/pdf', methods=['GET'])
@jwt_required()
def generate_bill_pdf(id):
    """Generates a downloadable PDF bill."""
    bill = CustomerBill.query.get_or_404(id)
    customer = bill.customer
    farm = customer.farm

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setTitle(f"Invoice_{bill.bill_number}")

    # Header
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, 750, "DairyMitra - Milk Invoice")
    
    p.setFont("Helvetica", 10)
    p.drawString(50, 735, f"Farm: {farm.farm_name} | {farm.city or ''} {farm.state or ''}")
    p.line(50, 725, 550, 725)

    # Invoice Meta
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 700, f"Invoice #: {bill.bill_number}")
    p.setFont("Helvetica", 10)
    p.drawString(50, 685, f"Period: {bill.start_date} to {bill.end_date}")
    p.drawString(50, 670, f"Customer: {customer.name} ({customer.phone})")
    p.drawString(50, 655, f"Address: {customer.address or 'N/A'}")

    # Bill Summary Box
    p.rect(50, 520, 500, 110)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(65, 605, "Description")
    p.drawString(450, 605, "Amount (INR)")
    p.line(50, 595, 550, 595)

    p.setFont("Helvetica", 10)
    p.drawString(65, 575, f"Milk Delivered: {bill.total_milk_qty} Litres")
    p.drawString(450, 575, f"{bill.milk_amount:.2f}")

    p.drawString(65, 555, "Previous Balance / Arrears:")
    p.drawString(450, 555, f"{bill.previous_balance:.2f}")

    p.drawString(65, 535, "Less Payments Received:")
    p.drawString(450, 535, f"- {bill.paid_amount:.2f}")

    p.line(50, 525, 550, 525)

    p.setFont("Helvetica-Bold", 14)
    p.drawString(65, 490, "Net Balance Due:")
    p.drawString(450, 490, f"Rs. {bill.balance_due:.2f}")

    # Footer
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, 100, "Thank you for supporting your local dairy farm! Powered by DairyMitra.")
    p.line(50, 90, 550, 90)

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{bill.bill_number}.pdf",
        mimetype='application/pdf'
    )

@bills_bp.route('/<int:id>/accept', methods=['POST'])
@jwt_required()
def accept_bill(id):
    """Customer or user accepts/confirms the bill statement."""
    user_id = int(get_jwt_identity())
    bill = CustomerBill.query.get_or_404(id)
    if bill.status != 'PAID':
        bill.status = 'ACCEPTED'
    db.session.commit()
    log_audit(
        action="BILL_ACCEPTED",
        user_id=user_id,
        farm_id=bill.farm_id,
        entity_type="CustomerBill",
        entity_id=bill.id,
        metadata={'bill_number': bill.bill_number, 'status': bill.status}
    )
    return success_response(data=bill.to_dict(), message="Bill accepted and confirmed successfully")

