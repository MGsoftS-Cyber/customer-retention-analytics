"""Bounded order, retention and monetary input contracts."""

import re
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password", mode="before")
    @classmethod
    def preserve_password(cls, value):
        # Password whitespace is meaningful; reject it at the boundaries instead of silently changing it.
        if isinstance(value, str) and value != value.strip():
            raise ValueError("Password must not start or end with whitespace.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        value = value.lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class StoreInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    currency: Literal["USD", "EUR", "GBP", "DZD"] = "USD"


class OrderInput(StrictModel):
    customer_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    order_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    order_date: date
    amount: str = Field(min_length=1, max_length=20)
    status: Literal["completed", "cancelled", "refunded"] = "completed"

    @field_validator("order_date")
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError("Order dates cannot be in the future.")
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def valid_amount(cls, value):
        # String amounts avoid binary-float money conversion; all supported currencies use two decimals.
        from decimal import Decimal

        text = str(value)
        if not re.fullmatch(r"\d{1,10}(?:\.\d{1,2})?", text):
            raise ValueError("Amount must be nonnegative decimal text with at most two decimal places.")
        amount = Decimal(text)
        if amount > Decimal("1000000000"):
            raise ValueError("Maximum order amount is 1000000000.")
        return format(amount, ".2f")


class DatasetInput(StrictModel):
    source: str = Field(min_length=1, max_length=200)
    coverage_end: date
    orders: list[OrderInput] = Field(min_length=1, max_length=10000)

    @field_validator("coverage_end")
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError("Coverage end cannot be in the future.")
        return value


class CsvInput(StrictModel):
    csv_text: str = Field(min_length=1, max_length=2000000)


class RetentionInput(StrictModel):
    dataset_id: str
    scenario_name: str = Field(default="Retention review", min_length=1, max_length=120)
    as_of: date
    inactivity_days: int = Field(default=90, ge=7, le=365)
    cohort_horizon: int = Field(default=6, ge=1, le=12)

    @field_validator("as_of")
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError("Analysis date cannot be in the future.")
        return value


class ComparisonInput(StrictModel):
    analysis_ids: list[str] = Field(min_length=2, max_length=10)

    @field_validator("analysis_ids")
    @classmethod
    def unique_ids(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Select distinct analyses.")
        return values
