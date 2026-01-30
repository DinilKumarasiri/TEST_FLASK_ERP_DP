from flask import render_template, session
from flask_login import login_required, current_user
from ... import db
from ...models import Product, StockItem, Invoice, ProductCategory
from datetime import datetime
from . import pos_bp
from ...utils.permissions import staff_required

@pos_bp.route('/')
@login_required
def pos_home():
    """Main POS page"""
    # Clear any existing cart in session
    if 'cart' in session:
        session.pop('cart')
    
    categories = ProductCategory.query.all()
    products = Product.query.filter_by(is_active=True).all()
    
    return render_template('pos/pos.html', 
                         categories=categories,
                         products=products,
                         title='POS Terminal')

@pos_bp.route('/dashboard')
@login_required
@staff_required  # Only staff and admin can access
def dashboard():
    """POS Dashboard"""
    # Get today's sales summary
    today = datetime.utcnow().date()
    
    today_invoices = Invoice.query.filter(
        db.func.date(Invoice.date) == today
    ).all()
    
    today_sales = sum(inv.total for inv in today_invoices)
    today_transactions = len(today_invoices)
    today_cash = sum(inv.total for inv in today_invoices if inv.payment_method == 'cash')
    
    # Get low stock products
    low_stock_products = []
    for product in Product.query.filter_by(is_active=True).all():
        stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
        
        if stock_count <= product.min_stock_level:
            low_stock_products.append({
                'product': product,
                'stock_count': stock_count
            })
    
    # Get recent transactions
    recent_invoices = Invoice.query.order_by(
        Invoice.date.desc()
    ).limit(10).all()
    
    return render_template('pos/dashboard.html',
                         now=datetime.utcnow(),
                         today_sales=today_sales,
                         today_transactions=today_transactions,
                         today_cash=today_cash,
                         low_stock_products=low_stock_products,
                         recent_invoices=recent_invoices,
                         title='Dashboard')


