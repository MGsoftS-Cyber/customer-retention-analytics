"""Relational ownership and immutable evaluation snapshots.

An account owns its stores. Every query must enforce that relationship rather
than treating an unpredictable UUID as authorization.
"""

import time
from uuid import uuid4
from sqlalchemy import String, Text, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def new_id():
    return str(uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[float] = mapped_column(Float)


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("user_id", "name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3))


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("store_id", "fingerprint"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    source: Mapped[str] = mapped_column(String(200))
    coverage_end: Mapped[str] = mapped_column(String(10))
    orders: Mapped[list] = mapped_column(JSON)
    quality: Mapped[dict] = mapped_column(JSON)
    fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    results: Mapped[dict] = mapped_column(JSON)
    engine_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class RequestRecord(Base):
    __tablename__ = "request_records"
    __table_args__ = (UniqueConstraint("user_id", "scope", "key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    scope: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(100))
    payload_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)
