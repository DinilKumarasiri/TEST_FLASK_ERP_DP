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

# Make sure all routes are imported
__all__ = ['inventory_bp']