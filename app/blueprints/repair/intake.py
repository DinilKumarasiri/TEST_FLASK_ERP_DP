from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import Customer, RepairJob
from datetime import datetime
import random
import string
from . import repair_bp

def generate_job_number():
    last_job = RepairJob.query.order_by(RepairJob.id.desc()).first()

    if last_job and last_job.job_number:
        last_number = int(last_job.job_number.split('-')[1])
        next_number = last_number + 1
    else:
        next_number = 1

    job_number = f"RJ-{next_number:06d}"
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

@repair_bp.route('/search-customers', methods=['GET'])
@login_required
def search_customers():
    """Search customers by phone, name, or email for autocomplete"""
    try:
        query = request.args.get('query', '').strip()
        field = request.args.get('field', 'phone')  # 'phone', 'name', or 'email'
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'customers': []})
        
        # Clean the query based on field type
        if field == 'phone':
            # Remove non-digits for phone search
            clean_query = ''.join(filter(str.isdigit, query))
            if not clean_query:
                return jsonify({'success': True, 'customers': []})
            
            # Search for phone matches
            customers = Customer.query.filter(
                Customer.phone.contains(clean_query)
            ).limit(10).all()
            
        elif field == 'name':
            # Search for name matches (case-insensitive)
            customers = Customer.query.filter(
                Customer.name.ilike(f'%{query}%')
            ).limit(10).all()
            
        elif field == 'email':
            # Search for email matches (case-insensitive)
            customers = Customer.query.filter(
                Customer.email.ilike(f'%{query}%')
            ).limit(10).all()
        else:
            return jsonify({'success': True, 'customers': []})
        
        # Format results for autocomplete
        results = []
        for customer in customers:
            # Format phone number nicely
            phone_display = customer.phone
            if len(customer.phone) >= 10:
                phone_display = f"{customer.phone[:3]}-{customer.phone[3:6]}-{customer.phone[6:]}"
            
            results.append({
                'phone': customer.phone,
                'phone_display': phone_display,
                'name': customer.name,
                'email': customer.email or '',
                'address': customer.address or '',
                'id': customer.id
            })
        
        return jsonify({
            'success': True,
            'customers': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Error in customer search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': 'Internal server error',
            'customers': []
        }), 500