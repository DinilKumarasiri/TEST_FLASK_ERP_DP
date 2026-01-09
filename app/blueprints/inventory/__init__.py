from flask import Blueprint

inventory_bp = Blueprint('inventory', __name__)

from . import dashboard, products, suppliers, purchase_orders, grn
