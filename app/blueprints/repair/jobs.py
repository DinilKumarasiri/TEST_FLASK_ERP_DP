from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import RepairJob, RepairItem, Product, StockItem, User, Customer
from datetime import datetime
from . import repair_bp
from datetime import datetime, timedelta  # Add timedelta here

@repair_bp.route('/jobs')
@login_required
def job_list():
    try:
        status = request.args.get('status', 'all')
        technician_id = request.args.get('technician_id', type=int)
        search_query = request.args.get('search', '').strip()
        pending_filter = request.args.get('pending', 'false') == 'true'
        
        print(f"DEBUG: status={status}, technician_id={technician_id}, search={search_query}")
        
        # Start with base query
        query = RepairJob.query
        
        # Apply status filter
        if status != 'all':
            query = query.filter_by(status=status)
        
        # Apply pending filter (all non-completed/delivered jobs)
        if pending_filter:
            query = query.filter(
                RepairJob.status.in_(['received', 'diagnostic', 'repairing', 'waiting_parts'])
            )
        
        # Apply technician filter
        if technician_id:
            query = query.filter_by(technician_id=technician_id)
        
        # Apply search filter - check if search_query exists
        if search_query and search_query.strip():
            # Create a base query with join for customer search
            from ...models import Customer  # Import Customer model
            
            # First, get all job IDs that match the search criteria
            job_ids = []
            
            # Search by job number
            jobs_by_number = RepairJob.query.filter(
                RepairJob.job_number.contains(search_query)
            ).with_entities(RepairJob.id).all()
            job_ids.extend([j.id for j in jobs_by_number])
            
            # Search by device info
            jobs_by_device = RepairJob.query.filter(
                db.or_(
                    RepairJob.brand.contains(search_query),
                    RepairJob.model.contains(search_query),
                    RepairJob.imei.contains(search_query),
                    RepairJob.serial_number.contains(search_query)
                )
            ).with_entities(RepairJob.id).all()
            job_ids.extend([j.id for j in jobs_by_device])
            
            # Search by customer info
            customers = Customer.query.filter(
                db.or_(
                    Customer.name.contains(search_query),
                    Customer.phone.contains(search_query)
                )
            ).all()
            
            if customers:
                customer_ids = [c.id for c in customers]
                jobs_by_customer = RepairJob.query.filter(
                    RepairJob.customer_id.in_(customer_ids)
                ).with_entities(RepairJob.id).all()
                job_ids.extend([j.id for j in jobs_by_customer])
            
            # Remove duplicates
            job_ids = list(set(job_ids))
            
            if job_ids:
                query = query.filter(RepairJob.id.in_(job_ids))
            else:
                # If no matches found, return empty result
                return render_template('repair/jobs.html',
                                     jobs=[],
                                     technicians=User.query.filter_by(role='technician', is_active=True).all(),
                                     status=status,
                                     title='Repair Jobs')
        
        # Order by creation date
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
        warranty_period = request.form.get('warranty_period', type=int, default=0)
        delivery_notes = request.form.get('delivery_notes', '')
        
        # Handle custom warranty
        if warranty_period == 'custom':
            custom_warranty = request.form.get('custom_warranty', type=int, default=0)
            warranty_period = custom_warranty
        
        # Mark as delivered
        job.status = 'delivered'
        job.delivered_date = datetime.utcnow()
        
        # Update warranty if provided
        if warranty_period:
            job.warranty_period = warranty_period
        
        # TODO: Create invoice for repair job with warranty info
        # Include payment_method, amount_paid, and delivery_notes in invoice
        
        db.session.commit()
        flash(f'Device delivered to customer. Warranty: {warranty_period} months', 'success')
        
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

@repair_bp.route('/file-warranty-claim/<int:job_id>', methods=['POST'])
@login_required
def file_warranty_claim(job_id):
    try:
        job = RepairJob.query.get_or_404(job_id)
        
        # Check if warranty is still valid
        if not job.delivered_date or job.warranty_period <= 0:
            flash('This job has no warranty or has not been delivered', 'danger')
            return redirect(url_for('repair.job_detail', job_id=job_id))
        
        warranty_end = job.delivered_date + timedelta(days=30 * job.warranty_period)
        if datetime.utcnow() > warranty_end:
            flash('Warranty has expired', 'danger')
            return redirect(url_for('repair.job_detail', job_id=job_id))
        
        # TODO: Create WarrantyClaim model and save claim
        # For now, just show a success message
        flash('Warranty claim submitted successfully', 'success')
        
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error filing warranty claim: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))
    


