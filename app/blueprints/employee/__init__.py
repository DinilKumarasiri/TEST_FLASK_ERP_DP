from flask import Blueprint

employee_bp = Blueprint('employee', __name__)

from . import dashboard, employees, attendance, leave, commissions, forms, barcode_attendance