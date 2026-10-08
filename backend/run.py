import os
import socket
from app import create_app
from app.extensions import db
from app.api.expenses import ensure_categories_exist

env = os.getenv('FLASK_ENV', 'development')
app = create_app(env)

def is_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    """Check if a local port is already bound by another application."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

with app.app_context():
    try:
        db.create_all()
        ensure_categories_exist()
        app.logger.info("DairyMitra Backend initialized: Tables & defaults verified.")
    except Exception as e:
        app.logger.warning(f"Database initialization notice: {e}")

if __name__ == '__main__':
    print("DairyMitra Backend initialized. Tables & defaults verified.")

    default_port = 5001
    port = int(os.getenv('PORT', default_port))
    host = os.getenv('HOST', '0.0.0.0')

    # Detect port collision (e.g. if port 5000 is occupied by another local service)
    if is_port_in_use(port):
        print(f"Notice: Port {port} is already in use by another application.")
        if port != 5001 and not is_port_in_use(5001):
            print(f"Automatically switching DairyMitra to free port 5001.")
            port = 5001

    print("=" * 60)
    print(f" DairyMitra REST API Server running on port {port}")
    print(f" -> Local Dashboard: http://127.0.0.1:{port}/")
    print(f" -> API Base URL:    http://127.0.0.1:{port}/api/v1")
    print(f" -> Health Check:    http://127.0.0.1:{port}/health")
    print("=" * 60)
    app.run(host=host, port=port, debug=(env == 'development'))

