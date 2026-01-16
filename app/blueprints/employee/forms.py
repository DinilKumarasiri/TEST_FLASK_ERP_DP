# app/blueprints/employee/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DateField, FloatField, IntegerField, EmailField, TelField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from datetime import datetime, date

class EmployeeForm(FlaskForm):
    # Basic Information
    username = StringField('Username *', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters')
    ])
    email = EmailField('Work Email *', validators=[
        DataRequired(message='Email is required'),
        Email(message='Enter a valid email address'),
        Length(max=120)
    ])
    password = PasswordField('Password *', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm Password *', validators=[
        DataRequired(message='Please confirm password'),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('System Role *', choices=[
        ('', 'Select Role'),
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('staff', 'Sales Staff'),
        ('technician', 'Technician')
    ], validators=[DataRequired(message='Please select a role')])
    is_active = BooleanField('Active Account', default=True)

    # Personal Information
    full_name = StringField('Full Name *', validators=[
        DataRequired(message='Full name is required'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    gender = SelectField('Gender', choices=[
        ('', 'Select Gender'),
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], validators=[Optional()])
    personal_phone = TelField('Personal Phone', validators=[
        Optional(),
        Length(min=10, max=15, message='Phone number must be between 10 and 15 digits')
    ])
    personal_email = EmailField('Personal Email', validators=[
        Optional(),
        Email(message='Enter a valid email address'),
        Length(max=120)
    ])
    
    # Emergency Contact
    emergency_contact = StringField('Emergency Contact Name', validators=[
        Optional(),
        Length(max=100)
    ])
    emergency_phone = TelField('Emergency Contact Phone', validators=[
        Optional(),
        Length(min=10, max=15, message='Phone number must be between 10 and 15 digits')
    ])
    
    # Address Information
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    
    # Government IDs
    aadhar_number = StringField('Aadhar Number', validators=[
        Optional(),
        Length(min=12, max=12, message='Aadhar number must be 12 digits')
    ])
    pan_number = StringField('PAN Number', validators=[
        Optional(),
        Length(min=10, max=10, message='PAN number must be 10 characters')
    ])
    
    # Employment Details
    employee_code = StringField('Employee Code', validators=[Optional(), Length(max=50)])
    job_title = SelectField('Job Title *', choices=[
        ('', 'Select Job Title'),
        ('sales_executive', 'Sales Executive'),
        ('senior_sales_executive', 'Senior Sales Executive'),
        ('sales_manager', 'Sales Manager'),
        ('repair_technician', 'Repair Technician'),
        ('senior_technician', 'Senior Technician'),
        ('repair_manager', 'Repair Manager'),
        ('store_manager', 'Store Manager'),
        ('inventory_manager', 'Inventory Manager'),
        ('cashier', 'Cashier'),
        ('accountant', 'Accountant')
    ], validators=[DataRequired(message='Please select a job title')])
    department = SelectField('Department *', choices=[
        ('', 'Select Department'),
        ('sales', 'Sales'),
        ('repair', 'Repair Service'),
        ('inventory', 'Inventory'),
        ('admin', 'Administration'),
        ('accounts', 'Accounts')
    ], validators=[DataRequired(message='Please select a department')])
    employment_type = SelectField('Employment Type *', choices=[
        ('', 'Select Employment Type'),
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Intern')
    ], validators=[DataRequired(message='Please select employment type')])
    date_of_joining = DateField('Date of Joining *', format='%Y-%m-%d', validators=[DataRequired(message='Date of joining is required')])
    probation_end_date = DateField('Probation End Date', format='%Y-%m-%d', validators=[Optional()])
    work_location = StringField('Work Location/Shop', validators=[Optional(), Length(max=200)])
    shift_timing = StringField('Shift Timing', validators=[Optional(), Length(max=50)])
    reporting_manager_id = SelectField('Reporting Manager', coerce=int, choices=[], validators=[Optional()])
    
    # Salary & Compensation
    basic_salary = FloatField('Basic Salary (Rs.)', validators=[
        Optional(),
        NumberRange(min=0, message='Salary cannot be negative')
    ])
    commission_rate = FloatField('Commission Rate (%)', validators=[
        Optional(),
        NumberRange(min=0, max=100, message='Commission rate must be between 0 and 100')
    ], default=5.0)
    
    # Banking Information
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    account_number = StringField('Account Number', validators=[Optional()])
    ifsc_code = StringField('IFSC Code', validators=[Optional()])
    
    # Skills & Qualifications
    education = TextAreaField('Education Details', validators=[Optional(), Length(max=1000)])
    certifications = TextAreaField('Certifications', validators=[Optional(), Length(max=1000)])
    skills = TextAreaField('Technical Skills', validators=[Optional(), Length(max=1000)])
    experience_years = IntegerField('Total Experience (Years)', validators=[
        Optional(),
        NumberRange(min=0, max=50, message='Experience must be between 0 and 50 years')
    ])
    
    # Sales Staff Specific
    sales_target_monthly = FloatField('Monthly Sales Target (Rs.)', validators=[
        Optional(),
        NumberRange(min=0, message='Sales target cannot be negative')
    ])

    def validate_date_of_birth(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('Date of birth cannot be in the future.')

    def validate_date_of_joining(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('Date of joining cannot be in the future.')

class EditEmployeeForm(EmployeeForm):
    password = PasswordField('New Password', validators=[
        Optional(),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('password', message='Passwords must match')
    ])
    
    def __init__(self, *args, **kwargs):
        super(EditEmployeeForm, self).__init__(*args, **kwargs)
        # Remove required validators for username and email in edit mode
        self.username.validators = [DataRequired(), Length(min=3, max=80)]
        self.email.validators = [DataRequired(), Email(), Length(max=120)]

class LeaveRequestForm(FlaskForm):
    leave_type = SelectField('Leave Type *', choices=[
        ('casual', 'Casual Leave'),
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    start_date = DateField('Start Date *', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date *', format='%Y-%m-%d', validators=[DataRequired()])
    reason = TextAreaField('Reason *', validators=[
        DataRequired(),
        Length(min=10, max=500)
    ])
    
    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError('End date must be after start date.')