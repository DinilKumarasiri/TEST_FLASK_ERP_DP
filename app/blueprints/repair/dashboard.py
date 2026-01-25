from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ... import db
from ...models import RepairJob, User
from datetime import datetime
from . import repair_bp

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
        
        # Jobs completed today for delivery
        today_deliveries = RepairJob.query.filter(
            db.func.date(RepairJob.completed_date) == datetime.utcnow().date(),
            RepairJob.status == 'completed'
        ).all()
        
        # Jobs assigned to current technician
        my_jobs = []
        if current_user.role == 'technician':
            my_jobs = RepairJob.query.filter(
                RepairJob.technician_id == current_user.id,
                RepairJob.status.in_(['diagnostic', 'repairing', 'waiting_parts'])
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
                             today_deliveries=today_deliveries,
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

@repair_bp.route('/job-card/<int:job_id>')
@login_required
def job_card(job_id):
    """Redirect to job detail page or create a print view"""
    try:
        # Instead of rendering a separate template, redirect to job detail
        return redirect(url_for('repair.job_detail', job_id=job_id))
    except Exception as e:
        flash(f'Error loading job: {str(e)}', 'danger')
        return redirect(url_for('repair.job_list'))
