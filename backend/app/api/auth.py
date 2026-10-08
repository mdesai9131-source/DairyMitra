from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from app.services.auth_service import AuthService
from app.utils.responses import success_response, error_response
from app.models.user import User
from app.models.farm import Farm

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    """Request a 6-digit OTP code to email."""
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    purpose = data.get('purpose', 'REGISTER')

    if not email:
        return error_response("Email address is required", status_code=400)

    success, message = AuthService.send_otp(email=email, purpose=purpose)
    if not success:
        return error_response(message, status_code=400)

    return success_response(message=message)

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify submitted 6-digit OTP code."""
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    otp_code = data.get('otp')
    purpose = data.get('purpose', 'REGISTER')

    if not email or not otp_code:
        return error_response("Both email and OTP code are required", status_code=400)

    success, message = AuthService.verify_otp(email=email, otp_code=str(otp_code), purpose=purpose)
    if not success:
        return error_response(message, status_code=400)

    return success_response(message=message)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new farmer/user account after OTP verification."""
    data = request.get_json(silent=True) or {}
    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')
    role = data.get('role', 'FARMER')

    if not full_name or not email or not password:
        return error_response("Full name, email, and password are required", status_code=400)

    if len(password) < 6:
        return error_response("Password must be at least 6 characters long", status_code=400)

    user, message = AuthService.register_user(
        full_name=full_name,
        email=email,
        password=password,
        phone=phone,
        role=role
    )
    if not user:
        return error_response(message, status_code=400)

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return success_response(
        data={
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        },
        message="Account created successfully",
        status_code=201
    )

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user with email and password."""
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return error_response("Email and password are required", status_code=400)

    user, message = AuthService.authenticate_user(email, password)
    if not user:
        return error_response(message, status_code=401)

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    # Also retrieve primary/first farm ID if user has one (owner or member or admin default)
    primary_farm = user.farms.first()
    farm_id = primary_farm.id if primary_farm else None
    if not farm_id:
        membership = user.memberships.first()
        if membership:
            farm_id = membership.farm_id
        elif user.role == 'ADMIN':
            system_farm = Farm.query.filter_by(is_active=True).first()
            farm_id = system_farm.id if system_farm else None

    return success_response(
        data={
            'user': user.to_dict(),
            'farm_id': farm_id,
            'access_token': access_token,
            'refresh_token': refresh_token
        },
        message="Login successful"
    )

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """Generate new access token using valid refresh token."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user or not user.is_active:
        return error_response("User account is inactive or not found", status_code=401)

    new_access_token = create_access_token(identity=str(user.id))
    return success_response(
        data={'access_token': new_access_token},
        message="Token refreshed successfully"
    )

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset OTP."""
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    if not email:
        return error_response("Email is required", status_code=400)

    user = User.query.filter_by(email=email.lower().strip()).first()
    if not user:
        # Don't reveal account existence for security, return standard message
        return success_response(message="If the email exists, an OTP has been sent.")

    success, message = AuthService.send_otp(email=email, purpose='FORGOT_PASSWORD')
    if not success:
        return error_response(message, status_code=400)

    return success_response(message="Password reset OTP sent to your email.")

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password after OTP verification."""
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    otp_code = data.get('otp')
    new_password = data.get('new_password')

    if not email or not otp_code or not new_password:
        return error_response("Email, OTP code, and new password are required", status_code=400)

    if len(new_password) < 6:
        return error_response("New password must be at least 6 characters long", status_code=400)

    # Verify OTP
    verified, msg = AuthService.verify_otp(email=email, otp_code=otp_code, purpose='FORGOT_PASSWORD')
    if not verified:
        return error_response(msg, status_code=400)

    # Reset password
    success, message = AuthService.reset_password(email=email, new_password=new_password)
    if not success:
        return error_response(message, status_code=400)

    return success_response(message=message)

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Fetch profile of authenticated user and their farms."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return error_response("User not found", status_code=404)

    farms = [f.to_dict() for f in user.farms.all()]
    return success_response(data={
        'user': user.to_dict(),
        'farms': farms
    })
