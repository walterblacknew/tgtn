# forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField,
    SelectField, SelectMultipleField, TextAreaField, FloatField,
    IntegerField, DateField
)
from wtforms.validators import DataRequired, Length, Optional, Email, NumberRange
from flask_wtf.file import FileField, FileAllowed, FileRequired


# --------------------- Authentication & User Management ---------------------
class LoginForm(FlaskForm):
    username = StringField('نام کاربری', validators=[DataRequired()])
    password = PasswordField('رمز عبور', validators=[DataRequired()])
    submit = SubmitField('ورود')


class UserForm(FlaskForm):
    username = StringField('نام کاربری', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('رمز عبور', validators=[DataRequired(), Length(min=4, max=50)])
    email = StringField('ایمیل', validators=[Optional(), Email(), Length(max=120)])
    fullname = StringField('نام و نام خانوادگی', validators=[Optional(), Length(max=120)])
    is_active = BooleanField('فعال')
    role = SelectField('نقش کاربر', choices=[
        ('admin', 'مدیر'),
        ('marketer', 'بازاریاب'),
        ('observer', 'ناظر')
    ])
    # New fields for job information
    job_title = StringField('عنوان شغلی', validators=[Optional(), Length(max=100)])
    department = StringField('دپارتمان', validators=[Optional(), Length(max=100)])
    parent_id = SelectField('زیرمجموعه کاربر', coerce=int, validators=[Optional()])
    submit = SubmitField('ذخیره')


# --------------------- Route & Point Management ---------------------
class RouteForm(FlaskForm):
    name = StringField('نام مسیر', validators=[DataRequired()])
    description = TextAreaField('توضیحات', validators=[Optional()])
    marketer_ids = SelectMultipleField('بازاریاب‌ها', coerce=int)
    submit = SubmitField('ذخیره مسیر')


class RoutePointForm(FlaskForm):
    name = StringField('نام نقطه', validators=[DataRequired()])
    latitude = FloatField('عرض جغرافیایی', validators=[
        DataRequired(),
        NumberRange(min=-90, max=90)
    ])
    longitude = FloatField('طول جغرافیایی', validators=[
        DataRequired(),
        NumberRange(min=-180, max=180)
    ])
    address = TextAreaField('آدرس', validators=[Optional()])
    order = IntegerField('ترتیب', validators=[DataRequired()])
    submit = SubmitField('افزودن نقطه')


# --------------------- Store & Evaluation ---------------------
class StoreForm(FlaskForm):
    name = StringField('نام فروشگاه', validators=[DataRequired(), Length(max=150)])
    lat = FloatField('عرض جغرافیایی', validators=[Optional()])
    lng = FloatField('طول جغرافیایی', validators=[Optional()])
    submit = SubmitField('ایجاد فروشگاه')


class EvaluationParameterForm(FlaskForm):
    name = StringField('نام پارامتر', validators=[DataRequired(), Length(max=150)])
    weight = FloatField('وزن', validators=[Optional()])
    submit = SubmitField('ذخیره')


class StoreEvaluationForm(FlaskForm):
    store_id = SelectField('فروشگاه', coerce=int, validators=[DataRequired()])
    start_date = DateField('تاریخ شروع', validators=[Optional()])
    end_date = DateField('تاریخ پایان', validators=[Optional()])
    submit = SubmitField('ایجاد ارزیابی')


class QuotaCategoryForm(FlaskForm):
    category = StringField('دسته‌بندی', validators=[DataRequired(), Length(max=50)])
    monthly_quota = IntegerField('سهمیه ماهانه', validators=[DataRequired()])
    submit = SubmitField('ذخیره سهمیه')


# --------------------- CSV Upload Forms ---------------------
class CSVRouteUploadForm(FlaskForm):
    route_csv = FileField('فایل CSV اطلاعات مسیر', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'فقط فایل CSV مجاز است.')
    ])
    submit = SubmitField('بارگذاری')


class CSVCustomerUploadForm(FlaskForm):
    customer_csv = FileField('فایل CSV اطلاعات مشتریان', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'فقط فایل CSV مجاز است.')
    ])
    submit = SubmitField('بارگذاری')


