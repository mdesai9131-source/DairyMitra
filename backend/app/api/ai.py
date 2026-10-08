from datetime import date, timedelta
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from app.extensions import db
from app.models.milk import MilkProduction
from app.models.customer import Customer, MilkDelivery
from app.models.expense import Expense, ExpenseCategory
from app.models.animal import Animal
from app.models.ghee import GheeProduction
from app.services.financial_engine import FinancialEngine
from app.utils.responses import success_response, error_response
from app.utils.decorators import farm_access_required

ai_bp = Blueprint('ai', __name__, url_prefix='/api/v1/ai')

@ai_bp.route('/insights', methods=['GET'])
@farm_access_required
def get_insights():
    """
    Returns AI/ML driven insights:
    1. Profit Forecast (Next 30 days estimate)
    2. Milk Production Trend & Anomaly Alerts
    3. Expense Category Insights
    4. Customer Demand Forecast
    """
    farm_id = int(request.args.get('farm_id'))
    today = date.today()

    # 1. Milk Trends & Anomaly detection
    animals = Animal.query.filter_by(farm_id=farm_id, current_status='ACTIVE').all()
    milk_alerts = []
    
    for a in animals:
        recent_7d = MilkProduction.query.filter(
            MilkProduction.animal_id == a.id,
            MilkProduction.date >= today - timedelta(days=7),
            MilkProduction.date < today
        ).all()
        avg_7d = sum(r.quantity for r in recent_7d) / 7.0 if recent_7d else 0.0

        today_records = MilkProduction.query.filter_by(animal_id=a.id, date=today).all()
        today_qty = sum(r.quantity for r in today_records)

        if avg_7d > 0 and today_qty > 0 and today_qty < (avg_7d * 0.75):
            milk_alerts.append({
                'animal_id': a.id,
                'animal_name': a.name,
                'animal_number': a.animal_number,
                'today_quantity': round(today_qty, 2),
                'seven_day_avg': round(avg_7d, 2),
                'notice': f"Production for {a.name} is noticeably lower than its 7-day average. (Statistical observation; not veterinary diagnosis)."
            })

    # 2. Expense Insights
    expenses = Expense.query.filter(
        Expense.farm_id == farm_id,
        Expense.date >= today - timedelta(days=30)
    ).all()

    category_sums = {}
    for e in expenses:
        name = e.category.name if e.category else "Other"
        category_sums[name] = category_sums.get(name, 0.0) + e.amount

    highest_cat = max(category_sums.items(), key=lambda x: x[1]) if category_sums else ("None", 0.0)
    total_recent_exp = sum(category_sums.values())

    expense_insights = {
        'highest_expense_category': highest_cat[0],
        'highest_category_amount': round(highest_cat[1], 2),
        'total_30d_expenses': round(total_recent_exp, 2),
        'note': f"The highest operational expenditure in the past 30 days is {highest_cat[0]}." if category_sums else "No expenses recorded recently."
    }

    # 3. Customer Demand Forecast
    active_customers = Customer.query.filter_by(farm_id=farm_id, status='ACTIVE').all()
    daily_demand = sum(c.daily_quantity for c in active_customers)
    demand_forecast = {
        'estimated_daily_demand_litres': round(daily_demand, 2),
        'customer_count': len(active_customers),
        'confidence': 'Statistical Estimate based on active customer agreements'
    }

    # 4. Profit Forecast
    month_fin = FinancialEngine.calculate_farm_financials(farm_id, start_date=today - timedelta(days=30), end_date=today)
    est_future_profit = round(month_fin['net_profit'] * 1.05, 2) if month_fin['net_profit'] > 0 else month_fin['net_profit']

    profit_forecast = {
        'estimated_next_30d_profit': est_future_profit,
        'label': 'Estimated Projection (Statistical Extrapolation, Subject to Market Changes)',
        'basis_30d_revenue': month_fin['total_revenue'],
        'basis_30d_expense': month_fin['total_expenses']
    }

    return success_response(data={
        'farm_id': farm_id,
        'milk_production_alerts': milk_alerts,
        'expense_insights': expense_insights,
        'customer_demand_forecast': demand_forecast,
        'profit_forecast': profit_forecast
    })

