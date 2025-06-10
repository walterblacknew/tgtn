from extentions import db
from flask_login import UserMixin
from datetime import datetime, timezone


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='marketer')
    email = db.Column(db.String(120), unique=True, nullable=True)
    fullname = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # Fields for live location updates
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    assigned_routes = db.relationship('RouteAssignment', backref='marketer', lazy=True)

    # New fields for job information
    job_title = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    position_level = db.Column(db.Integer, default=0)  # Organizational level (0=top)

    def __repr__(self):
        return f'<User {self.username}, role={self.role}>'


class UserHierarchy(db.Model):
    __tablename__ = 'user_hierarchy'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.Integer, default=1)  # Depth in the hierarchy
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    parent = db.relationship('User', foreign_keys=[parent_id], backref='subordinates_rel')
    child = db.relationship('User', foreign_keys=[child_id], backref='superiors_rel')

    __table_args__ = (db.UniqueConstraint('parent_id', 'child_id', name='_parent_child_uc'),)


class Route(db.Model):
    __tablename__ = 'route'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field
    points = db.relationship('RoutePoint', backref='route', lazy=True, order_by='RoutePoint.order')
    assignments = db.relationship('RouteAssignment', backref='route', lazy=True)

    def __repr__(self):
        return f'<Route {self.name}>'


class RoutePoint(db.Model):
    __tablename__ = 'route_point'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<RoutePoint {self.name} ({self.latitude}, {self.longitude})>'


class RouteAssignment(db.Model):
    __tablename__ = 'route_assignment'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    marketer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<RouteAssignment route={self.route_id}, marketer={self.marketer_id}>'


class Store(db.Model):
    __tablename__ = 'store'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field

    def __repr__(self):
        return f'<Store {self.name} lat={self.lat} lng={self.lng}>'


class EvaluationParameter(db.Model):
    __tablename__ = 'evaluation_parameter'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<EvaluationParameter {self.name} (weight={self.weight})>'


class StoreEvaluation(db.Model):
    __tablename__ = 'store_evaluation'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    total_score = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    province = db.Column(db.String(100), nullable=True)  # Added province field

    store = db.relationship('Store', backref='evaluations', lazy=True)
    details = db.relationship('StoreEvaluationDetail', backref='evaluation', lazy=True)

    def __repr__(self):
        return f'<StoreEvaluation store={self.store_id}, total_score={self.total_score}>'


class StoreEvaluationDetail(db.Model):
    __tablename__ = 'store_evaluation_detail'
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('store_evaluation.id'), nullable=False)
    parameter_id = db.Column(db.Integer, db.ForeignKey('evaluation_parameter.id'), nullable=False)
    score = db.Column(db.Float, default=0.0)

    parameter = db.relationship('EvaluationParameter', backref='evaluation_details', lazy=True)

    def __repr__(self):
        return f'<StoreEvaluationDetail eval={self.evaluation_id}, param={self.parameter_id}, score={self.score}>'


class QuotaCategory(db.Model):
    __tablename__ = 'quota_category'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, unique=True)
    monthly_quota = db.Column(db.Integer, default=100)

    def __repr__(self):
        return f'<QuotaCategory {self.category} quota={self.monthly_quota}>'


class StoreType(db.Model):
    """Store type model to categorize stores (supermarket, cafe, etc.)"""
    __tablename__ = 'store_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    exclusion_rules = db.relationship('ProductExclusionRule', backref='store_type', lazy=True)
    allocation_rules = db.relationship('StoreTypeAllocation', backref='store_type', lazy=True)

    def __repr__(self):
        return f'<StoreType {self.name}>'