@repair_bp.route('/complete-warranty-claim/<int:job_id>', methods=['POST'])
@login_required
def complete_warranty_claim(job_id):
    try:
        claim_id = request.form.get('claim_id')
        final_status = request.form.get('final_status')
        final_resolution = request.form.get('final_resolution')
        parts_used = request.form.get('parts_used')
        customer_cost = request.form.get('customer_cost', type=float, default=0)
        
        # TODO: Complete claim logic here
        flash(f'Warranty claim #{claim_id} marked as {final_status}', 'success')
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error completing warranty claim: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))
    
@repair_bp.route('/search-repair-jobs', methods=['GET'])
@login_required
def search_repair_jobs():
    """Search repair jobs for autocomplete"""
    try:
        query = request.args.get('query', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'jobs': []})
        
        # Search repair jobs by job number, customer name, customer phone, device details
        jobs = RepairJob.query.join(Customer).filter(
            db.or_(
                RepairJob.job_number.contains(query),
                RepairJob.brand.contains(query),
                RepairJob.model.contains(query),
                RepairJob.imei.contains(query),
                Customer.name.contains(query),
                Customer.phone.contains(query)
            )
        ).limit(15).all()
        
        # Format results for autocomplete
        results = []
        for job in jobs:
            customer_name = job.customer.name if job.customer else 'N/A'
            customer_phone = job.customer.phone if job.customer else 'N/A'
            
            results.append({
                'id': job.id,
                'job_number': job.job_number,
                'customer_name': customer_name,
                'customer_phone': customer_phone,
                'device': f"{job.brand} {job.model}",
                'status': job.status,
                'status_display': job.status.title(),
                'technician': job.technician.username if job.technician else 'Unassigned'
            })
        
        return jsonify({
            'success': True,
            'jobs': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Error in repair job search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@repair_bp.route('/search-jobs', methods=['GET'])
@login_required
def search_jobs():
    """Search repair jobs for autocomplete"""
    try:
        query = request.args.get('query', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'jobs': []})
        
        from ...models import Customer  # Import Customer model
        
        # Get all jobs that match the search criteria
        jobs = []
        
        # Search by job number
        jobs_by_number = RepairJob.query.filter(
            RepairJob.job_number.contains(query)
        ).all()
        jobs.extend(jobs_by_number)
        
        # Search by device info
        jobs_by_device = RepairJob.query.filter(
            db.or_(
                RepairJob.brand.contains(query),
                RepairJob.model.contains(query),
                RepairJob.imei.contains(query),
                RepairJob.serial_number.contains(query)
            )
        ).all()
        jobs.extend(jobs_by_device)
        
        # Search by customer info
        customers = Customer.query.filter(
            db.or_(
                Customer.name.contains(query),
                Customer.phone.contains(query)
            )
        ).all()
        
        if customers:
            customer_ids = [c.id for c in customers]
            jobs_by_customer = RepairJob.query.filter(
                RepairJob.customer_id.in_(customer_ids)
            ).all()
            jobs.extend(jobs_by_customer)
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_jobs = []
        for job in jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                unique_jobs.append(job)
        
        # Limit to 10 results
        unique_jobs = unique_jobs[:10]
        
        # Format results for autocomplete
        results = []
        for job in unique_jobs:
            results.append({
                'id': job.id,
                'job_number': job.job_number,
                'customer_name': job.customer.name if job.customer else 'N/A',
                'brand': job.brand,
                'model': job.model,
                'status': job.status,
                'phone': job.customer.phone if job.customer else '',
                'device_type': job.device_type
            })
        
        return jsonify({
            'success': True,
            'jobs': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Error in job search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': 'Internal server error',
            'jobs': []
        }), 500