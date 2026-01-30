from flask import Blueprint

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

# Import all routes
from . import (
    dashboard,
    products,
    purchase_orders,
    suppliers,
    grn
)

# Import permissions
from app.utils.permissions import staff_required

# Apply staff_required decorator to all routes that need staff or admin access
# (This is a structural change - individual routes will be decorated separately)

__all__ = ['inventory_bp']