class ProductExclusionRule(db.Model):
    """Rules for excluding products from specific store types"""
    __tablename__ = 'product_exclusion_rule'
    id = db.Column(db.Integer, primary_key=True)
    store_type_id = db.Column(db.Integer, db.ForeignKey('store_type.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    batch_id = db.Column(db.String(50), nullable=True)  # Optional: for batch-specific rules
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationship
    product = db.relationship('Product', backref='exclusion_rules', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('store_type_id', 'product_id', 'batch_id', name='_store_product_batch_uc'),
    )

    def __repr__(self):
        return f'<ProductExclusionRule store_type={self.store_type_id} product={self.product_id}>'


class StoreTypeAllocation(db.Model):
    """Allocation percentages for store types from total quota"""
    __tablename__ = 'store_type_allocation'
    id = db.Column(db.Integer, primary_key=True)
    store_type_id = db.Column(db.Integer, db.ForeignKey('store_type.id'), nullable=False)
    batch_id = db.Column(db.String(50), nullable=False)
    province_id = db.Column(db.Integer, db.ForeignKey('province.id'), nullable=False)
    percentage = db.Column(db.Float, nullable=False)  # Percentage of total allocation
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationship
    province = db.relationship('Province', backref='store_allocations', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('store_type_id', 'batch_id', 'province_id', name='_store_batch_province_uc'),
    )

    def __repr__(self):
        return f'<StoreTypeAllocation store_type={self.store_type_id} batch={self.batch_id} percentage={self.percentage}%>'


class CustomerReport(db.Model):
    __tablename__ = 'customer_report'
    id = db.Column(db.Integer, primary_key=True)
    textbox29 = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.String(255), nullable=True)
    bname = db.Column(db.String(255), nullable=True)
    number = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    textbox16 = db.Column(db.String(255), nullable=True)
    textbox12 = db.Column(db.String(255), nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    textbox4 = db.Column(db.String(255), nullable=True)
    textbox10 = db.Column(db.String(255), nullable=True)
    grade = db.Column(db.String(10), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Province field
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    store_type_id = db.Column(db.Integer, db.ForeignKey('store_type.id'), nullable=True)
    store_type = db.relationship('StoreType', backref='customers', lazy=True)
    evaluations = db.relationship('CustomerEvaluation', backref='customer', lazy=True)
    csv_evaluations = db.relationship('CSVEvaluationRecord', backref='customer', lazy=True)

    def __repr__(self):
        return f'<CustomerReport {self.name}>'


class RouteReport(db.Model):
    __tablename__ = 'route_report'
    id = db.Column(db.Integer, primary_key=True)
    route_number = db.Column(db.String(50), nullable=True)
    route_name = db.Column(db.String(255), nullable=True)
    number_of_customers = db.Column(db.Integer, nullable=True)
    employee_intermediary = db.Column(db.String(255), nullable=True)
    sales_center = db.Column(db.String(255), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<RouteReport {self.route_name}>'


class GradeMapping(db.Model):
    __tablename__ = 'grade_mapping'
    id = db.Column(db.Integer, primary_key=True)
    grade_letter = db.Column(db.String(10), unique=True, nullable=False)
    min_score = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<GradeMapping {self.grade_letter}: {self.min_score}>'


class CustomerEvaluation(db.Model):
    __tablename__ = 'customer_evaluation'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_report.id'), nullable=False)
    total_score = db.Column(db.Float, nullable=False)
    assigned_grade = db.Column(db.String(10), nullable=False)
    evaluated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    evaluation_method = db.Column(db.String(20), default='manual')
    batch_id = db.Column(db.String(50), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field

    def __repr__(self):
        return f'<CustomerEvaluation customer={self.customer_id}, grade={self.assigned_grade}, score={self.total_score}>'


class DescriptiveCriterion(db.Model):
    __tablename__ = 'descriptive_criterion'
    id = db.Column(db.Integer, primary_key=True)
    parameter_name = db.Column(db.String(255), nullable=False)
    criterion = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<DescriptiveCriterion {self.parameter_name}: {self.criterion}={self.score}>'


class CSVEvaluationRecord(db.Model):
    __tablename__ = 'csv_evaluation_record'
    id = db.Column(db.Integer, primary_key=True)
    row_data = db.Column(db.JSON)
    total_score = db.Column(db.Float, nullable=False)
    assigned_grade = db.Column(db.String(10), nullable=False)
    evaluated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    batch_id = db.Column(db.String(50), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_report.id'), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field

    def __repr__(self):
        return f'<CSVEvaluationRecord grade={self.assigned_grade}, score={self.total_score}>'


class Province(db.Model):
    __tablename__ = 'province'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    population = db.Column(db.Integer, nullable=False)

    targets = db.relationship('ProvinceTarget', backref='province', lazy=True)

    def __repr__(self):
        return f'<Province {self.name}, population={self.population}>'


class ProvinceTarget(db.Model):
    __tablename__ = 'province_target'
    id = db.Column(db.Integer, primary_key=True)
    province_id = db.Column(db.Integer, db.ForeignKey('province.id'), nullable=False)
    liter_capacity = db.Column(db.Float, nullable=True)
    shrink_capacity = db.Column(db.Float, nullable=True)
    liter_percentage = db.Column(db.Float, nullable=True)
    shrink_percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ProvinceTarget for {self.province.name if self.province else "Unknown"}>'


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    # New relationships
    category_id = db.Column(db.Integer, db.ForeignKey('product_category.id'), nullable=True)
    flavor_id = db.Column(db.Integer, db.ForeignKey('product_flavor.id'), nullable=True)
    packaging_id = db.Column(db.Integer, db.ForeignKey('product_packaging.id'), nullable=True)
    volume_id = db.Column(db.Integer, db.ForeignKey('product_volume.id'), nullable=True)

    # Original fields
    liter_capacity = db.Column(db.Float, nullable=True)
    shrink_capacity = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    province_targets = db.relationship('ProductProvinceTarget', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'


class ProductCategory(db.Model):
    """Product category model to store reusable categories"""
    __tablename__ = 'product_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    products = db.relationship('Product', backref='category_relation', lazy=True)

    def __repr__(self):
        return f'<ProductCategory {self.name}>'


class ProductFlavor(db.Model):
    """Product flavor model to store reusable flavors"""
    __tablename__ = 'product_flavor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    products = db.relationship('Product', backref='flavor_relation', lazy=True)

    def __repr__(self):
        return f'<ProductFlavor {self.name}>'


class ProductPackaging(db.Model):
    """Product packaging model to store reusable packaging types"""
    __tablename__ = 'product_packaging'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    products = db.relationship('Product', backref='packaging_relation', lazy=True)

    def __repr__(self):
        return f'<ProductPackaging {self.name}>'


class ProductVolume(db.Model):
    """Product volume model to store reusable volumes"""
    __tablename__ = 'product_volume'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='لیتر')
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    products = db.relationship('Product', backref='volume_relation', lazy=True)

    __table_args__ = (db.UniqueConstraint('value', 'unit', name='_volume_unit_uc'),)

    def __repr__(self):
        return f'<ProductVolume {self.value} {self.unit}>'

    @property
    def display_name(self):
        """Format volume for display"""
        return f"{self.value} {self.unit}"


class ProductProvinceTarget(db.Model):
    __tablename__ = 'product_province_target'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    province_id = db.Column(db.Integer, db.ForeignKey('province.id'), nullable=False)
    liter_capacity = db.Column(db.Float, nullable=True)
    shrink_capacity = db.Column(db.Float, nullable=True)
    liter_percentage = db.Column(db.Float, nullable=True)
    shrink_percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('product_id', 'province_id', name='_product_province_uc'),)

    def __repr__(self):
        return f'<ProductProvinceTarget {self.product_id}_{self.province_id}>'


# Add this to models.py (a new model for batch targets)
# Update the BatchGradeTarget model in models.py

class BatchGradeTarget(db.Model):
    __tablename__ = 'batch_grade_target'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(50), nullable=False)
    province_id = db.Column(db.Integer, db.ForeignKey('province.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    liter_capacity = db.Column(db.Float, nullable=True)
    shrink_capacity = db.Column(db.Float, nullable=True)
    customer_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    # Add the store type field
    store_type_id = db.Column(db.Integer, db.ForeignKey('store_type.id'), nullable=True)

    # Relationships
    province = db.relationship('Province', backref='batch_grade_targets', lazy=True)
    product = db.relationship('Product', backref='batch_grade_targets', lazy=True)
    store_type = db.relationship('StoreType', backref='batch_grade_targets', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('batch_id', 'province_id', 'product_id', 'grade', 'store_type_id', name='_batch_product_grade_storetype_uc'),
    )

    def __repr__(self):
        store_type_info = f", store_type={self.store_type_id}" if self.store_type_id else ""
        return f'<BatchGradeTarget batch={self.batch_id} product={self.product_id} grade={self.grade}{store_type_info}>'