# --------------------- New Grade Mapping Form ---------------------
class GradeMappingForm(FlaskForm):
    grade_letter = StringField('درجه', validators=[DataRequired(), Length(max=10)])
    min_score = FloatField('حداقل نمره', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('ذخیره')


# --------------------- New Customer Evaluation Form ---------------------
# Updated to reflect the new parameter structure.
class CustomerEvaluationForm(FlaskForm):
    customer_id = SelectField('مشتری', coerce=int, validators=[DataRequired()])

    # Parameter 1: شاخص فروش with sub-parameters
    sales_volume_weight = FloatField('وزن فروش بر مبنای حجم/تعداد', validators=[DataRequired()])
    sales_volume_score = FloatField('امتیاز فروش بر مبنای حجم/تعداد', validators=[DataRequired()])
    sales_revenue_weight = FloatField('وزن فروش بر مبنای ریالی/تومانی', validators=[DataRequired()])
    sales_revenue_score = FloatField('امتیاز فروش بر مبنای ریالی/تومانی', validators=[DataRequired()])
    sales_diversity_weight = FloatField('وزن تنوع فروش', validators=[DataRequired()])
    sales_diversity_score = FloatField('امتیاز تنوع فروش', validators=[DataRequired()])

    # Parameter 2: ابعاد فروشگاه (no sub-parameters)
    store_dimensions_weight = FloatField('وزن ابعاد فروشگاه', validators=[DataRequired()])
    store_dimensions_score = FloatField('امتیاز ابعاد فروشگاه', validators=[DataRequired()])

    # Parameter 3: میزان بر فروشگاه (کنار خیابون بودن) (no sub-parameters)
    street_visibility_weight = FloatField('وزن میزان کنار خیابون بودن', validators=[DataRequired()])
    street_visibility_score = FloatField('امتیاز میزان کنار خیابون بودن', validators=[DataRequired()])

    # Parameter 4: لوکیشن with sub-parameters
    location_city_weight = FloatField('وزن میزان شهری/روستایی', validators=[DataRequired()])
    location_city_score = FloatField('امتیاز میزان شهری/روستایی', validators=[DataRequired()])
    location_zone_weight = FloatField('وزن منطقه در شهر یا روستا', validators=[DataRequired()])
    location_zone_score = FloatField('امتیاز منطقه در شهر یا روستا', validators=[DataRequired()])

    # Parameter 5: مالکیت مغازه with sub-parameters
    ownership_owner_weight = FloatField('وزن مالکیت (مالک)', validators=[DataRequired()])
    ownership_owner_score = FloatField('امتیاز مالکیت (مالک)', validators=[DataRequired()])
    ownership_rented_weight = FloatField('وزن مالکیت (اجاره‌ای)', validators=[DataRequired()])
    ownership_rented_score = FloatField('امتیاز مالکیت (اجاره‌ای)', validators=[DataRequired()])
    ownership_owned_weight = FloatField('وزن مالکیت (سرقفلی)', validators=[DataRequired()])
    ownership_owned_score = FloatField('امتیاز مالکیت (سرقفلی)', validators=[DataRequired()])

    # Parameter 6: میزان نظافت و زیبایی (no sub-parameters)
    cleanliness_weight = FloatField('وزن میزان نظافت و زیبایی', validators=[DataRequired()])
    cleanliness_score = FloatField('امتیاز میزان نظافت و زیبایی', validators=[DataRequired()])

    # Parameter 7: میزان تجهیزات (no sub-parameters)
    equipment_weight = FloatField('وزن میزان تجهیزات', validators=[DataRequired()])
    equipment_score = FloatField('امتیاز میزان تجهیزات', validators=[DataRequired()])

    # Parameter 8: حضور کالاهای لوکس (no sub-parameters)
    luxury_weight = FloatField('وزن حضور کالاهای لوکس', validators=[DataRequired()])
    luxury_score = FloatField('امتیاز حضور کالاهای لوکس', validators=[DataRequired()])

    # Parameter 9: حضور برندهای معتبر (no sub-parameters)
    brand_weight = FloatField('وزن حضور برندهای معتبر', validators=[DataRequired()])
    brand_score = FloatField('امتیاز حضور برندهای معتبر', validators=[DataRequired()])

    submit = SubmitField('ذخیره ارزیابی')


# --------------------- Target Setting Form ---------------------
class TargetSettingForm(FlaskForm):
    liter_enabled = BooleanField('ظرفیت بر حسب لیتر')
    liter_capacity = FloatField('ظرفیت کل (لیتر)', validators=[Optional()])

    shrink_enabled = BooleanField('ظرفیت بر حسب شرینک')
    shrink_capacity = FloatField('ظرفیت کل (شرینک)', validators=[Optional()])

    submit = SubmitField('محاسبه و ذخیره تارگت‌ها')


class ProductForm(FlaskForm):
    name = StringField('نام محصول', validators=[DataRequired(), Length(max=100)])

    # New fields with select/options for reusability
    category_id = SelectField('دسته بندی', coerce=int, validators=[Optional()])
    new_category = StringField('دسته بندی جدید', validators=[Optional(), Length(max=100)])

    flavor_id = SelectField('طعم', coerce=int, validators=[Optional()])
    new_flavor = StringField('طعم جدید', validators=[Optional(), Length(max=100)])

    packaging_id = SelectField('بسته بندی', coerce=int, validators=[Optional()])
    new_packaging = StringField('بسته بندی جدید', validators=[Optional(), Length(max=100)])

    volume_id = SelectField('حجم', coerce=int, validators=[Optional()])
    new_volume = FloatField('حجم جدید', validators=[Optional()])
    volume_unit = StringField('واحد', validators=[Optional(), Length(max=20)], default='لیتر')

    # Original fields
    liter_capacity = FloatField('ظرفیت کل (لیتر)', validators=[Optional()])
    shrink_capacity = FloatField('ظرفیت کل (شرینک)', validators=[Optional()])
    submit = SubmitField('ذخیره محصول')



# Add to forms.py
class CustomerTypeForm(FlaskForm):
    name = StringField('نوع مشتری', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('توضیحات', validators=[Optional()])
    submit = SubmitField('ذخیره')


# Add this to forms.py

class CustomerTypeQuotaForm(FlaskForm):
    customer_type_id = SelectField('نوع فروشگاه', coerce=int, validators=[DataRequired()])
    product_id = SelectField('محصول', coerce=int, validators=[Optional()])
    province_id = SelectField('استان', coerce=int, validators=[Optional()])
    percentage = FloatField('درصد تخصیص', validators=[
        DataRequired(),
        NumberRange(min=0, max=100, message='درصد باید بین 0 تا 100 باشد')
    ])
    is_active = BooleanField('فعال', default=True)
    submit = SubmitField('ذخیره تخصیص')

    def validate_percentage(self, field):
        # Additional validation can be added here, for example:
        # - Check if the sum of all active percentages doesn't exceed 100%
        # This would require database access, which is typically done in route functions
        pass