@ai_bp.route('/ask', methods=['POST'])
@farm_access_required
def ask_assistant():
    """
    Farmer Conversational Business Assistant.
    Interprets natural language queries using live backend data sources.
    """
    data = request.get_json(silent=True) or {}
    farm_id = data.get('farm_id')
    question = (data.get('question') or '').strip().lower()

    if not question:
        return error_response("Question cannot be empty", status_code=400)

    today = date.today()

    # Query routing
    if "milk" in question and ("today" in question or "sell" in question or "sold" in question):
        deliveries = MilkDelivery.query.filter_by(farm_id=farm_id, date=today, delivery_status='DELIVERED').all()
        qty = sum(d.quantity for d in deliveries)
        amt = sum(d.total_amount for d in deliveries)
        reply = f"Today you delivered {qty:.1f} litres of milk generating Rs. {amt:.2f} in sales."

    elif "profit" in question:
        month_start = today.replace(day=1)
        fin = FinancialEngine.calculate_farm_financials(farm_id, start_date=month_start, end_date=today)
        reply = f"For this month, total revenue is Rs. {fin['total_revenue']:.2f}, expenses are Rs. {fin['total_expenses']:.2f}, and net profit is Rs. {fin['net_profit']:.2f}."

    elif "pending" in question or "balance" in question or "owe" in question:
        customers = Customer.query.filter(Customer.farm_id == farm_id, Customer.current_balance > 0).all()
        if customers:
            names = [f"{c.name} (Rs. {c.current_balance:.2f})" for c in customers[:5]]
            reply = f"Customers with pending balances include: {', '.join(names)}."
        else:
            reply = "No active customers currently have overdue pending balances."

    elif "feed" in question or "spend on feed" in question:
        cat = ExpenseCategory.query.filter_by(code='FEED').first()
        if cat:
            month_start = today.replace(day=1)
            feed_exps = Expense.query.filter(Expense.farm_id == farm_id, Expense.category_id == cat.id, Expense.date >= month_start).all()
            total_feed = sum(e.amount for e in feed_exps)
            reply = f"This month you have spent Rs. {total_feed:.2f} on cattle feed."
        else:
            reply = "No cattle feed expenses recorded this month."

    elif "most milk" in question or "highest milk" in question or "which animal" in question:
        top_prod = db.session.query(
            MilkProduction.animal_id,
            func.sum(MilkProduction.quantity).label('total_qty')
        ).filter(
            MilkProduction.farm_id == farm_id,
            MilkProduction.date >= today - timedelta(days=7)
        ).group_by(MilkProduction.animal_id).order_by(db.desc('total_qty')).first()

        if top_prod:
            animal = Animal.query.get(top_prod[0])
            if animal:
                reply = f"In the last 7 days, {animal.name} (#{animal.animal_number}) produced the most milk with {top_prod[1]:.1f} litres."
            else:
                reply = f"In the last 7 days, animal #{top_prod[0]} produced the most milk with {top_prod[1]:.1f} litres."
        else:
            reply = "Not enough milk production records available to calculate top producer."

    elif "ghee" in question:
        batches = GheeProduction.query.filter(GheeProduction.farm_id == farm_id, GheeProduction.date >= today - timedelta(days=30)).all()
        total_ghee = sum(b.ghee_produced_kg for b in batches)
        reply = f"In the past 30 days, your farm produced {total_ghee:.2f} kg of ghee."

    else:
        # Default smart summary
        today_milk = FinancialEngine.calculate_daily_milk_summary(farm_id, today)
        reply = f"Today's total milk production is {today_milk['total_quantity']} litres. Ask me about your milk sales, expenses, profits, or pending customer balances!"

    return success_response(data={
        'question': question,
        'answer': reply,
        'timestamp': date.today().isoformat()
    })
