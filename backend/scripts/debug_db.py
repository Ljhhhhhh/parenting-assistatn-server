from sqlmodel import Session, select
from app.core.db import engine
from app.models import User
from app.core.config import settings
from app import crud
from app.models import UserCreate

def check_db_connection():
    print("Checking database connection...")
    try:
        with Session(engine) as session:
            result = session.exec(select(1)).first()
            print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    return True

def check_user_table():
    print("\nChecking user table...")
    try:
        with Session(engine) as session:
            users = session.exec(select(User)).all()
            print(f"Found {len(users)} users in database")
            for user in users:
                print(f"User: {user.email}, Superuser: {user.is_superuser}")
    except Exception as e:
        print(f"Error querying user table: {e}")

def create_superuser():
    print("\nCreating superuser...")
    try:
        with Session(engine) as session:
            # Check if superuser already exists
            existing_user = session.exec(
                select(User).where(User.email == settings.FIRST_SUPERUSER)
            ).first()
            
            if existing_user:
                print(f"Superuser {existing_user.email} already exists")
                return
            
            # Create new superuser
            user_in = UserCreate(
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                is_superuser=True,
            )
            user = crud.create_user(session=session, user_create=user_in)
            print(f"Successfully created superuser: {user.email}")
            
    except Exception as e:
        print(f"Error creating superuser: {e}")

if __name__ == "__main__":
    print("Database Debug Script")
    print("====================")
    print(f"Database URI: {settings.SQLALCHEMY_DATABASE_URI}")
    print(f"Superuser Email: {settings.FIRST_SUPERUSER}")
    
    if check_db_connection():
        check_user_table()
        create_superuser()
        check_user_table()  # Check again after creation