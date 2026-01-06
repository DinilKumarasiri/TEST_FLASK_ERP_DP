from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from modules.models import (
    Customer, RepairJob, RepairItem, Product, StockItem, User
)
from datetime import datetime, timedelta
import random
import string

repair_bp = Blueprint('repair', __name__)

@repair_bp.route('/')
@login_required
def repair_dashboard():
    try:
        # Get repair job statistics
        total_jobs = RepairJob.query.count()
        pending_jobs = RepairJob.query.filter(
            RepairJob.status.in_(['received', 'diagnostic', 'repairing', 'waiting_parts'])
        ).count()
        completed_today = RepairJob.query.filter(
            db.func.date(RepairJob.completed_date) == datetime.utcnow().date(),
            RepairJob.status == 'completed'
        ).count()
        
        # Recent jobs
        recent_jobs = RepairJob.query.order_by(
            RepairJob.created_at.desc()
        ).limit(10).all()
        
        # Jobs assigned to current technician
        my_jobs = []
        if current_user.role == 'technician':
            my_jobs = RepairJob.query.filter_by(
                technician_id=current_user.id,
                status__in=['diagnostic', 'repairing', 'waiting_parts']
            ).order_by(RepairJob.created_at).all()
        
        # Calculate status counts
        status_counts = {
            'received': 0,
            'diagnostic': 0,
            'repairing': 0,
            'waiting_parts': 0,
            'completed': 0,
            'delivered': 0
        }
        
        for job in recent_jobs:
            if job.status in status_counts:
                status_counts[job.status] += 1
        
        return render_template('repair/dashboard.html',
                             total_jobs=total_jobs,
                             pending_jobs=pending_jobs,
                             completed_today=completed_today,
                             recent_jobs=recent_jobs,
                             my_jobs=my_jobs,
                             status_counts=status_counts,
                             title='Repair Dashboard')
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('index'))

@repair_bp.route('/technician-dashboard')
@login_required
def technician_dashboard():
    if current_user.role != 'technician':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get jobs assigned to this technician
        assigned_jobs = RepairJob.query.filter_by(
            technician_id=current_user.id
        ).order_by(
            db.case(
                [
                    (RepairJob.status == 'diagnostic', 1),
                    (RepairJob.status == 'repairing', 2),
                    (RepairJob.status == 'waiting_parts', 3),
                    (RepairJob.status == 'received', 4),
                    (RepairJob.status == 'completed', 5)
                ]
            ),
            RepairJob.created_at
        ).all()
        
        # Get completed jobs this month
        month_start = datetime(datetime.now().year, datetime.now().month, 1)
        completed_this_month = RepairJob.query.filter(
            RepairJob.technician_id == current_user.id,
            RepairJob.status == 'completed',
            RepairJob.completed_date >= month_start
        ).count()
        
        return render_template('repair/technician_dashboard.html',
                             assigned_jobs=assigned_jobs,
                             completed_this_month=completed_this_month,
                             title='Technician Dashboard')
    except Exception as e:
        flash(f'Error loading technician dashboard: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_dashboard'))

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

