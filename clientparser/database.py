#!/usr/bin/env python3
# ----------------------------------------------------------------------------------
# Project: ClientParser
# File: clientparser/database.py
# ----------------------------------------------------------------------------------
# Purpose:
# This is the database module for the Client Parser application.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (C) 2025 GSECARS, The University of Chicago, USA
# Copyright (C) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text, inspect
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from clientparser.config import Config

__all__ = ["initialize_and_create_tables", "session_scope", "DHCPModel", "DNSModel" "DBException"]


config = Config()

# Create a declarative base
Base = declarative_base()

# Declare global variables
global db_engine, db_session
db_engine = None
db_session = None


def initialize_db():
    """Initialize the database connection."""
    db_engine = create_engine(config.database_uri, pool_size=10, max_overflow=2, pool_timeout=30)
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=db_engine))
    return db_engine, db_session, Base


@contextmanager
def session_scope():
    """Provide a transactional scope for the database session."""
    global db_session
    if db_session is None:
        db_engine, db_session, Base = initialize_db()
    try:
        yield db_session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def initialize_and_create_tables():
    """Initialize the database connection and create tables."""
    global db_engine, db_session, Base
    db_engine, db_session, Base = initialize_db()
    dns_model = DNSModel()
    dhcp_models = DHCPModel.create_dhcp_models(config.scopes)

    for model in dhcp_models:
        # Drop the table if it exists
        model.__table__.drop(bind=db_engine, checkfirst=True)  
        # Create the table
        model.__table__.create(bind=db_engine, checkfirst=True)

    # Drop and create the DNS table
    dns_model.__table__.drop(bind=db_engine, checkfirst=True)
    dns_model.__table__.create(bind=db_engine, checkfirst=True)


def drop_and_rename_table(temp_table_name: str, final_table_name: str):
    """Drop the existing table with the final name (if it exists) and rename the temp table."""
    global db_engine
    inspector = inspect(db_engine)

    with db_engine.connect() as connection:
        # Check if the final table exists and drop it
        if inspector.has_table(final_table_name):
            connection.execute(text(f"DROP TABLE {final_table_name}"))
            print(f"Dropped existing table: {final_table_name}")

        # Check if the temp table exists before renaming
        if inspector.has_table(temp_table_name):
            connection.execute(text(f"ALTER TABLE {temp_table_name} RENAME TO {final_table_name}"))
            print(f"Renamed table '{temp_table_name}' to '{final_table_name}'")
        else:
            raise RuntimeError(f"Temporary table '{temp_table_name}' does not exist. Cannot rename.")


class DHCPModel(Base):
    """
    Abstract base class for DHCP models. Each subclass will have a table name
    based on the scope.
    """
    __abstract__ = True
    __table_args__ = {"extend_existing": True}

    @declared_attr
    def __tablename__(cls):
        """
        Generate table name based on the scope. If the scope starts with "10",
        it is considered private; otherwise, it is public.
        """
        if cls.scope.startswith("10"):
            scope_name = f"temp_private_{cls.scope.split('.')[2]}"
        else:
            scope_name = f"temp_public_{cls.scope.split('.')[2]}"
        return f"{scope_name}"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(15), nullable=False)
    mac_address = Column(String(26), nullable=False, unique=True)
    lease_status = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=True)
    subnet = Column(String(15), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # Cache for dynamically created models
    _model_cache = {}

    @classmethod
    def create_dhcp_models(cls, scopes):
        """Create a list of DHCPModel classes for each scope in scopes."""
        models = []
        for scope in scopes:
            if scope not in cls._model_cache:
                class_name = f"DHCPModel_{scope.replace('.', '_')}"
                model = type(class_name, (cls,), {"scope": scope})
                # Cache the model
                cls._model_cache[scope] = model
            models.append(cls._model_cache[scope])
        return models
    

class DNSModel(Base):
    """DNS model for storing DNS records."""
    __tablename__ = "temp_dns_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    record_type = Column(String(10), nullable=False)
    data = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)


class DBException(Exception):
    """Custom exception class for database-related errors."""

    def __init__(self, message) -> None:
        self.message = message
        super(DBException, self).__init__(self.message)

    def __str__(self) -> str:
        return self.message
