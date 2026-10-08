from functools import wraps
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.utils.responses import error_response
from app.models.user import User
from app.models.farm import Farm, FarmMember

def role_required(*allowed_roles):
    """Decorator to enforce role-based access control (RBAC)."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            if not user or not user.is_active:
                return error_response("User account is inactive or not found", status_code=401)
            
            # Admins always have access to resources; otherwise check allowed roles
            if user.role != 'ADMIN' and user.role not in allowed_roles:
                return error_response("You do not have permission to access this resource", status_code=403)
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def farm_access_required(fn):
    """
    Decorator to verify that the authenticated user owns or belongs to the requested farm.
    Reads farm_id from JSON payload, query parameters, or url kwargs.
    If an ADMIN requests without specifying farm_id, auto-resolves to their primary/system farm.
    """
    @wraps(fn)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())

        user = User.query.get(user_id)
        if not user or not user.is_active:
            return error_response("User account is inactive or not found", status_code=401)

        # Locate farm_id from kwargs, query params, or JSON body
        farm_id = kwargs.get('farm_id')
        if not farm_id:
            farm_id = request.args.get('farm_id')
        if not farm_id and request.is_json:
            farm_data = request.get_json(silent=True, force=False)
            if isinstance(farm_data, dict):
                farm_id = farm_data.get('farm_id')

        # If route belongs to 'farms' blueprint, kwargs['id'] is farm_id
        if not farm_id and request.blueprint == 'farms' and 'id' in kwargs:
            farm_id = kwargs.get('id')

        # If route has an entity 'id', look up farm_id from the entity
        if not farm_id and 'id' in kwargs:
            entity_id = kwargs.get('id')
            if request.blueprint == 'customers':
                from app.models.customer import Customer
                c = Customer.query.get(entity_id)
                if c:
                    farm_id = c.farm_id
            elif request.blueprint == 'animals':
                from app.models.animal import Animal
                a = Animal.query.get(entity_id)
                if a:
                    farm_id = a.farm_id
            elif request.blueprint == 'bills':
                from app.models.bill import CustomerBill
                b = CustomerBill.query.get(entity_id)
                if b:
                    farm_id = b.farm_id

        # If admin didn't specify farm_id, resolve to their primary farm or system default
        if not farm_id and user.role == 'ADMIN':
            primary = user.farms.first() or (user.memberships.first().farm if user.memberships.first() else None) or Farm.query.filter_by(is_active=True).first()
            if primary:
                farm_id = primary.id

        if not farm_id:
            return error_response("Missing farm_id identifier", status_code=400)

        try:
            farm_id = int(farm_id)
        except (ValueError, TypeError):
            return error_response("Invalid farm_id identifier", status_code=400)
        except (ValueError, TypeError):
            return error_response("Invalid farm_id identifier", status_code=400)

        # Verify farm exists and is active
        farm = Farm.query.get(farm_id)
        if not farm or not farm.is_active:
            return error_response("Farm not found or inactive", status_code=404)

        # Full unrestricted access for Admin across the entire application once farm_id is resolved
        if user.role == 'ADMIN':
            request.environ['dairy_farm_id'] = farm_id
            return fn(*args, **kwargs)

        if farm.owner_id == user_id:
            request.environ['dairy_farm_id'] = farm_id
            return fn(*args, **kwargs)

        member = FarmMember.query.filter_by(farm_id=farm_id, user_id=user_id).first()
        if not member:
            return error_response("Access denied: You are not a member of this farm", status_code=403)

        request.environ['dairy_farm_id'] = farm_id
        return fn(*args, **kwargs)
    return decorator