@repair_bp.route('/jobs')
@login_required
def job_list():
    try:
        status = request.args.get('status', 'all')
        technician_id = request.args.get('technician_id', type=int)
        
        print(f"DEBUG: status={status}, technician_id={technician_id}")
        
        query = RepairJob.query
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        if technician_id:
            query = query.filter_by(technician_id=technician_id)
        
        jobs = query.order_by(RepairJob.created_at.desc()).all()
        technicians = User.query.filter_by(role='technician', is_active=True).all()
        
        print(f"DEBUG: Found {len(jobs)} jobs, {len(technicians)} technicians")
        
        # Simple test render
        return render_template('repair/jobs.html',
                             jobs=jobs,
                             technicians=technicians,
                             status=status,
                             title='Repair Jobs')
    except Exception as e:
        print(f"DEBUG: Full error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading jobs: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_dashboard'))
    
    
    

@repair_bp.route('/job/<int:job_id>')
@login_required
def job_detail(job_id):
    try:
        # Debug: Print to console
        print(f"DEBUG: Looking for job with ID: {job_id}")
        
        job = RepairJob.query.get(job_id)
        
        if not job:
            print(f"DEBUG: Job with ID {job_id} not found")
            flash(f'Job #{job_id} not found', 'danger')
            return redirect(url_for('repair.job_list'))
        
        print(f"DEBUG: Found job: {job.job_number}")
        
        technicians = User.query.filter_by(role='technician', is_active=True).all()
        spare_parts = Product.query.filter_by(is_active=True).all()
        
        return render_template('repair/job_detail.html',
                             job=job,
                             technicians=technicians,
                             spare_parts=spare_parts,
                             title=f'Job {job.job_number}')
    except Exception as e:
        print(f"DEBUG: Error in job_detail: {str(e)}")
        flash(f'Error loading job details: {str(e)}', 'danger')
        return redirect(url_for('repair.job_list'))

@repair_bp.route('/assign-technician/<int:job_id>', methods=['POST'])
@login_required
def assign_technician(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        technician_id = request.form.get('technician_id', type=int)
        
        if technician_id:
            technician = User.query.get(technician_id)
            if technician and technician.role == 'technician':
                job.technician_id = technician_id
                job.status = 'diagnostic'
                db.session.commit()
                flash(f'Job assigned to {technician.username}', 'success')
            else:
                flash('Invalid technician', 'danger')
        else:
            job.technician_id = None
            db.session.commit()
            flash('Technician removed from job', 'info')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error assigning technician: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/update-status/<int:job_id>', methods=['POST'])
@login_required
def update_status(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        new_status = request.form.get('status')
        
        valid_statuses = ['received', 'diagnostic', 'repairing', 'waiting_parts', 'completed', 'delivered']
        
        if new_status in valid_statuses:
            job.status = new_status
            
            # Set dates based on status
            if new_status == 'completed' and not job.completed_date:
                job.completed_date = datetime.utcnow()
            elif new_status == 'delivered' and not job.delivered_date:
                job.delivered_date = datetime.utcnow()
            
            db.session.commit()
            flash(f'Status updated to {new_status}', 'success')
        else:
            flash('Invalid status', 'danger')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/add-diagnosis/<int:job_id>', methods=['POST'])
@login_required
def add_diagnosis(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        
        if current_user.role != 'technician' or current_user.id != job.technician_id:
            flash('You are not assigned to this job', 'danger')
            return redirect(url_for('repair.job_detail', job_id=job_id))
        
        diagnosis = request.form.get('diagnosis_details', '')
        estimated_cost = request.form.get('estimated_cost', type=float, default=0)
        
        job.diagnosis_details = diagnosis
        job.estimated_cost = estimated_cost or 0
        job.status = 'waiting_parts' if request.form.get('needs_parts') else 'repairing'
        
        db.session.commit()
        flash('Diagnosis added successfully', 'success')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error adding diagnosis: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/add-spare-part/<int:job_id>', methods=['POST'])
@login_required
def add_spare_part(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        
        product_id = request.form.get('product_id', type=int)
        quantity = request.form.get('quantity', type=int, default=1)
        
        product = Product.query.get(product_id)
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('repair.job_detail', job_id=job_id))
        
        # Check stock availability
        available_stock = StockItem.query.filter_by(
            product_id=product_id,
            status='available'
        ).count()
        
        if available_stock < quantity:
            flash(f'Only {available_stock} items available in stock', 'danger')
            return redirect(url_for('repair.job_detail', job_id=job_id))
        
        # Get stock items to use
        stock_items = StockItem.query.filter_by(
            product_id=product_id,
            status='available'
        ).limit(quantity).all()
        
        total_price = 0
        
        for stock_item in stock_items:
            repair_item = RepairItem(
                repair_job_id=job_id,
                product_id=product_id,
                stock_item_id=stock_item.id,
                quantity=1,
                unit_price=product.selling_price,
                total_price=product.selling_price
            )
            
            db.session.add(repair_item)
            
            # Mark stock item as used
            stock_item.status = 'used'
            
            total_price += product.selling_price
        
        # Update job cost
        job.final_cost += total_price
        
        db.session.commit()
        flash(f'{quantity} {product.name} added to job', 'success')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error adding spare part: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/customer-approval/<int:job_id>', methods=['POST'])
@login_required
def customer_approval(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        
        approval = request.form.get('approval') == 'yes'
        job.customer_approval = approval
        job.approval_date = datetime.utcnow() if approval else None
        
        if approval:
            job.status = 'repairing'
        
        db.session.commit()
        
        if approval:
            flash('Customer approval received', 'success')
        else:
            flash('Customer rejected the estimate', 'warning')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error processing approval: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/complete-job/<int:job_id>', methods=['POST'])
@login_required
def complete_job(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        repair_details = request.form.get('repair_details', '')
        warranty_period = request.form.get('warranty_period', type=int, default=0)
        
        job.repair_details = repair_details
        job.warranty_period = warranty_period or 0
        job.status = 'completed'
        job.completed_date = datetime.utcnow()
        
        db.session.commit()
        flash('Job marked as completed', 'success')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error completing job: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/deliver-job/<int:job_id>', methods=['POST'])
@login_required
def deliver_job(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        
        payment_method = request.form.get('payment_method', 'cash')
        amount_paid = request.form.get('amount_paid', type=float, default=job.final_cost or 0)
        
        # Mark as delivered
        job.status = 'delivered'
        job.delivered_date = datetime.utcnow()
        
        # TODO: Create invoice for repair job
        
        db.session.commit()
        flash('Device delivered to customer', 'success')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error delivering job: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/job-card/<int:job_id>')
@login_required
def job_card(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        return render_template('repair/job_card.html',
                             job=job,
                             title=f'Job Card - {job.job_number}')
    except Exception as e:
        flash(f'Error loading job card: {str(e)}', 'danger')
        return redirect(url_for('repair.job_list'))

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

@repair_bp.route('/warranty-jobs')
@login_required
def warranty_jobs():
    try:
        # Get jobs with warranty
        jobs = RepairJob.query.filter(
            RepairJob.warranty_period > 0,
            RepairJob.completed_date.isnot(None)
        ).order_by(RepairJob.completed_date.desc()).all()
        
        # Check warranty status for each job
        warranty_data = []
        for job in jobs:
            if job.completed_date:
                warranty_end = job.completed_date + timedelta(days=30 * job.warranty_period)
                is_active = datetime.utcnow() <= warranty_end
                
                warranty_data.append({
                    'job': job,
                    'warranty_end': warranty_end,
                    'is_active': is_active,
                    'days_remaining': (warranty_end - datetime.utcnow()).days if is_active else 0
                })
        
        return render_template('repair/warranty_jobs.html',
                             warranty_data=warranty_data,
                             title='Warranty Jobs')
    except Exception as e:
        flash(f'Error loading warranty jobs: {str(e)}', 'danger')
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

# Add a debug endpoint (but with different name to avoid conflict)
@repair_bp.route('/db-debug/jobs')
@login_required
def debug_jobs_list():
    """Debug route to see all jobs in database"""
    try:
        all_jobs = RepairJob.query.all()
        jobs_info = []
        for job in all_jobs:
            jobs_info.append({
                'id': job.id,
                'job_number': job.job_number,
                'customer': job.customer.name if job.customer else 'No customer',
                'device': f"{job.brand} {job.model}",
                'status': job.status,
                'created_at': job.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({
            'success': True,
            'total_jobs': len(all_jobs),
            'jobs': jobs_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })