import os
import logging
from sqlalchemy import Column, String, Integer, DateTime, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, ValidationError, constr, validator
import re
import functools

# Setup Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base for ORM models
Base = declarative_base()

# Asynchronous Engine Setup (without pool_size and max_overflow for SQLite)
DB_URL = os.getenv('DATABASE_URL', f"sqlite+aiosqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'async_records.db')}")
async_engine = create_async_engine(DB_URL, echo=False)

# Async Session Factory
AsyncSessionFactory = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

# Model definition for a record
class Record(Base):
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # NAME
    phone = Column(String, nullable=False)  # PHONE #
    usernames = Column(String)  # USERNAMES
    emails = Column(String, nullable=False)  # EMAILS
    passwords = Column(String)  # PASSWORDS
    birthday = Column(String)  # BIRTHDAY
    city = Column(String)  # CITY
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic schema for data validation
class RecordSchema(BaseModel):
    name: constr(min_length=1)  # Allow any name with at least 1 character, no max length.
    phone: str  # More flexible phone number format.
    emails: EmailStr  # Keep email validation strict.
    usernames: constr(min_length=1) = None  # Allow usernames to be as short as 1 character.
    passwords: str = None  # No minimum length for passwords.
    birthday: str = None  # Allow birthday in flexible formats.
    city: str = None  # Standardize city name.

    @validator('phone')
    def check_phone_format(cls, v):
        # Remove all non-digit characters.
        cleaned = re.sub(r'\D', '', v)
        if not (7 <= len(cleaned) <= 15):  # Allow for 7 to 15 digits.
            raise ValueError('Phone number must contain between 7 and 15 digits.')

        # Standardize phone number to +1-555-123-4567 format.
        if len(cleaned) == 10:
            formatted_phone = f"+1-{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) > 10:
            country_code_len = len(cleaned) - 10
            formatted_phone = f"+{cleaned[:country_code_len]}-{cleaned[country_code_len:country_code_len+3]}-{cleaned[country_code_len+3:country_code_len+6]}-{cleaned[country_code_len+6:]}"
        else:
            formatted_phone = cleaned

        return formatted_phone

    @validator('birthday', pre=True)
    def check_birthday_format(cls, v):
        # List of accepted date formats
        date_formats = ['%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y', '%B %d, %Y', '%b %d, %Y']

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(v, fmt).date()
                return parsed_date.strftime('%Y-%m-%d')  # Standardize to YYYY-MM-DD.
            except ValueError:
                continue

        raise ValueError('Invalid birthday format. Accepted formats: YYYY-MM-DD, MM-DD-YYYY, DD-MM-YYYY, Month DD, YYYY')

    @validator('city')
    def standardize_city_format(cls, v):
        if v:
            return v.title()  # Standardize to title case (e.g., "New York").
        return v

# Dependency injection for session management
class DBContext:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def __aenter__(self):
        self.session = self._session_factory()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

# Function decorator for async session lifecycle management
def async_db_session(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with DBContext(AsyncSessionFactory) as session:
            try:
                result = await func(session, *args, **kwargs)
                await session.commit()
                return result
            except exc.SQLAlchemyError as e:
                await session.rollback()
                logging.error(f"Database error in {func.__name__}: {e}")
                raise
    return wrapper

# Function to add a record to the database with validation
@async_db_session
async def add_record(session, record_data):
    try:
        validated_record = RecordSchema(**record_data)
        new_record = Record(**validated_record.dict())
        session.add(new_record)
        logging.info(f"Record {new_record.name} added successfully.")
    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        raise

# Function to fetch all records
@async_db_session
async def get_all_records(session):
    records = await session.execute(select(Record))
    records_list = records.scalars().all()
    logging.info(f"Fetched {len(records_list)} records.")
    return records_list

# Function to update a record
@async_db_session
async def update_record(session, record_id, updated_data):
    record = await session.get(Record, record_id)
    if not record:
        logging.error(f"Record with ID {record_id} not found.")
        return False

    for key, value in updated_data.items():
        if value is not None and hasattr(record, key):
            setattr(record, key, value)
    logging.info(f"Record with ID {record_id} updated successfully.")
    return True

# Function to search records
@async_db_session
async def search_records(session, search_term):
    search_term = f"%{search_term}%"
    results = await session.execute(
        select(Record).filter(
            (Record.name.ilike(search_term)) |
            (Record.emails.ilike(search_term)) |
            (Record.phone.ilike(search_term))
        )
    )
    records = results.scalars().all()
    logging.info(f"Found {len(records)} records matching '{search_term}'.")
    return records

# Function to delete a record
@async_db_session
async def delete_record(session, name, phone, emails):
    record = await session.execute(
        select(Record).filter_by(name=name, phone=phone, emails=emails)
    )
    record_to_delete = record.scalar_one_or_none()
    if not record_to_delete:
        logging.error(f"Record with name: {name}, phone: {phone}, and emails: {emails} not found.")
        return False

    await session.delete(record_to_delete)
    logging.info(f"Record for {name} deleted successfully.")
    return True

# Bulk insert operation for performance improvement
@async_db_session
async def bulk_insert_records(session, records_data):
    try:
        records = [Record(**RecordSchema(**data).dict()) for data in records_data]
        session.add_all(records)
        logging.info(f"{len(records)} records inserted successfully.")
    except ValidationError as e:
        logging.error(f"Validation error in bulk insert: {e}")
        raise

# Async cleanup to properly close engine in async environments
async def async_cleanup():
    await async_engine.dispose()
    logging.info("Asynchronous database engine disposed.")

# Helper function to initialize the database (typically used for migrations)
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logging.info("Database initialized with all tables.")
