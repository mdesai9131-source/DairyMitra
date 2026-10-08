from flask import Flask
from app.config import config_by_name
from app.extensions import db, migrate, jwt, cors, limiter
from app.api import register_blueprints
from app.utils.responses import error_response, success_response

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Disable strict trailing slashes so /api/v1/animals and /api/v1/animals/ both work seamlessly
    app.url_map.strict_slashes = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    limiter.init_app(app)

    # Register blueprints
    register_blueprints(app)

    # Root endpoint / landing status
    @app.route('/')
    @app.route('/api')
    @app.route('/api/')
    @app.route('/api/v1')
    @app.route('/api/v1/')
    @app.route('/docs')
    @app.route('/api/docs')
    @app.route('/api/v1/docs')
    def index():
        from flask import request, render_template_string
        # If opened in a web browser, render a beautiful status dashboard
        if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
            html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>DairyMitra — Smart Dairy & Farm Admin Console</title>
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
                <style>
                    :root {
                        --primary: #1B5E20;
                        --primary-light: #2E7D32;
                        --primary-bg: #E8F5E9;
                        --secondary: #F57F17;
                        --bg: #F4F6F4;
                        --surface: #FFFFFF;
                        --text: #1E293B;
                        --text-muted: #64748B;
                        --border: #E2E8F0;
                        --error: #D32F2F;
                        --success: #2E7D32;
                    }
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body {
                        font-family: 'Plus Jakarta Sans', sans-serif;
                        background: var(--bg);
                        color: var(--text);
                        min-height: 100vh;
                        padding-bottom: 60px;
                    }
                    header {
                        background: var(--surface);
                        border-bottom: 1px solid var(--border);
                        padding: 16px 24px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        position: sticky;
                        top: 0;
                        z-index: 100;
                    }
                    .logo-wrap { display: flex; align-items: center; gap: 12px; }
                    .logo-badge {
                        background: linear-gradient(135deg, #1B5E20, #43A047);
                        color: white;
                        font-size: 20px;
                        font-weight: 800;
                        padding: 8px 12px;
                        border-radius: 12px;
                    }
                    .logo-text h1 { font-size: 18px; font-weight: 800; color: var(--primary); }
                    .logo-text p { font-size: 12px; color: var(--text-muted); }
                    .header-actions { display: flex; align-items: center; gap: 12px; }
                    .auth-pill {
                        background: var(--primary-bg);
                        color: var(--primary);
                        padding: 6px 14px;
                        border-radius: 30px;
                        font-size: 13px;
                        font-weight: 600;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                    }
                    .dot-live { width: 8px; height: 8px; background: #2E7D32; border-radius: 50%; }
                    .main-container { max-width: 1200px; margin: 24px auto; padding: 0 16px; }
                    
                    /* Hero & Quick Actions */
                    .hero-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px; }
                    @media (max-width: 860px) { .hero-grid { grid-template-columns: 1fr; } }
                    .banner-card {
                        background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
                        color: white;
                        padding: 28px;
                        border-radius: 20px;
                        box-shadow: 0 10px 25px rgba(27, 94, 32, 0.15);
                    }
                    .banner-card h2 { font-size: 24px; font-weight: 800; margin-bottom: 8px; }
                    .banner-card p { font-size: 14px; opacity: 0.9; margin-bottom: 20px; line-height: 1.5; }
                    .quick-btns { display: flex; flex-wrap: wrap; gap: 10px; }
                    .btn {
                        padding: 10px 18px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        border: none;
                        display: inline-flex;
                        align-items: center;
                        gap: 8px;
                        transition: all 0.2s;
                    }
                    .btn-white { background: white; color: var(--primary); }
                    .btn-white:hover { background: #F1F5F9; transform: translateY(-1px); }
                    .btn-secondary { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.4); }
                    .btn-secondary:hover { background: rgba(255,255,255,0.3); }
                    .btn-primary { background: var(--primary); color: white; }
                    .btn-primary:hover { background: var(--primary-light); }
                    
                    .auth-card {
                        background: var(--surface);
                        border: 1px solid var(--border);
                        border-radius: 20px;
                        padding: 24px;
                    }
                    .auth-card h3 { font-size: 16px; font-weight: 700; margin-bottom: 12px; }
                    .admin-chip {
                        background: #FFFDE7;
                        border-left: 4px solid var(--secondary);
                        padding: 10px 14px;
                        border-radius: 0 8px 8px 0;
                        font-size: 12px;
                        margin-bottom: 16px;
                    }

                    /* Stats Grid */
                    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
                    .stat-card {
                        background: var(--surface);
                        border: 1px solid var(--border);
                        border-radius: 16px;
                        padding: 20px;
                    }
                    .stat-label { font-size: 13px; color: var(--text-muted); font-weight: 600; margin-bottom: 6px; }
                    .stat-val { font-size: 26px; font-weight: 800; color: var(--text); }
                    .stat-sub { font-size: 12px; color: var(--primary); font-weight: 600; margin-top: 4px; }

                    /* Tabs */
                    .tab-bar { display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
                    .tab-btn {
                        padding: 8px 16px;
                        border-radius: 10px;
                        background: none;
                        border: none;
                        font-size: 14px;
                        font-weight: 700;
                        color: var(--text-muted);
                        cursor: pointer;
                    }
                    .tab-btn.active { background: var(--primary-bg); color: var(--primary); }
                    .tab-content { display: none; }
                    .tab-content.active { display: block; }

                    /* Table */
                    .table-card {
                        background: var(--surface);
                        border: 1px solid var(--border);
                        border-radius: 16px;
                        overflow: hidden;
                    }
                    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
                    th { background: #F8FAFC; color: var(--text-muted); padding: 12px 16px; font-weight: 700; font-size: 13px; border-bottom: 1px solid var(--border); }
                    td { padding: 12px 16px; border-bottom: 1px solid var(--border); }
                    tr:last-child td { border-bottom: none; }
                    .badge-pill { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }
                    .badge-green { background: #E8F5E9; color: #2E7D32; }
                    .badge-yellow { background: #FFF3E0; color: #E65100; }

                    /* Modal */
                    .modal-overlay {
                        position: fixed;
                        top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(0,0,0,0.5);
                        display: none;
                        align-items: center;
                        justify-content: center;
                        z-index: 1000;
                        padding: 16px;
                    }
                    .modal-card {
                        background: var(--surface);
                        border-radius: 20px;
                        max-width: 500px;
                        width: 100%;
                        padding: 24px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.2);
                    }
                    .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
                    .modal-header h3 { font-size: 18px; font-weight: 800; color: var(--primary); }
                    .modal-close { background: none; border: none; font-size: 22px; cursor: pointer; color: var(--text-muted); }
                    .form-group { margin-bottom: 14px; }
                    .form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
                    .form-control {
                        width: 100%;
                        padding: 10px 14px;
                        border-radius: 10px;
                        border: 1px solid var(--border);
                        font-size: 14px;
                        font-family: inherit;
                    }
                    .form-control:focus { outline: none; border-color: var(--primary); }
                    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

                    /* Toast */
                    #toast {
                        position: fixed;
                        bottom: 24px;
                        right: 24px;
                        background: #1E293B;
                        color: white;
                        padding: 12px 20px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 600;
                        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
                        display: none;
                        z-index: 2000;
                    }
                </style>
            </head>
            <body>
                <header>
                    <div class="logo-wrap">
                        <div class="logo-badge">DM</div>
                        <div class="logo-text">
                            <h1>DairyMitra Admin Console</h1>
                            <p>Desai Dairy Farm • Anand, Gujarat</p>
                        </div>
                    </div>
                    <div class="header-actions">
                        <div class="auth-pill"><div class="dot-live"></div> <span id="admin-status">Admin Connected</span></div>
                        <button class="btn btn-primary" onclick="reloginAdmin()">Sync / Re-Auth</button>
                    </div>
                </header>

                <div class="main-container">
                    <div class="hero-grid">
                        <div class="banner-card">
                            <h2>Smart Dairy & Farm Management</h2>
                            <p>Direct administrator controls to record milk production, register dairy customers, and monitor herd yields in real time.</p>
                            <div class="quick-btns">
                                <button class="btn btn-white" onclick="openMilkModal()">🥛 Record Daily Milk</button>
                                <button class="btn btn-white" onclick="openCustomerModal()">👥 Add New Customer</button>
                                <button class="btn btn-secondary" onclick="refreshAllData()">🔄 Refresh Data</button>
                            </div>
                        </div>

                        <div class="auth-card">
                            <h3>Admin Session</h3>
                            <div class="admin-chip">
                                <strong>Admin Farmer:</strong> Mahesh Desai<br>
                                <strong>Role:</strong> System Administrator (Full Access)<br>
                                <strong>Email:</strong> admin@dairymitra.com
                            </div>
                            <p style="font-size: 12px; color: var(--text-muted); line-height: 1.4;">
                                You have full administrative privileges to add milk records, manage customers, generate bills, and inspect herd profiles.
                            </p>
                        </div>
                    </div>

                    <!-- Live Stat Cards -->
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-label">Total Dairy Animals</div>
                            <div class="stat-val" id="stat-animals">10</div>
                            <div class="stat-sub">5 Cows • 5 Buffaloes</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Today's Total Milk</div>
                            <div class="stat-val" id="stat-milk">-- L</div>
                            <div class="stat-sub" id="stat-milk-sub">Morning + Evening</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Active Customers</div>
                            <div class="stat-val" id="stat-customers">--</div>
                            <div class="stat-sub">Subscribed for daily delivery</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Base Milk Price</div>
                            <div class="stat-val">₹60.0</div>
                            <div class="stat-sub">Per Litre Standard</div>
                        </div>
                    </div>

                    <!-- Navigation Tabs -->
                    <div class="tab-bar">
                        <button class="tab-btn active" onclick="switchTab('tab-milk')">🥛 Daily Milk Register</button>
                        <button class="tab-btn" onclick="switchTab('tab-customers')">👥 Customer Directory</button>
                        <button class="tab-btn" onclick="switchTab('tab-herd')">🐄 Herd Directory</button>
                        <button class="tab-btn" onclick="switchTab('tab-api')">🔌 REST API Blueprints</button>
                    </div>

                    <!-- Tab 1: Milk -->
                    <div id="tab-milk" class="tab-content active">
                        <div class="table-card">
                            <div style="padding: 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border);">
                                <strong>Today's Animal Milk Yields</strong>
                                <button class="btn btn-primary" onclick="openMilkModal()">+ Add Milk Record</button>
                            </div>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Tag / Number</th>
                                        <th>Animal Name</th>
                                        <th>Type & Breed</th>
                                        <th>Morning (L)</th>
                                        <th>Evening (L)</th>
                                        <th>Total (L)</th>
                                    </tr>
                                </thead>
                                <tbody id="milk-table-body">
                                    <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading milk records...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Tab 2: Customers -->
                    <div id="tab-customers" class="tab-content">
                        <div class="table-card">
                            <div style="padding: 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border);">
                                <strong>Registered Dairy Customers</strong>
                                <button class="btn btn-primary" onclick="openCustomerModal()">+ Add Customer</button>
                            </div>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Customer Name</th>
                                        <th>Phone</th>
                                        <th>Daily Quota</th>
                                        <th>Rate (₹/L)</th>
                                        <th>Balance</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="customer-table-body">
                                    <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading customers...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Tab 3: Herd -->
                    <div id="tab-herd" class="tab-content">
                        <div class="table-card">
                            <div style="padding: 16px;">
                                <strong>Active Herd Animals</strong>
                            </div>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Tag Number</th>
                                        <th>Name</th>
                                        <th>Animal Type</th>
                                        <th>Breed</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="herd-table-body">
                                    <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Loading herd...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Tab 4: API Endpoints -->
                    <div id="tab-api" class="tab-content">
                        <div class="table-card" style="padding: 24px;">
                            <h3 style="margin-bottom: 16px;">Available REST Blueprints</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
                                <div style="background: #F8FAFC; border: 1px solid var(--border); padding: 12px; border-radius: 10px;">
                                    <strong>Auth Service</strong>: <code>/api/v1/auth</code>
                                </div>
                                <div style="background: #F8FAFC; border: 1px solid var(--border); padding: 12px; border-radius: 10px;">
                                    <strong>Milk Production</strong>: <code>/api/v1/milk</code>
                                </div>
                                <div style="background: #F8FAFC; border: 1px solid var(--border); padding: 12px; border-radius: 10px;">
                                    <strong>Customer Ledger</strong>: <code>/api/v1/customers</code>
                                </div>
                                <div style="background: #F8FAFC; border: 1px solid var(--border); padding: 12px; border-radius: 10px;">
                                    <strong>Herd Animals</strong>: <code>/api/v1/animals</code>
                                </div>
                                <div style="background: #F8FAFC; border: 1px solid var(--border); padding: 12px; border-radius: 10px;">
                                    <strong>Invoicing & Bills</strong>: <code>/api/v1/bills</code>
                                </div>
                                <div style="background: #F8FAFC; border: 1px solid var(--border); padding: 12px; border-radius: 10px;">
                                    <strong>P&L Financials</strong>: <code>/api/v1/reports/profit</code>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Record Milk Modal -->
                <div id="milk-modal" class="modal-overlay">
                    <div class="modal-card">
                        <div class="modal-header">
                            <h3>🥛 Record Milk Production</h3>
                            <button class="modal-close" onclick="closeModal('milk-modal')">&times;</button>
                        </div>
                        <form onsubmit="handleRecordMilk(event)">
                            <div class="form-group">
                                <label>Select Animal*</label>
                                <select id="milk-animal-select" class="form-control" required></select>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Shift*</label>
                                    <select id="milk-shift" class="form-control">
                                        <option value="MORNING">Morning (सुबह)</option>
                                        <option value="EVENING">Evening (शाम)</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>Quantity (Litres)*</label>
                                    <input type="number" step="0.1" id="milk-qty" class="form-control" placeholder="e.g. 7.5" required>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Date</label>
                                <input type="date" id="milk-date" class="form-control">
                            </div>
                            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;">
                                <button type="button" class="btn" onclick="closeModal('milk-modal')">Cancel</button>
                                <button type="submit" class="btn btn-primary">Save Milk Record</button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Add Customer Modal -->
                <div id="customer-modal" class="modal-overlay">
                    <div class="modal-card">
                        <div class="modal-header">
                            <h3>👥 Add Dairy Customer</h3>
                            <button class="modal-close" onclick="closeModal('customer-modal')">&times;</button>
                        </div>
                        <form onsubmit="handleAddCustomer(event)">
                            <div class="form-group">
                                <label>Customer Name*</label>
                                <input type="text" id="cust-name" class="form-control" placeholder="e.g. Bhavesh Patel" required>
                            </div>
                            <div class="form-group">
                                <label>Phone Number*</label>
                                <input type="tel" id="cust-phone" class="form-control" placeholder="e.g. 9825099887" required>
                            </div>
                            <div class="form-group">
                                <label>Delivery Address</label>
                                <input type="text" id="cust-address" class="form-control" placeholder="House/Society address">
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Daily Quantity (L)*</label>
                                    <input type="number" step="0.5" id="cust-qty" class="form-control" value="1.5" required>
                                </div>
                                <div class="form-group">
                                    <label>Price / Litre (₹)*</label>
                                    <input type="number" step="1.0" id="cust-rate" class="form-control" value="60.0" required>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;">
                                <button type="button" class="btn" onclick="closeModal('customer-modal')">Cancel</button>
                                <button type="submit" class="btn btn-primary">Register Customer</button>
                            </div>
                        </form>
                    </div>
                </div>

                <div id="toast"></div>

                <script>
                    let token = localStorage.getItem('dairymitra_token');
                    let farmId = localStorage.getItem('dairymitra_farm_id') || 1;
                    let animalsList = [];

                    function showToast(msg) {
                        const t = document.getElementById('toast');
                        t.textContent = msg;
                        t.style.display = 'block';
                        setTimeout(() => t.style.display = 'none', 3500);
                    }

                    function switchTab(tabId) {
                        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                        event.target.classList.add('active');
                        document.getElementById(tabId).classList.add('active');
                    }

                    function openMilkModal() {
                        document.getElementById('milk-date').value = new Date().toISOString().split('T')[0];
                        document.getElementById('milk-modal').style.display = 'flex';
                    }

                    function openCustomerModal() {
                        document.getElementById('customer-modal').style.display = 'flex';
                    }

                    function closeModal(id) {
                        document.getElementById(id).style.display = 'none';
                    }

                    async function ensureAdminAuth() {
                        if (!token) {
                            await reloginAdmin();
                        }
                    }

                    async function reloginAdmin() {
                        try {
                            const res = await fetch('/api/v1/auth/login', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ email: 'admin@dairymitra.com', password: 'DairyMitra@2026' })
                            });
                            const json = await res.json();
                            if (json.success) {
                                token = json.data.access_token;
                                farmId = json.data.farm_id || 1;
                                localStorage.setItem('dairymitra_token', token);
                                localStorage.setItem('dairymitra_farm_id', farmId);
                                showToast('Logged in as Admin Mahesh Desai');
                                refreshAllData();
                            }
                        } catch (e) {
                            showToast('Admin login error: ' + e);
                        }
                    }

                    async function fetchHerd() {
                        try {
                            const res = await fetch(`/api/v1/animals?farm_id=${farmId}`, {
                                headers: { 'Authorization': `Bearer ${token}` }
                            });
                            const json = await res.json();
                            if (json.success) {
                                animalsList = json.data;
                                document.getElementById('stat-animals').textContent = animalsList.length;
                                
                                const select = document.getElementById('milk-animal-select');
                                select.innerHTML = animalsList.map(a => `<option value="${a.id}">${a.name} (${a.animal_number}) — ${a.breed}</option>`).join('');

                                const tbody = document.getElementById('herd-table-body');
                                tbody.innerHTML = animalsList.map(a => `
                                    <tr>
                                        <td><strong>${a.animal_number}</strong></td>
                                        <td>${a.name}</td>
                                        <td>${a.animal_type}</td>
                                        <td>${a.breed}</td>
                                        <td><span class="badge-pill badge-green">${a.current_status}</span></td>
                                    </tr>
                                `).join('');
                            }
                        } catch (e) { console.error(e); }
                    }

                    async function fetchMilk() {
                        try {
                            const today = new Date().toISOString().split('T')[0];
                            const res = await fetch(`/api/v1/milk?farm_id=${farmId}&date=${today}`, {
                                headers: { 'Authorization': `Bearer ${token}` }
                            });
                            const json = await res.json();
                            if (json.success) {
                                const d = json.data;
                                document.getElementById('stat-milk').textContent = `${d.grand_total} L`;
                                document.getElementById('stat-milk-sub').textContent = `Morning: ${d.morning_total}L | Evening: ${d.evening_total}L`;

                                const tbody = document.getElementById('milk-table-body');
                                if (!d.animals || d.animals.length === 0) {
                                    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No animals found.</td></tr>`;
                                } else {
                                    tbody.innerHTML = d.animals.map(a => `
                                        <tr>
                                            <td><strong>${a.animal_number}</strong></td>
                                            <td>${a.animal_name}</td>
                                            <td>${a.animal_type} (${a.breed})</td>
                                            <td>${a.morning > 0 ? a.morning + ' L' : '—'}</td>
                                            <td>${a.evening > 0 ? a.evening + ' L' : '—'}</td>
                                            <td><strong>${a.total} L</strong></td>
                                        </tr>
                                    `).join('');
                                }
                            }
                        } catch (e) { console.error(e); }
                    }

                    async function fetchCustomers() {
                        try {
                            const res = await fetch(`/api/v1/customers?farm_id=${farmId}`, {
                                headers: { 'Authorization': `Bearer ${token}` }
                            });
                            const json = await res.json();
                            if (json.success) {
                                const list = json.data;
                                document.getElementById('stat-customers').textContent = list.length;

                                const tbody = document.getElementById('customer-table-body');
                                if (!list || list.length === 0) {
                                    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No customers registered.</td></tr>`;
                                } else {
                                    tbody.innerHTML = list.map(c => `
                                        <tr>
                                            <td><strong>${c.name}</strong></td>
                                            <td>${c.phone}</td>
                                            <td>${c.daily_quantity} L / day</td>
                                            <td>₹${c.price_per_litre}</td>
                                            <td>₹${c.current_balance || 0}</td>
                                            <td><span class="badge-pill badge-green">${c.status}</span></td>
                                        </tr>
                                    `).join('');
                                }
                            }
                        } catch (e) { console.error(e); }
                    }

                    async function handleRecordMilk(e) {
                        e.preventDefault();
                        const animalId = document.getElementById('milk-animal-select').value;
                        const shift = document.getElementById('milk-shift').value;
                        const qty = parseFloat(document.getElementById('milk-qty').value);
                        const dateVal = document.getElementById('milk-date').value;

                        try {
                            const res = await fetch('/api/v1/milk', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': `Bearer ${token}`
                                },
                                body: JSON.stringify({
                                    farm_id: farmId,
                                    animal_id: parseInt(animalId),
                                    shift: shift,
                                    quantity: qty,
                                    date: dateVal
                                })
                            });
                            const json = await res.json();
                            if (json.success) {
                                closeModal('milk-modal');
                                showToast('Milk recorded successfully!');
                                fetchMilk();
                            } else {
                                alert(json.message || 'Error saving milk');
                            }
                        } catch (err) {
                            alert('Request failed: ' + err);
                        }
                    }

                    async function handleAddCustomer(e) {
                        e.preventDefault();
                        const name = document.getElementById('cust-name').value;
                        const phone = document.getElementById('cust-phone').value;
                        const address = document.getElementById('cust-address').value;
                        const qty = parseFloat(document.getElementById('cust-qty').value);
                        const rate = parseFloat(document.getElementById('cust-rate').value);

                        try {
                            const res = await fetch('/api/v1/customers', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': `Bearer ${token}`
                                },
                                body: JSON.stringify({
                                    farm_id: farmId,
                                    name: name,
                                    phone: phone,
                                    address: address,
                                    daily_quantity: qty,
                                    price_per_litre: rate
                                })
                            });
                            const json = await res.json();
                            if (json.success) {
                                closeModal('customer-modal');
                                showToast('Customer registered successfully!');
                                fetchCustomers();
                            } else {
                                alert(json.message || 'Error adding customer');
                            }
                        } catch (err) {
                            alert('Request failed: ' + err);
                        }
                    }

                    function refreshAllData() {
                        fetchHerd();
                        fetchMilk();
                        fetchCustomers();
                    }

                    window.onload = async () => {
                        await ensureAdminAuth();
                        refreshAllData();
                    };
                </script>
            </body>
            </html>
            """
            return render_template_string(html)

        return success_response(
            data={
                'service': 'DairyMitra Smart Dairy & Farm API Server',
                'status': 'healthy',
                'version': '1.0.0',
                'base_url': '/api/v1',
                'modules': [
                    'auth', 'farms', 'animals', 'milk', 'customers',
                    'bills', 'payments', 'expenses', 'ghee', 'inventory',
                    'reports', 'ai', 'notifications', 'sync'
                ]
            },
            message="Welcome to DairyMitra API Server"
        )

    # Health check endpoint
    @app.route('/health')
    def health():
        return success_response(data={'status': 'healthy', 'service': 'DairyMitra API'})

    # JWT Error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return error_response("Token has expired. Please refresh or login again.", status_code=401)

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return error_response("Invalid authentication token.", status_code=401)

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return error_response("Authentication required. Please provide a valid Bearer token.", status_code=401)

    # Global HTTP error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return error_response(str(e.description) if hasattr(e, 'description') else "Bad request", status_code=400)

    @app.errorhandler(404)
    def not_found(e):
        return error_response("The requested resource was not found", status_code=404)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return error_response("Rate limit exceeded. Please try again later.", status_code=429)

    @app.errorhandler(500)
    def internal_error(e):
        return error_response("An internal server error occurred.", status_code=500)

    return app
