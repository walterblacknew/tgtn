class Config:
    SECRET_KEY = 'SECRET_KEY_FOR_FLASK_WTF'  # کلید مخفی برای سشن و CSRF
    SQLALCHEMY_DATABASE_URI = 'sqlite:///mydatabase.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # می‌توانید سایر تنظیمات دلخواه Flask را هم در اینجا اضافه کنید
    """
    export DATABASE_URL="mysql+pymysql://myuser:mypassword@localhost/mydatabase"
    export DATABASE_URL="postgresql://username:password@localhost/mydatabase"
    export MONGO_URI="mongodb://username:password@localhost:27017/my_mongo_db"
    """