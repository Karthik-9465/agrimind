from app.db.session import engine, Base
from app.db.models import User, Farm, Crop, DiseaseReport, NotificationLog

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Initializing database tables...")
    init_db()
    print("Database tables created successfully!")
