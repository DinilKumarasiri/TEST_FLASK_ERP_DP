from flask import Blueprint

repair_bp = Blueprint('repair', __name__)

from . import dashboard, jobs, intake, warranty, invoices