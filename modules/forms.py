from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, DecimalField, IntegerField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from modules.models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('technician', 'Technician')
    ], validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already exists.')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', 
                                    validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class EmployeeForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    role = SelectField('Role', choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('technician', 'Technician')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Employee')

class AttendanceForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    check_in = StringField('Check In Time', validators=[Optional()])
    check_out = StringField('Check Out Time', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('leave', 'Leave')
    ])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Attendance')

class LeaveRequestForm(FlaskForm):
    leave_type = SelectField('Leave Type', choices=[
        ('sick', 'Sick Leave'),
        ('casual', 'Casual Leave'),
        ('annual', 'Annual Leave'),
        ('emergency', 'Emergency Leave'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Submit Leave Request')

class ProductForm(FlaskForm):
    sku = StringField('SKU', validators=[DataRequired(), Length(max=50)])
    name = StringField('Product Name', validators=[DataRequired(), Length(max=200)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    purchase_price = DecimalField('Purchase Price', validators=[DataRequired(), NumberRange(min=0)])
    selling_price = DecimalField('Selling Price', validators=[DataRequired(), NumberRange(min=0)])
    wholesale_price = DecimalField('Wholesale Price', validators=[Optional(), NumberRange(min=0)])
    min_stock_level = IntegerField('Minimum Stock Level', default=5, validators=[DataRequired(), NumberRange(min=0)])
    has_imei = BooleanField('Has IMEI/Serial', default=False)
    submit = SubmitField('Save Product')

class CustomerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    address = TextAreaField('Address', validators=[Optional()])
    submit = SubmitField('Save Customer')

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired(), Length(max=100)])
    contact_person = StringField('Contact Person', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    address = TextAreaField('Address', validators=[Optional()])
    gst_number = StringField('GST Number', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Save Supplier')