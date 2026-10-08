from app.api.auth import auth_bp
from app.api.farms import farms_bp
from app.api.animals import animals_bp
from app.api.milk import milk_bp
from app.api.customers import customers_bp
from app.api.bills import bills_bp
from app.api.payments import payments_bp
from app.api.expenses import expenses_bp
from app.api.ghee import ghee_bp
from app.api.inventory import inventory_bp
from app.api.reports import reports_bp
from app.api.ai import ai_bp
from app.api.notifications import notifications_bp
from app.api.sync import sync_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(farms_bp)
    app.register_blueprint(animals_bp)
    app.register_blueprint(milk_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(ghee_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(sync_bp)
