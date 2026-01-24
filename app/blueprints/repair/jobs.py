from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import RepairJob, RepairItem, Product, StockItem, User
from datetime import datetime
from . import repair_bp

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
            # Check permissions
            if current_user.role == 'technician' and current_user.id != job.technician_id:
                flash('You are not assigned to this job', 'danger')
                return redirect(url_for('repair.job_detail', job_id=job_id))
            
            # Check valid status transitions
            valid_transitions = {
                'received': ['diagnostic'],
                'diagnostic': ['repairing', 'waiting_parts'],
                'repairing': ['completed', 'waiting_parts'],
                'waiting_parts': ['repairing'],
                'completed': ['delivered'],
                'delivered': []
            }
            
            if new_status not in valid_transitions.get(job.status, []):
                flash(f'Cannot change status from {job.status} to {new_status}', 'danger')
                return redirect(url_for('repair.job_detail', job_id=job_id))
            
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
