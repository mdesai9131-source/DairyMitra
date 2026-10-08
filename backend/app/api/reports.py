import csv
import io
from datetime import date
from flask import Blueprint, request, Response
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.milk import MilkProduction
from app.models.customer import Customer, MilkDelivery
from app.models.expense import Expense, ExpenseCategory
from app.services.financial_engine import FinancialEngine
from app.utils.responses import success_response
from app.utils.decorators import farm_access_required

reports_bp = Blueprint('reports', __name__, url_prefix='/api/v1/reports')

@reports_bp.route('/profit', methods=['GET'])
@farm_access_required
def profit_report():
    """Consolidated Revenue, Expense, and Net Profit report."""
    farm_id = int(request.args.get('farm_id'))
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date = date.fromisoformat(start_date_str) if start_date_str else None
    end_date = date.fromisoformat(end_date_str) if end_date_str else None

    fin = FinancialEngine.calculate_farm_financials(farm_id, start_date=start_date, end_date=end_date)
    return success_response(data=fin)

@reports_bp.route('/milk', methods=['GET'])
@farm_access_required
def milk_report():
    """Summary of milk production across date range."""
    farm_id = int(request.args.get('farm_id'))
    start_date = date.fromisoformat(request.args.get('start_date', date.today().replace(day=1).isoformat()))
    end_date = date.fromisoformat(request.args.get('end_date', date.today().isoformat()))

    records = MilkProduction.query.filter(
        MilkProduction.farm_id == farm_id,
        MilkProduction.date >= start_date,
        MilkProduction.date <= end_date
    ).all()

    total_litres = sum(r.quantity for r in records)
    morning_litres = sum(r.quantity for r in records if r.shift == 'MORNING')
    evening_litres = sum(r.quantity for r in records if r.shift == 'EVENING')

    return success_response(data={
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_litres': round(total_litres, 2),
        'morning_litres': round(morning_litres, 2),
        'evening_litres': round(evening_litres, 2),
        'total_records': len(records)
    })

@reports_bp.route('/csv', methods=['GET'])
@farm_access_required
def export_csv():
    """Export daily milk or expenses data to CSV format."""
    farm_id = int(request.args.get('farm_id'))
    report_type = request.args.get('type', 'milk').lower()

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'milk':
        writer.writerow(['Date', 'Animal Number', 'Animal Name', 'Shift', 'Quantity (L)', 'Fat %'])
        records = MilkProduction.query.filter_by(farm_id=farm_id).order_by(MilkProduction.date.desc()).all()
        for r in records:
            writer.writerow([
                r.date.isoformat(),
                r.animal.animal_number if r.animal else '',
                r.animal.name if r.animal else '',
                r.shift,
                r.quantity,
                r.fat_content or ''
            ])
        filename = f"milk_report_{farm_id}.csv"
    else:
        writer.writerow(['Date', 'Category', 'Description', 'Amount (INR)', 'Payment Method'])
        expenses = Expense.query.filter_by(farm_id=farm_id).order_by(Expense.date.desc()).all()
        for e in expenses:
            writer.writerow([
                e.date.isoformat(),
                e.category.name if e.category else '',
                e.description or '',
                e.amount,
                e.payment_method
            ])
        filename = f"expense_report_{farm_id}.csv"

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
