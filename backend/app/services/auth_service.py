import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app
from app.extensions import db
from app.models.user import User, EmailOTP
from app.services.email_service import send_otp_email
from app.services.audit_service import log_audit

def get_utc_now() -> datetime:
    """Returns naive UTC timestamp for SQLAlchemy datetime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def hash_otp(otp_str: str) -> str:
    """Hashes the OTP code using SHA-256 before database persistence."""
    return hashlib.sha256(otp_str.encode('utf-8')).hexdigest()

def generate_secure_otp() -> str:
    """Generates a secure, 6-digit numeric OTP string."""
    code = secrets.randbelow(900000) + 100000
    return str(code)

class AuthService:
    @staticmethod
    def send_otp(email: str, purpose: str = 'REGISTER'):
        """
        Generates and sends a 6-digit OTP to the email.
        Enforces cooldown and invalidates old active tokens.
        """
        email = email.lower().strip()
        purpose = purpose.upper().strip()

        # Check existing active OTP for cooldown
        latest_otp = EmailOTP.query.filter_by(
            email=email,
            purpose=purpose,
            is_used=False
        ).order_by(EmailOTP.created_at.desc()).first()

        cooldown_seconds = current_app.config.get('OTP_RESEND_COOLDOWN_SECONDS', 60)
        now = get_utc_now()

        if latest_otp:
            elapsed = (now - latest_otp.created_at).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return False, f"Please wait {remaining} seconds before requesting a new OTP."

            # Invalidate older pending OTPs
            EmailOTP.query.filter_by(
                email=email,
                purpose=purpose,
                is_used=False
            ).update({'is_used': True})
            db.session.commit()

        # Generate new 6-digit OTP
        plain_otp = generate_secure_otp()
        otp_hash = hash_otp(plain_otp)
        expiry_minutes = current_app.config.get('OTP_EXPIRY_MINUTES', 10)
        expires_at = now + timedelta(minutes=expiry_minutes)

        otp_record = EmailOTP(
            email=email,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
            max_attempts=current_app.config.get('OTP_MAX_ATTEMPTS', 5)
        )
        db.session.add(otp_record)
        db.session.commit()

        # Send email
        dispatched = send_otp_email(email, plain_otp, purpose=purpose)
        if not dispatched:
            return False, "Failed to send OTP email. Please verify email settings."

        log_audit(action=f"OTP_SENT_{purpose}", metadata={'email': email})
        return True, "OTP sent successfully."

    @staticmethod
    def verify_otp(email: str, otp_code: str, purpose: str = 'REGISTER'):
        """
        Verifies the provided 6-digit OTP against the hashed value.
        Checks expiration, attempt limit, and marks used upon success.
        """
        email = email.lower().strip()
        otp_code = str(otp_code).strip()
        purpose = purpose.upper().strip()

        record = EmailOTP.query.filter_by(
            email=email,
            purpose=purpose,
            is_used=False
        ).order_by(EmailOTP.created_at.desc()).first()

        # Optional convenience bypass for local/mock development (code 123456)
        if current_app.config.get('OTP_MOCK_MODE', False) and otp_code == '123456':
            if record:
                record.is_used = True
                db.session.commit()
            return True, "OTP verified successfully."

        if not record:
            return False, "No active OTP request found. Please request a new OTP."

        now = get_utc_now()
        if now > record.expires_at:
            record.is_used = True
            db.session.commit()
            return False, "OTP has expired. Please request a new OTP."

        if record.attempts >= record.max_attempts:
            record.is_used = True
            db.session.commit()
            return False, "Maximum verification attempts exceeded. Please request a new OTP."

        record.attempts += 1
        hashed_input = hash_otp(otp_code)

        if record.otp_hash != hashed_input:
            remaining = record.max_attempts - record.attempts
            db.session.commit()
            return False, f"Incorrect OTP. {remaining} attempt(s) remaining."

        # OTP verified successfully
        record.is_used = True
        db.session.commit()

        log_audit(action=f"OTP_VERIFIED_{purpose}", metadata={'email': email})
        return True, "OTP verified successfully."

    @staticmethod
    def register_user(full_name: str, email: str, password: str, phone: str = None, role: str = 'FARMER'):
        """
        Registers a new user after OTP verification.
        """
        email = email.lower().strip()
        if User.query.filter_by(email=email).first():
            return None, "An account with this email already exists."

        user = User(
            full_name=full_name.strip(),
            email=email,
            phone=phone.strip() if phone else None,
            role=role.upper(),
            is_active=True,
            is_verified=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        log_audit(action="USER_REGISTERED", user_id=user.id, metadata={'email': email, 'role': user.role})
        return user, "User registered successfully."

    @staticmethod
    def authenticate_user(email: str, password: str):
        """
        Authenticates user with email and password.
        """
        email = email.lower().strip()
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return None, "Invalid email or password."

        if not user.is_active:
            return None, "Account is disabled. Please contact support."

        log_audit(action="LOGIN", user_id=user.id, metadata={'email': email})
        return user, "Login successful."

    @staticmethod
    def reset_password(email: str, new_password: str):
        """
        Updates user password after successful FORGOT_PASSWORD OTP verification.
        """
        email = email.lower().strip()
        user = User.query.filter_by(email=email).first()
        if not user:
            return False, "User not found."

        user.set_password(new_password)
        db.session.commit()

        log_audit(action="PASSWORD_RESET", user_id=user.id, metadata={'email': email})
        return True, "Password reset successfully. You can now login with your new password."
