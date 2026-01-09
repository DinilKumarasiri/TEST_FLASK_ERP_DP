from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import Customer, RepairJob
from datetime import datetime
import random
import string
from . import repair_bp

def generate_job_number():
    """Generate unique repair job number"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=4))
    job_number = f'RJ-{date_str}-{random_str}'
    
    # Check if exists
    while RepairJob.query.filter_by(job_number=job_number).first():
        random_str = ''.join(random.choices(string.digits, k=4))
        job_number = f'RJ-{date_str}-{random_str}'
    
    return job_number

@repair_bp.route('/intake', methods=['GET', 'POST'])
@login_required
def device_intake():
    try:
        if request.method == 'POST':
            # Create or find customer
            customer_phone = request.form.get('customer_phone', '').strip()
            customer = Customer.query.filter_by(phone=customer_phone).first()
            
            if not customer:
                customer = Customer(
                    name=request.form.get('customer_name', ''),
                    phone=customer_phone,
                    email=request.form.get('customer_email', ''),
                    address=request.form.get('customer_address', '')
                )
                db.session.add(customer)
                db.session.flush()
            
            # Generate job number
            job_number = generate_job_number()
            
            # Create repair job
            repair_job = RepairJob(
                job_number=job_number,
                customer_id=customer.id,
                device_type=request.form.get('device_type', 'mobile'),
                brand=request.form.get('brand', ''),
                model=request.form.get('model', ''),
                imei=request.form.get('imei', ''),
                serial_number=request.form.get('serial_number', ''),
                issue_description=request.form.get('issue_description', ''),
                accessories_received=request.form.get('accessories_received', ''),
                estimated_cost=float(request.form.get('estimated_cost', 0) or 0),
                status='received',
                created_by=current_user.id
            )
            
            db.session.add(repair_job)
            db.session.commit()
            
            flash(f'Device intake successful. Job Number: {job_number}', 'success')
            return redirect(url_for('repair.job_detail', job_id=repair_job.id))
        
        return render_template('repair/device_intake.html', title='Device Intake')
    except Exception as e:
        flash(f'Error in device intake: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_dashboard'))

@repair_bp.route('/test/create-job')
@login_required
def create_test_job():
    """Create a test repair job for debugging"""
    try:
        # Check if we have a customer
        customer = Customer.query.first()
        if not customer:
            # Create a test customer
            customer = Customer(
                name='Test Customer',
                phone='1234567890',
                email='test@example.com'
            )
            db.session.add(customer)
            db.session.flush()
        
        # Generate job number
        job_number = generate_job_number()
        
        # Create test repair job
        job = RepairJob(
            job_number=job_number,
            customer_id=customer.id,
            device_type='mobile',
            brand='Apple',
            model='iPhone 13',
            issue_description='Screen not working, needs replacement',
            estimated_cost=150.00,
            status='received',
            created_by=current_user.id
        )
        
        db.session.add(job)
        db.session.commit()
        
        flash(f'Test job created: {job_number} (ID: {job.id})', 'success')
        return redirect(url_for('repair.job_detail', job_id=job.id))
    except Exception as e:
        flash(f'Error creating test job: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_dashboard'))

@repair_bp.route('/find-customer', methods=['POST'])
@login_required
def find_customer():
    try:
        phone = request.json.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'message': 'Phone number required'})
        
        customer = Customer.query.filter_by(phone=phone).first()
        
        if customer:
            # Count repair jobs for this customer
            repair_count = RepairJob.query.filter_by(customer_id=customer.id).count()
            
            customer_data = {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'address': customer.address,
                'repair_count': repair_count
            }
            return jsonify({'success': True, 'customer': customer_data})
        
        return jsonify({'success': False, 'message': 'Customer not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
