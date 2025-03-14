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
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from clientparser.config import Config

__all__ = ["initialize_and_create_tables", "session_scope", "DHCPModel", "DNSModel" "DBException"]


config = Config()

# Create a declarative base
Base = declarative_base()

# Move the global declaration to the top
global db_session
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



def initialize_and_create_tables() -> None:
    """Initialize the database and create tables."""
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
            scope_name = f"private_{cls.scope.split('.')[2]}"
        else:
            scope_name = f"public_{cls.scope.split('.')[2]}"
        return f"{scope_name}"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(15), nullable=False)
    mac_address = Column(String(26), nullable=False, unique=True)
    lease_status = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=True)
    subnet = Column(String(15), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    @classmethod
    def create_dhcp_models(cls, scopes):
        """Create a list of DHCPModel classes for each scope in scopes."""
        models = []
        for scope in scopes:
            class_name = f"DHCPModel_{scope.replace('.', '_')}"
            model = type(class_name, (cls,), {"scope": scope})
            models.append(model)
        return models
    

class DNSModel(Base):
    """DNS model for storing DNS records."""
    __tablename__ = "dns_records"

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
