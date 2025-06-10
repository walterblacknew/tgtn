from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from extentions import db, login_manager
from models import (
    User, Route, RoutePoint, RouteAssignment,
    Store, EvaluationParameter, StoreEvaluation, StoreEvaluationDetail, QuotaCategory,
    CustomerReport, RouteReport, GradeMapping, CustomerEvaluation, DescriptiveCriterion,
    CSVEvaluationRecord, Province, ProvinceTarget
)
from forms import (
    LoginForm, UserForm, RouteForm, RoutePointForm,
    StoreForm, EvaluationParameterForm, StoreEvaluationForm, QuotaCategoryForm,
    GradeMappingForm, CustomerEvaluationForm, TargetSettingForm
)
from models import (
    User, Route, RoutePoint, RouteAssignment,
    Store, EvaluationParameter, StoreEvaluation, StoreEvaluationDetail, QuotaCategory,
    CustomerReport, RouteReport, GradeMapping, CustomerEvaluation, DescriptiveCriterion,
    CSVEvaluationRecord, Province, ProvinceTarget, Product, ProductProvinceTarget,
    ProductCategory, ProductFlavor, ProductPackaging, ProductVolume, # Add these new models
)
from forms import (
    LoginForm, UserForm, RouteForm, RoutePointForm,
    StoreForm, EvaluationParameterForm, StoreEvaluationForm, QuotaCategoryForm,
    GradeMappingForm, CustomerEvaluationForm, TargetSettingForm, ProductForm, StoreTypeForm, ProductExclusionForm, StoreTypeAllocationForm  # Add ProductForm here
)
from models import (
    User, Route, RoutePoint, RouteAssignment,
    Store, EvaluationParameter, StoreEvaluation, StoreEvaluationDetail, QuotaCategory,
    CustomerReport, RouteReport, GradeMapping, CustomerEvaluation, DescriptiveCriterion,
    CSVEvaluationRecord, Province, ProvinceTarget, UserHierarchy, Product, ProductCategory,
    ProductFlavor, ProductPackaging, ProductVolume, ProductProvinceTarget, BatchGradeTarget, StoreType, ProductExclusionRule, StoreTypeAllocation
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, desc, text
from datetime import datetime, timezone
import csv
import io
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from datetime import datetime, timezone, timedelta
from models import ProvinceTarget
# Add this to the imports section at the top of your app.py file
import json
import os
import tempfile
import uuid
import time
from flask import make_response, send_file
import csv
from io import StringIO, BytesIO
import pandas as pd
from werkzeug.utils import secure_filename
import tempfile  # Also needed for the Excel file handling
def create_admin_user():
    """Ensure an admin user named 'admin' exists."""
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        new_admin = User(
            username='admin',
            password=generate_password_hash('adminpassword'),
            role='admin',
            email='admin@example.com',
            fullname='مدیر سیستم',
            is_active=True
        )
        db.session.add(new_admin)
        db.session.commit()

def safe_float(val):
    """Convert a value to float safely; return None if conversion fails."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        create_admin_user()

    @login_manager.user_loader
    def load_user(user_id):
        # Use Session.get() instead of Query.get()
        return db.session.get(User, int(user_id))

    # --------------------- LOGIN / LOGOUT ---------------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user)
                flash('خوش آمدید!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('با موفقیت خارج شدید.', 'info')
        return redirect(url_for('login'))

    # --------------------- DASHBOARD ---------------------
    @app.route('/')
    @login_required
    def dashboard():
        if current_user.role == 'admin':
            return redirect(url_for('admin_index'))
        elif current_user.role == 'observer':
            return redirect(url_for('observer_index'))
        else:
            return redirect(url_for('marketer_index'))

    # --------------------- ADMIN SECTION ---------------------
    @app.route('/admin', methods=['GET'])
    @login_required
    def admin_index():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        route_reports = RouteReport.query.all()
        route_data = [{
            'شماره_مسیر': r.route_number,
            'نام_مسیر': r.route_name,
            'تعداد_مشتری': r.number_of_customers,
            'واسط_کارمند': r.employee_intermediary,
            'مرکز_فروش': r.sales_center,
            'تاریخ_ایجاد': r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for r in route_reports]
        customer_reports = CustomerReport.query.all()
        customer_data = [{
            'Textbox29': c.textbox29,
            'Caption': c.caption,
            'bname': c.bname,
            'Number': c.number,
            'Name': c.name,
            'Textbox16': c.textbox16,
            'Textbox12': c.textbox12,
            'Longitude': c.longitude,
            'Latitude': c.latitude,
            'Textbox4': c.textbox4,
            'Textbox10': c.textbox10,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customer_reports]
        return render_template('admin/index.html', route_data=route_data, customer_data=customer_data)

    @app.route('/admin/data')
    @login_required
    def admin_data():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/data.html')

    # --------------------- CSV UPLOAD (Existing) ---------------------
    @app.route('/admin/upload_route_csv', methods=['POST'])
    @login_required
    def admin_upload_route_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('admin_routes_csv'))
        file = request.files.get('route_csv')
        if not file:
            flash('هیچ فایلی انتخاب نشده است.', 'danger')
            return redirect(url_for('admin_routes_csv'))
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            for row in csv_reader:
                report = RouteReport(
                    route_number=row.get('شماره_مسیر'),
                    route_name=row.get('نام_مسیر'),
                    number_of_customers=int(row.get('تعداد_مشتری')) if row.get('تعداد_مشتری') else None,
                    employee_intermediary=row.get('واسط_کارمند'),
                    sales_center=row.get('مرکز_فروش'),
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(report)
            db.session.commit()
            flash('فایل CSV اطلاعات مسیر با موفقیت بارگذاری و ذخیره شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در پردازش فایل CSV: {e}', 'danger')
        return redirect(url_for('admin_routes_csv'))

    @app.route('/admin/upload_customer_csv', methods=['POST'])
    @login_required
    def admin_upload_customer_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('admin_customers_csv'))

        file = request.files.get('customer_csv')
        province = request.form.get('province')

        if not file:
            flash('هیچ فایلی انتخاب نشده است.', 'danger')
            return redirect(url_for('admin_customers_csv'))

        if not province:
            flash('لطفاً استان را انتخاب کنید.', 'danger')
            return redirect(url_for('admin_customers_csv'))

        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)

            for row in csv_reader:
                report = CustomerReport(
                    textbox29=row.get('Textbox29'),
                    caption=row.get('Caption'),
                    bname=row.get('bname'),
                    number=row.get('Number'),
                    name=row.get('Name'),
                    textbox16=row.get('Textbox16'),
                    textbox12=row.get('Textbox12'),
                    longitude=safe_float(row.get('Longitude')),
                    latitude=safe_float(row.get('Latitude')),
                    textbox4=row.get('Textbox4'),
                    textbox10=row.get('Textbox10'),
                    province=province,  # Add the province
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(report)

            db.session.commit()
            flash(f'فایل CSV اطلاعات مشتریان برای استان {province} با موفقیت بارگذاری و ذخیره شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در پردازش فایل CSV: {e}', 'danger')
        return redirect(url_for('admin_customers_csv'))

    @app.route('/admin/customers-csv/preview/<province>')
    @login_required
    def preview_province_customers(province):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of records per page

        customers = CustomerReport.query.filter_by(province=province) \
            .order_by(CustomerReport.created_at.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        customer_data = [{
            'Textbox29': c.textbox29,
            'Caption': c.caption,
            'bname': c.bname,
            'Number': c.number,
            'Name': c.name,
            'Textbox16': c.textbox16,
            'Textbox12': c.textbox12,
            'Longitude': c.longitude,
            'Latitude': c.latitude,
            'Textbox4': c.textbox4,
            'Textbox10': c.textbox10,
            'Province': c.province,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customers.items]

        return jsonify({
            'data': customer_data,
            'total': customers.total,
            'pages': customers.pages,
            'current_page': customers.page
        })

    @app.route('/admin/customers-csv/province/<province>/delete', methods=['POST'])
    @login_required
    def delete_province_customers(province):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        try:
            CustomerReport.query.filter_by(province=province).delete()
            db.session.commit()
            flash(f'تمام رکوردهای استان {province} با موفقیت حذف شدند.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف رکوردها: {e}', 'danger')

        return redirect(url_for('admin_customers_csv'))

    def upgrade_customer_report():
        """Add province column to customer_report table"""
        with app.app_context():
            # Add the province column if it doesn't exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('customer_report')]

            if 'province' not in columns:
                # Create the province column
                db.engine.execute('ALTER TABLE customer_report ADD COLUMN province VARCHAR(100)')

                # Set default province for existing records
                db.engine.execute("UPDATE customer_report SET province = 'نامشخص' WHERE province IS NULL")

                db.session.commit()

    @app.route('/admin/customers-csv/province/<province>')
    @login_required
    def get_province_customers(province):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        customers = CustomerReport.query.filter_by(province=province).all()
        customer_data = [{
            'Textbox29': c.textbox29,
            'Caption': c.caption,
            'bname': c.bname,
            'Number': c.number,
            'Name': c.name,
            'Textbox16': c.textbox16,
            'Textbox12': c.textbox12,
            'Longitude': c.longitude,
            'Latitude': c.latitude,
            'Textbox4': c.textbox4,
            'Textbox10': c.textbox10,
            'Province': c.province,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customers]

        return jsonify(customer_data)



    # --------------------- FULL-SCREEN CSV PAGES (Existing) ---------------------
    @app.route('/admin/routes-csv', methods=['GET'])
    @login_required
    def admin_routes_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        route_reports = RouteReport.query.all()
        route_data = [{
            'شماره_مسیر': r.route_number,
            'نام_مسیر': r.route_name,
            'تعداد_مشتری': r.number_of_customers,
            'واسط_کارمند': r.employee_intermediary,
            'مرکز_فروش': r.sales_center,
            'تاریخ_ایجاد': r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for r in route_reports]
        return render_template('admin/routes_csv.html', route_data=route_data)

    @app.route('/admin/customers-csv', methods=['GET'])
    @login_required
    def admin_customers_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        try:
            # Create provinces if they don't exist
            if Province.query.count() == 0:
                provinces_data = [
                    ("مرکز فروش تهران", 13267637),
                    ("مرکز فروش خراسان رضوی", 6434501),
                    ("مرکز فروش اصفهان", 5120850),
                    ("مرکز فروش شیراز", 4851274),
                    ("مرکز فروش خوزستان", 4710509),
                    ("مرکز فروش آذربایجان ", 3909652),
                    ("مرکز فروش مازندران", 3283582),
                    ("مرکز فروش آذربایجان غربی", 3265219),
                    ("مرکز فروش کرمان", 3164718),
                    ("مرکز فروش سیستان و بلوچستان", 2775014),
                    ("مرکز فروش البرز", 2712400),
                    ("مرکز فروش گیلان", 2530696),
                    ("مرکز فروش کرمانشاه", 1952434),
                    ("مرکز فروش لرستان", 1760649),
                    ("مرکز فروش همدان", 1738234),
                    ("مرکز فروش گلستان", 1777014),
                    ("مرکز فروش کردستان", 1603011),
                    ("مرکز فروش هرمزگان", 1578183),
                    ("مرکز فروش مرکزی", 1429475),
                    ("مرکز فروش اردبیل", 1270420),
                    ("مرکز فروش قزوین", 1201565),
                    ("مرکز فروش قم", 1151672),
                    ("مرکز فروش یزد", 1074428),
                    ("مرکز فروش زنجان", 1015734),
                    ("مرکز فروش بوشهر", 1032949),
                    ("مرکز فروش چهار محال و بختیاری", 895263),
                    ("مرکز فروش خراسان شمالی", 867727),
                    ("مرکز فروش کهکولویه و بویراحد", 658629),
                    ("مرکز فروش خراسان جنوبی", 622534),
                    ("مرکز فروش سمنان", 631218),
                    ("مرکز فروش ایلام", 557599)
                ]

                for name, population in provinces_data:
                    province = Province(name=name, population=population)
                    db.session.add(province)

                try:
                    db.session.commit()
                    print("Provinces initialized successfully")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error initializing provinces: {e}")
                    flash('خطا در ایجاد استان‌ها', 'danger')

            # Get all provinces for the dropdown
            provinces = Province.query.order_by(Province.name).all()
            print(f"Found {len(provinces)} provinces")
            for p in provinces:
                print(f"Province: {p.name}")

            # Get all customer reports
            all_customers = CustomerReport.query.all()
            print(f"Found {len(all_customers)} customers")

            # Group data by province
            customer_data_by_province = {}
            column_headers = []

            if all_customers:
                # Get headers from first record
                sample_data = {
                    'Textbox29': all_customers[0].textbox29,
                    'Caption': all_customers[0].caption,
                    'bname': all_customers[0].bname,
                    'Number': all_customers[0].number,
                    'Name': all_customers[0].name,
                    'Textbox16': all_customers[0].textbox16,
                    'Textbox12': all_customers[0].textbox12,
                    'Longitude': all_customers[0].longitude,
                    'Latitude': all_customers[0].latitude,
                    'Textbox4': all_customers[0].textbox4,
                    'Textbox10': all_customers[0].textbox10,
                    'Province': all_customers[0].province,
                    'تاریخ_ایجاد': all_customers[0].created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                column_headers = list(sample_data.keys())

                # Group by province
                for customer in all_customers:
                    province_name = customer.province or 'نامشخص'

                    if province_name not in customer_data_by_province:
                        customer_data_by_province[province_name] = []

                    customer_data = {
                        'Textbox29': customer.textbox29,
                        'Caption': customer.caption,
                        'bname': customer.bname,
                        'Number': customer.number,
                        'Name': customer.name,
                        'Textbox16': customer.textbox16,
                        'Textbox12': customer.textbox12,
                        'Longitude': customer.longitude,
                        'Latitude': customer.latitude,
                        'Textbox4': customer.textbox4,
                        'Textbox10': customer.textbox10,
                        'Province': customer.province,
                        'تاریخ_ایجاد': customer.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    customer_data_by_province[province_name].append(customer_data)

            return render_template(
                'admin/customers_csv.html',
                provinces=provinces,
                customer_data_by_province=customer_data_by_province,
                column_headers=column_headers
            )
        except Exception as e:
            print(f"Error in admin_customers_csv: {str(e)}")
            flash(f'خطا در بارگذاری صفحه: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    @app.route('/admin/customers-csv/map')
    @login_required
    def admin_customers_csv_map():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        customer_reports = CustomerReport.query.all()
        customer_data = [{
            'Textbox29': c.textbox29,
            'Caption': c.caption,
            'bname': c.bname,
            'Number': c.number,
            'Name': c.name,
            'Textbox16': c.textbox16,
            'Textbox12': c.textbox12,
            'Longitude': c.longitude,
            'Latitude': c.latitude,
            'Textbox4': c.textbox4,
            'Textbox10': c.textbox10,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customer_reports]
        return render_template('admin/customers_map.html', customer_data=customer_data)

    @app.route('/admin/products', methods=['GET', 'POST'])
    @login_required
    def admin_products():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        form = ProductForm()

        # Populate select fields with existing options
        form.category_id.choices = [(0, '-- انتخاب دسته بندی --')] + [
            (c.id, c.name) for c in ProductCategory.query.order_by(ProductCategory.name).all()
        ]
        form.flavor_id.choices = [(0, '-- انتخاب طعم --')] + [
            (f.id, f.name) for f in ProductFlavor.query.order_by(ProductFlavor.name).all()
        ]
        form.packaging_id.choices = [(0, '-- انتخاب بسته بندی --')] + [
            (p.id, p.name) for p in ProductPackaging.query.order_by(ProductPackaging.name).all()
        ]
        form.volume_id.choices = [(0, '-- انتخاب حجم --')] + [
            (v.id, v.display_name) for v in ProductVolume.query.order_by(ProductVolume.value).all()
        ]

        if form.validate_on_submit():
            # Handle category (either new or existing)
            category_id = None
            if form.new_category.data and form.new_category.data.strip():
                # Create new category
                new_category = ProductCategory(name=form.new_category.data.strip())
                try:
                    db.session.add(new_category)
                    db.session.flush()  # Get ID without committing
                    category_id = new_category.id
                except IntegrityError:
                    db.session.rollback()
                    # If category already exists, find its ID
                    existing_category = ProductCategory.query.filter_by(name=form.new_category.data.strip()).first()
                    if existing_category:
                        category_id = existing_category.id
            elif form.category_id.data and form.category_id.data != 0:
                category_id = form.category_id.data

            # Handle flavor (either new or existing)
            flavor_id = None
            if form.new_flavor.data and form.new_flavor.data.strip():
                # Create new flavor
                new_flavor = ProductFlavor(name=form.new_flavor.data.strip())
                try:
                    db.session.add(new_flavor)
                    db.session.flush()
                    flavor_id = new_flavor.id
                except IntegrityError:
                    db.session.rollback()
                    existing_flavor = ProductFlavor.query.filter_by(name=form.new_flavor.data.strip()).first()
                    if existing_flavor:
                        flavor_id = existing_flavor.id
            elif form.flavor_id.data and form.flavor_id.data != 0:
                flavor_id = form.flavor_id.data

            # Handle packaging (either new or existing)
            packaging_id = None
            if form.new_packaging.data and form.new_packaging.data.strip():
                new_packaging = ProductPackaging(name=form.new_packaging.data.strip())
                try:
                    db.session.add(new_packaging)
                    db.session.flush()
                    packaging_id = new_packaging.id
                except IntegrityError:
                    db.session.rollback()
                    existing_packaging = ProductPackaging.query.filter_by(name=form.new_packaging.data.strip()).first()
                    if existing_packaging:
                        packaging_id = existing_packaging.id
            elif form.packaging_id.data and form.packaging_id.data != 0:
                packaging_id = form.packaging_id.data

            # Handle volume (either new or existing)
            volume_id = None
            if form.new_volume.data:
                unit = form.volume_unit.data.strip() or 'لیتر'
                new_volume = ProductVolume(value=form.new_volume.data, unit=unit)
                try:
                    db.session.add(new_volume)
                    db.session.flush()
                    volume_id = new_volume.id
                except IntegrityError:
                    db.session.rollback()
                    existing_volume = ProductVolume.query.filter_by(value=form.new_volume.data, unit=unit).first()
                    if existing_volume:
                        volume_id = existing_volume.id
            elif form.volume_id.data and form.volume_id.data != 0:
                volume_id = form.volume_id.data

            # Create the product
            product = Product(
                name=form.name.data.strip(),
                category_id=category_id,
                flavor_id=flavor_id,
                packaging_id=packaging_id,
                volume_id=volume_id,
                liter_capacity=form.liter_capacity.data,
                shrink_capacity=form.shrink_capacity.data
            )

            try:
                db.session.add(product)
                db.session.commit()

                # Calculate province targets if provinces exist
                provinces = Province.query.all()
                if provinces and (form.liter_capacity.data or form.shrink_capacity.data):
                    # Calculate total population
                    total_population = sum(province.population for province in provinces)

                    for province in provinces:
                        percentage = province.population / total_population

                        product_target = ProductProvinceTarget(
                            product_id=product.id,
                            province_id=province.id,
                            liter_capacity=product.liter_capacity * percentage if product.liter_capacity else None,
                            shrink_capacity=product.shrink_capacity * percentage if product.shrink_capacity else None,
                            liter_percentage=percentage * 100 if product.liter_capacity else None,
                            shrink_percentage=percentage * 100 if product.shrink_capacity else None
                        )
                        db.session.add(product_target)

                    db.session.commit()
                    flash(f'محصول {product.name} با تارگت‌های استانی ایجاد شد.', 'success')
                else:
                    flash(f'محصول {product.name} ایجاد شد، اما تارگت‌های استانی محاسبه نشد.', 'warning')

                return redirect(url_for('admin_products'))

            except IntegrityError:
                db.session.rollback()
                flash(f'خطا در ایجاد محصول: نام محصول تکراری است.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در ایجاد محصول: {str(e)}', 'danger')

        products = Product.query.all()

        # Load related data for display
        categories = ProductCategory.query.all()
        flavors = ProductFlavor.query.all()
        packagings = ProductPackaging.query.all()
        volumes = ProductVolume.query.all()

        return render_template('admin/products.html',
                               form=form,
                               products=products,
                               categories=categories,
                               flavors=flavors,
                               packagings=packagings,
                               volumes=volumes)

    @app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_product(product_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        product = Product.query.get_or_404(product_id)
        form = ProductForm(obj=product)

        # Populate select fields with existing options
        form.category_id.choices = [(0, '-- انتخاب دسته بندی --')] + [
            (c.id, c.name) for c in ProductCategory.query.order_by(ProductCategory.name).all()
        ]
        form.flavor_id.choices = [(0, '-- انتخاب طعم --')] + [
            (f.id, f.name) for f in ProductFlavor.query.order_by(ProductFlavor.name).all()
        ]
        form.packaging_id.choices = [(0, '-- انتخاب بسته بندی --')] + [
            (p.id, p.name) for p in ProductPackaging.query.order_by(ProductPackaging.name).all()
        ]
        form.volume_id.choices = [(0, '-- انتخاب حجم --')] + [
            (v.id, v.display_name) for v in ProductVolume.query.order_by(ProductVolume.value).all()
        ]

        if request.method == 'GET':
            # Set the form's values from the product
            form.category_id.data = product.category_id or 0
            form.flavor_id.data = product.flavor_id or 0
            form.packaging_id.data = product.packaging_id or 0
            form.volume_id.data = product.volume_id or 0

        if form.validate_on_submit():
            # Store old values to check for changes
            old_liter = product.liter_capacity
            old_shrink = product.shrink_capacity

            # Handle category (either new or existing)
            if form.new_category.data and form.new_category.data.strip():
                new_category = ProductCategory(name=form.new_category.data.strip())
                try:
                    db.session.add(new_category)
                    db.session.flush()
                    product.category_id = new_category.id
                except IntegrityError:
                    db.session.rollback()
                    existing_category = ProductCategory.query.filter_by(name=form.new_category.data.strip()).first()
                    if existing_category:
                        product.category_id = existing_category.id
            elif form.category_id.data and form.category_id.data != 0:
                product.category_id = form.category_id.data
            else:
                product.category_id = None

            # Handle flavor (either new or existing)
            if form.new_flavor.data and form.new_flavor.data.strip():
                new_flavor = ProductFlavor(name=form.new_flavor.data.strip())
                try:
                    db.session.add(new_flavor)
                    db.session.flush()
                    product.flavor_id = new_flavor.id
                except IntegrityError:
                    db.session.rollback()
                    existing_flavor = ProductFlavor.query.filter_by(name=form.new_flavor.data.strip()).first()
                    if existing_flavor:
                        product.flavor_id = existing_flavor.id
            elif form.flavor_id.data and form.flavor_id.data != 0:
                product.flavor_id = form.flavor_id.data
            else:
                product.flavor_id = None

            # Handle packaging (either new or existing)
            if form.new_packaging.data and form.new_packaging.data.strip():
                new_packaging = ProductPackaging(name=form.new_packaging.data.strip())
                try:
                    db.session.add(new_packaging)
                    db.session.flush()
                    product.packaging_id = new_packaging.id
                except IntegrityError:
                    db.session.rollback()
                    existing_packaging = ProductPackaging.query.filter_by(name=form.new_packaging.data.strip()).first()
                    if existing_packaging:
                        product.packaging_id = existing_packaging.id
            elif form.packaging_id.data and form.packaging_id.data != 0:
                product.packaging_id = form.packaging_id.data
            else:
                product.packaging_id = None

            # Handle volume (either new or existing)
            if form.new_volume.data:
                unit = form.volume_unit.data.strip() or 'لیتر'
                new_volume = ProductVolume(value=form.new_volume.data, unit=unit)
                try:
                    db.session.add(new_volume)
                    db.session.flush()
                    product.volume_id = new_volume.id
                except IntegrityError:
                    db.session.rollback()
                    existing_volume = ProductVolume.query.filter_by(value=form.new_volume.data, unit=unit).first()
                    if existing_volume:
                        product.volume_id = existing_volume.id
            elif form.volume_id.data and form.volume_id.data != 0:
                product.volume_id = form.volume_id.data
            else:
                product.volume_id = None

            # Update other fields
            product.name = form.name.data.strip()
            product.liter_capacity = form.liter_capacity.data
            product.shrink_capacity = form.shrink_capacity.data

            try:
                db.session.commit()

                # If capacity changed, update all province targets
                if old_liter != form.liter_capacity.data or old_shrink != form.shrink_capacity.data:
                    provinces = Province.query.all()
                    if provinces:
                        total_population = sum(province.population for province in provinces)

                        for province in provinces:
                            percentage = province.population / total_population

                            # Find existing target or create new one
                            target = ProductProvinceTarget.query.filter_by(
                                product_id=product.id,
                                province_id=province.id
                            ).first()

                            if not target:
                                target = ProductProvinceTarget(
                                    product_id=product.id,
                                    province_id=province.id
                                )
                                db.session.add(target)

                            # Update capacities
                            target.liter_capacity = product.liter_capacity * percentage if product.liter_capacity else None
                            target.shrink_capacity = product.shrink_capacity * percentage if product.shrink_capacity else None
                            target.liter_percentage = percentage * 100 if product.liter_capacity else None
                            target.shrink_percentage = percentage * 100 if product.shrink_capacity else None

                        db.session.commit()
                        flash(f'محصول {product.name} و تارگت‌های آن به‌روزرسانی شدند.', 'success')
                    else:
                        flash(f'محصول {product.name} به‌روزرسانی شد.', 'success')
                else:
                    flash(f'محصول {product.name} به‌روزرسانی شد.', 'success')

                return redirect(url_for('admin_products'))
            except IntegrityError:
                db.session.rollback()
                flash(f'خطا در به‌روزرسانی محصول: نام محصول تکراری است.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در به‌روزرسانی محصول: {str(e)}', 'danger')

        # Load related data for display
        categories = ProductCategory.query.all()
        flavors = ProductFlavor.query.all()
        packagings = ProductPackaging.query.all()
        volumes = ProductVolume.query.all()

        return render_template('admin/edit_product.html',
                               form=form,
                               product=product,
                               categories=categories,
                               flavors=flavors,
                               packagings=packagings,
                               volumes=volumes)

    @app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
    @login_required
    def delete_product(product_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        product = Product.query.get_or_404(product_id)

        try:
            # Delete related targets first
            ProductProvinceTarget.query.filter_by(product_id=product.id).delete()

            # Then delete the product
            db.session.delete(product)
            db.session.commit()

            flash(f'محصول {product.name} و تارگت‌های آن با موفقیت حذف شدند.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف محصول: {str(e)}', 'danger')

        return redirect(url_for('admin_products'))

    @app.route('/admin/products/<int:product_id>/targets')
    @login_required
    def product_province_targets(product_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        product = Product.query.get_or_404(product_id)
        provinces = Province.query.order_by(Province.name).all()

        # Get all targets for this product
        targets_query = ProductProvinceTarget.query.filter_by(product_id=product.id)
        targets = {target.province_id: target for target in targets_query.all()}

        # Get customer counts by province
        customers_by_province = {}
        for province in provinces:
            customers_count = CustomerReport.query.filter_by(province=province.name).count()
            customers_by_province[province.id] = customers_count

        return render_template('admin/product_targets.html',
                               product=product,
                               provinces=provinces,
                               targets=targets,
                               customers_by_province=customers_by_province)

    # --------------------- ADMIN: QUOTAS (Grade Mapping, Customer List & Evaluations) ---------------------
    @app.route('/admin/quotas', methods=['GET', 'POST'])
    @login_required
    def admin_quotas():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Form for grade mapping
        gradeForm = GradeMappingForm()

        # Form for target setting
        targetForm = TargetSettingForm()

        # Get customer list
        customers = CustomerReport.query.order_by(CustomerReport.number).all()

        # Get grade mappings
        grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()

        # Get individual evaluations (manual evaluations, limited to 100)
        evaluations = CustomerEvaluation.query.filter(
            CustomerEvaluation.evaluation_method == 'manual'
        ).order_by(CustomerEvaluation.evaluated_at.desc()).limit(100).all()

        # SIMPLIFIED APPROACH: Get all distinct batch IDs from CSVEvaluationRecord
        batch_ids_query = text("SELECT DISTINCT batch_id FROM csv_evaluation_record WHERE batch_id IS NOT NULL")
        result = db.session.execute(batch_ids_query)
        batch_ids = [row[0] for row in result if row[0]]

        print(f"Found {len(batch_ids)} distinct batch IDs in CSVEvaluationRecord")

        # If no batches found in CSVEvaluationRecord, try looking in CustomerEvaluation as fallback
        if not batch_ids:
            batch_ids_query = text("SELECT DISTINCT batch_id FROM customer_evaluation WHERE batch_id IS NOT NULL")
            result = db.session.execute(batch_ids_query)
            batch_ids = [row[0] for row in result if row[0]]
            print(f"Fallback: Found {len(batch_ids)} distinct batch IDs in CustomerEvaluation")

        # Process each batch
        batch_evaluations = []
        batch_statistics = {}

        for batch_id in batch_ids:
            # Get count of evaluations in batch from CSVEvaluationRecord
            count_query = text("SELECT COUNT(*) FROM csv_evaluation_record WHERE batch_id = :batch_id")
            count = db.session.execute(count_query, {"batch_id": batch_id}).scalar() or 0

            # If count is 0, try CustomerEvaluation as fallback
            if count == 0:
                count_query = text("SELECT COUNT(*) FROM customer_evaluation WHERE batch_id = :batch_id")
                count = db.session.execute(count_query, {"batch_id": batch_id}).scalar() or 0

            # Get latest evaluation date
            date_query = text("SELECT MAX(evaluated_at) FROM csv_evaluation_record WHERE batch_id = :batch_id")
            latest_date = db.session.execute(date_query, {"batch_id": batch_id}).scalar()

            # If no date found, try CustomerEvaluation as fallback
            if not latest_date:
                date_query = text("SELECT MAX(evaluated_at) FROM customer_evaluation WHERE batch_id = :batch_id")
                latest_date = db.session.execute(date_query, {"batch_id": batch_id}).scalar()

            # Create batch info object
            if count > 0 and latest_date:
                batch_info = {
                    'batch_id': batch_id,
                    'count': count,
                    'evaluated_at': latest_date if isinstance(latest_date, datetime) else str(latest_date)
                }
                batch_evaluations.append(batch_info)

                # Get grade distribution
                grade_query = text("""
                    SELECT assigned_grade, COUNT(*) as count 
                    FROM csv_evaluation_record 
                    WHERE batch_id = :batch_id 
                    GROUP BY assigned_grade
                """)
                grade_dist = db.session.execute(grade_query, {"batch_id": batch_id}).fetchall()
                grade_counts = {grade[0]: grade[1] for grade in grade_dist}

                # If no grades found, try CustomerEvaluation as fallback
                if not grade_counts:
                    grade_query = text("""
                        SELECT assigned_grade, COUNT(*) as count 
                        FROM customer_evaluation 
                        WHERE batch_id = :batch_id 
                        GROUP BY assigned_grade
                    """)
                    grade_dist = db.session.execute(grade_query, {"batch_id": batch_id}).fetchall()
                    grade_counts = {grade[0]: grade[1] for grade in grade_dist}

                # Calculate average score
                avg_query = text("SELECT AVG(total_score) FROM csv_evaluation_record WHERE batch_id = :batch_id")
                avg_score = db.session.execute(avg_query, {"batch_id": batch_id}).scalar() or 0

                # If no average found, try CustomerEvaluation as fallback
                if avg_score == 0:
                    avg_query = text("SELECT AVG(total_score) FROM customer_evaluation WHERE batch_id = :batch_id")
                    avg_score = db.session.execute(avg_query, {"batch_id": batch_id}).scalar() or 0

                # Store statistics
                batch_statistics[batch_id] = {
                    'grades': grade_counts,
                    'avg_score': round(avg_score, 2),
                    'count': count,
                    'date': latest_date if isinstance(latest_date, datetime) else str(latest_date)
                }

        # Sort batches by evaluation date (newest first)
        batch_evaluations = sorted(batch_evaluations, key=lambda x: x.get('evaluated_at', datetime.min), reverse=True)

        # Get provinces and targets for the target setting section
        provinces = Province.query.order_by(Province.name).all()

        # Get province targets if they exist
        province_targets = {}
        targets = ProvinceTarget.query.order_by(ProvinceTarget.id.desc()).limit(31).all()

        # Create a mapping of province ID to target
        for target in targets:
            if target.province_id not in province_targets:
                province_targets[target.province_id] = target

        # Get products for the product target section
        products = Product.query.order_by(Product.name).all()

        # Process POST request for target setting
        if 'submit_target' in request.form:
            liter_enabled = 'liter_enabled' in request.form
            shrink_enabled = 'shrink_enabled' in request.form

            if not liter_enabled and not shrink_enabled:
                flash('لطفاً حداقل یکی از ظرفیت‌ها را انتخاب کنید.', 'warning')
                return redirect(url_for('admin_quotas'))

            liter_capacity = float(request.form.get('liter_capacity', 0)) if liter_enabled else 0
            shrink_capacity = float(request.form.get('shrink_capacity', 0)) if shrink_enabled else 0

            # Calculate total population to compute percentages
            total_population = sum(province.population for province in provinces)

            # Clear previous targets
            ProvinceTarget.query.delete()

            # Create new targets for each province
            for province in provinces:
                percentage = province.population / total_population

                target = ProvinceTarget(
                    province_id=province.id,
                    liter_capacity=liter_capacity * percentage if liter_enabled else None,
                    shrink_capacity=shrink_capacity * percentage if shrink_enabled else None,
                    liter_percentage=percentage * 100 if liter_enabled else None,
                    shrink_percentage=percentage * 100 if shrink_enabled else None
                )
                db.session.add(target)

            try:
                db.session.commit()
                flash('تارگت‌ها با موفقیت محاسبه و ذخیره شدند.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در ذخیره تارگت‌ها: {str(e)}', 'danger')

            return redirect(url_for('admin_quotas'))

        # Process POST request for new grade mapping
        if request.method == 'POST' and 'grade_letter' in request.form:
            if gradeForm.validate_on_submit():
                grade_letter = gradeForm.grade_letter.data.strip()
                min_score = gradeForm.min_score.data
                new_mapping = GradeMapping(
                    grade_letter=grade_letter,
                    min_score=min_score
                )
                db.session.add(new_mapping)
                try:
                    db.session.commit()
                    flash(f'درجه {grade_letter} با حداقل نمره {min_score} ذخیره شد.', 'success')
                except IntegrityError:
                    db.session.rollback()
                    flash('خطا در ذخیره درجه. ممکن است این درجه تکراری باشد.', 'danger')
                return redirect(url_for('admin_quotas'))
            else:
                flash('خطا در اعتبارسنجی فرم.', 'danger')
                return redirect(url_for('admin_quotas'))

        return render_template('admin/quotas.html',
                               form=gradeForm,
                               target_form=targetForm,
                               customers=customers,
                               grade_mappings=grade_mappings,
                               evaluations=evaluations,
                               batch_evaluations=batch_evaluations,
                               batch_statistics=batch_statistics,
                               provinces=provinces,
                               province_targets=province_targets,
                               products=products)

    @app.route('/api/product_distribution')
    @login_required
    def api_product_distribution():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        products = Product.query.all()
        product_data = []

        for product in products:
            product_info = {
                'id': product.id,
                'name': product.name,
                'liter_capacity': product.liter_capacity,
                'shrink_capacity': product.shrink_capacity,
                'province_targets': []
            }

            # Get province targets for this product
            targets = ProductProvinceTarget.query.filter_by(product_id=product.id).all()

            for target in targets:
                province = Province.query.get(target.province_id)
                if province:
                    product_info['province_targets'].append({
                        'province_name': province.name,
                        'liter_capacity': target.liter_capacity,
                        'shrink_capacity': target.shrink_capacity,
                        'liter_percentage': target.liter_percentage,
                        'shrink_percentage': target.shrink_percentage
                    })

            product_data.append(product_info)

        return jsonify(product_data)
    
    
    # --------------------- ADMIN: PROVINCE TARGETS MANAGEMENT ---------------------
    @app.route('/admin/init_provinces')
    @login_required
    def init_provinces():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Check if provinces already exist
        if Province.query.count() > 0:
            flash('استان‌ها قبلاً اضافه شده‌اند.', 'info')
            return redirect(url_for('admin_customers_csv'))

        # Province data (name, population)
        provinces_data = [
            ("مرکز فروش تهران", 13267637),
                    ("مرکز فروش خراسان رضوی", 6434501),
                    ("مرکز فروش اصفهان", 5120850),
                    ("مرکز فروش شیراز", 4851274),
                    ("مرکز فروش خوزستان", 4710509),
                    ("مرکز فروش آذربایجان ", 3909652),
                    ("مرکز فروش مازندران", 3283582),
                    ("مرکز فروش آذربایجان غربی", 3265219),
                    ("مرکز فروش کرمان", 3164718),
                    ("مرکز فروش سیستان و بلوچستان", 2775014),
                    ("مرکز فروش البرز", 2712400),
                    ("مرکز فروش گیلان", 2530696),
                    ("مرکز فروش کرمانشاه", 1952434),
                    ("مرکز فروش لرستان", 1760649),
                    ("مرکز فروش همدان", 1738234),
                    ("مرکز فروش گلستان", 1777014),
                    ("مرکز فروش کردستان", 1603011),
                    ("مرکز فروش هرمزگان", 1578183),
                    ("مرکز فروش مرکزی", 1429475),
                    ("مرکز فروش اردبیل", 1270420),
                    ("مرکز فروش قزوین", 1201565),
                    ("مرکز فروش قم", 1151672),
                    ("مرکز فروش یزد", 1074428),
                    ("مرکز فروش زنجان", 1015734),
                    ("مرکز فروش بوشهر", 1032949),
                    ("مرکز فروش چهار محال و بختیاری", 895263),
                    ("مرکز فروش خراسان شمالی", 867727),
                    ("مرکز فروش کهکولویه و بویراحد", 658629),
                    ("مرکز فروش خراسان جنوبی", 622534),
                    ("مرکز فروش سمنان", 631218),
                    ("مرکز فروش ایلام", 557599)
        ]

        for name, population in provinces_data:
            province = Province(name=name, population=population)
            db.session.add(province)

        try:
            db.session.commit()
            flash('استان‌ها با موفقیت اضافه شدند.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در اضافه کردن استان‌ها: {str(e)}', 'danger')

        return redirect(url_for('admin_customers_csv'))

    @app.route('/admin/province_targets')
    @login_required
    def admin_province_targets():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get provinces and targets
        provinces = Province.query.order_by(Province.name).all()

        # Get the latest target for each province
        province_targets = {}
        for province in provinces:
            target = ProvinceTarget.query.filter_by(province_id=province.id).order_by(ProvinceTarget.id.desc()).first()
            if target:
                province_targets[province.id] = target

        # Get customers by province
        customers_by_province = {}
        for province in provinces:
            customers = CustomerReport.query.filter_by(province=province.name).all()
            customers_by_province[province.id] = customers

        # Get all grade mappings for allocation by grade
        grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()

        # Count customers by grade for each province
        customer_grades_by_province = {}
        for province_id, customers in customers_by_province.items():
            grade_counts = {}
            for grade_mapping in grade_mappings:
                grade_counts[grade_mapping.grade_letter] = 0

            # Count ungraded customers too
            grade_counts['بدون درجه'] = 0

            for customer in customers:
                if customer.grade in grade_counts:
                    grade_counts[customer.grade] += 1
                else:
                    grade_counts['بدون درجه'] += 1

            customer_grades_by_province[province_id] = grade_counts

        # Get grade weights from session or set defaults
        grade_weights = session.get('grade_weights', {})

        # If no weights in session, set defaults based on min_score
        if not grade_weights:
            for grade_mapping in grade_mappings:
                # Set weights based on min_score (higher score = higher weight)
                grade_weights[grade_mapping.grade_letter] = grade_mapping.min_score / 100

            # Default weight for ungraded customers
            grade_weights['بدون درجه'] = 0.5

        # Check what capacities were set (for table headers)
        has_liter = any(t.liter_capacity is not None for t in province_targets.values()) if province_targets else False
        has_shrink = any(
            t.shrink_capacity is not None for t in province_targets.values()) if province_targets else False

        # Calculate per-customer allocation by grade
        allocation_by_province_and_grade = {}

        for province_id, target in province_targets.items():
            if province_id not in customer_grades_by_province:
                continue

            grade_counts = customer_grades_by_province[province_id]
            allocation_by_grade = {}

            # Calculate total weighted count
            total_weighted_count = 0
            for grade, count in grade_counts.items():
                weight = grade_weights.get(grade, 0.5)  # Default weight if grade not found
                total_weighted_count += count * weight

            # Calculate allocation per customer by grade
            for grade, count in grade_counts.items():
                if count == 0 or total_weighted_count == 0:
                    allocation_by_grade[grade] = {
                        'liter': None,
                        'shrink': None,
                        'count': count
                    }
                    continue

                weight = grade_weights.get(grade, 0.5)

                # Calculate total allocation for this grade group
                if has_liter and target.liter_capacity is not None:
                    liter_per_customer = (
                                                     target.liter_capacity * weight * count / total_weighted_count) / count if count > 0 else 0
                else:
                    liter_per_customer = None

                if has_shrink and target.shrink_capacity is not None:
                    shrink_per_customer = (
                                                      target.shrink_capacity * weight * count / total_weighted_count) / count if count > 0 else 0
                else:
                    shrink_per_customer = None

                allocation_by_grade[grade] = {
                    'liter': liter_per_customer,
                    'shrink': shrink_per_customer,
                    'count': count
                }

            allocation_by_province_and_grade[province_id] = allocation_by_grade

        return render_template('admin/province_targets.html',
                               provinces=provinces,
                               province_targets=province_targets,
                               has_liter=has_liter,
                               has_shrink=has_shrink,
                               customers_by_province=customers_by_province,
                               customer_grades_by_province=customer_grades_by_province,
                               grade_mappings=grade_mappings,
                               grade_weights=grade_weights,
                               allocation_by_province_and_grade=allocation_by_province_and_grade)

    @app.route('/admin/update_grade_weights', methods=['POST'])
    @login_required
    def update_grade_weights():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get data from the form
        weights = {}
        for key, value in request.form.items():
            if key.startswith('weight_'):
                grade = key[7:]  # Remove 'weight_' prefix
                try:
                    weights[grade] = float(value)
                except ValueError:
                    pass

        # Store weights in session for persistence
        session['grade_weights'] = weights

        flash('وزن‌های درجه‌بندی با موفقیت به‌روزرسانی شدند.', 'success')
        return redirect(url_for('admin_province_targets'))
    # --------------------- ADMIN: EVALUATE CUSTOMER (Single Evaluation) ---------------------
    @app.route('/admin/evaluate_customer/<int:customer_id>', methods=['GET', 'POST'], endpoint='evaluate_customer')
    @login_required
    def evaluate_customer_view(customer_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        customer = CustomerReport.query.get_or_404(customer_id)
        form = CustomerEvaluationForm()
        form.customer_id.choices = [(customer.id, f"{customer.number} - {customer.name}")]
        form.customer_id.data = customer.id

        if request.method == 'POST':
            if form.validate_on_submit():
                total_score = (
                    form.sales_volume_weight.data * form.sales_volume_score.data +
                    form.sales_revenue_weight.data * form.sales_revenue_score.data +
                    form.sales_diversity_weight.data * form.sales_diversity_score.data +
                    form.store_dimensions_weight.data * form.store_dimensions_score.data +
                    form.street_visibility_weight.data * form.street_visibility_score.data +
                    form.location_city_weight.data * form.location_city_score.data +
                    form.location_zone_weight.data * form.location_zone_score.data +
                    form.ownership_owner_weight.data * form.ownership_owner_score.data +
                    form.ownership_rented_weight.data * form.ownership_rented_score.data +
                    form.ownership_owned_weight.data * form.ownership_owned_score.data +
                    form.cleanliness_weight.data * form.cleanliness_score.data +
                    form.equipment_weight.data * form.equipment_score.data +
                    form.luxury_weight.data * form.luxury_score.data +
                    form.brand_weight.data * form.brand_score.data
                )
                mapping_obj = GradeMapping.query.filter(GradeMapping.min_score <= total_score)\
                            .order_by(GradeMapping.min_score.desc()).first()
                if mapping_obj:
                    assigned_grade = mapping_obj.grade_letter
                else:
                    assigned_grade = "بدون درجه"
                flash(f'ارزیابی انجام شد. نمره کل: {total_score:.2f}, درجه: {assigned_grade}', 'success')
                evaluation = CustomerEvaluation(
                    customer_id=customer.id,
                    total_score=total_score,
                    assigned_grade=assigned_grade,
                    evaluated_at=datetime.now(timezone.utc),
                    evaluation_method="manual"
                )
                
                # Update customer's grade
                customer.grade = assigned_grade
                
                db.session.add(evaluation)
                db.session.commit()
                return redirect(url_for('admin_quotas'))
            else:
                print("Evaluation form errors:", form.errors)
                flash('خطا در اعتبارسنجی فرم. لطفاً تمامی فیلدها را به درستی پر کنید.', 'danger')
        return render_template('admin/evaluate_customer.html', form=form, customer=customer)

    # --------------------- ADMIN: GRADE MAPPING EDIT ---------------------
    @app.route('/admin/quotas/edit/<int:mapping_id>', methods=['GET', 'POST'])
    @login_required
    def edit_grade_mapping(mapping_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        mapping = GradeMapping.query.get_or_404(mapping_id)
        form = GradeMappingForm(obj=mapping)
        if form.validate_on_submit():
            mapping.grade_letter = form.grade_letter.data.strip()
            mapping.min_score = form.min_score.data
            try:
                db.session.commit()
                flash('درجه با موفقیت ویرایش شد.', 'success')
                return redirect(url_for('admin_quotas'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ویرایش درجه.', 'danger')
        return render_template('admin/edit_grade_mapping.html', form=form, mapping=mapping)

    # --------------------- ADMIN: GRADE MAPPING DELETE ---------------------
    @app.route('/admin/quotas/delete/<int:mapping_id>', methods=['GET', 'POST'])
    @login_required
    def delete_grade_mapping(mapping_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        mapping = GradeMapping.query.get_or_404(mapping_id)
        db.session.delete(mapping)
        db.session.commit()
        flash('درجه حذف شد.', 'info')
        return redirect(url_for('admin_quotas'))

    # --------------------- ADMIN: USER MANAGEMENT ---------------------
    @app.route('/admin/users', methods=['GET', 'POST'])
    @login_required
    def admin_users():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get counts for different user roles
        count_admin = User.query.filter_by(role='admin').count()
        count_marketer = User.query.filter_by(role='marketer').count()
        count_observer = User.query.filter_by(role='observer').count()

        # Get search query if exists
        search_query = request.args.get('search', '').strip()
        if search_query:
            users = User.query.filter(
                or_(
                    User.username.ilike(f"%{search_query}%"),
                    User.email.ilike(f"%{search_query}%")
                )
            ).all()
        else:
            users = User.query.all()

        # Setup form for creating/editing users
        form = UserForm()
        edit_id = request.args.get('edit_id', type=int)
        edit_mode = False
        user_to_edit = None

        # Create a dictionary to store the hierarchy
        hierarchy = {}

        # Find top-level users (those with no superiors)
        top_level_users = []
        for user in users:
            superiors = UserHierarchy.query.filter_by(child_id=user.id).all()
            if not superiors:
                top_level_users.append(user)

        # Build the hierarchy tree
        for top_user in top_level_users:
            hierarchy[top_user.id] = build_user_tree(top_user.id)

        # Check if we're in edit mode
        if edit_id:
            user_to_edit = User.query.get(edit_id)
            if user_to_edit:
                form.username.data = user_to_edit.username
                form.email.data = user_to_edit.email or ''
                form.fullname.data = user_to_edit.fullname
                form.is_active.data = user_to_edit.is_active
                form.role.data = user_to_edit.role
                form.job_title.data = user_to_edit.job_title
                form.department.data = user_to_edit.department

                # Get current parent if exists
                parent = UserHierarchy.query.filter_by(child_id=user_to_edit.id).first()
                if parent:
                    form.parent_id.data = parent.parent_id

                edit_mode = True

        # Get potential parent users for the dropdown (exclude self and subordinates)
        if edit_id:
            # Get all subordinate IDs to exclude them
            subordinate_ids = get_all_subordinate_ids(edit_id)
            subordinate_ids.append(edit_id)  # Also exclude self

            potential_parents = User.query.filter(~User.id.in_(subordinate_ids)).all()
        else:
            potential_parents = users

        # Populate the parent_id choices
        form.parent_id.choices = [(0, '-- بدون سرپرست --')] + [
            (u.id, u.fullname or u.username) for u in potential_parents
        ]

        # Process form submission
        if form.validate_on_submit():
            email_value = form.email.data.strip() if form.email.data else None

            if edit_mode and user_to_edit:
                # Update existing user
                user_to_edit.username = form.username.data
                if form.password.data:  # Only update password if provided
                    user_to_edit.password = generate_password_hash(form.password.data)
                user_to_edit.email = email_value
                user_to_edit.fullname = form.fullname.data
                user_to_edit.is_active = form.is_active.data
                user_to_edit.role = form.role.data
                user_to_edit.job_title = form.job_title.data
                user_to_edit.department = form.department.data

                user = user_to_edit
            else:
                # Create new user
                hashed_password = generate_password_hash(form.password.data)
                new_user = User(
                    username=form.username.data,
                    password=hashed_password,
                    email=email_value,
                    fullname=form.fullname.data,
                    is_active=form.is_active.data,
                    role=form.role.data,
                    job_title=form.job_title.data,
                    department=form.department.data
                )
                db.session.add(new_user)
                # Need to flush to get the ID
                try:
                    db.session.flush()
                    user = new_user
                except IntegrityError:
                    db.session.rollback()
                    flash('خطا: نام کاربری یا ایمیل تکراری است.', 'danger')
                    return redirect(url_for('admin_users'))

            # Handle hierarchy if parent_id is provided
            parent_id = form.parent_id.data

            # Remove existing hierarchy entries for this user
            UserHierarchy.query.filter_by(child_id=user.id).delete()

            if parent_id and parent_id != 0:
                # Get the parent user
                parent_user = User.query.get(parent_id)

                if parent_user:
                    # Determine level (parent's level + 1)
                    parent_level = 0
                    parent_hierarchy = UserHierarchy.query.filter_by(child_id=parent_id).first()
                    if parent_hierarchy:
                        parent_level = parent_hierarchy.level

                    # Create new hierarchy
                    new_hierarchy = UserHierarchy(
                        parent_id=parent_id,
                        child_id=user.id,
                        level=parent_level + 1
                    )
                    db.session.add(new_hierarchy)

                    # Update user's position level
                    user.position_level = parent_level + 1

            try:
                db.session.commit()
                if edit_mode:
                    flash('کاربر با موفقیت ویرایش شد.', 'success')
                else:
                    flash('کاربر جدید با موفقیت ایجاد شد.', 'success')
                return redirect(url_for('admin_users'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا: اطلاعات وارد شده تکراری یا نامعتبر است.', 'danger')

        # Render the template with all data
        return render_template('admin/users.html',
                               users=users,
                               form=form,
                               edit_mode=edit_mode,
                               search_query=search_query,
                               count_admin=count_admin,
                               count_marketer=count_marketer,
                               count_observer=count_observer,
                               hierarchy=hierarchy,
                               potential_parents=potential_parents)

    # Helper function to build the user tree
    def build_user_tree(user_id):
        result = {}

        # Get direct subordinates
        subordinates = UserHierarchy.query.filter_by(parent_id=user_id).all()

        for sub in subordinates:
            result[sub.child_id] = build_user_tree(sub.child_id)

        return result

    # Helper function to get all subordinates recursively
    def get_all_subordinate_ids(user_id):
        result = []

        # Get direct subordinates
        direct_subordinates = UserHierarchy.query.filter_by(parent_id=user_id).all()

        for sub in direct_subordinates:
            result.append(sub.child_id)
            result.extend(get_all_subordinate_ids(sub.child_id))

        return result

    @app.route('/api/user-hierarchy-data')
    @login_required
    def user_hierarchy_data():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get all users
        users = User.query.all()
        user_dict = {user.id: user for user in users}

        # Find top-level users (those with no superiors)
        top_level_users = []
        for user in users:
            superiors = UserHierarchy.query.filter_by(child_id=user.id).all()
            if not superiors:
                top_level_users.append(user)

        # Build the hierarchy
        result = []
        for top_user in top_level_users:
            node = convert_user_to_node(top_user)
            add_children_to_node(node, top_user.id, user_dict)
            result.append(node)

        return jsonify(result)

    def convert_user_to_node(user):
        role_classes = {
            'admin': 'admin',
            'marketer': 'marketer',
            'observer': 'observer'
        }

        return {
            'id': user.id,
            'name': user.fullname or user.username,
            'title': user.job_title or '',
            'role': user.role,
            'className': role_classes.get(user.role, ''),
            'children': []
        }

    def add_children_to_node(node, user_id, user_dict):
        children = UserHierarchy.query.filter_by(parent_id=user_id).all()

        for child in children:
            if child.child_id in user_dict:
                child_user = user_dict[child.child_id]
                child_node = convert_user_to_node(child_user)
                add_children_to_node(child_node, child_user.id, user_dict)
                node['children'].append(child_node)

    def build_hierarchy_node(user, user_dict, parent_to_children):
        # Define role-based classes for styling
        role_classes = {
            'admin': 'admin',
            'marketer': 'marketer',
            'observer': 'observer'
        }

        # Create node for this user
        node = {
            'id': user.id,
            'name': user.fullname or user.username,
            'title': user.job_title or '',
            'department': user.department or '',
            'role': user.role,
            'className': role_classes.get(user.role, ''),
            'children': []
        }

        # Add children nodes recursively
        if user.id in parent_to_children:
            for child_id in parent_to_children[user.id]:
                if child_id in user_dict:
                    child_user = user_dict[child_id]
                    node['children'].append(build_hierarchy_node(child_user, user_dict, parent_to_children))

        return node
    @app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
    @login_required
    def delete_user(user_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        user_to_delete = User.query.get_or_404(user_id)
        if user_to_delete.username == 'admin':
            flash('نمی‌توان ادمین اصلی را حذف کرد!', 'warning')
            return redirect(url_for('admin_users'))
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('کاربر حذف شد.', 'info')
        return redirect(url_for('admin_users'))

    # --------------------- ADMIN: ROUTE MANAGEMENT ---------------------
    @app.route('/admin/routes', methods=['GET', 'POST'])
    @login_required
    def admin_routes():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        route_form = RouteForm()
        marketers = User.query.filter_by(role='marketer').all()
        route_form.marketer_ids.choices = [(m.id, m.fullname or m.username) for m in marketers]
        if route_form.validate_on_submit():
            route = Route(
                name=route_form.name.data,
                description=route_form.description.data
            )
            db.session.add(route)
            db.session.flush()
            for marketer_id in route_form.marketer_ids.data:
                assignment = RouteAssignment(route_id=route.id, marketer_id=marketer_id)
                db.session.add(assignment)
            try:
                db.session.commit()
                flash('مسیر جدید با موفقیت ایجاد شد.', 'success')
                return redirect(url_for('admin_routes'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ایجاد مسیر.', 'danger')
        routes = Route.query.all()
        return render_template('admin/routes.html', route_form=route_form, routes=routes)

    @app.route('/admin/routes/<int:route_id>', methods=['GET', 'POST'])
    @login_required
    def admin_route_detail(route_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        route = Route.query.get_or_404(route_id)
        point_form = RoutePointForm()
        if point_form.validate_on_submit():
            new_point = RoutePoint(
                route_id=route.id,
                name=point_form.name.data,
                latitude=point_form.latitude.data,
                longitude=point_form.longitude.data,
                address=point_form.address.data,
                order=point_form.order.data
            )
            db.session.add(new_point)
            try:
                db.session.commit()
                flash('نقطه جدید اضافه شد.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('خطا در افزودن نقطه.', 'danger')
            return redirect(url_for('admin_route_detail', route_id=route.id))
        return render_template('admin/route_detail.html', route=route, point_form=point_form)

    @app.route('/admin/routes/<int:route_id>/points/<int:point_id>', methods=['DELETE', 'POST'])
    @login_required
    def delete_route_point(route_id, point_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403
        point = RoutePoint.query.get_or_404(point_id)
        if point.route_id != route_id:
            return jsonify({'error': 'Not found'}), 404
        db.session.delete(point)
        db.session.commit()
        if request.method == 'DELETE':
            return jsonify({'message': 'Point deleted'})
        else:
            flash('نقطه حذف شد.', 'success')
            return redirect(url_for('admin_route_detail', route_id=route_id))

    @app.route('/admin/reports')
    @login_required
    def admin_reports():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/reports.html')

    @app.route('/admin/alerts')
    @login_required
    def admin_alerts():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/alerts.html')

    @app.route('/admin/settings')
    @login_required
    def admin_settings():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/settings.html')

    @app.route('/admin/marketer_locations')
    @login_required
    def admin_marketer_locations():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/marketer_locations.html')

    @app.route('/marketer', methods=['GET'])
    @login_required
    def marketer_index():
        if current_user.role != 'marketer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # You might want to fetch additional data for the marketer dashboard here
        # For example, getting today's stats, scheduled visits, etc.

        # Get assigned routes for the current marketer
        assigned_routes = RouteAssignment.query.filter_by(
            marketer_id=current_user.id,
            is_active=True
        ).all()

        route_data = []
        for assignment in assigned_routes:
            if assignment.route:
                route_data.append({
                    'id': assignment.route.id,
                    'name': assignment.route.name,
                    'description': assignment.route.description,
                    'points_count': len(assignment.route.points) if assignment.route.points else 0
                })

        return render_template('marketer/index.html',
                               assigned_routes=route_data)


    @app.route('/marketer/map', methods=['GET'])
    @login_required
    def marketer_map():
        if current_user.role != 'marketer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get assigned routes and their points
        assigned_routes = RouteAssignment.query.filter_by(
            marketer_id=current_user.id,
            is_active=True
        ).all()

        routes = []
        for assignment in assigned_routes:
            if assignment.route:
                points = []
                for point in assignment.route.points:
                    # Get customer info if available
                    customer = None
                    if point.name and point.latitude and point.longitude:
                        # Try to find a customer near this point
                        nearby_customers = CustomerReport.query.filter(
                            CustomerReport.latitude.between(point.latitude - 0.001, point.latitude + 0.001),
                            CustomerReport.longitude.between(point.longitude - 0.001, point.longitude + 0.001)
                        ).all()

                        if nearby_customers:
                            customer = nearby_customers[0]

                    points.append({
                        'id': point.id,
                        'name': point.name,
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'address': point.address,
                        'order': point.order,
                        'customer_info': {
                            'name': customer.name if customer else None,
                            'number': customer.number if customer else None,
                            'grade': customer.grade if customer else None
                        } if customer else None
                    })

                routes.append({
                    'id': assignment.route.id,
                    'name': assignment.route.name,
                    'description': assignment.route.description,
                    'points': sorted(points, key=lambda x: x['order'])
                })

        return render_template('marketer/map.html',
                               routes=routes,
                               current_lat=current_user.current_lat,
                               current_lng=current_user.current_lng)

    @app.route('/api/update-location', methods=['POST'])
    @login_required
    def update_location():
        if current_user.role != 'marketer':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        try:
            # Update location if provided
            if 'latitude' in data and 'longitude' in data:
                current_user.current_lat = float(data['latitude'])
                current_user.current_lng = float(data['longitude'])
                current_user.last_location_update = datetime.now(timezone.utc)

            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Location updated',
                'timestamp': current_user.last_location_update.strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/marketer/assigned-routes')
    @login_required
    def get_marketer_assigned_routes():
        if current_user.role != 'marketer':
            return jsonify({'error': 'Unauthorized'}), 403

        # Fetch active route assignments for the current marketer
        assignments = RouteAssignment.query.filter_by(
            marketer_id=current_user.id,
            is_active=True
        ).all()

        routes_data = []
        for assignment in assignments:
            route = assignment.route
            if route:
                route_points = []
                for point in route.points:
                    customer = None
                    # Try to find a customer near this point
                    if point.latitude and point.longitude:
                        nearby_customers = CustomerReport.query.filter(
                            CustomerReport.latitude.between(point.latitude - 0.001, point.latitude + 0.001),
                            CustomerReport.longitude.between(point.longitude - 0.001, point.longitude + 0.001)
                        ).all()

                        if nearby_customers:
                            customer = nearby_customers[0]

                    route_points.append({
                        'id': point.id,
                        'name': point.name,
                        'latitude': point.latitude,  # Use consistent field names
                        'longitude': point.longitude,  # Use consistent field names
                        'address': point.address,
                        'order': point.order,
                        'customer': {
                            'id': customer.id if customer else None,
                            'name': customer.name if customer else None,
                            'number': customer.number if customer else None,
                            'grade': customer.grade if customer else None
                        } if customer else None
                    })

                # Sort points by order
                route_points = sorted(route_points, key=lambda x: x['order'])


                routes_data.append({
                    'id': route.id,
                    'name': route.name,
                    'description': route.description,
                    'points': route_points
                })

        return jsonify(routes_data)
    @app.route('/observer', methods=['GET'])
    @login_required
    def observer_index():
        if current_user.role != 'observer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get all marketers for tracking
        marketers = User.query.filter_by(role='marketer').all()

        # Get marketers with recent location updates (active within the last 2 hours)
        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        active_marketers = User.query.filter(
            User.role == 'marketer',
            User.last_location_update >= two_hours_ago
        ).count()

        # Get all routes
        routes = Route.query.all()

        # Get basic stats for the dashboard
        stats = {
            'total_marketers': len(marketers),
            'active_marketers': active_marketers,
            'inactive_marketers': len(marketers) - active_marketers,
            'total_routes': len(routes),
            'alerts_count': 0  # You might want to implement alerts logic
        }

        # Get marketer details for tracking list
        marketer_details = []
        for marketer in marketers:
            # Determine status based on location update time
            status = 'inactive'
            if marketer.last_location_update:
                # Make sure last_location_update has timezone info before comparing
                last_update = marketer.last_location_update
                if last_update.tzinfo is None:
                    # If it's naive, assume it's in UTC
                    last_update = last_update.replace(tzinfo=timezone.utc)

                time_diff = datetime.now(timezone.utc) - last_update
                if time_diff.total_seconds() < 7200:  # Within 2 hours
                    # Check if marketer is on their assigned route
                    status = 'on_track'  # Default to on track (can implement route checking logic)

            # Get assigned route name if any
            current_assignment = RouteAssignment.query.filter_by(
                marketer_id=marketer.id,
                is_active=True
            ).first()

            route_name = current_assignment.route.name if current_assignment and current_assignment.route else 'بدون مسیر'

            marketer_details.append({
                'id': marketer.id,
                'name': marketer.fullname or marketer.username,
                'status': status,
                'location': {
                    'lat': marketer.current_lat,
                    'lng': marketer.current_lng,
                    'last_update': marketer.last_location_update
                },
                'route_name': route_name
            })

        return render_template('observer/index.html',
                               stats=stats,
                               marketers=marketer_details)
    # --------------------- ADMIN: DESCRIPTIVE CRITERIA MANAGEMENT ---------------------
    @app.route('/admin/descriptive_criteria', methods=['GET', 'POST'])
    @login_required
    def descriptive_criteria():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        criteria = DescriptiveCriterion.query.all()
        if request.method == 'POST':
            parameter = request.form.get('parameter')
            criterion = request.form.get('criterion')
            score = request.form.get('score')
            try:
                score = float(score)
            except:
                flash('نمره باید عددی باشد.', 'danger')
                return redirect(url_for('descriptive_criteria'))
            new_crit = DescriptiveCriterion(parameter_name=parameter, criterion=criterion, score=score)
            db.session.add(new_crit)
            try:
                db.session.commit()
                flash('معیار اضافه شد.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ذخیره معیار.', 'danger')
            return redirect(url_for('descriptive_criteria'))
        return render_template('admin/descriptive_criteria.html', criteria=criteria)

    @app.route('/admin/descriptive_criteria/edit/<int:crit_id>', methods=['GET', 'POST'])
    @login_required
    def edit_descriptive_criteria(crit_id):
       if current_user.role != 'admin':
           flash('دسترسی غیرمجاز!', 'danger')
           return redirect(url_for('dashboard'))
       crit = DescriptiveCriterion.query.get_or_404(crit_id)
       if request.method == 'POST':
           crit.parameter_name = request.form.get('parameter')
           crit.criterion = request.form.get('criterion')
           try:
               crit.score = float(request.form.get('score'))
           except:
               flash('نمره باید عددی باشد.', 'danger')
               return redirect(url_for('edit_descriptive_criteria', crit_id=crit_id))
           try:
               db.session.commit()
               flash('معیار ویرایش شد.', 'success')
               return redirect(url_for('descriptive_criteria'))
           except IntegrityError:
               db.session.rollback()
               flash('خطا در ویرایش معیار.', 'danger')
       return render_template('admin/edit_descriptive_criteria.html', crit=crit)

    @app.route('/admin/descriptive_criteria/delete/<int:crit_id>', methods=['POST'])
    @login_required
    def delete_descriptive_criteria(crit_id):
       if current_user.role != 'admin':
           flash('دسترسی غیرمجاز!', 'danger')
           return redirect(url_for('dashboard'))
       crit = DescriptiveCriterion.query.get_or_404(crit_id)
       db.session.delete(crit)
       db.session.commit()
       flash('معیار حذف شد.', 'info')
       return redirect(url_for('descriptive_criteria'))

    # --- Helper function to get/create the permanent evaluation files directory ---
    def get_evaluation_dir():
        """Create and return the directory path for permanently saved evaluation files"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Define the permanent directory name
        eval_dir = os.path.join(base_dir, 'evaluation_files')
        if not os.path.exists(eval_dir):
            try:
                os.makedirs(eval_dir)
                print(f"Created evaluation files directory: {eval_dir}")
            except OSError as e:
                print(f"Error creating directory {eval_dir}: {e}")
                raise OSError(f"Could not create evaluation_files directory: {e}") from e
        return eval_dir

    from datetime import datetime, timezone, date
    # --------------------- ADMIN: EVALUATE WITH CSV/EXCEL (Enhanced) ---------------------
    @app.route('/admin/evaluate_csv', methods=['GET', 'POST'])
    @login_required
    def admin_evaluate_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Use a session key for the permanent file path
        perm_filepath_session_key = 'csv_eval_perm_filepath'

        if request.method == 'GET':
            # No file cleanup needed here anymore for GET requests
            # Just show the upload form
            # Clear session key in case user navigates away and comes back
            session.pop(perm_filepath_session_key, None)
            return render_template('admin/evaluate_csv_upload.html')

        # --- POST Request Logic ---
        action = request.form.get('action')

        if action == 'upload_file':
            # --- Upload Action: Save file PERMANENTLY, store path in session ---
            permanent_save_path = None  # Define for potential error handling
            try:
                file = request.files.get('file')
                if not file or not file.filename:
                    flash('هیچ فایلی انتخاب نشده است یا نام فایل نامعتبر است.', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))

                filename = secure_filename(file.filename)  # Keep original case potentially, but sanitize
                file_base, file_ext = os.path.splitext(filename)
                file_ext = file_ext.lower()  # Use lower case extension for checks

                # --- Define permanent save path ---
                eval_dir = get_evaluation_dir()
                # Create a unique name to avoid overwrites, keeping original name part
                unique_save_filename = f"{file_base}_{uuid.uuid4().hex}{file_ext}"
                permanent_save_path = os.path.join(eval_dir, unique_save_filename)
                # --- End Define path ---

                # --- Save the file ---
                file.save(permanent_save_path)
                print(f"Saved evaluation file permanently: {permanent_save_path}")
                # --- End Save ---

                # --- Read file to validate and get columns ---
                if file_ext == '.csv':
                    df = pd.read_csv(permanent_save_path, encoding='utf-8-sig')
                elif file_ext in ['.xls', '.xlsx']:
                    df = pd.read_excel(permanent_save_path)
                else:
                    # Invalid file type, delete the saved file
                    if os.path.exists(permanent_save_path): os.remove(permanent_save_path)
                    flash('فایل پشتیبانی نمی‌شود. لطفاً CSV یا Excel آپلود کنید.', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))
                # --- End Read file ---

                # Store PERMANENT path in session
                session[perm_filepath_session_key] = permanent_save_path

                # --- Prepare data for configuration template ---
                columns = [str(col) for col in df.columns]
                descriptive_criteria = DescriptiveCriterion.query.all()
                criteria_by_param = {}
                for crit in descriptive_criteria:
                    param_name = str(crit.parameter_name);
                    if param_name not in criteria_by_param: criteria_by_param[param_name] = []
                    criteria_by_param[param_name].append({'criterion': crit.criterion, 'score': crit.score})
                grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()
                # --- End Prepare data ---

                return render_template('admin/evaluate_csv_configure.html',
                                       columns=columns, criteria_by_param=criteria_by_param,
                                       grade_mappings=grade_mappings)

            except Exception as e_upload:
                flash(f'خطا در مرحله آپلود و ذخیره فایل: {e_upload}', 'danger')
                print(f"Error during 'upload_file' action: {e_upload}")
                # Cleanup attempt if path was assigned but process failed
                if permanent_save_path and os.path.exists(permanent_save_path):
                    # Decide if you want to delete on upload error or keep the partially uploaded file
                    # Let's delete it for now if upload stage fails completely
                    try:
                        os.remove(permanent_save_path); print(
                            f"Deleted file due to upload error: {permanent_save_path}")
                    except OSError as e_del_err:
                        print(f"Error deleting file during upload error cleanup: {e_del_err}")
                session.pop(perm_filepath_session_key, None)  # Clear session key on error
                return redirect(url_for('admin_evaluate_csv'))


        elif action == 'configure':
            # --- Configure Action: Read PERMANENT file, process, render results ---
            permanent_filepath = session.get(perm_filepath_session_key)  # Retrieve permanent path

            try:
                if not permanent_filepath or not os.path.exists(permanent_filepath):
                    flash('فایل ذخیره شده یافت نشد. لطفاً دوباره آپلود کنید.', 'danger')
                    print(
                        f"Permanent file path error before processing: Path='{permanent_filepath}', Exists={os.path.exists(permanent_filepath) if permanent_filepath else 'N/A'}")
                    session.pop(perm_filepath_session_key, None)  # Clean potentially invalid session key
                    return redirect(url_for('admin_evaluate_csv'))  # Redirect if file is gone

                # Determine file type from extension
                file_ext = os.path.splitext(permanent_filepath)[1].lower()
                if file_ext not in ['.csv', '.xls', '.xlsx']:
                    flash(f'نوع فایل ذخیره شده نامعتبر است: {file_ext}', 'danger')
                    session.pop(perm_filepath_session_key, None)
                    # Optionally delete the invalid file here if desired
                    # if os.path.exists(permanent_filepath): os.remove(permanent_filepath)
                    return redirect(url_for('admin_evaluate_csv'))

                # --- Build configuration ---
                config = {};
                criteria_config = {}
                # (Same logic as before to build config and criteria_config)
                submitted_columns = [key[4:] for key in request.form if key.startswith('use_')]
                for col in submitted_columns:
                    if request.form.get(f'use_{col}') == 'on':
                        try:
                            weight = float(request.form.get(f'weight_{col}', 1))
                        except ValueError:
                            weight = 1
                        var_type = request.form.get(f'type_{col}', 'numeric')
                        config[col] = {'weight': weight, 'type': var_type}
                        if var_type == 'descriptive':
                            criteria_config[col] = []
                            for prefix in ['criteria', 'existing_criteria']:
                                values = request.form.getlist(f'{prefix}_{col}[]');
                                scores = request.form.getlist(f'{prefix.replace("criteria", "score")}_{col}[]')
                                for i in range(len(values)):
                                    if values[i].strip() and i < len(scores):
                                        try:
                                            s_val = float(scores[i]);
                                            c_val = values[i].strip()
                                            if prefix == 'criteria' or not any(
                                                d['criterion'] == c_val for d in criteria_config[col]): criteria_config[
                                                col].append({'criterion': c_val, 'score': s_val})
                                        except (ValueError, IndexError, TypeError):
                                            continue
                if not config:
                    flash('هیچ ستونی برای ارزیابی انتخاب نشده است.', 'danger')
                    # Keep permanent file path in session, allow user to re-configure
                    return redirect(url_for('admin_evaluate_csv'))
                # --- End Build Configuration ---

                # --- Read DataFrame from PERMANENT file ---
                try:
                    if file_ext == '.csv':
                        df = pd.read_csv(permanent_filepath, encoding='utf-8-sig')
                    else:
                        df = pd.read_excel(permanent_filepath)
                except Exception as e_read:
                    flash(f'خطا در خواندن فایل ذخیره شده برای پردازش: {e_read}', 'danger');
                    print(f"Error reading {permanent_filepath} for processing: {e_read}")
                    # Keep permanent file path in session, allow user to re-configure
                    return redirect(url_for('admin_evaluate_csv'))
                # --- End Read DataFrame ---

                # --- Process Rows ---
                # (Row processing logic remains the same)
                valid_rows = [];
                error_saving_rows = [];
                successful_evaluations = 0
                all_grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()
                evaluation_batch_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
                print(f"Processing batch ID: {evaluation_batch_id} using file {permanent_filepath}")

                for index, row in df.iterrows():
                    score = 0.0;
                    parameter_scores = {}
                    for col, params in config.items():  # Process based on config
                        if col not in row.index: continue  # Skip if col missing in row
                        val = row.get(col);
                        param_score = 0.0
                        if params['type'] == 'numeric':  # Numeric processing
                            try:
                                numeric_val = 0.0 if pd.isnull(val) or (
                                            isinstance(val, str) and val.strip() == '') else float(val)
                            except (ValueError, TypeError):
                                numeric_val = 0.0
                            param_score = params['weight'] * numeric_val
                        elif params['type'] == 'descriptive':  # Descriptive processing
                            val_str = "" if pd.isnull(val) or (isinstance(val, str) and val.strip() == '') else str(
                                val).strip()
                            if val_str:  # Only lookup if value exists
                                found_match = False
                                if col in criteria_config:  # Check configured criteria first
                                    for crit_data in criteria_config[col]:
                                        if crit_data['criterion'].lower() == val_str.lower(): param_score = params[
                                                                                                                'weight'] * \
                                                                                                            crit_data[
                                                                                                                'score']; found_match = True; break
                                if not found_match:  # Check DB if not found in config
                                    try:
                                        crit_db = DescriptiveCriterion.query.filter(
                                            DescriptiveCriterion.parameter_name.ilike(col),
                                            DescriptiveCriterion.criterion.ilike(val_str)).first()
                                        if crit_db: param_score = params['weight'] * crit_db.score
                                    except Exception as e_lk:
                                        print(f"Crit lookup err: {e_lk}")
                        score += param_score;
                        parameter_scores[col] = param_score  # Accumulate score

                    score = round(score, 2);
                    assigned_grade = "بدون درجه"  # Assign grade
                    for mapping in all_grade_mappings:
                        if score >= mapping.min_score: assigned_grade = mapping.grade_letter; break

                    row_dict = {};  # Prepare row dictionary for output/DB
                    for k, v in row.items():  # Serialize row data safely
                        key_str = str(k)
                        if pd.isnull(v):
                            row_dict[key_str] = None
                        elif isinstance(v, (datetime, date, pd.Timestamp)):
                            row_dict[key_str] = v.isoformat()
                        else:
                            try:
                                row_dict[key_str] = v if isinstance(v, (str, int, float, bool)) else str(v)
                            except Exception:
                                row_dict[key_str] = "[Serialization Error]"
                    row_dict["نمره کل"] = f"{score:.2f}";
                    row_dict["درجه"] = assigned_grade;
                    row_dict["batch_id"] = evaluation_batch_id
                    for param, p_score in parameter_scores.items():  # Add parameter scores
                        safe_param_name = ''.join(c if c.isalnum() else '_' for c in str(param));
                        score_key = f"نمره_{safe_param_name}";
                        row_dict[score_key] = f"{p_score:.2f}"
                    valid_rows.append(row_dict)

                    # --- Database Saving ---
                    try:  # Attempt to save evaluation record
                        csv_record = CSVEvaluationRecord(row_data=row_dict, total_score=score,
                                                         assigned_grade=assigned_grade,
                                                         evaluated_at=datetime.now(timezone.utc),
                                                         batch_id=evaluation_batch_id)
                        cust_number_col = "Number";
                        cust_number = row.get(cust_number_col);
                        customer_province = None
                        if cust_number and not pd.isnull(cust_number):  # Try linking customer
                            cust_number_str = str(cust_number).strip()
                            if cust_number_str:
                                customer = CustomerReport.query.filter_by(number=cust_number_str).first()
                                if customer:
                                    csv_record.customer_id = customer.id;
                                    customer.grade = assigned_grade;
                                    customer_province = customer.province;
                                    csv_record.province = customer_province
                                    try:
                                        db.session.add(CustomerEvaluation(customer_id=customer.id, total_score=score,
                                                                          assigned_grade=assigned_grade,
                                                                          evaluated_at=datetime.now(timezone.utc),
                                                                          evaluation_method="csv",
                                                                          batch_id=evaluation_batch_id,
                                                                          province=customer_province))
                                    except Exception as e_ce:
                                        print(f"Err CustEval: {e_ce}")
                        db.session.add(csv_record);
                        db.session.commit();
                        successful_evaluations += 1
                    except Exception as e_db:  # Handle DB save errors
                        db.session.rollback();
                        print(f"DB ERROR row {index}, Batch {evaluation_batch_id}: {e_db}");
                        error_info = {};
                        try:
                            error_info = row.to_dict(); error_info['error_message'] = str(e_db)
                        except Exception as e_conv:
                            error_info = {'row_index': index, 'error_message': str(e_db),
                                          'conversion_error': str(e_conv)}
                        error_saving_rows.append(error_info)
                # --- End Row Processing ---

                # Save descriptive criteria definitions
                if criteria_config:
                    try:
                        for col, criteria_list in criteria_config.items():
                            for crit_data in criteria_list:
                                existing = DescriptiveCriterion.query.filter_by(parameter_name=col, criterion=crit_data[
                                    'criterion']).first()
                                if not existing:
                                    db.session.add(
                                        DescriptiveCriterion(parameter_name=col, criterion=crit_data['criterion'],
                                                             score=crit_data['score']))
                                elif existing.score != crit_data['score']:
                                    existing.score = crit_data['score']
                        db.session.commit();
                        print("Descriptive criteria definitions updated/saved.")
                    except Exception as e_crit:
                        db.session.rollback(); print(f"Error saving criteria definitions: {e_crit}"); flash(
                            f'خطا در ذخیره‌سازی معیارها: {e_crit}', 'danger')

                # Final status message
                total_rows = len(df);
                failed_saves = len(error_saving_rows)
                flash(
                    f'ارزیابی کامل شد. {successful_evaluations} رکورد ذخیره شد. {failed_saves} خطا در ذخیره‌سازی (از {total_rows} ردیف).',
                    'info' if failed_saves == 0 else 'warning')
                if failed_saves > 0: print(f"Batch {evaluation_batch_id}: {failed_saves} rows failed DB save.")

                descriptive_params = [col for col, params in config.items() if params['type'] == 'descriptive']

                # Clear the session key AFTER successful processing
                session.pop(perm_filepath_session_key, None)
                print(f"Cleared session key {perm_filepath_session_key} after successful processing.")

                # Render results page
                return render_template('admin/evaluate_csv.html',
                                       valid_rows=valid_rows, error_saving_rows=error_saving_rows,
                                       descriptive_params=descriptive_params, config=config,
                                       grade_mappings=all_grade_mappings, batch_id=evaluation_batch_id)

            except Exception as e_configure:
                flash(f'خطای کلی در مرحله پردازش: {e_configure}', 'danger')
                print(f"Error during 'configure' action processing: {e_configure}")
                # Don't clear session key on general error, maybe user can retry config
                return redirect(url_for('admin_evaluate_csv'))

            # --- REMOVED the finally block for cleanup ---
            # Cleanup is no longer needed as file is permanent

        else:  # Invalid action POSTed
            flash('درخواست نامعتبر.', 'danger')
            # Clean up session key if it exists from an unknown state
            session.pop(perm_filepath_session_key, None)
            return redirect(url_for('admin_evaluate_csv'))

    # --- End of admin_evaluate_csv function ---
    # --------------------- NEW ROUTES FOR BATCH EVALUATION MANAGEMENT ---------------------
    # Replace the existing view_batch_evaluations function with this updated version
    # Replace the existing view_batch_evaluations function with this updated version

    # Fix for the 'min' is undefined error in batch_evaluations.html

    # Option 1: Fix in the view_batch_evaluations function - add a simple min function to the template context
    @app.route('/admin/batch_evaluations/<batch_id>')
    @login_required
    def view_batch_evaluations(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get all provinces for the dropdown
        provinces = Province.query.order_by(Province.name).all()

        # First try CSVEvaluationRecord
        csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).order_by(
            CSVEvaluationRecord.total_score.desc()
        ).all()

        # Check if there's a province assigned to this batch
        current_province = None
        if csv_evals and csv_evals[0].province:
            province_name = csv_evals[0].province
            current_province = Province.query.filter_by(name=province_name).first()

        # If no CSV records found, fallback to CustomerEvaluation
        if not csv_evals:
            customer_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).order_by(
                desc(CustomerEvaluation.total_score)
            ).all()

            # Check for province in customer evaluations
            if customer_evals and customer_evals[0].province:
                province_name = customer_evals[0].province
                current_province = Province.query.filter_by(name=province_name).first()

            if not customer_evals:
                flash('دسته ارزیابی یافت نشد.', 'warning')
                return redirect(url_for('admin_quotas'))

            # Get statistics for customer_evals
            grade_dist = db.session.query(
                CustomerEvaluation.assigned_grade,
                db.func.count(CustomerEvaluation.id).label('count')
            ).filter(CustomerEvaluation.batch_id == batch_id). \
                group_by(CustomerEvaluation.assigned_grade).all()

            # Format as dictionary for easy access in template
            grade_counts = {grade.assigned_grade: grade.count for grade in grade_dist}

            # Calculate average score
            avg_score = db.session.query(
                db.func.avg(CustomerEvaluation.total_score)
            ).filter(CustomerEvaluation.batch_id == batch_id).scalar() or 0

            # Get batch grade targets
            batch_targets = []
            if current_province:
                batch_targets = BatchGradeTarget.query.filter_by(
                    batch_id=batch_id,
                    province_id=current_province.id,
                    store_type_id=None  # Only get general targets, not store-type specific
                ).order_by(BatchGradeTarget.grade, BatchGradeTarget.product_id).all()

            # Get all products for target display
            products = Product.query.all()

            # Get store types for quota management
            store_types = StoreType.query.all()

            # Get product exclusion rules
            exclusion_rules = ProductExclusionRule.query.filter_by(batch_id=batch_id).all()
            exclusions_by_store_type = {}
            for store_type in store_types:
                exclusions = [rule.product_id for rule in exclusion_rules if rule.store_type_id == store_type.id]
                exclusions_by_store_type[store_type.id] = exclusions

            # Get store type allocations
            store_allocations = StoreTypeAllocation.query.filter_by(
                batch_id=batch_id,
                province_id=current_province.id if current_province else None
            ).all()
            allocations_by_store_type = {alloc.store_type_id: alloc.percentage for alloc in store_allocations}

            # Calculate total allocation percentage
            total_allocation = sum(allocations_by_store_type.values())
            remaining_allocation = 100 - total_allocation

            # Add a safe_min function for the template to use
            def safe_min(a, b):
                return min(a, b)

            return render_template('admin/batch_evaluations.html',
                                   batch_id=batch_id,
                                   evaluations=customer_evals,
                                   grade_counts=grade_counts,
                                   avg_score=round(avg_score, 2),
                                   date=customer_evals[0].evaluated_at if customer_evals else None,
                                   is_csv_record=False,
                                   provinces=provinces,
                                   current_province=current_province,
                                   batch_targets=batch_targets,
                                   products=products,
                                   store_types=store_types,
                                   exclusions_by_store_type=exclusions_by_store_type,
                                   allocations_by_store_type=allocations_by_store_type,
                                   total_allocation=total_allocation,
                                   remaining_allocation=remaining_allocation,
                                   safe_min=safe_min)  # Pass the function to the template
        else:
            # Get grade distribution for CSVEvaluationRecord
            grade_query = text("""
                SELECT assigned_grade, COUNT(*) as count 
                FROM csv_evaluation_record 
                WHERE batch_id = :batch_id 
                GROUP BY assigned_grade
            """)
            grade_dist = db.session.execute(grade_query, {"batch_id": batch_id}).fetchall()
            grade_counts = {grade[0]: grade[1] for grade in grade_dist}

            # Calculate average score
            avg_query = text("SELECT AVG(total_score) FROM csv_evaluation_record WHERE batch_id = :batch_id")
            avg_score = db.session.execute(avg_query, {"batch_id": batch_id}).scalar() or 0

            # Get batch grade targets
            batch_targets = []
            if current_province:
                batch_targets = BatchGradeTarget.query.filter_by(
                    batch_id=batch_id,
                    province_id=current_province.id,
                    store_type_id=None  # Only get general targets, not store-type specific
                ).order_by(BatchGradeTarget.grade, BatchGradeTarget.product_id).all()

            # Get all products for target display
            products = Product.query.all()

            # Get store types for quota management
            store_types = StoreType.query.all()

            # Get product exclusion rules
            exclusion_rules = ProductExclusionRule.query.filter_by(batch_id=batch_id).all()
            exclusions_by_store_type = {}
            for store_type in store_types:
                exclusions = [rule.product_id for rule in exclusion_rules if rule.store_type_id == store_type.id]
                exclusions_by_store_type[store_type.id] = exclusions

            # Get store type allocations
            store_allocations = StoreTypeAllocation.query.filter_by(
                batch_id=batch_id,
                province_id=current_province.id if current_province else None
            ).all()
            allocations_by_store_type = {alloc.store_type_id: alloc.percentage for alloc in store_allocations}

            # Calculate total allocation percentage
            total_allocation = sum(allocations_by_store_type.values())
            remaining_allocation = 100 - total_allocation

            # Add a safe_min function for the template to use
            def safe_min(a, b):
                return min(a, b)

            return render_template('admin/batch_evaluations.html',
                                   batch_id=batch_id,
                                   evaluations=csv_evals,
                                   grade_counts=grade_counts,
                                   avg_score=round(avg_score, 2),
                                   date=csv_evals[0].evaluated_at if csv_evals else None,
                                   is_csv_record=True,
                                   provinces=provinces,
                                   current_province=current_province,
                                   batch_targets=batch_targets,
                                   products=products,
                                   store_types=store_types,
                                   exclusions_by_store_type=exclusions_by_store_type,
                                   allocations_by_store_type=allocations_by_store_type,
                                   total_allocation=total_allocation,
                                   remaining_allocation=remaining_allocation,
                                   safe_min=safe_min)  # Pass the function to the template
    @app.route('/admin/batch_evaluations/delete/<batch_id>', methods=['POST'])
    @login_required
    def delete_batch_evaluations(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
            
        try:
            # Delete from CSVEvaluationRecord
            csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()
            for eval in csv_evals:
                db.session.delete(eval)
            
            # Also delete from CustomerEvaluation for compatibility
            customer_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).all()
            for eval in customer_evals:
                db.session.delete(eval)
                
            db.session.commit()
            flash(f'دسته ارزیابی با موفقیت حذف شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف دسته ارزیابی: {e}', 'danger')
            
        return redirect(url_for('admin_quotas'))
        
    @app.route('/admin/evaluations/delete/<int:eval_id>', methods=['POST'])
    @login_required
    def delete_evaluation(eval_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
            
        try:
            # First try CSVEvaluationRecord
            evaluation = CSVEvaluationRecord.query.get(eval_id)
            
            # If not found, try CustomerEvaluation
            if not evaluation:
                evaluation = CustomerEvaluation.query.get_or_404(eval_id)
            
            # Save batch_id for redirect
            batch_id = evaluation.batch_id
            
            db.session.delete(evaluation)
            db.session.commit()
            flash('ارزیابی با موفقیت حذف شد.', 'success')
            
            # Redirect based on where the delete was initiated
            if batch_id:
                return redirect(url_for('view_batch_evaluations', batch_id=batch_id))
            else:
                return redirect(url_for('admin_quotas'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف ارزیابی: {e}', 'danger')
            
        return redirect(url_for('admin_quotas'))

    # Edit individual evaluation
    @app.route('/admin/evaluations/edit/<int:eval_id>', methods=['GET', 'POST'])
    @login_required
    def edit_evaluation(eval_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        
        # First try to find in CSVEvaluationRecord
        evaluation = CSVEvaluationRecord.query.get(eval_id)
        is_csv_record = True
        
        # If not found, try CustomerEvaluation
        if not evaluation:
            evaluation = CustomerEvaluation.query.get_or_404(eval_id)
            is_csv_record = False
        
        if request.method == 'POST':
            try:
                new_score = float(request.form.get('total_score'))
                
                # Get appropriate grade based on the score
                mapping_obj = GradeMapping.query.filter(GradeMapping.min_score <= new_score)\
                            .order_by(GradeMapping.min_score.desc()).first()
                
                if mapping_obj:
                    new_grade = mapping_obj.grade_letter
                else:
                    new_grade = "بدون درجه"
                
                # Update evaluation record
                evaluation.total_score = new_score
                evaluation.assigned_grade = new_grade
                
                # If it's a CSVEvaluationRecord, also update the row_data
                if is_csv_record and evaluation.row_data:
                    evaluation.row_data["نمره کل"] = f"{new_score:.2f}"
                    evaluation.row_data["درجه"] = new_grade
                
                # If associated with a customer, update customer's grade
                if hasattr(evaluation, 'customer_id') and evaluation.customer_id:
                    customer = None
                    if is_csv_record:
                        customer = CustomerReport.query.get(evaluation.customer_id)
                    else:
                        customer = evaluation.customer
                    
                    if customer:
                        customer.grade = new_grade
                
                db.session.commit()
                flash('ارزیابی با موفقیت ویرایش شد.', 'success')
                
                # Redirect based on where the edit was initiated (batch view or main quotas page)
                if evaluation.batch_id:
                    return redirect(url_for('view_batch_evaluations', batch_id=evaluation.batch_id))
                else:
                    return redirect(url_for('admin_quotas'))
            
            except ValueError:
                flash('نمره باید عددی باشد.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در ویرایش ارزیابی: {e}', 'danger')
        
        # Modify the template to handle both types
        return render_template('admin/edit_evaluation.html', 
                            evaluation=evaluation, 
                            grade_mappings=GradeMapping.query.order_by(GradeMapping.min_score.desc()).all(),
                            is_csv_record=is_csv_record)

    # --------------------- ADMIN: QUOTA CATEGORIES MANAGEMENT ---------------------
    @app.route('/admin/quota_categories', methods=['GET', 'POST'])
    @login_required
    def admin_quota_categories():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        form = QuotaCategoryForm()
        quota_list = QuotaCategory.query.all()
        
        if form.validate_on_submit():
            category = form.category.data.strip()
            monthly_quota = form.monthly_quota.data
            
            new_category = QuotaCategory(
                category=category,
                monthly_quota=monthly_quota
            )
            
            try:
                db.session.add(new_category)
                db.session.commit()
                flash(f'سهمیه برای دسته {category} با موفقیت تعریف شد.', 'success')
                return redirect(url_for('admin_quota_categories'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ذخیره سهمیه. احتمالاً این دسته قبلاً تعریف شده است.', 'danger')
        
        return render_template('admin/quota_categories.html', form=form, quota_list=quota_list)

    @app.route('/admin/quota_categories/delete/<int:qc_id>', methods=['POST'])
    @login_required
    def delete_quota_category(qc_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        
        quota_category = QuotaCategory.query.get_or_404(qc_id)
        db.session.delete(quota_category)
        db.session.commit()
        flash('سهمیه با موفقیت حذف شد.', 'info')
        return redirect(url_for('admin_quota_categories'))

    # --------------------- ADMIN: PROVINCE EVALUATION ---------------------
    @app.route('/admin/province-evaluation', methods=['GET'])
    @login_required
    def admin_province_evaluation():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        return render_template('admin/province_evaluation.html')  # Changed path here

    @app.route('/admin/upload-province-evaluation', methods=['POST'])
    @login_required
    def admin_upload_province_evaluation():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        action = request.form.get('action')

        if action == 'upload_file':
            file = request.files.get('file')
            if not file:
                flash('هیچ فایلی انتخاب نشده است.', 'danger')
                return redirect(url_for('admin_province_evaluation'))

            filename = file.filename.lower()
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(file)
                elif filename.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(file)
                else:
                    flash('فایل پشتیبانی نمی‌شود. لطفاً CSV یا Excel آپلود کنید.', 'danger')
                    return redirect(url_for('admin_province_evaluation'))
            except Exception as e:
                flash(f'خطا در خواندن فایل: {e}', 'danger')
                return redirect(url_for('admin_province_evaluation'))

            # Check if the file has a province column
            province_column_candidates = ['استان', 'province', 'Province', 'استان ها', 'استان‌ها']
            province_column = None

            for candidate in province_column_candidates:
                if candidate in df.columns:
                    province_column = candidate
                    break

            if not province_column:
                flash('فایل باید شامل ستونی با نام استان باشد.', 'danger')
                return redirect(url_for('admin_province_evaluation'))

            columns = list(df.columns)

            # Take only the first 10 rows for preview
            preview_data = df.head(10).to_dict('records')
            file_content = df.to_csv(index=False)

            # Get all grade mappings for debugging/display
            grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()

            # Get all provinces and their population data
            provinces = Province.query.all()
            province_population = {province.name: province.population for province in provinces}

            # Calculate cover ability based on population
            cover_ability_data = []
            for _, row in df.iterrows():
                province_name = row.get(province_column)
                if province_name in province_population:
                    population = province_population[province_name]

                    # Calculate the total of all numeric values in the row
                    # This will be used instead of just looking for a 'total_score' column
                    row_total = 0
                    for col, val in row.items():
                        # Skip non-numeric columns and the province column
                        if col != province_column and isinstance(val, (int, float)):
                            row_total += val

                    # Calculate the cover ability (total scores - population)
                    cover_ability = row_total - population

                    # Create a copy of the row to avoid modifying the original DataFrame
                    row_copy = row.copy()
                    row_copy['total_score'] = row_total
                    row_copy['توانایی پوشش بر اساس جمعیت'] = cover_ability
                    cover_ability_data.append(row_copy)

            return render_template('admin/province_evaluation_configure.html',
                                   columns=columns,
                                   file_content=file_content,
                                   grade_mappings=grade_mappings,
                                   preview_data=preview_data,
                                   cover_ability_data=cover_ability_data,
                                   province_column=province_column,
                                   province_population=province_population)

        flash('عملیات نامشخص.', 'danger')
        return redirect(url_for('admin_province_evaluation'))

    @app.route('/admin/configure-province-evaluation', methods=['POST'])
    @login_required
    def admin_configure_province_evaluation():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        action = request.form.get('action')

        if action == 'configure':
            file_content = request.form.get('file_content')
            if not file_content:
                flash('مشکل در بازیابی فایل آپلود شده.', 'danger')
                return redirect(url_for('admin_province_evaluation'))

            # Find province column
            province_column = request.form.get('province_column')
            if not province_column:
                province_column_candidates = ['استان', 'province', 'Province', 'استان ها', 'استان‌ها']
                for candidate in province_column_candidates:
                    if request.form.get(f'use_{candidate}'):
                        province_column = candidate
                        break

            if not province_column:
                flash('ستون استان را انتخاب نکرده‌اید.', 'danger')
                return redirect(url_for('admin_province_evaluation'))

            config = {}
            criteria_config = {}

            # Build configuration for each column from checkboxes, weights, and types
            for key in request.form:
                if key.startswith('use_'):
                    col = key[4:]
                    if request.form.get(key) == 'on':
                        try:
                            weight = float(request.form.get(f'weight_{col}', 1))
                        except ValueError:
                            weight = 1
                        var_type = request.form.get(f'type_{col}', 'numeric')
                        config[col] = {'weight': weight, 'type': var_type}

                        # For descriptive parameters, collect the criteria data
                        if var_type == 'descriptive':
                            criteria_config[col] = []

                            # Get new criteria added in the form
                            criteria_values = request.form.getlist(f'criteria_{col}[]')
                            criteria_scores = request.form.getlist(f'score_{col}[]')

                            for i in range(len(criteria_values)):
                                if i < len(criteria_scores):
                                    try:
                                        score = float(criteria_scores[i])
                                        criteria_config[col].append({
                                            'criterion': criteria_values[i],
                                            'score': score
                                        })
                                    except (ValueError, IndexError):
                                        continue

                            # Get existing criteria (that may have been edited)
                            existing_criteria = request.form.getlist(f'existing_criteria_{col}[]')
                            existing_scores = request.form.getlist(f'existing_score_{col}[]')

                            for i in range(len(existing_criteria)):
                                if i < len(existing_scores):
                                    try:
                                        score = float(existing_scores[i])
                                        criteria_config[col].append({
                                            'criterion': existing_criteria[i],
                                            'score': score
                                        })
                                    except (ValueError, IndexError):
                                        continue

            if not config:
                flash('هیچ ستونی انتخاب نشده است.', 'danger')
                return redirect(url_for('admin_province_evaluation'))

            try:
                df = pd.read_csv(io.StringIO(file_content))
            except Exception as e:
                flash(f'خطا در بازیابی فایل: {e}', 'danger')
                return redirect(url_for('admin_province_evaluation'))

            valid_rows = []
            missing_rows = []
            total_scores = []
            grades = []

            # Get all grade mappings for scoring
            all_grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()

            # Create a batch identifier for this evaluation session
            evaluation_batch_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
            print(f"Created batch ID: {evaluation_batch_id}")

            # Process each row
            for index, row in df.iterrows():
                missing = False

                # Check for province name (skip if missing)
                if pd.isna(row.get(province_column)) or row.get(province_column) == '':
                    missing = True
                    missing_rows.append(row.to_dict())
                    continue

                # Check for missing numeric values for selected numeric parameters
                for col, params in config.items():
                    if params['type'] == 'numeric' and pd.isna(row.get(col)):
                        missing = True
                        break

                if missing:
                    missing_rows.append(row.to_dict())
                    continue

                score = 0
                parameter_scores = {}

                for col, params in config.items():
                    val = row.get(col, 0)
                    if pd.isna(val):
                        val = 0

                    # Handle different parameter types
                    if params['type'] == 'numeric':
                        try:
                            numeric_val = float(val)
                        except:
                            numeric_val = 0
                        param_score = params['weight'] * numeric_val

                    else:
                        # For descriptive parameters, look up the corresponding criterion
                        val_str = str(val).strip()
                        param_score = 0

                        # First check if we have specific criteria defined in the form
                        if col in criteria_config:
                            found_match = False
                            for criterion_data in criteria_config[col]:
                                if criterion_data['criterion'].lower() == val_str.lower():
                                    # Multiply by weight here
                                    param_score = params['weight'] * criterion_data['score']
                                    found_match = True
                                    break

                            # If no match was found in the form criteria, check database
                            if not found_match:
                                # Otherwise use existing criteria from database
                                crit = DescriptiveCriterion.query.filter(
                                    DescriptiveCriterion.parameter_name.ilike(col),
                                    DescriptiveCriterion.criterion.ilike(val_str)
                                ).first()
                                if crit:
                                    param_score = params['weight'] * crit.score

                    # Add to total score and track individual parameter score
                    score += param_score
                    parameter_scores[col] = param_score

                # Round score to 2 decimal places for consistency
                score = round(score, 2)
                total_scores.append(score)

                # Find the appropriate grade based on the score
                mapping_obj = GradeMapping.query.filter(GradeMapping.min_score <= score) \
                    .order_by(GradeMapping.min_score.desc()).first()

                if mapping_obj:
                    assigned_grade = mapping_obj.grade_letter
                else:
                    assigned_grade = "بدون درجه"

                grades.append(assigned_grade)

                row_dict = row.to_dict()
                row_dict["نمره کل"] = f"{score:.2f}"
                row_dict["درجه"] = assigned_grade
                row_dict["batch_id"] = evaluation_batch_id

                # Add parameter scores to row data
                for param, param_score in parameter_scores.items():
                    row_dict[f"نمره {param}"] = f"{param_score:.2f}"

                # Calculate the cover ability based on the population
                province_name = row.get(province_column)
                province = Province.query.filter_by(name=province_name).first()
                if province:
                    population = province.population
                    # Now use the calculated score correctly
                    cover_ability = score - population
                    row_dict["توانایی پوشش بر اساس جمعیت"] = round(cover_ability, 2)
                    # Also save total score for display
                    row_dict["total_score"] = score

                valid_rows.append(row_dict)

            # Save the criteria to database if they don't exist yet
            try:
                for col, criteria_list in criteria_config.items():
                    for criteria_data in criteria_list:
                        existing = DescriptiveCriterion.query.filter_by(
                            parameter_name=col,
                            criterion=criteria_data['criterion']
                        ).first()

                        if not existing:
                            new_criterion = DescriptiveCriterion(
                                parameter_name=col,
                                criterion=criteria_data['criterion'],
                                score=criteria_data['score']
                            )
                            db.session.add(new_criterion)
                        elif existing.score != criteria_data['score']:
                            # Update score if it's different
                            existing.score = criteria_data['score']

                db.session.commit()
                print("Successfully saved all criteria")
            except Exception as e:
                db.session.rollback()
                print(f"Error saving criteria: {e}")
                flash(f'خطا در ذخیره‌سازی معیارها: {e}', 'danger')

            # Get all unique province names and their scores/grades for charts
            province_names = [row[province_column] for row in valid_rows]
            province_scores = [float(row["نمره کل"]) for row in valid_rows]
            province_grades = [row["درجه"] for row in valid_rows]

            # Get descriptive parameters for the template
            descriptive_params = [col for col, params in config.items() if params['type'] == 'descriptive']

            # For each valid row, add the population data
            for row in valid_rows:
                province_name = row.get(province_column)
                province = Province.query.filter_by(name=province_name).first()
                if province:
                    row['جمعیت'] = province.population

            return render_template('admin/province_evaluation_results.html',
                                   valid_rows=valid_rows,
                                   missing_rows=missing_rows,
                                   descriptive_params=descriptive_params,
                                   config=config,
                                   grades=grades,
                                   grade_mappings=all_grade_mappings,
                                   batch_id=evaluation_batch_id,
                                   province_column=province_column,
                                   province_names=province_names,
                                   province_scores=province_scores,
                                   province_grades=province_grades)
        else:
            flash('عملیات نامشخص.', 'danger')
            return redirect(url_for('admin_province_evaluation'))
    # --------------------- API ENDPOINTS ---------------------
    @app.route('/api/observer/marketer-locations')
    @login_required
    def api_marketer_locations():
        if current_user.role not in ['admin', 'observer']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        marketers = User.query.filter_by(role='marketer').all()
        result = []
        
        for marketer in marketers:
            location_data = {
                'id': marketer.id,
                'name': marketer.fullname or marketer.username,
                'lat': marketer.current_lat,
                'lng': marketer.current_lng,
                'last_update': marketer.last_location_update.strftime('%Y-%m-%d %H:%M:%S') if marketer.last_location_update else None
            }
            result.append(location_data)
        
        return jsonify(result)

    # Add this route to your app.py file
    # Add this route to your app.py file
    @app.route('/admin/update-province-product-targets', methods=['POST'])
    @login_required
    def update_province_product_targets():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        province_id = request.form.get('province_id')
        batch_id = request.form.get('batch_id')

        if not province_id:
            flash('استان مشخص نشده است.', 'danger')
            return redirect(url_for('admin_products'))

        try:
            # Get all products
            products = Product.query.all()
            province = Province.query.get_or_404(province_id)

            for product in products:
                # Check if percentage is provided
                percentage_key = f'percentage_{product.id}'
                if percentage_key in request.form and request.form[percentage_key].strip():
                    percentage = float(request.form[percentage_key])

                    # Get or create target
                    target = ProductProvinceTarget.query.filter_by(
                        product_id=product.id,
                        province_id=province_id
                    ).first()

                    if not target:
                        target = ProductProvinceTarget(
                            product_id=product.id,
                            province_id=province_id
                        )
                        db.session.add(target)

                    # Update percentage
                    target.liter_percentage = percentage
                    target.shrink_percentage = percentage

                    # Check if specific capacity values are provided
                    liter_key = f'liter_{product.id}'
                    if liter_key in request.form and request.form[liter_key].strip():
                        target.liter_capacity = float(request.form[liter_key])
                    elif product.liter_capacity:
                        # Calculate from percentage if not explicitly provided
                        target.liter_capacity = product.liter_capacity * (percentage / 100)

                    shrink_key = f'shrink_{product.id}'
                    if shrink_key in request.form and request.form[shrink_key].strip():
                        target.shrink_capacity = float(request.form[shrink_key])
                    elif product.shrink_capacity:
                        # Calculate from percentage if not explicitly provided
                        target.shrink_capacity = product.shrink_capacity * (percentage / 100)

            db.session.commit()
            flash(f'تارگت‌های محصول برای استان {province.name} با موفقیت به‌روزرسانی شد.', 'success')

            # Clear session variables after successful update
            if batch_id:
                return redirect(url_for('view_batch_evaluations', batch_id=batch_id))

        except ValueError as e:
            db.session.rollback()
            flash(f'خطا در مقادیر وارد شده: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در به‌روزرسانی تارگت‌ها: {str(e)}', 'danger')

        return redirect(url_for('admin_products'))

    # Add these routes to your app.py file

    @app.route('/admin/routes-upload', methods=['GET'])
    @login_required
    def admin_routes_upload():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get provinces
        provinces = Province.query.order_by(Province.name).all()

        # Get available marketers for assignment
        marketers = User.query.filter_by(role='marketer').all()

        # Get existing routes
        routes = Route.query.all()

        # Prepare route data for frontend
        route_data = []
        for route in routes:
            # Get province name if available
            province_name = None
            if route.province:
                province = Province.query.filter_by(id=route.province).first()
                if province:
                    province_name = province.name

            route_data.append({
                'id': route.id,
                'name': route.name,
                'description': route.description,
                'province_id': route.province,
                'province': province_name,
                'color': getattr(route, 'color', '#4f46e5'),  # Default color if not set
                'points': [
                    {
                        'id': point.id,
                        'name': point.name,
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'address': point.address,
                        'order': point.order
                    } for point in route.points
                ],
                'assignments': [
                    {
                        'id': assignment.id,
                        'marketer_id': assignment.marketer_id
                    } for assignment in route.assignments if assignment.is_active
                ]
            })

        # Convert routes to JSON for JavaScript
        routes_json = json.dumps(route_data)

        # Check if we're showing file preview
        # Modified condition: consider columns existing as an indication of file uploaded
        has_columns = 'columns' in session and len(session.get('columns', [])) > 0
        file_uploaded = has_columns or 'temp_filepath' in session

        # Get data from session
        temp_filepath = session.get('temp_filepath', '')
        columns = session.get('columns', [])
        preview_data = session.get('preview_data', [])
        file_type = session.get('file_type', '')
        province_id = session.get('province_id', '')

        # Debug log
        print(f"File uploaded: {file_uploaded}")
        print(f"Columns: {columns}")

        return render_template('admin/routes_upload.html',
                               provinces=provinces,
                               marketers=marketers,
                               routes=route_data,
                               routes_json=routes_json,
                               file_uploaded=file_uploaded,
                               file_content='',  # No longer needed
                               columns=columns,
                               preview_data=preview_data,
                               file_type=file_type,
                               province_id=province_id)

    @app.route('/admin/upload-routes-file', methods=['POST'])
    @login_required
    def admin_upload_routes_file():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        file = request.files.get('file')
        province_id = request.form.get('province')

        if not file:
            flash('لطفاً یک فایل انتخاب کنید.', 'danger')
            return redirect(url_for('admin_routes_upload'))

        try:
            # Determine file type
            filename = file.filename.lower()

            # Create a unique filename
            unique_filename = f"{uuid.uuid4()}_{secure_filename(filename)}"
            temp_filepath = os.path.join(get_temp_dir(), unique_filename)

            # Save the file to the temp directory
            file.save(temp_filepath)

            # Determine file type and load with pandas
            if filename.endswith('.csv'):
                df = pd.read_csv(temp_filepath)
                file_type = 'csv'
            elif filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(temp_filepath)
                file_type = 'excel'
            else:
                # Clean up the file if it's not a supported type
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                flash('فرمت فایل پشتیبانی نمی‌شود. لطفاً فایل CSV یا Excel آپلود کنید.', 'danger')
                return redirect(url_for('admin_routes_upload'))

            # Convert columns to list of strings for JSON serialization
            columns = [str(col) for col in df.columns]

            # Convert DataFrame to records (just the first 5 rows for preview)
            preview_records = df.head(5).to_dict('records')

            # Format the preview data for proper serialization
            preview_data = []
            for record in preview_records:
                formatted_record = {}
                for key, value in record.items():
                    formatted_record[str(key)] = str(value) if pd.notna(value) else ""
                preview_data.append(formatted_record)

            # Store only the file path and metadata in the session, not the file content
            session['temp_filepath'] = temp_filepath
            session['file_type'] = file_type
            session['columns'] = columns
            session['preview_data'] = preview_data
            session['province_id'] = province_id

            flash('فایل با موفقیت بارگذاری شد. لطفاً پارامترها را تنظیم کنید.', 'success')
            return redirect(url_for('admin_routes_upload', tab='upload'))

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            # Clean up the file in case of error
            if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            flash(f'خطا در بارگذاری فایل: {str(e)}', 'danger')
            return redirect(url_for('admin_routes_upload'))

    # Add this new API endpoint to app.py

    @app.route('/api/csv_evaluation/<int:eval_id>')
    @login_required
    def get_csv_evaluation_data(eval_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        try:
            # Get the CSV evaluation record
            csv_eval = CSVEvaluationRecord.query.get_or_404(eval_id)

            # Safely process row_data to ensure it's JSON-serializable
            sanitized_row_data = {}
            if csv_eval.row_data:
                for key, value in csv_eval.row_data.items():
                    # Handle various data types to ensure JSON compatibility
                    if isinstance(value, (datetime, date)):
                        sanitized_row_data[key] = value.isoformat()
                    elif value is None:
                        sanitized_row_data[key] = None
                    elif isinstance(value, (int, float, bool, str)):
                        sanitized_row_data[key] = value
                    else:
                        # Convert any other types to string
                        try:
                            sanitized_row_data[key] = str(value)
                        except:
                            sanitized_row_data[key] = "[Complex Object]"

            # Format datetime to string to avoid serialization issues
            evaluated_at = csv_eval.evaluated_at.strftime('%Y-%m-%d %H:%M:%S') if csv_eval.evaluated_at else None

            # Return sanitized data
            return jsonify({
                'id': csv_eval.id,
                'total_score': float(csv_eval.total_score) if csv_eval.total_score is not None else None,
                'assigned_grade': csv_eval.assigned_grade,
                'evaluated_at': evaluated_at,
                'batch_id': csv_eval.batch_id,
                'customer_id': csv_eval.customer_id,
                'province': csv_eval.province,
                'row_data': sanitized_row_data
            })
        except Exception as e:
            import traceback
            print(f"Error in CSV evaluation API: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    # Add this to app.py to support the alternative download approach

    @app.route('/api/download_evaluation_csv/<int:eval_id>')
    @login_required
    def download_evaluation_csv(eval_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        try:
            # Get grade parameter
            grade = request.args.get('grade', '')

            # Get the CSV evaluation record
            csv_eval = CSVEvaluationRecord.query.get_or_404(eval_id)

            # Create CSV content
            output = StringIO()
            writer = csv.writer(output)

            # Add BOM for UTF-8
            output.write('\ufeff')

            # Add header for evaluation information
            writer.writerow(["اطلاعات ارزیابی"])

            # Add basic evaluation info
            writer.writerow(["نمره کل", str(csv_eval.total_score or '')])
            writer.writerow(["درجه", csv_eval.assigned_grade or ''])
            writer.writerow(
                ["تاریخ ارزیابی", csv_eval.evaluated_at.strftime('%Y-%m-%d %H:%M:%S') if csv_eval.evaluated_at else ''])
            writer.writerow(["استان", csv_eval.province or ''])

            # Add row data details if available
            if csv_eval.row_data and isinstance(csv_eval.row_data, dict):
                for key, value in csv_eval.row_data.items():
                    # Skip keys we've already included
                    if key not in ["نمره کل", "درجه", "تاریخ ارزیابی", "استان"]:
                        # Ensure value is string
                        safe_value = str(value) if value is not None else ''
                        writer.writerow([key, safe_value])

            # Add product quotas section
            writer.writerow([])  # Empty row as separator
            writer.writerow(["سهمیه محصولات براساس درجه"])

            # Get province if available
            province = None
            province_id = None
            if csv_eval.province:
                province = Province.query.filter_by(name=csv_eval.province).first()
                if province:
                    province_id = province.id

            # Use grade from evaluation or parameter
            grade_to_use = csv_eval.assigned_grade or grade

            # Flag to track if we found any products
            product_found = False

            # First check for batch-specific targets
            batch_targets = []
            if csv_eval.batch_id and province_id:
                batch_targets = BatchGradeTarget.query.filter_by(
                    batch_id=csv_eval.batch_id,
                    province_id=province_id,
                    grade=grade_to_use
                ).all()

            if batch_targets:
                # Write header for products
                writer.writerow(["نام محصول", "سهمیه لیتر", "سهمیه شرینک"])

                # Add data for each batch target
                for target in batch_targets:
                    product = Product.query.get(target.product_id)
                    if product:
                        liter_str = f"{target.liter_capacity:.2f}" if target.liter_capacity is not None else "-"
                        shrink_str = f"{target.shrink_capacity:.2f}" if target.shrink_capacity is not None else "-"
                        writer.writerow([product.name, liter_str, shrink_str])
                        product_found = True

            # If no batch targets or no products found, calculate based on general targets
            if not product_found and grade_to_use and province_id:
                # Get all products
                products = Product.query.all()

                # Define grade weights
                grade_weights = {
                    'A+': 2.0, 'A': 1.75, 'B+': 1.5, 'B': 1.25,
                    'C': 1.0, 'D': 0.75, 'بدون درجه': 0.5
                }

                # Get weight for this grade
                weight = grade_weights.get(grade_to_use, 0.5)

                # Write header for products (only if we haven't written it yet)
                if not batch_targets:
                    writer.writerow(["نام محصول", "سهمیه لیتر", "سهمیه شرینک"])

                # Get customer counts by grade
                customers_by_grade = {}
                province_customers = CustomerReport.query.filter_by(province=province.name).all()

                for customer in province_customers:
                    customer_grade = customer.grade or 'بدون درجه'
                    if customer_grade not in customers_by_grade:
                        customers_by_grade[customer_grade] = 0
                    customers_by_grade[customer_grade] += 1

                # Calculate weighted total
                total_weighted_count = 0
                for g, count in customers_by_grade.items():
                    g_weight = grade_weights.get(g, 0.5)
                    total_weighted_count += count * g_weight

                # Get the count for the current grade
                grade_count = customers_by_grade.get(grade_to_use, 0)

                for product in products:
                    # Get product's province target
                    target = ProductProvinceTarget.query.filter_by(
                        product_id=product.id,
                        province_id=province_id
                    ).first()

                    if target and grade_count > 0 and total_weighted_count > 0:
                        # Calculate values
                        liter_quota = None
                        shrink_quota = None

                        if target.liter_capacity is not None:
                            grade_liter = (target.liter_capacity * weight *
                                           grade_count / total_weighted_count)
                            liter_quota = grade_liter / grade_count

                        if target.shrink_capacity is not None:
                            grade_shrink = (target.shrink_capacity * weight *
                                            grade_count / total_weighted_count)
                            shrink_quota = grade_shrink / grade_count

                        # Format values
                        liter_str = f"{liter_quota:.2f}" if liter_quota is not None else "-"
                        shrink_str = f"{shrink_quota:.2f}" if shrink_quota is not None else "-"

                        # Add to CSV
                        writer.writerow([product.name, liter_str, shrink_str])
                        product_found = True

            # If we still didn't find any products
            if not product_found:
                writer.writerow(["هیچ سهمیه محصولی برای این درجه یافت نشد."])
                writer.writerow(["اطلاعات مورد نیاز:", f"درجه: {grade_to_use}",
                                 f"استان: {province.name if province else 'نامشخص'}"])

            # Prepare response
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = f"attachment; filename=evaluation_{eval_id}_details.csv"
            response.headers["Content-type"] = "text/csv; charset=utf-8"

            return response

        except Exception as e:
            import traceback
            print(f"Error generating CSV download: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    @app.route('/api/download_batch_evaluations/<batch_id>')
    @login_required
    def download_batch_evaluations(batch_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        try:
            # Get all evaluations in this batch
            csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()

            # If no CSV records found, try CustomerEvaluation
            if not csv_evals:
                customer_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).all()
                if not customer_evals:
                    return jsonify({'error': 'No evaluations found for this batch'}), 404

            # Get province for this batch if available
            province = None
            province_id = None
            if csv_evals and csv_evals[0].province:
                province_name = csv_evals[0].province
                province = Province.query.filter_by(name=province_name).first()
                if province:
                    province_id = province.id
            elif not csv_evals and customer_evals and customer_evals[0].province:
                province_name = customer_evals[0].province
                province = Province.query.filter_by(name=province_name).first()
                if province:
                    province_id = province.id

            # Define grade weights
            grade_weights = {
                'A+': 2.0, 'A': 1.75, 'B+': 1.5, 'B': 1.25,
                'C': 1.0, 'D': 0.75, 'بدون درجه': 0.5
            }

            # Get all products
            products = Product.query.all()

            # Generate a unique timestamp for the filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

            # Create CSV content
            output = StringIO()
            writer = csv.writer(output)

            # Add BOM for UTF-8
            output.write('\ufeff')

            # First process evaluations to collect all possible customer fields
            all_customer_fields = set()

            # Process CSV evaluations to extract all fields
            for eval_record in csv_evals:
                if eval_record.row_data and isinstance(eval_record.row_data, dict):
                    for key in eval_record.row_data.keys():
                        all_customer_fields.add(key)

            # Add basic customer fields that may not be in row_data
            standard_fields = ["شماره ردیف", "شماره مشتری", "نام مشتری", "درجه", "نمره کل", "استان",
                               "تاریخ ارزیابی", "latitude", "longitude", "Latitude", "Longitude"]

            for field in standard_fields:
                all_customer_fields.add(field)

            # Add additional CustomerReport fields
            additional_fields = ["textbox29", "caption", "bname", "textbox16", "textbox12", "textbox4", "textbox10"]
            for field in additional_fields:
                all_customer_fields.add(field)

            # Convert to sorted list for consistent order
            customer_fields = sorted(list(all_customer_fields))

            # Ensure basic fields are at the beginning for better readability
            for field in reversed(["استان", "نمره کل", "درجه", "نام مشتری", "شماره مشتری", "شماره ردیف"]):
                if field in customer_fields:
                    customer_fields.remove(field)
                    customer_fields.insert(0, field)

            # Prepare header row
            header_row = customer_fields.copy()

            # Add product columns for both liter and shrink
            for product in products:
                header_row.append(f"لیتر - {product.name}")
                header_row.append(f"شرینک - {product.name}")

            writer.writerow(header_row)

            # Process each evaluation
            row_index = 1

            # Get customer counts by grade for the current province
            customers_by_grade = {}
            if province:
                province_customers = CustomerReport.query.filter_by(province=province.name).all()
                for c in province_customers:
                    customer_grade = c.grade or 'بدون درجه'
                    if customer_grade not in customers_by_grade:
                        customers_by_grade[customer_grade] = 0
                    customers_by_grade[customer_grade] += 1

                # Calculate total weighted count once
                total_weighted_count = 0
                for g, count in customers_by_grade.items():
                    g_weight = grade_weights.get(g, 0.5)
                    total_weighted_count += count * g_weight

            # Process CSV evaluations first
            for eval_record in csv_evals:
                # Initialize row data with empty values for all fields
                row_data = [""] * len(customer_fields)

                # Set row index
                row_index_position = customer_fields.index("شماره ردیف") if "شماره ردیف" in customer_fields else -1
                if row_index_position >= 0:
                    row_data[row_index_position] = row_index

                # Get customer info if available
                customer = None
                if eval_record.customer_id:
                    customer = CustomerReport.query.get(eval_record.customer_id)

                # Set customer-specific fields if available
                if customer:
                    # Map basic customer fields
                    field_mapping = {
                        "شماره مشتری": customer.number,
                        "نام مشتری": customer.name,
                        "استان": customer.province,
                        "Latitude": customer.latitude,
                        "Longitude": customer.longitude,
                        "latitude": customer.latitude,
                        "longitude": customer.longitude
                    }

                    # Map additional customer fields
                    for field in additional_fields:
                        if hasattr(customer, field):
                            field_mapping[field] = getattr(customer, field)

                    # Set values in row_data
                    for field, value in field_mapping.items():
                        if field in customer_fields:
                            field_index = customer_fields.index(field)
                            row_data[field_index] = value if value is not None else ""

                # Add evaluation-specific fields
                field_mapping = {
                    "درجه": eval_record.assigned_grade,
                    "نمره کل": eval_record.total_score,
                    "تاریخ ارزیابی": eval_record.evaluated_at.strftime(
                        '%Y-%m-%d %H:%M:%S') if eval_record.evaluated_at else ""
                }

                for field, value in field_mapping.items():
                    if field in customer_fields:
                        field_index = customer_fields.index(field)
                        row_data[field_index] = value if value is not None else ""

                # Add row_data from CSV record
                if eval_record.row_data and isinstance(eval_record.row_data, dict):
                    for field, value in eval_record.row_data.items():
                        if field in customer_fields:
                            field_index = customer_fields.index(field)
                            row_data[field_index] = value if value is not None else ""

                # Get the grade for quota calculation - IMPORTANT PART
                grade = eval_record.assigned_grade or ""

                # Calculate product quotas for this specific customer's grade
                product_quotas = []
                for product in products:
                    liter_quota = "-"
                    shrink_quota = "-"

                    # First check if there are batch-specific quotas for this specific grade
                    if province_id and grade:
                        batch_target = BatchGradeTarget.query.filter_by(
                            batch_id=batch_id,
                            province_id=province_id,
                            product_id=product.id,
                            grade=grade  # This is the specific customer's grade
                        ).first()

                        if batch_target:
                            if batch_target.liter_capacity is not None:
                                liter_quota = f"{batch_target.liter_capacity:.2f}"
                            if batch_target.shrink_capacity is not None:
                                shrink_quota = f"{batch_target.shrink_capacity:.2f}"
                        else:
                            # If no batch target, calculate based on this specific grade
                            if province_id and grade in grade_weights:
                                target = ProductProvinceTarget.query.filter_by(
                                    product_id=product.id,
                                    province_id=province_id
                                ).first()

                                if target and total_weighted_count > 0:
                                    # Get the count for THIS SPECIFIC grade
                                    grade_count = customers_by_grade.get(grade, 0)
                                    weight = grade_weights.get(grade, 0.5)

                                    # Calculate quotas based on THIS SPECIFIC grade
                                    if grade_count > 0:
                                        if target.liter_capacity is not None:
                                            grade_liter = (target.liter_capacity * weight *
                                                           grade_count / total_weighted_count)
                                            liter_per_customer = grade_liter / grade_count
                                            liter_quota = f"{liter_per_customer:.2f}"

                                        if target.shrink_capacity is not None:
                                            grade_shrink = (target.shrink_capacity * weight *
                                                            grade_count / total_weighted_count)
                                            shrink_per_customer = grade_shrink / grade_count
                                            shrink_quota = f"{shrink_per_customer:.2f}"

                    # Add quotas to the list
                    product_quotas.append(liter_quota)
                    product_quotas.append(shrink_quota)

                # Combine customer data with product quotas
                final_row = row_data + product_quotas

                # Write the row
                writer.writerow(final_row)
                row_index += 1

            # Process CustomerEvaluation records if needed
            if not csv_evals:
                for eval_record in customer_evals:
                    # Initialize row data with empty values for all fields
                    row_data = [""] * len(customer_fields)

                    # Set row index
                    row_index_position = customer_fields.index("شماره ردیف") if "شماره ردیف" in customer_fields else -1
                    if row_index_position >= 0:
                        row_data[row_index_position] = row_index

                    # Get customer
                    customer = eval_record.customer

                    if customer:
                        # Map basic customer fields
                        field_mapping = {
                            "شماره مشتری": customer.number,
                            "نام مشتری": customer.name,
                            "استان": customer.province,
                            "Latitude": customer.latitude,
                            "Longitude": customer.longitude,
                            "latitude": customer.latitude,
                            "longitude": customer.longitude
                        }

                        # Map additional customer fields
                        for field in additional_fields:
                            if hasattr(customer, field):
                                field_mapping[field] = getattr(customer, field)

                        # Set values in row_data
                        for field, value in field_mapping.items():
                            if field in customer_fields:
                                field_index = customer_fields.index(field)
                                row_data[field_index] = value if value is not None else ""

                    # Add evaluation-specific fields
                    field_mapping = {
                        "درجه": eval_record.assigned_grade,
                        "نمره کل": eval_record.total_score,
                        "تاریخ ارزیابی": eval_record.evaluated_at.strftime(
                            '%Y-%m-%d %H:%M:%S') if eval_record.evaluated_at else ""
                    }

                    for field, value in field_mapping.items():
                        if field in customer_fields:
                            field_index = customer_fields.index(field)
                            row_data[field_index] = value if value is not None else ""

                    # Get the grade for quota calculation - IMPORTANT PART
                    grade = eval_record.assigned_grade or ""

                    # Calculate product quotas for this customer using the same logic as above
                    product_quotas = []
                    for product in products:
                        liter_quota = "-"
                        shrink_quota = "-"

                        # First check if there are batch-specific quotas for this specific grade
                        if province_id and grade:
                            batch_target = BatchGradeTarget.query.filter_by(
                                batch_id=batch_id,
                                province_id=province_id,
                                product_id=product.id,
                                grade=grade  # This is the specific customer's grade
                            ).first()

                            if batch_target:
                                if batch_target.liter_capacity is not None:
                                    liter_quota = f"{batch_target.liter_capacity:.2f}"
                                if batch_target.shrink_capacity is not None:
                                    shrink_quota = f"{batch_target.shrink_capacity:.2f}"
                            else:
                                # If no batch target, calculate based on this specific grade
                                if province_id and grade in grade_weights:
                                    target = ProductProvinceTarget.query.filter_by(
                                        product_id=product.id,
                                        province_id=province_id
                                    ).first()

                                    if target and total_weighted_count > 0:
                                        # Get the count for THIS SPECIFIC grade
                                        grade_count = customers_by_grade.get(grade, 0)
                                        weight = grade_weights.get(grade, 0.5)

                                        # Calculate quotas based on THIS SPECIFIC grade
                                        if grade_count > 0:
                                            if target.liter_capacity is not None:
                                                grade_liter = (target.liter_capacity * weight *
                                                               grade_count / total_weighted_count)
                                                liter_per_customer = grade_liter / grade_count
                                                liter_quota = f"{liter_per_customer:.2f}"

                                            if target.shrink_capacity is not None:
                                                grade_shrink = (target.shrink_capacity * weight *
                                                                grade_count / total_weighted_count)
                                                shrink_per_customer = grade_shrink / grade_count
                                                shrink_quota = f"{shrink_per_customer:.2f}"

                        # Add quotas to the list
                        product_quotas.append(liter_quota)
                        product_quotas.append(shrink_quota)

                    # Combine customer data with product quotas
                    final_row = row_data + product_quotas

                    # Write the row
                    writer.writerow(final_row)
                    row_index += 1

            # Prepare response
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers[
                "Content-Disposition"] = f"attachment; filename=batch_{batch_id}_evaluations_{timestamp}.csv"
            response.headers["Content-type"] = "text/csv; charset=utf-8"

            return response

        except Exception as e:
            import traceback
            print(f"Error generating batch CSV download: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    @app.route('/admin/configure-routes', methods=['POST'])
    @login_required
    def admin_configure_routes():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get file path from session
        temp_filepath = session.get('temp_filepath')
        file_type = session.get('file_type')
        province_id = request.form.get('province_id')

        # Get column mappings
        route_name_column = request.form.get('route_name_column')
        lat_column = request.form.get('lat_column')
        lng_column = request.form.get('lng_column')
        address_column = request.form.get('address_column')
        name_column = request.form.get('name_column')

        if not temp_filepath or not os.path.exists(
                temp_filepath) or not route_name_column or not lat_column or not lng_column:
            flash('لطفاً تمامی فیلدهای ضروری را تکمیل کنید یا فایل را مجددا آپلود کنید.', 'danger')
            return redirect(url_for('admin_routes_upload'))

        try:
            # Parse the file
            if file_type == 'csv':
                df = pd.read_csv(temp_filepath)
            else:  # Excel
                df = pd.read_excel(temp_filepath)

            # Group by route name
            grouped_routes = {}

            for _, row in df.iterrows():
                route_name = str(row[route_name_column]).strip()

                # Skip rows with missing route name or coordinates
                if not route_name or pd.isna(row[lat_column]) or pd.isna(row[lng_column]):
                    continue

                # Convert lat/lng to float
                try:
                    lat = float(row[lat_column])
                    lng = float(row[lng_column])
                except (ValueError, TypeError):
                    continue  # Skip if conversion fails

                # Get optional fields
                address = str(row[address_column]) if address_column and not pd.isna(row[address_column]) else None
                name = str(row[name_column]) if name_column and not pd.isna(row[name_column]) else None

                # Add to grouped routes
                if route_name not in grouped_routes:
                    grouped_routes[route_name] = []

                grouped_routes[route_name].append({
                    'name': name,
                    'latitude': lat,
                    'longitude': lng,
                    'address': address
                })

            # Create or update routes in the database
            routes_created = 0
            routes_updated = 0
            points_added = 0

            for route_name, points in grouped_routes.items():
                # Check if route already exists
                existing_route = Route.query.filter_by(name=route_name).first()

                if existing_route:
                    route = existing_route
                    routes_updated += 1
                else:
                    # Create new route
                    route = Route(
                        name=route_name,
                        description=f'مسیر بارگذاری شده از فایل - {len(points)} نقطه',
                        province=province_id if province_id else None,
                        is_active=True,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.session.add(route)
                    db.session.flush()  # Get the ID without committing
                    routes_created += 1

                # Add points to the route
                for i, point_data in enumerate(points):
                    # Check if a similar point already exists
                    existing_point = RoutePoint.query.filter_by(
                        route_id=route.id,
                        latitude=point_data['latitude'],
                        longitude=point_data['longitude']
                    ).first()

                    if not existing_point:
                        new_point = RoutePoint(
                            route_id=route.id,
                            name=point_data['name'] or f'نقطه {i + 1}',
                            latitude=point_data['latitude'],
                            longitude=point_data['longitude'],
                            address=point_data['address'],
                            order=i + 1,
                            created_at=datetime.now(timezone.utc)
                        )
                        db.session.add(new_point)
                        points_added += 1

            # Commit all changes
            db.session.commit()

            # Clean up - remove the temp file
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

            # Clear session data
            session.pop('temp_filepath', None)
            session.pop('columns', None)
            session.pop('preview_data', None)
            session.pop('file_type', None)
            session.pop('province_id', None)

            flash(
                f'{routes_created} مسیر جدید ایجاد شد. {routes_updated} مسیر به‌روزرسانی شد. {points_added} نقطه اضافه شد.',
                'success')
            return redirect(url_for('admin_routes_upload', tab='manage'))

        except Exception as e:
            # Clean up the file in case of error
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

            flash(f'خطا در پردازش فایل: {str(e)}', 'danger')
            return redirect(url_for('admin_routes_upload'))

    @app.route('/admin/cleanup-temp-files')
    @login_required
    def cleanup_temp_files():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        temp_dir = get_temp_dir()
        deleted_count = 0

        # Get all files in the directory
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)

            # Check if the file is older than 24 hours
            if os.path.isfile(filepath):
                file_time = os.path.getmtime(filepath)
                if (time.time() - file_time) > 86400:  # 24 hours in seconds
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except:
                        pass

        flash(f'{deleted_count} فایل موقت قدیمی پاک شد.', 'success')
        return redirect(url_for('admin_routes_upload'))

    def get_temp_dir():
        """Create and return a temporary directory path for file uploads"""
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_uploads')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        return temp_dir

    @app.route('/admin/debug-session')
    @login_required
    def debug_session():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        session_data = {}
        for key, value in session.items():
            # Only include values that can be safely serialized
            try:
                json.dumps({key: value})
                session_data[key] = value
            except:
                session_data[key] = f"[Not serializable: {type(value)}]"

        return jsonify(session_data)

    @app.route('/admin/clear-session')
    @login_required
    def clear_session():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Clear all session data
        session.clear()
        flash('Session data cleared', 'success')
        return redirect(url_for('admin_routes_upload'))


    @app.route('/admin/assign-marketers-to-route', methods=['POST'])
    @login_required
    def admin_assign_marketers_to_route():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        route_id = request.form.get('route_id')
        marketer_ids = request.form.getlist('marketer_ids[]')

        if not route_id or not marketer_ids:
            flash('لطفاً حداقل یک بازاریاب انتخاب کنید.', 'danger')
            return redirect(url_for('admin_routes_upload', tab='manage'))

        try:
            route = Route.query.get_or_404(route_id)

            # Deactivate previous assignments
            for assignment in route.assignments:
                assignment.is_active = False

            # Create new assignments
            for marketer_id in marketer_ids:
                new_assignment = RouteAssignment(
                    route_id=route.id,
                    marketer_id=marketer_id,
                    assigned_at=datetime.now(timezone.utc),
                    is_active=True
                )
                db.session.add(new_assignment)

            db.session.commit()
            flash(f'مسیر {route.name} با موفقیت به {len(marketer_ids)} بازاریاب تخصیص داده شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در تخصیص مسیر: {str(e)}', 'danger')

        return redirect(url_for('admin_routes_upload', tab='manage'))

    @app.route('/admin/update-route-color', methods=['POST'])
    @login_required
    def admin_update_route_color():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        route_id = request.form.get('route_id')
        color = request.form.get('color')

        if not route_id or not color:
            flash('اطلاعات ناقص است.', 'danger')
            return redirect(url_for('admin_routes_upload', tab='manage'))

        try:
            route = Route.query.get_or_404(route_id)

            # Add color column if it doesn't exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('route')]

            if 'color' not in columns:
                # Use SQLAlchemy's text() for executing raw SQL
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE route ADD COLUMN color VARCHAR(50)'))
                    conn.commit()

            # Set color
            route.color = color
            db.session.commit()

            flash(f'رنگ مسیر {route.name} با موفقیت به‌روزرسانی شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در تغییر رنگ مسیر: {str(e)}', 'danger')

        return redirect(url_for('admin_routes_upload', tab='map'))
    @app.route('/admin/batch_evaluations/<batch_id>/assign-province', methods=['POST'])
    @login_required
    def assign_batch_province(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        province_id = request.form.get('province_id')

        if not province_id:
            flash('لطفاً یک استان انتخاب کنید.', 'warning')
            return redirect(url_for('view_batch_evaluations', batch_id=batch_id))

        try:
            province = Province.query.get_or_404(province_id)

            # Update CSVEvaluationRecord
            csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()
            for eval in csv_evals:
                eval.province = province.name

                # If the eval is linked to a customer, also update customer's province
                if eval.customer_id:
                    customer = CustomerReport.query.get(eval.customer_id)
                    if customer:
                        customer.province = province.name

            # Also update CustomerEvaluation for compatibility
            customer_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).all()
            for eval in customer_evals:
                eval.province = province.name

            # Store the batch_id and province_id in the session for use in product targeting
            session['current_batch_id'] = batch_id
            session['current_province_id'] = province_id

            db.session.commit()
            flash(f'استان "{province.name}" با موفقیت به دسته ارزیابی تخصیص داده شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در تخصیص استان: {str(e)}', 'danger')

        return redirect(url_for('view_batch_evaluations', batch_id=batch_id))

    # Add this new route to your app.py file

    @app.route('/admin/update-bulk-province-product-targets', methods=['POST'])
    @login_required
    def update_bulk_province_product_targets():
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز!'})

        province_id = request.form.get('province_id')
        batch_id = request.form.get('batch_id')
        calculation_basis = request.form.get('calculation_basis', 'population')  # population, customer, or grade
        product_ids = request.form.getlist('product_ids')

        if not province_id:
            return jsonify({'success': False, 'message': 'استان مشخص نشده است.'})

        if not product_ids:
            return jsonify({'success': False, 'message': 'هیچ محصولی انتخاب نشده است.'})

        try:
            # Get province
            province = Province.query.get_or_404(province_id)

            # Get customer count for this province
            customer_count = CustomerReport.query.filter_by(province=province.name).count()

            # Get grade distribution for this province if needed
            grade_distribution = {}
            if calculation_basis == 'grade':
                # Get all customers in this province
                customers = CustomerReport.query.filter_by(province=province.name).all()

                # Count by grade
                for customer in customers:
                    grade = customer.grade or 'بدون درجه'
                    if grade not in grade_distribution:
                        grade_distribution[grade] = 0
                    grade_distribution[grade] += 1

            # Process each selected product
            for product_id in product_ids:
                # Get percentage for this product
                percentage_key = f'percentage_{product_id}'
                if percentage_key in request.form and request.form[percentage_key].strip():
                    percentage = float(request.form[percentage_key])

                    # Get product
                    product = Product.query.get(product_id)
                    if not product:
                        continue

                    # Calculate capacity based on percentage
                    liter_capacity = None
                    shrink_capacity = None

                    if product.liter_capacity:
                        liter_capacity = product.liter_capacity * (percentage / 100)

                    if product.shrink_capacity:
                        shrink_capacity = product.shrink_capacity * (percentage / 100)

                    # Get or create target
                    target = ProductProvinceTarget.query.filter_by(
                        product_id=product_id,
                        province_id=province_id
                    ).first()

                    if not target:
                        target = ProductProvinceTarget(
                            product_id=product_id,
                            province_id=province_id
                        )
                        db.session.add(target)

                    # Update target
                    target.liter_capacity = liter_capacity
                    target.shrink_capacity = shrink_capacity
                    target.liter_percentage = percentage
                    target.shrink_percentage = percentage

                    # Calculate grade-based distribution if needed
                    if calculation_basis == 'grade' and grade_distribution:
                        # Logic for grade-based distribution would go here
                        # This would need to be implemented according to your specific requirements
                        pass

            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'تارگت‌های محصولات با موفقیت به‌روزرسانی شدند.'
            })

        except ValueError as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'خطا در مقادیر وارد شده: {str(e)}'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'خطا در به‌روزرسانی تارگت‌ها: {str(e)}'})

    # Add these routes for the export functionality

    # Improved export route with comprehensive target calculations

    @app.route('/admin/export-report/<report_type>/<export_format>', methods=['POST'])
    @login_required
    def export_report(report_type, export_format):
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز!'})

        # Get fields and other parameters
        fields = request.form.getlist(f'{report_type}_fields')
        batch_id = request.form.get('batch_id')
        province_id = request.form.get('province_id')

        if not fields:
            return jsonify({'success': False, 'message': 'هیچ فیلدی انتخاب نشده است.'})

        try:
            # Prepare filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{report_type}_report_{timestamp}"

            # Get province if specified
            province = None
            if province_id:
                province = Province.query.get(province_id)

            # Process based on report type
            if report_type == 'customer':
                return export_customer_report(fields, batch_id, province, export_format, filename)
            elif report_type == 'product':
                return export_product_report(fields, batch_id, province, export_format, filename)
            elif report_type == 'province':
                return export_province_report(fields, batch_id, export_format, filename)
            else:
                return jsonify({'success': False, 'message': 'نوع گزارش نامعتبر است.'})

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'خطا در ایجاد فایل خروجی: {str(e)}'
            })

    def export_customer_report(fields, batch_id, province, export_format, filename):
        """Export customer report with target allocations"""

        # Get customers based on batch ID or province
        customers = []

        if batch_id:
            # Get customers from CSVEvaluationRecord
            csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()
            for eval_record in csv_evals:
                if eval_record.customer_id:
                    customer = CustomerReport.query.get(eval_record.customer_id)
                    if customer and customer not in customers:
                        customers.append(customer)

        # If no customers from batch or province specified, use province filter
        if not customers and province:
            customers = CustomerReport.query.filter_by(province=province.name).all()

        # If still no customers, get all customers
        if not customers:
            customers = CustomerReport.query.all()

        # Get products for target allocation
        products = Product.query.all()

        # Get grade weights
        grade_weights = {
            'A+': 2.0,
            'A': 1.75,
            'B+': 1.5,
            'B': 1.25,
            'C': 1.0,
            'D': 0.75,
            'بدون درجه': 0.5
        }

        # Prepare data for export
        data = []

        for customer in customers:
            row = {}

            # Add basic customer fields
            for field in fields:
                if field == 'number':
                    row['number'] = customer.number or ''
                elif field == 'name':
                    row['name'] = customer.name or ''
                elif field == 'grade':
                    row['grade'] = customer.grade or 'بدون درجه'
                elif field == 'location':
                    if customer.latitude and customer.longitude:
                        row['location'] = f"{customer.latitude},{customer.longitude}"
                    else:
                        row['location'] = ''
                elif field == 'province':
                    row['province'] = customer.province or ''

            # Calculate product allocations if requested
            if 'products' in fields and customer.province:
                product_allocations = []
                customer_province = Province.query.filter_by(name=customer.province).first()

                if customer_province:
                    # Get all customers in this province for grade distribution calculation
                    province_customers = CustomerReport.query.filter_by(province=customer.province).all()

                    if province_customers:
                        # Count customers by grade
                        grade_counts = {}
                        for pc in province_customers:
                            grade = pc.grade or 'بدون درجه'
                            if grade not in grade_counts:
                                grade_counts[grade] = 0
                            grade_counts[grade] += 1

                        # Calculate grade weights
                        total_weighted_count = 0
                        for grade, count in grade_counts.items():
                            weight = grade_weights.get(grade, 0.5)
                            total_weighted_count += count * weight

                        # Calculate customer weight
                        customer_grade = customer.grade or 'بدون درجه'
                        customer_weight = grade_weights.get(customer_grade, 0.5)

                        # Calculate allocations for each product
                        for product in products:
                            target = ProductProvinceTarget.query.filter_by(
                                product_id=product.id,
                                province_id=customer_province.id
                            ).first()

                            if target:
                                # Calculate allocation based on grade
                                grade_count = grade_counts.get(customer_grade, 0)
                                if grade_count > 0 and total_weighted_count > 0:
                                    # Total allocation for this grade
                                    grade_allocation_liter = None
                                    grade_allocation_shrink = None

                                    if target.liter_capacity is not None:
                                        grade_allocation_liter = (target.liter_capacity *
                                                                  customer_weight * grade_count /
                                                                  total_weighted_count)
                                        # Per customer allocation
                                        customer_liter = grade_allocation_liter / grade_count

                                    if target.shrink_capacity is not None:
                                        grade_allocation_shrink = (target.shrink_capacity *
                                                                   customer_weight * grade_count /
                                                                   total_weighted_count)
                                        # Per customer allocation
                                        customer_shrink = grade_allocation_shrink / grade_count

                                    # Format allocation for display
                                    if grade_allocation_liter is not None and grade_allocation_shrink is not None:
                                        product_allocations.append(
                                            f"{product.name}: {customer_liter:.2f} لیتر, {customer_shrink:.2f} شرینک"
                                        )
                                    elif grade_allocation_liter is not None:
                                        product_allocations.append(
                                            f"{product.name}: {customer_liter:.2f} لیتر"
                                        )
                                    elif grade_allocation_shrink is not None:
                                        product_allocations.append(
                                            f"{product.name}: {customer_shrink:.2f} شرینک"
                                        )

                    # Add product allocations to row
                    row['products'] = ' | '.join(product_allocations)

            data.append(row)

        # Format field headers
        headers = {field: get_field_label('customer', field) for field in fields}

        # Export based on format
        return create_export_file(data, headers, export_format, filename)

    def export_product_report(fields, batch_id, province, export_format, filename):
        """Export product report with target allocations by province and grade"""

        # Get products (filter by selected products if specified)
        product_ids = request.form.getlist('report_product_ids')
        if product_ids:
            products = Product.query.filter(Product.id.in_(product_ids)).all()
        else:
            products = Product.query.all()

        # Get provinces for target allocation
        provinces = Province.query.all() if not province else [province]

        # Prepare data for export
        data = []

        for product in products:
            for province in provinces:
                row = {}

                # Add basic product fields
                for field in fields:
                    if field == 'name':
                        row['name'] = product.name
                    elif field == 'category':
                        if hasattr(product, 'category_relation') and product.category_relation:
                            row['category'] = product.category_relation.name
                        else:
                            row['category'] = ''
                    elif field == 'liter':
                        row['liter'] = product.liter_capacity if product.liter_capacity is not None else ''
                    elif field == 'shrink':
                        row['shrink'] = product.shrink_capacity if product.shrink_capacity is not None else ''
                    elif field == 'province':
                        row['province'] = province.name

                # Get province target
                target = ProductProvinceTarget.query.filter_by(
                    product_id=product.id,
                    province_id=province.id
                ).first()

                if target:
                    if 'province' in fields:
                        percentage = ''
                        if target.liter_percentage is not None:
                            percentage = f"{target.liter_percentage:.2f}%"
                        elif target.shrink_percentage is not None:
                            percentage = f"{target.shrink_percentage:.2f}%"

                        province_allocation = f"{province.name} ({percentage})"
                        if target.liter_capacity is not None:
                            province_allocation += f" لیتر: {target.liter_capacity:.2f}"
                        if target.shrink_capacity is not None:
                            province_allocation += f" شرینک: {target.shrink_capacity:.2f}"

                        row['province'] = province_allocation

                    # Add grade-based allocation if requested
                    if 'grade' in fields:
                        # Get customers by grade in this province
                        province_customers = CustomerReport.query.filter_by(province=province.name).all()

                        if province_customers:
                            # Count customers by grade
                            grade_counts = {}
                            for customer in province_customers:
                                grade = customer.grade or 'بدون درجه'
                                if grade not in grade_counts:
                                    grade_counts[grade] = 0
                                grade_counts[grade] += 1

                            # Get grade weights for allocation
                            grade_weights = {
                                'A+': 2.0,
                                'A': 1.75,
                                'B+': 1.5,
                                'B': 1.25,
                                'C': 1.0,
                                'D': 0.75,
                                'بدون درجه': 0.5
                            }

                            # Calculate total weighted count
                            total_weighted_count = 0
                            for grade, count in grade_counts.items():
                                weight = grade_weights.get(grade, 0.5)
                                total_weighted_count += count * weight

                            # Calculate allocation by grade
                            grade_allocations = []

                            for grade, count in grade_counts.items():
                                if count > 0 and total_weighted_count > 0:
                                    weight = grade_weights.get(grade, 0.5)
                                    percentage = weight * count / total_weighted_count * 100

                                    grade_allocation = f"{grade} ({count} مشتری, {percentage:.1f}%)"

                                    if target.liter_capacity is not None:
                                        liter_allocation = target.liter_capacity * percentage / 100
                                        liter_per_customer = liter_allocation / count
                                        grade_allocation += f", لیتر: {liter_per_customer:.2f}/مشتری"

                                    if target.shrink_capacity is not None:
                                        shrink_allocation = target.shrink_capacity * percentage / 100
                                        shrink_per_customer = shrink_allocation / count
                                        grade_allocation += f", شرینک: {shrink_per_customer:.2f}/مشتری"

                                    grade_allocations.append(grade_allocation)

                            row['grade'] = ' | '.join(grade_allocations)

                data.append(row)

        # Format field headers
        headers = {field: get_field_label('product', field) for field in fields}

        # Export based on format
        return create_export_file(data, headers, export_format, filename)

    def export_province_report(fields, batch_id, export_format, filename):
        """Export province report with detailed allocation information"""

        # Get all provinces
        provinces = Province.query.all()

        # Get all products for allocation details
        products = Product.query.all()

        # Prepare data for export
        data = []

        for province in provinces:
            row = {}

            # Add basic province fields
            for field in fields:
                if field == 'name':
                    row['name'] = province.name
                elif field == 'population':
                    row['population'] = f"{province.population:,}"
                elif field == 'customers':
                    customer_count = CustomerReport.query.filter_by(province=province.name).count()
                    row['customers'] = customer_count

            # Get all customers in this province
            province_customers = CustomerReport.query.filter_by(province=province.name).all()

            # Add grade distribution if requested
            if 'grades' in fields and province_customers:
                # Count customers by grade
                grade_counts = {}
                for customer in province_customers:
                    grade = customer.grade or 'بدون درجه'
                    if grade not in grade_counts:
                        grade_counts[grade] = 0
                    grade_counts[grade] += 1

                # Format grade distribution
                grade_distribution = []
                for grade, count in grade_counts.items():
                    percentage = count / len(province_customers) * 100 if province_customers else 0
                    grade_distribution.append(f"{grade}: {count} ({percentage:.1f}%)")

                row['grades'] = ' | '.join(grade_distribution)

            # Add capacity allocation if requested
            capacity_fields = []
            if 'liter' in fields:
                # Calculate total liter capacity for this province
                total_liter = 0
                for product in products:
                    target = ProductProvinceTarget.query.filter_by(
                        product_id=product.id,
                        province_id=province.id
                    ).first()

                    if target and target.liter_capacity is not None:
                        total_liter += target.liter_capacity

                # Format capacity
                customer_count = CustomerReport.query.filter_by(province=province.name).count()
                if customer_count > 0:
                    per_customer = total_liter / customer_count
                    capacity_fields.append(f"لیتر: {total_liter:.2f} (هر مشتری: {per_customer:.2f})")
                else:
                    capacity_fields.append(f"لیتر: {total_liter:.2f}")

                row['liter'] = ' | '.join(capacity_fields)

            if 'shrink' in fields:
                # Calculate total shrink capacity for this province
                total_shrink = 0
                for product in products:
                    target = ProductProvinceTarget.query.filter_by(
                        product_id=product.id,
                        province_id=province.id
                    ).first()

                    if target and target.shrink_capacity is not None:
                        total_shrink += target.shrink_capacity

                # Format capacity
                customer_count = CustomerReport.query.filter_by(province=province.name).count()
                if customer_count > 0:
                    per_customer = total_shrink / customer_count
                    capacity_fields.append(f"شرینک: {total_shrink:.2f} (هر مشتری: {per_customer:.2f})")
                else:
                    capacity_fields.append(f"شرینک: {total_shrink:.2f}")

                row['shrink'] = ' | '.join(capacity_fields)

            # Add product details if requested
            if 'products' in fields:
                product_details = []

                for product in products:
                    target = ProductProvinceTarget.query.filter_by(
                        product_id=product.id,
                        province_id=province.id
                    ).first()

                    if target:
                        detail = f"{product.name}"

                        if target.liter_capacity is not None:
                            detail += f" (لیتر: {target.liter_capacity:.2f}"

                            if target.liter_percentage is not None:
                                detail += f", {target.liter_percentage:.1f}%"

                            detail += ")"

                        if target.shrink_capacity is not None:
                            detail += f" (شرینک: {target.shrink_capacity:.2f}"

                            if target.shrink_percentage is not None:
                                detail += f", {target.shrink_percentage:.1f}%"

                            detail += ")"

                        product_details.append(detail)

                row['products'] = ' | '.join(product_details)

            data.append(row)

        # Format field headers
        headers = {field: get_field_label('province', field) for field in fields}

        # Export based on format
        return create_export_file(data, headers, export_format, filename)

    def create_export_file(data, headers, export_format, filename):
        """Create and return the export file in the specified format"""

        if export_format == 'excel':
            # Create DataFrame from data
            df = pd.DataFrame(data)

            # Rename columns to use field labels
            df = df.rename(columns=headers)

            # Convert to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Report')

                # Auto-adjust columns width
                worksheet = writer.sheets['Report']
                for i, col in enumerate(df.columns):
                    # Get the maximum length of the column
                    col_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    # Column width in Excel is based on the width of '0' character
                    col_width = col_len  # Can be adjusted if needed
                    worksheet.set_column(i, i, col_width)

            output.seek(0)

            return send_file(
                output,
                as_attachment=True,
                download_name=f"{filename}.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        elif export_format == 'csv':
            # Create CSV
            output = StringIO()

            # Write header row
            header_row = {}
            for field in data[0].keys() if data else []:
                header_row[field] = headers.get(field, field)

            # Create CSV writer
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()) if data else [])
            writer.writerow(header_row)
            writer.writerows(data)

            # Create response
            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
            response.headers["Content-type"] = "text/csv"

            return response

        elif export_format == 'pdf':
            return jsonify({
                'success': False,
                'message': 'برای استفاده از خروجی PDF، لطفاً پکیج WeasyPrint یا ReportLab را نصب کنید.'
            })

        else:
            return jsonify({
                'success': False,
                'message': 'فرمت خروجی نامعتبر است.'
            })

    # Helper function to get field labels
    def get_field_label(report_type, field):
        labels = {
            'customer': {
                'number': 'شماره مشتری',
                'name': 'نام مشتری',
                'grade': 'درجه',
                'score': 'نمره',
                'location': 'موقعیت جغرافیایی',
                'province': 'استان',
                'eval_date': 'تاریخ ارزیابی',
                'products': 'تخصیص محصولات'
            },
            'product': {
                'name': 'نام محصول',
                'category': 'دسته‌بندی',
                'liter': 'ظرفیت لیتر',
                'shrink': 'ظرفیت شرینک',
                'province': 'تخصیص استانی',
                'grade': 'تخصیص بر اساس درجه'
            },
            'province': {
                'name': 'نام استان',
                'population': 'جمعیت',
                'customers': 'تعداد مشتریان',
                'grades': 'توزیع درجه‌ها',
                'liter': 'تخصیص لیتر',
                'shrink': 'تخصیص شرینک',
                'products': 'جزئیات محصولات'
            }
        }

        return labels.get(report_type, {}).get(field, field)

    # Update the api_product_quotas function to account for store type exclusions

    @app.route('/api/product_quotas')
    @login_required
    def api_product_quotas():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get parameters
        grade = request.args.get('grade')
        province_id = request.args.get('province_id')
        eval_id = request.args.get('eval_id')
        store_type_id = request.args.get('store_type_id')
        batch_id = request.args.get('batch_id')

        if not grade:
            return jsonify({'error': 'Grade is required'}), 400

        try:
            # Get all products
            products = Product.query.all()

            # Get the province
            province = None
            if province_id and province_id != 'null':
                province = Province.query.get(province_id)

            # Get grade weights from session or set defaults
            grade_weights = {
                'A+': 2.0,
                'A': 1.75,
                'B+': 1.5,
                'B': 1.25,
                'C': 1.0,
                'D': 0.75,
                'بدون درجه': 0.5
            }

            # Get weight for the specified grade
            weight = grade_weights.get(grade, 0.5)  # Default weight if grade not found

            # Prepare results
            result = {
                'grade': grade,
                'weight': weight,
                'products': []
            }

            # If store_type_id is provided, get exclusion rules
            excluded_products = []
            if store_type_id and store_type_id != 'null':
                store_type = StoreType.query.get(store_type_id)
                if store_type:
                    result['store_type'] = {
                        'id': store_type.id,
                        'name': store_type.name
                    }

                    # Get exclusion rules for this store type
                    exclusion_query = ProductExclusionRule.query.filter_by(store_type_id=store_type_id)
                    if batch_id and batch_id != 'null':
                        exclusion_query = exclusion_query.filter(
                            db.or_(
                                ProductExclusionRule.batch_id == batch_id,
                                ProductExclusionRule.batch_id == None
                            )
                        )

                    exclusions = exclusion_query.all()
                    excluded_products = [rule.product_id for rule in exclusions]

                    # Also get allocation percentage for this store type if available
                    if province and batch_id and batch_id != 'null':
                        allocation = StoreTypeAllocation.query.filter_by(
                            store_type_id=store_type_id,
                            batch_id=batch_id,
                            province_id=province.id
                        ).first()

                        if allocation:
                            result['allocation_percentage'] = allocation.percentage

            if province:
                # Get customer count by grade in this province
                customers_by_grade = {}
                province_customers = CustomerReport.query.filter_by(province=province.name).all()
                total_customers = len(province_customers)

                for customer in province_customers:
                    customer_grade = customer.grade or 'بدون درجه'
                    if customer_grade not in customers_by_grade:
                        customers_by_grade[customer_grade] = 0
                    customers_by_grade[customer_grade] += 1

                # Calculate total weighted count for this grade
                total_weighted_count = 0
                for g, count in customers_by_grade.items():
                    w = grade_weights.get(g, 0.5)
                    total_weighted_count += count * w

                # Get the number of customers with the specified grade
                grade_count = customers_by_grade.get(grade, 0)

                # If store_type_id is provided, get count of customers with this grade and store type
                store_type_grade_count = 0
                if store_type_id and store_type_id != 'null':
                    store_type_grade_count = CustomerReport.query.filter_by(
                        province=province.name,
                        grade=grade,
                        store_type_id=store_type_id
                    ).count()

                    result['store_type_customer_count'] = store_type_grade_count

                # Calculate quotas for each product
                for product in products:
                    # Skip excluded products
                    if product.id in excluded_products:
                        continue

                    product_data = {
                        'id': product.id,
                        'name': product.name,
                        'liter_quota': None,
                        'shrink_quota': None
                    }

                    # First check if there's a specific batch target for this combination
                    if batch_id and batch_id != 'null':
                        # Query parameters for batch target
                        target_params = {
                            'batch_id': batch_id,
                            'province_id': province.id,
                            'product_id': product.id,
                            'grade': grade
                        }

                        # If store_type_id is provided, check for specific store type target
                        if store_type_id and store_type_id != 'null':
                            target_params['store_type_id'] = store_type_id
                        else:
                            target_params['store_type_id'] = None

                        batch_target = BatchGradeTarget.query.filter_by(**target_params).first()

                        if batch_target:
                            product_data['liter_quota'] = batch_target.liter_capacity
                            product_data['shrink_quota'] = batch_target.shrink_capacity
                            product_data['source'] = 'batch_target'
                            result['products'].append(product_data)
                            continue

                    # If no batch target or no batch_id, fall back to regular product-province target
                    product_target = ProductProvinceTarget.query.filter_by(
                        product_id=product.id,
                        province_id=province.id
                    ).first()

                    if product_target:
                        # If store_type_id is provided and allocation exists, use it
                        if store_type_id and store_type_id != 'null' and batch_id and batch_id != 'null':
                            allocation = StoreTypeAllocation.query.filter_by(
                                store_type_id=store_type_id,
                                batch_id=batch_id,
                                province_id=province.id
                            ).first()

                            if allocation and store_type_grade_count > 0:
                                # Calculate quota based on allocation percentage
                                if product_target.liter_capacity is not None:
                                    total_allocation = product_target.liter_capacity * (allocation.percentage / 100)
                                    product_data['liter_quota'] = total_allocation / store_type_grade_count

                                if product_target.shrink_capacity is not None:
                                    total_allocation = product_target.shrink_capacity * (allocation.percentage / 100)
                                    product_data['shrink_quota'] = total_allocation / store_type_grade_count

                                product_data['source'] = 'store_type_allocation'
                                result['products'].append(product_data)
                                continue

                        # Otherwise, use grade-based allocation
                        if grade_count > 0 and total_weighted_count > 0:
                            # Calculate allocation based on grade weight
                            if product_target.liter_capacity is not None:
                                # Calculate the total allocation for this grade group
                                grade_allocation = (
                                            product_target.liter_capacity * weight * grade_count / total_weighted_count)
                                # Calculate allocation per customer
                                product_data['liter_quota'] = grade_allocation / grade_count

                            if product_target.shrink_capacity is not None:
                                # Calculate the total allocation for this grade group
                                grade_allocation = (
                                            product_target.shrink_capacity * weight * grade_count / total_weighted_count)
                                # Calculate allocation per customer
                                product_data['shrink_quota'] = grade_allocation / grade_count

                            product_data['source'] = 'grade_based'
                            result['products'].append(product_data)

                return jsonify(result)
            else:
                # If no province found, just include product basic info without quotas
                for product in products:
                    # Skip excluded products
                    if product.id in excluded_products:
                        continue

                    result['products'].append({
                        'id': product.id,
                        'name': product.name,
                        'liter_quota': None,
                        'shrink_quota': None,
                        'source': None
                    })

                return jsonify(result)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return jsonify({'error': str(e)}), 500

    # Add this to app.py

    @app.route('/admin/store-types', methods=['GET', 'POST'])
    @login_required
    def admin_store_types():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        form = StoreTypeForm()

        if form.validate_on_submit():
            store_type = StoreType(
                name=form.name.data.strip(),
                description=form.description.data
            )

            try:
                db.session.add(store_type)
                db.session.commit()
                flash(f'نوع فروشگاه {store_type.name} با موفقیت ایجاد شد.', 'success')
                return redirect(url_for('admin_store_types'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا: این نوع فروشگاه قبلاً تعریف شده است.', 'danger')

        # Get all store types
        store_types = StoreType.query.all()

        return render_template(
            'admin/store_types.html',
            form=form,
            store_types=store_types
        )

    @app.route('/admin/store-types/<int:store_type_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_store_type(store_type_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        store_type = StoreType.query.get_or_404(store_type_id)
        form = StoreTypeForm(obj=store_type)

        if form.validate_on_submit():
            store_type.name = form.name.data.strip()
            store_type.description = form.description.data

            try:
                db.session.commit()
                flash(f'نوع فروشگاه {store_type.name} با موفقیت ویرایش شد.', 'success')
                return redirect(url_for('admin_store_types'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا: این نوع فروشگاه قبلاً تعریف شده است.', 'danger')

        return render_template(
            'admin/edit_store_type.html',
            form=form,
            store_type=store_type
        )

    @app.route('/admin/store-types/<int:store_type_id>/delete', methods=['POST'])
    @login_required
    def delete_store_type(store_type_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        store_type = StoreType.query.get_or_404(store_type_id)

        try:
            # Delete associated exclusion rules and allocations
            ProductExclusionRule.query.filter_by(store_type_id=store_type_id).delete()
            StoreTypeAllocation.query.filter_by(store_type_id=store_type_id).delete()

            # Delete the store type
            db.session.delete(store_type)
            db.session.commit()
            flash(f'نوع فروشگاه {store_type.name} با موفقیت حذف شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف نوع فروشگاه: {str(e)}', 'danger')

        return redirect(url_for('admin_store_types'))

    # --------------------- PRODUCT EXCLUSION ROUTES ---------------------
    @app.route('/admin/batch_evaluations/<batch_id>/exclusions', methods=['GET', 'POST'])
    @login_required
    def manage_product_exclusions(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get store types and products
        store_types = StoreType.query.all()
        products = Product.query.all()

        if request.method == 'POST':
            store_type_id = request.form.get('store_type_id')
            excluded_product_ids = request.form.getlist('product_ids[]')

            if not store_type_id:
                flash('لطفاً یک نوع فروشگاه انتخاب کنید.', 'warning')
                return redirect(url_for('manage_product_exclusions', batch_id=batch_id))

            try:
                # Delete existing exclusion rules for this store type and batch
                ProductExclusionRule.query.filter_by(
                    store_type_id=store_type_id,
                    batch_id=batch_id
                ).delete()

                # Add new exclusion rules
                for product_id in excluded_product_ids:
                    exclusion = ProductExclusionRule(
                        store_type_id=store_type_id,
                        product_id=product_id,
                        batch_id=batch_id
                    )
                    db.session.add(exclusion)

                db.session.commit()
                flash('قوانین عدم تخصیص با موفقیت به‌روزرسانی شدند.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در به‌روزرسانی قوانین عدم تخصیص: {str(e)}', 'danger')

            return redirect(url_for('manage_product_exclusions', batch_id=batch_id))

        # Get existing exclusions for each store type
        exclusions_by_store_type = {}
        for store_type in store_types:
            exclusions = ProductExclusionRule.query.filter_by(
                store_type_id=store_type.id,
                batch_id=batch_id
            ).all()

            excluded_product_ids = [exclusion.product_id for exclusion in exclusions]
            exclusions_by_store_type[store_type.id] = excluded_product_ids

        return render_template(
            'admin/product_exclusions.html',
            batch_id=batch_id,
            store_types=store_types,
            products=products,
            exclusions_by_store_type=exclusions_by_store_type
        )

    # --------------------- STORE TYPE ALLOCATION ROUTES ---------------------
    @app.route('/admin/batch_evaluations/<batch_id>/allocations', methods=['GET', 'POST'])
    @login_required
    def manage_store_allocations(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Find province for this batch
        province = None
        csv_eval = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).first()
        if csv_eval and csv_eval.province:
            province = Province.query.filter_by(name=csv_eval.province).first()

        if not province:
            flash('لطفاً ابتدا یک استان را به این دسته ارزیابی تخصیص دهید.', 'warning')
            return redirect(url_for('view_batch_evaluations', batch_id=batch_id))

        # Get store types
        store_types = StoreType.query.all()

        if request.method == 'POST':
            allocations = []
            total_percentage = 0

            # Process each store type allocation
            for store_type in store_types:
                percentage_key = f'percentage_{store_type.id}'
                if percentage_key in request.form and request.form[percentage_key].strip():
                    try:
                        percentage = float(request.form[percentage_key])
                        total_percentage += percentage

                        allocations.append({
                            'store_type_id': store_type.id,
                            'percentage': percentage
                        })
                    except ValueError:
                        flash(f'مقدار درصد برای {store_type.name} نامعتبر است.', 'danger')
                        return redirect(url_for('manage_store_allocations', batch_id=batch_id))

            # Validate total percentage doesn't exceed 100%
            if total_percentage > 100:
                flash('مجموع درصدهای تخصیص نمی‌تواند بیش از 100% باشد.', 'danger')
                return redirect(url_for('manage_store_allocations', batch_id=batch_id))

            try:
                # Delete existing allocations for this batch and province
                StoreTypeAllocation.query.filter_by(
                    batch_id=batch_id,
                    province_id=province.id
                ).delete()

                # Add new allocations
                for allocation in allocations:
                    new_allocation = StoreTypeAllocation(
                        store_type_id=allocation['store_type_id'],
                        batch_id=batch_id,
                        province_id=province.id,
                        percentage=allocation['percentage']
                    )
                    db.session.add(new_allocation)

                db.session.commit()
                flash('تخصیص‌های نوع فروشگاه با موفقیت به‌روزرسانی شدند.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در به‌روزرسانی تخصیص‌ها: {str(e)}', 'danger')

            return redirect(url_for('manage_store_allocations', batch_id=batch_id))

        # Get existing allocations
        existing_allocations = StoreTypeAllocation.query.filter_by(
            batch_id=batch_id,
            province_id=province.id
        ).all()

        # Create a dictionary for easier access
        allocations_dict = {allocation.store_type_id: allocation.percentage for allocation in existing_allocations}

        # Calculate total allocated percentage
        total_allocated = sum(allocations_dict.values())
        remaining_percentage = 100 - total_allocated

        return render_template(
            'admin/store_allocations.html',
            batch_id=batch_id,
            province=province,
            store_types=store_types,
            allocations=allocations_dict,
            total_allocated=total_allocated,
            remaining_percentage=remaining_percentage
        )

    # --------------------- API ENDPOINTS FOR STORE TYPES ---------------------
    @app.route('/api/store-types')
    @login_required
    def api_store_types():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        store_types = StoreType.query.all()
        result = [{
            'id': st.id,
            'name': st.name,
            'description': st.description
        } for st in store_types]

        return jsonify(result)

    @app.route('/api/batch/<batch_id>/store-type-exclusions')
    @login_required
    def api_batch_exclusions(batch_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get exclusions for each store type in this batch
        exclusions = ProductExclusionRule.query.filter_by(batch_id=batch_id).all()

        # Group by store type
        result = {}
        for exclusion in exclusions:
            if exclusion.store_type_id not in result:
                store_type = StoreType.query.get(exclusion.store_type_id)
                if store_type:
                    result[exclusion.store_type_id] = {
                        'id': store_type.id,
                        'name': store_type.name,
                        'excluded_products': []
                    }

            if exclusion.store_type_id in result:
                product = Product.query.get(exclusion.product_id)
                if product:
                    result[exclusion.store_type_id]['excluded_products'].append({
                        'id': product.id,
                        'name': product.name
                    })

        return jsonify(list(result.values()))

    @app.route('/api/batch/<batch_id>/store-type-allocations')
    @login_required
    def api_batch_allocations(batch_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Find province for this batch
        province = None
        csv_eval = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).first()
        if csv_eval and csv_eval.province:
            province = Province.query.filter_by(name=csv_eval.province).first()

        if not province:
            return jsonify({'error': 'No province found for this batch'}), 404

        # Get allocations for this batch and province
        allocations = StoreTypeAllocation.query.filter_by(
            batch_id=batch_id,
            province_id=province.id
        ).all()

        result = [{
            'store_type_id': allocation.store_type_id,
            'store_type_name': StoreType.query.get(allocation.store_type_id).name if StoreType.query.get(
                allocation.store_type_id) else 'Unknown',
            'percentage': allocation.percentage
        } for allocation in allocations]

        # Calculate total allocated percentage
        total_allocated = sum(allocation.percentage for allocation in allocations)

        return jsonify({
            'allocations': result,
            'total_allocated': total_allocated,
            'remaining_percentage': 100 - total_allocated
        })


    @app.route('/admin/batch_evaluations/<batch_id>/calculate_targets', methods=['POST'])
    @login_required
    def calculate_batch_targets(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get the province for this batch
        province_id = request.form.get('province_id')
        if not province_id:
            # Try to find from database
            csv_eval = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).first()
            if csv_eval and csv_eval.province:
                province = Province.query.filter_by(name=csv_eval.province).first()
                if province:
                    province_id = province.id

        if not province_id:
            flash('لطفاً ابتدا یک استان را به این دسته ارزیابی تخصیص دهید.', 'warning')
            return redirect(url_for('view_batch_evaluations', batch_id=batch_id))

        # Get province and products
        province = Province.query.get_or_404(province_id)
        products = Product.query.all()

        # Get grade distribution for this batch/province
        grade_counts = {}

        # Try with CSVEvaluationRecord first
        grade_dist_query = db.session.query(
            CSVEvaluationRecord.assigned_grade,
            db.func.count(CSVEvaluationRecord.id).label('count')
        ).filter(
            CSVEvaluationRecord.batch_id == batch_id,
            CSVEvaluationRecord.province == province.name
        ).group_by(CSVEvaluationRecord.assigned_grade).all()

        if not grade_dist_query:
            # Try with CustomerEvaluation
            grade_dist_query = db.session.query(
                CustomerEvaluation.assigned_grade,
                db.func.count(CustomerEvaluation.id).label('count')
            ).filter(
                CustomerEvaluation.batch_id == batch_id,
                CustomerEvaluation.province == province.name
            ).group_by(CustomerEvaluation.assigned_grade).all()

        for grade, count in grade_dist_query:
            grade_counts[grade] = count

        # Get grade weights from session or use default
        grade_weights = {
            'A+': 2.0,
            'A': 1.75,
            'B+': 1.5,
            'B': 1.25,
            'C': 1.0,
            'D': 0.75,
            'بدون درجه': 0.5
        }

        # Calculate total weighted count
        total_customers = sum(grade_counts.values())
        total_weighted_count = 0
        for grade, count in grade_counts.items():
            weight = grade_weights.get(grade, 0.5)
            total_weighted_count += count * weight

        # Delete existing targets for this batch
        BatchGradeTarget.query.filter_by(batch_id=batch_id).delete()

        # Get store type allocations
        store_type_allocations = StoreTypeAllocation.query.filter_by(
            batch_id=batch_id,
            province_id=province_id
        ).all()

        # Create a dictionary of store type allocations for easier access
        allocation_by_store_type = {
            allocation.store_type_id: allocation.percentage / 100  # Convert to decimal
            for allocation in store_type_allocations
        }

        # Get exclusion rules
        exclusion_rules = ProductExclusionRule.query.filter_by(
            batch_id=batch_id
        ).all()

        # Create a dictionary of excluded products by store type
        excluded_products = {}
        for rule in exclusion_rules:
            if rule.store_type_id not in excluded_products:
                excluded_products[rule.store_type_id] = []
            excluded_products[rule.store_type_id].append(rule.product_id)

        # Calculate and save targets for each product and grade
        for product in products:
            # Get province target for this product
            product_target = ProductProvinceTarget.query.filter_by(
                product_id=product.id,
                province_id=province_id
            ).first()

            if not product_target:
                continue

            # Create a dictionary to track capacity allocation by store type
            store_type_capacity_allocation = {}

            # First, handle store type allocations
            for store_type_id, allocation_percentage in allocation_by_store_type.items():
                # Check if this product is excluded for this store type
                if store_type_id in excluded_products and product.id in excluded_products[store_type_id]:
                    continue

                # Calculate allocation for this store type
                if product_target.liter_capacity is not None:
                    liter_allocation = product_target.liter_capacity * allocation_percentage
                else:
                    liter_allocation = None

                if product_target.shrink_capacity is not None:
                    shrink_allocation = product_target.shrink_capacity * allocation_percentage
                else:
                    shrink_allocation = None

                store_type_capacity_allocation[store_type_id] = {
                    'liter': liter_allocation,
                    'shrink': shrink_allocation
                }

            # Calculate the remaining capacity after store type allocations
            total_allocated_liter = sum(alloc['liter'] or 0 for alloc in store_type_capacity_allocation.values())
            total_allocated_shrink = sum(alloc['shrink'] or 0 for alloc in store_type_capacity_allocation.values())

            remaining_liter = None
            if product_target.liter_capacity is not None:
                remaining_liter = product_target.liter_capacity - total_allocated_liter

            remaining_shrink = None
            if product_target.shrink_capacity is not None:
                remaining_shrink = product_target.shrink_capacity - total_allocated_shrink

            # Now calculate grade-based targets for the remaining capacity
            for grade, count in grade_counts.items():
                if count == 0 or total_weighted_count == 0:
                    continue

                weight = grade_weights.get(grade, 0.5)

                # Calculate allocation based on weight for the remaining capacity
                liter_capacity = None
                shrink_capacity = None

                if remaining_liter is not None:
                    # Calculate total for this grade group
                    grade_liter = remaining_liter * weight * count / total_weighted_count
                    # Convert to per customer
                    liter_capacity = grade_liter / count

                if remaining_shrink is not None:
                    # Calculate total for this grade group
                    grade_shrink = remaining_shrink * weight * count / total_weighted_count
                    # Convert to per customer
                    shrink_capacity = grade_shrink / count

                # Save to database
                batch_target = BatchGradeTarget(
                    batch_id=batch_id,
                    province_id=province_id,
                    product_id=product.id,
                    grade=grade,
                    liter_capacity=liter_capacity,
                    shrink_capacity=shrink_capacity,
                    customer_count=count
                )
                db.session.add(batch_target)

                # Now add targets for specific store types
                for store_type_id, capacity in store_type_capacity_allocation.items():
                    # Check if this product is excluded for this store type
                    if store_type_id in excluded_products and product.id in excluded_products[store_type_id]:
                        continue

                    # Get customers of this grade and store type
                    store_type_customers = CustomerReport.query.filter_by(
                        province=province.name,
                        grade=grade,
                        store_type_id=store_type_id
                    ).count()

                    if store_type_customers > 0:
                        # Calculate per customer capacity
                        st_liter_capacity = None
                        st_shrink_capacity = None

                        if capacity['liter'] is not None:
                            st_liter_capacity = capacity['liter'] / store_type_customers

                        if capacity['shrink'] is not None:
                            st_shrink_capacity = capacity['shrink'] / store_type_customers

                        # Create a special target for this store type
                        store_type_target = BatchGradeTarget(
                            batch_id=batch_id,
                            province_id=province_id,
                            product_id=product.id,
                            grade=grade,
                            liter_capacity=st_liter_capacity,
                            shrink_capacity=st_shrink_capacity,
                            customer_count=store_type_customers,
                            store_type_id=store_type_id  # Add this field to the model
                        )
                        db.session.add(store_type_target)

        try:
            db.session.commit()
            flash('تارگت‌های مبتنی بر درجه‌بندی و نوع فروشگاه با موفقیت محاسبه و ذخیره شدند.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در ذخیره تارگت‌ها: {str(e)}', 'danger')

        return redirect(url_for('view_batch_evaluations', batch_id=batch_id))

    @app.route('/admin/batch_target/<int:target_id>/edit', methods=['POST'])
    @login_required
    def edit_batch_target(target_id):
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'دسترسی غیرمجاز!'})

        target = BatchGradeTarget.query.get_or_404(target_id)

        try:
            liter_capacity = request.form.get('liter_capacity')
            shrink_capacity = request.form.get('shrink_capacity')

            if liter_capacity is not None and liter_capacity.strip():
                target.liter_capacity = float(liter_capacity)

            if shrink_capacity is not None and shrink_capacity.strip():
                target.shrink_capacity = float(shrink_capacity)

            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'تارگت با موفقیت به‌روزرسانی شد.',
                'liter_capacity': target.liter_capacity,
                'shrink_capacity': target.shrink_capacity
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'خطا در به‌روزرسانی تارگت: {str(e)}'})

    @app.route('/admin/batch_target/<int:target_id>/delete', methods=['POST'])
    @login_required
    def delete_batch_target(target_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        target = BatchGradeTarget.query.get_or_404(target_id)
        batch_id = target.batch_id

        try:
            db.session.delete(target)
            db.session.commit()
            flash('تارگت با موفقیت حذف شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف تارگت: {str(e)}', 'danger')

        return redirect(url_for('view_batch_evaluations', batch_id=batch_id))

    # Update the get_customer_product_quotas function

    @app.route('/api/customer/<int:customer_id>/product_quotas')
    @login_required
    def get_customer_product_quotas(customer_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get the customer
        customer = CustomerReport.query.get_or_404(customer_id)

        if not customer.grade or not customer.province:
            return jsonify({
                'success': False,
                'message': 'مشتری درجه‌بندی یا استان تعیین شده ندارد.'
            })

        # Get the province
        province = Province.query.filter_by(name=customer.province).first()
        if not province:
            return jsonify({
                'success': False,
                'message': 'استان مشتری یافت نشد.'
            })

        # Get all products
        products = Product.query.all()

        # Prepare result with customer info
        result = {
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'number': customer.number,
                'grade': customer.grade,
                'province': customer.province,
                'store_type': {
                    'id': customer.store_type_id,
                    'name': customer.store_type.name if customer.store_type else None
                },
                'location': {
                    'latitude': customer.latitude,
                    'longitude': customer.longitude
                } if customer.latitude and customer.longitude else None
            },
            'products': []
        }

        # Find targets for each product
        for product in products:
            # Check if this customer belongs to a store type with product exclusions
            if customer.store_type_id:
                # Check if this product is excluded for this store type
                exclusion = ProductExclusionRule.query.filter_by(
                    store_type_id=customer.store_type_id,
                    product_id=product.id
                ).first()

                if exclusion:
                    # Skip this product as it's excluded for this store type
                    continue

            # First check if there are store-type specific targets for this customer
            store_type_target = None
            batch_id = None

            # Check if this customer has been evaluated in a batch
            customer_eval = CustomerEvaluation.query.filter_by(customer_id=customer.id).order_by(
                CustomerEvaluation.evaluated_at.desc()).first()

            if not customer_eval:
                # Try CSV evaluation
                csv_eval = CSVEvaluationRecord.query.filter_by(customer_id=customer.id).order_by(
                    CSVEvaluationRecord.evaluated_at.desc()).first()
                if csv_eval:
                    batch_id = csv_eval.batch_id
            else:
                batch_id = customer_eval.batch_id

            # If we have a batch ID and customer has a store type, check for store-type specific targets
            if batch_id and customer.store_type_id:
                store_type_target = BatchGradeTarget.query.filter_by(
                    batch_id=batch_id,
                    province_id=province.id,
                    product_id=product.id,
                    grade=customer.grade,
                    store_type_id=customer.store_type_id
                ).first()

                if store_type_target:
                    result['products'].append({
                        'id': product.id,
                        'name': product.name,
                        'liter_quota': store_type_target.liter_capacity,
                        'shrink_quota': store_type_target.shrink_capacity,
                        'source': 'store_type_target'
                    })
                    continue

            # If no store-type target, check regular batch targets
            batch_target = None
            if batch_id:
                batch_target = BatchGradeTarget.query.filter_by(
                    batch_id=batch_id,
                    province_id=province.id,
                    product_id=product.id,
                    grade=customer.grade,
                    store_type_id=None  # General targets have no store_type_id
                ).first()

            # If batch target found, use it
            if batch_target:
                result['products'].append({
                    'id': product.id,
                    'name': product.name,
                    'liter_quota': batch_target.liter_capacity,
                    'shrink_quota': batch_target.shrink_capacity,
                    'source': 'batch_target'
                })
                continue

            # If no batch target, calculate based on general province-product targets
            product_target = ProductProvinceTarget.query.filter_by(
                product_id=product.id,
                province_id=province.id
            ).first()

            if product_target:
                # Check for store type allocation
                if customer.store_type_id:
                    allocation = StoreTypeAllocation.query.filter_by(
                        store_type_id=customer.store_type_id,
                        province_id=province.id
                    ).first()

                    if allocation:
                        # Calculate based on allocation percentage
                        store_type_customers = CustomerReport.query.filter_by(
                            province=province.name,
                            store_type_id=customer.store_type_id,
                            grade=customer.grade
                        ).count()

                        if store_type_customers > 0:
                            liter_allocation = None
                            shrink_allocation = None

                            if product_target.liter_capacity is not None:
                                total_allocation = product_target.liter_capacity * (allocation.percentage / 100)
                                liter_allocation = total_allocation / store_type_customers

                            if product_target.shrink_capacity is not None:
                                total_allocation = product_target.shrink_capacity * (allocation.percentage / 100)
                                shrink_allocation = total_allocation / store_type_customers

                            result['products'].append({
                                'id': product.id,
                                'name': product.name,
                                'liter_quota': liter_allocation,
                                'shrink_quota': shrink_allocation,
                                'source': 'store_type_allocation'
                            })
                            continue

                # Grade weights for regular calculation
                grade_weights = {
                    'A+': 2.0,
                    'A': 1.75,
                    'B+': 1.5,
                    'B': 1.25,
                    'C': 1.0,
                    'D': 0.75,
                    'بدون درجه': 0.5
                }

                # Get customer count by grade in this province
                customers_by_grade = {}
                province_customers = CustomerReport.query.filter_by(province=province.name).all()

                for prov_customer in province_customers:
                    grade = prov_customer.grade or 'بدون درجه'
                    if grade not in customers_by_grade:
                        customers_by_grade[grade] = 0
                    customers_by_grade[grade] += 1

                # Calculate weighted total
                total_weighted_count = 0
                for grade, count in customers_by_grade.items():
                    weight = grade_weights.get(grade, 0.5)
                    total_weighted_count += count * weight

                # If this grade has customers and there's a total weighted count
                if customer.grade in customers_by_grade and customers_by_grade[
                    customer.grade] > 0 and total_weighted_count > 0:
                    grade_count = customers_by_grade[customer.grade]
                    weight = grade_weights.get(customer.grade, 0.5)

                    # Calculate liter allocation
                    liter_allocation = None
                    if product_target.liter_capacity is not None:
                        grade_liter = product_target.liter_capacity * weight * grade_count / total_weighted_count
                        liter_allocation = grade_liter / grade_count

                    # Calculate shrink allocation
                    shrink_allocation = None
                    if product_target.shrink_capacity is not None:
                        grade_shrink = product_target.shrink_capacity * weight * grade_count / total_weighted_count
                        shrink_allocation = grade_shrink / grade_count

                    # Add product if it has any allocation
                    if liter_allocation is not None or shrink_allocation is not None:
                        result['products'].append({
                            'id': product.id,
                            'name': product.name,
                            'liter_quota': liter_allocation,
                            'shrink_quota': shrink_allocation,
                            'source': 'calculated'
                        })

        return jsonify(result)

    # API endpoints for managing customer store types

    @app.route('/api/customer/<int:customer_id>/store-type', methods=['POST'])
    @login_required
    def update_customer_store_type(customer_id):
        """Update a customer's store type"""
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        customer = CustomerReport.query.get_or_404(customer_id)
        store_type_id = request.json.get('store_type_id')

        if store_type_id is not None:
            # If store_type_id is 0 or empty string, set to None
            if store_type_id == 0 or store_type_id == '':
                customer.store_type_id = None
            else:
                # Verify store type exists
                store_type = StoreType.query.get(store_type_id)
                if not store_type:
                    return jsonify({'success': False, 'message': 'نوع فروشگاه یافت نشد'}), 404
                customer.store_type_id = store_type_id

            try:
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'نوع فروشگاه مشتری با موفقیت به‌روزرسانی شد',
                    'store_type': {
                        'id': customer.store_type_id,
                        'name': customer.store_type.name if customer.store_type else None
                    }
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'خطا در به‌روزرسانی: {str(e)}'}), 500
        else:
            return jsonify({'success': False, 'message': 'شناسه نوع فروشگاه ارائه نشده است'}), 400

    @app.route('/api/batch/<batch_id>/customers/store-type', methods=['POST'])
    @login_required
    def batch_update_customer_store_types(batch_id):
        """Update store types for multiple customers in a batch"""
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.json
        if not data or 'updates' not in data:
            return jsonify({'success': False, 'message': 'داده‌های به‌روزرسانی ارائه نشده است'}), 400

        updates = data['updates']
        if not isinstance(updates, list):
            return jsonify({'success': False, 'message': 'فرمت داده‌های به‌روزرسانی نامعتبر است'}), 400

        # Collect customer IDs from batch
        customer_ids = set()
        csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()
        for eval in csv_evals:
            if eval.customer_id:
                customer_ids.add(eval.customer_id)

        cust_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).all()
        for eval in cust_evals:
            customer_ids.add(eval.customer_id)

        success_count = 0
        errors = []

        for update in updates:
            customer_id = update.get('customer_id')
            store_type_id = update.get('store_type_id')

            if not customer_id or store_type_id is None:
                errors.append(f'داده‌های نامعتبر برای مشتری: {customer_id}')
                continue

            # Verify customer belongs to batch
            if customer_id not in customer_ids:
                errors.append(f'مشتری {customer_id} به این دسته ارزیابی تعلق ندارد')
                continue

            # Update store type
            customer = CustomerReport.query.get(customer_id)
            if not customer:
                errors.append(f'مشتری با شناسه {customer_id} یافت نشد')
                continue

            # If store_type_id is 0, set to None
            if store_type_id == 0 or store_type_id == '':
                customer.store_type_id = None
            else:
                # Verify store type exists
                store_type = StoreType.query.get(store_type_id)
                if not store_type:
                    errors.append(f'نوع فروشگاه {store_type_id} برای مشتری {customer_id} یافت نشد')
                    continue

                customer.store_type_id = store_type_id

            success_count += 1

        # Commit all changes
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'{success_count} مشتری با موفقیت به‌روزرسانی شد',
                'errors': errors if errors else None
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'خطا در به‌روزرسانی: {str(e)}'}), 500

    @app.route('/api/batch/<batch_id>/store-type-summary')
    @login_required
    def get_batch_store_type_summary(batch_id):
        """Get summary of customer store types in a batch"""
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get province for this batch
        province = None
        csv_eval = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).first()
        if csv_eval and csv_eval.province:
            province_name = csv_eval.province
            province = Province.query.filter_by(name=province_name).first()

        if not province:
            cust_eval = CustomerEvaluation.query.filter_by(batch_id=batch_id).first()
            if cust_eval and cust_eval.province:
                province_name = cust_eval.province
                province = Province.query.filter_by(name=province_name).first()

        if not province:
            return jsonify({'success': False, 'message': 'استان برای این دسته ارزیابی یافت نشد'}), 404

        # Get all store types
        store_types = StoreType.query.all()

        # Get customer evaluations for this batch
        customer_ids = set()
        csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()
        for eval in csv_evals:
            if eval.customer_id:
                customer_ids.add(eval.customer_id)

        cust_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).all()
        for eval in cust_evals:
            customer_ids.add(eval.customer_id)

        # Get customers by grade and store type
        customers_by_grade_and_store_type = {}
        total_by_store_type = {}
        total_by_grade = {}
        unassigned_count = 0

        customers = CustomerReport.query.filter(
            CustomerReport.id.in_(customer_ids),
            CustomerReport.province == province.name
        ).all()

        for customer in customers:
            grade = customer.grade or 'بدون درجه'

            # Count by grade
            if grade not in total_by_grade:
                total_by_grade[grade] = 0
            total_by_grade[grade] += 1

            if customer.store_type_id:
                # Count by store type
                if customer.store_type_id not in total_by_store_type:
                    total_by_store_type[customer.store_type_id] = 0
                total_by_store_type[customer.store_type_id] += 1

                # Count by grade and store type
                if grade not in customers_by_grade_and_store_type:
                    customers_by_grade_and_store_type[grade] = {}

                if customer.store_type_id not in customers_by_grade_and_store_type[grade]:
                    customers_by_grade_and_store_type[grade][customer.store_type_id] = 0

                customers_by_grade_and_store_type[grade][customer.store_type_id] += 1
            else:
                unassigned_count += 1

        # Prepare store type data
        store_type_data = []
        for store_type in store_types:
            count = total_by_store_type.get(store_type.id, 0)
            percentage = (count / len(customers)) * 100 if customers else 0

            # Get grade distribution for this store type
            grade_distribution = []
            for grade in sorted(total_by_grade.keys()):
                grade_count = customers_by_grade_and_store_type.get(grade, {}).get(store_type.id, 0)
                grade_percentage = (grade_count / count) * 100 if count > 0 else 0

                grade_distribution.append({
                    'grade': grade,
                    'count': grade_count,
                    'percentage': round(grade_percentage, 1)
                })

            store_type_data.append({
                'id': store_type.id,
                'name': store_type.name,
                'count': count,
                'percentage': round(percentage, 1),
                'grade_distribution': grade_distribution
            })

        # Add unassigned customers
        unassigned_percentage = (unassigned_count / len(customers)) * 100 if customers else 0

        return jsonify({
            'success': True,
            'total_customers': len(customers),
            'grades': [{'grade': g, 'count': c} for g, c in total_by_grade.items()],
            'store_types': store_type_data,
            'unassigned': {
                'count': unassigned_count,
                'percentage': round(unassigned_percentage, 1)
            }
        })

    @app.route('/api/evaluations/<int:eval_id>')
    @login_required
    def get_evaluation_details(eval_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # First check if it's a CSVEvaluationRecord
        evaluation = CSVEvaluationRecord.query.get(eval_id)
        if evaluation:
            return jsonify({
                'id': evaluation.id,
                'total_score': evaluation.total_score,
                'assigned_grade': evaluation.assigned_grade,
                'evaluated_at': evaluation.evaluated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'batch_id': evaluation.batch_id,
                'customer_id': evaluation.customer_id,
                'is_csv_record': True
            })

        # If not found, try CustomerEvaluation
        evaluation = CustomerEvaluation.query.get(eval_id)
        if evaluation:
            return jsonify({
                'id': evaluation.id,
                'total_score': evaluation.total_score,
                'assigned_grade': evaluation.assigned_grade,
                'evaluated_at': evaluation.evaluated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'batch_id': evaluation.batch_id,
                'customer_id': evaluation.customer_id,
                'is_csv_record': False
            })

        return jsonify({'error': 'Evaluation not found'}), 404

    @app.route('/api/customer/<int:customer_id>/details')
    @login_required
    def get_customer_details(customer_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        customer = CustomerReport.query.get_or_404(customer_id)

        # Get the latest evaluation
        latest_eval = CustomerEvaluation.query.filter_by(customer_id=customer.id).order_by(
            CustomerEvaluation.evaluated_at.desc()).first()

        # Get CSV evaluation if this customer has one
        csv_eval = CSVEvaluationRecord.query.filter_by(customer_id=customer.id).order_by(
            CSVEvaluationRecord.evaluated_at.desc()).first()

        result = {
            'id': customer.id,
            'name': customer.name or 'بدون نام',
            'number': customer.number or 'بدون شماره',
            'grade': customer.grade or 'بدون درجه',
            'province': customer.province or 'نامشخص',
            'location': {
                'latitude': customer.latitude,
                'longitude': customer.longitude
            } if customer.latitude and customer.longitude else None,
            'evaluation': None
        }

        # Add detailed fields from customer
        for field in ['textbox29', 'caption', 'bname', 'textbox16', 'textbox12', 'textbox4', 'textbox10']:
            if hasattr(customer, field) and getattr(customer, field):
                result[field] = getattr(customer, field)

        # Add evaluation details if available
        if latest_eval:
            result['evaluation'] = {
                'id': latest_eval.id,
                'total_score': latest_eval.total_score,
                'assigned_grade': latest_eval.assigned_grade,
                'evaluated_at': latest_eval.evaluated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'evaluation_method': latest_eval.evaluation_method,
                'batch_id': latest_eval.batch_id
            }
        elif csv_eval:
            result['evaluation'] = {
                'id': csv_eval.id,
                'total_score': csv_eval.total_score,
                'assigned_grade': csv_eval.assigned_grade,
                'evaluated_at': csv_eval.evaluated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'evaluation_method': 'csv',
                'batch_id': csv_eval.batch_id,
                'row_data': csv_eval.row_data
            }

        return jsonify(result)

    # Add this to your app.py file

    @app.route('/api/batch/<batch_id>/customers')
    @login_required
    def get_batch_customers(batch_id):
        """Get all customers in a batch evaluation"""
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get province for this batch
        province_name = None
        csv_eval = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).first()
        if csv_eval and csv_eval.province:
            province_name = csv_eval.province

        if not province_name:
            cust_eval = CustomerEvaluation.query.filter_by(batch_id=batch_id).first()
            if cust_eval and cust_eval.province:
                province_name = cust_eval.province

        if not province_name:
            return jsonify([])

        # First get customer IDs from evaluations
        customer_ids = set()

        # Get IDs from CSV evaluations
        csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()
        for eval in csv_evals:
            if eval.customer_id:
                customer_ids.add(eval.customer_id)

        # Get IDs from customer evaluations
        cust_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).all()
        for eval in cust_evals:
            customer_ids.add(eval.customer_id)

        # Get all customers in this province matching those IDs
        customers = []
        if customer_ids:
            customers = CustomerReport.query.filter(
                CustomerReport.id.in_(customer_ids),
                CustomerReport.province == province_name
            ).all()

        # Get store types for all customers
        store_types = {st.id: st.name for st in StoreType.query.all()}

        # Format customer data
        result = []
        for customer in customers:
            store_type_name = store_types.get(customer.store_type_id, None) if customer.store_type_id else None

            result.append({
                'id': customer.id,
                'number': customer.number,
                'name': customer.name,
                'grade': customer.grade,
                'province': customer.province,
                'store_type_id': customer.store_type_id,
                'store_type_name': store_type_name
            })

        return jsonify(result)
    # Add API endpoint for marketer to update location
    @app.route('/api/marketer/update-location', methods=['POST'])
    @login_required
    def api_update_location():
        if current_user.role != 'marketer':
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.json
        if not data or 'lat' not in data or 'lng' not in data:
            return jsonify({'error': 'Invalid data'}), 400
        
        try:
            current_user.current_lat = float(data['lat'])
            current_user.current_lng = float(data['lng'])
            current_user.last_location_update = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Location updated'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    return app

if __name__ == '__main__':
   application = create_app()
   application.run(debug=True, port=5000)
