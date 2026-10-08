"""
Centralized Financial Engine for DairyMitra.
Serves as the single authoritative source of truth for:
- Daily milk calculations
- Customer delivery bill calculations
- Expense aggregations
- Revenue & Net Profit calculations
- Inventory stock movements
"""
from datetime import date
from sqlalchemy import func
from app.extensions import db
from app.models.milk import MilkProduction, MilkPrice
from app.models.customer import Customer, MilkDelivery
from app.models.bill import CustomerBill
from app.models.expense import Expense
from app.models.ghee import GheeSale
from app.models.sale import Sale
from app.models.payment import Payment

class FinancialEngine:
    @staticmethod
    def get_current_milk_price(farm_id: int) -> float:
        """Retrieves the currently active milk price per litre for a farm."""
        record = MilkPrice.query.filter_by(farm_id=farm_id, is_current=True).order_by(MilkPrice.effective_from.desc()).first()
        return record.price_per_litre if record else 60.0

    @staticmethod
    def calculate_daily_milk_summary(farm_id: int, target_date: date):
        """Calculates morning, evening, and total milk yields for a given farm date."""
        records = MilkProduction.query.filter_by(farm_id=farm_id, date=target_date).all()
        morning_total = sum(r.quantity for r in records if r.shift == 'MORNING')
        evening_total = sum(r.quantity for r in records if r.shift == 'EVENING')
        grand_total = morning_total + evening_total
        return {
            'date': target_date.isoformat(),
            'morning_quantity': round(morning_total, 2),
            'evening_quantity': round(evening_total, 2),
            'total_quantity': round(grand_total, 2),
            'animal_count': len(records)
        }

    @staticmethod
    def calculate_customer_bill(farm_id: int, customer_id: int, start_date: date, end_date: date):
        """
        Calculates customer billing from actual daily delivery records within date range.
        Bill Total = Total Delivery Amount + Previous Balance
        """
        customer = Customer.query.filter_by(id=customer_id, farm_id=farm_id).first()
        if not customer:
            raise ValueError("Customer not found")

        deliveries = MilkDelivery.query.filter(
            MilkDelivery.farm_id == farm_id,
            MilkDelivery.customer_id == customer_id,
            MilkDelivery.date >= start_date,
            MilkDelivery.date <= end_date,
            MilkDelivery.delivery_status == 'DELIVERED'
        ).all()

        total_milk_qty = sum(d.quantity for d in deliveries)
        milk_amount = sum(d.total_amount for d in deliveries)
        previous_balance = customer.current_balance
        grand_total = round(milk_amount + previous_balance, 2)

        return {
            'customer_id': customer.id,
            'customer_name': customer.name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'deliveries_count': len(deliveries),
            'total_milk_qty': round(total_milk_qty, 2),
            'milk_amount': round(milk_amount, 2),
            'previous_balance': round(previous_balance, 2),
            'grand_total': grand_total,
            'balance_due': grand_total
        }

    @staticmethod
    def calculate_farm_financials(farm_id: int, start_date=None, end_date=None):
        """
        Calculates Total Revenue, Total Expenses, and Net Profit.
        Revenue = Milk Sales/Deliveries + Ghee Sales + Other Sales
        Expenses = All categorized farm expenses
        Net Profit = Total Revenue - Total Expenses
        """
        # Milk Deliveries Revenue
        delivery_q = db.session.query(func.coalesce(func.sum(MilkDelivery.total_amount), 0.0)).filter(
            MilkDelivery.farm_id == farm_id,
            MilkDelivery.delivery_status == 'DELIVERED'
        )
        if start_date:
            delivery_q = delivery_q.filter(MilkDelivery.date >= start_date)
        if end_date:
            delivery_q = delivery_q.filter(MilkDelivery.date <= end_date)
        milk_revenue = float(delivery_q.scalar())

        # Ghee Sales Revenue
        ghee_q = db.session.query(func.coalesce(func.sum(GheeSale.total_amount), 0.0)).filter(
            GheeSale.farm_id == farm_id
        )
        if start_date:
            ghee_q = ghee_q.filter(GheeSale.date >= start_date)
        if end_date:
            ghee_q = ghee_q.filter(GheeSale.date <= end_date)
        ghee_revenue = float(ghee_q.scalar())

        # Other Sales Revenue
        other_q = db.session.query(func.coalesce(func.sum(Sale.total_amount), 0.0)).filter(
            Sale.farm_id == farm_id
        )
        if start_date:
            other_q = other_q.filter(Sale.date >= start_date)
        if end_date:
            other_q = other_q.filter(Sale.date <= end_date)
        other_revenue = float(other_q.scalar())

        total_revenue = round(milk_revenue + ghee_revenue + other_revenue, 2)

        # Expenses
        expense_q = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
            Expense.farm_id == farm_id
        )
        if start_date:
            expense_q = expense_q.filter(Expense.date >= start_date)
        if end_date:
            expense_q = expense_q.filter(Expense.date <= end_date)
        total_expenses = round(float(expense_q.scalar()), 2)

        net_profit = round(total_revenue - total_expenses, 2)

        return {
            'milk_revenue': round(milk_revenue, 2),
            'ghee_revenue': round(ghee_revenue, 2),
            'other_revenue': round(other_revenue, 2),
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'is_profitable': net_profit >= 0
        }
