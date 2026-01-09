from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import RepairJob
from datetime import datetime, timedelta
from . import repair_bp

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
