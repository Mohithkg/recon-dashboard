import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.database import get_db
from app.models import User, Order, Payment

router = APIRouter(prefix="/uploads", tags=["uploads"])

VALID_ORDER_COLUMNS = {
    "order_id", "order_date", "customer_email", "currency",
    "gross_amount", "discount", "net_amount", "status",
}
VALID_PAYMENT_COLUMNS = {
    "transaction_ref", "processed_at", "order_reference", "currency",
    "amount", "fee", "net_settled", "type", "status",
}

VALID_CURRENCIES = {"USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "CHF", "CNY", "SGD"}


def _clean_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from all string columns and normalize null-like values to None."""
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": None, "None": None, "": None})
    return df


def _normalize_currency(df: pd.DataFrame) -> pd.DataFrame:
    """Uppercase currency codes."""
    if "currency" in df.columns:
        df["currency"] = df["currency"].str.upper().str.strip()
    return df


def _clean_amounts(df: pd.DataFrame, amount_cols: list[str]) -> pd.DataFrame:
    """Coerce amount columns to numeric, invalid values become NaN."""
    for col in amount_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df



def _validate_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], int]:
    """Validate and clean orders DataFrame. Returns (clean_df, rejected_rows, dupes_removed)."""
    rejected = []

    df = _clean_string_columns(df)
    df = _normalize_currency(df)
    df = _clean_amounts(df, ["gross_amount", "discount", "net_amount"])

    # Dedupe exact duplicate rows
    before_dedup = len(df)
    df = df.drop_duplicates()
    dupes_removed = before_dedup - len(df)

    # Validate required fields
    for idx, row in df.iterrows():
        reasons = []

        if pd.isna(row.get("order_id")) or str(row.get("order_id")).strip() == "":
            reasons.append("missing order_id")
        if pd.isna(row.get("gross_amount")):
            reasons.append("invalid or missing gross_amount")
        if pd.isna(row.get("net_amount")):
            reasons.append("invalid or missing net_amount")

        currency = row.get("currency")
        if pd.isna(currency) or currency not in VALID_CURRENCIES:
            reasons.append(f"invalid or unsupported currency: {currency}")
        if pd.isna(row.get("status")) or str(row.get("status")).strip() == "":
            reasons.append("missing status")

        if reasons:
            rejected.append({"row_index": int(idx), "reasons": reasons})

    if rejected:
        reject_indices = [r["row_index"] for r in rejected]
        df = df.drop(index=reject_indices).reset_index(drop=True)

    return df, rejected, dupes_removed



def _validate_payments(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], int]:
    """Validate and clean payments DataFrame. Returns (clean_df, rejected_rows, dupes_removed)."""
    rejected = []

    df = _clean_string_columns(df)
    df = _normalize_currency(df)
    df = _clean_amounts(df, ["amount", "fee", "net_settled"])

    # Dedupe exact duplicate rows
    before_dedup = len(df)
    df = df.drop_duplicates()
    dupes_removed = before_dedup - len(df)

    # Validate required fields
    for idx, row in df.iterrows():
        reasons = []

        if pd.isna(row.get("transaction_ref")) or str(row.get("transaction_ref")).strip() == "":
            reasons.append("missing transaction_ref")
        if pd.isna(row.get("amount")):
            reasons.append("invalid or missing amount")
        if pd.isna(row.get("net_settled")):
            reasons.append("invalid or missing net_settled")

        currency = row.get("currency")
        if pd.isna(currency) or currency not in VALID_CURRENCIES:
            reasons.append(f"invalid or unsupported currency: {currency}")
        if pd.isna(row.get("type")) or str(row.get("type")).strip() == "":
            reasons.append("missing type")
        if pd.isna(row.get("status")) or str(row.get("status")).strip() == "":
            reasons.append("missing status")

        if reasons:
            rejected.append({"row_index": int(idx), "reasons": reasons})

    if rejected:
        reject_indices = [r["row_index"] for r in rejected]
        df = df.drop(index=reject_indices).reset_index(drop=True)

    return df, rejected, dupes_removed


@router.post("/orders")
async def upload_orders(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload orders CSV. Returns ingestion summary."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV",
        )

    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    missing_cols = VALID_ORDER_COLUMNS - set(df.columns)
    if missing_cols:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required columns: {missing_cols}",
        )

    df, rejected, dupes_removed = _validate_orders(df)

    ingested = 0
    for _, row in df.iterrows():
        order = Order(
            user_id=current_user.id,
            order_id=str(row["order_id"]),
            order_date=pd.to_datetime(row.get("order_date"), errors="coerce", utc=True) if pd.notna(row.get("order_date")) else None,
            customer_email=str(row["customer_email"]) if pd.notna(row.get("customer_email")) else None,
            currency=str(row["currency"]).upper(),
            gross_amount=round(float(row["gross_amount"]), 2),
            discount=round(float(row.get("discount") or 0), 2),
            net_amount=round(float(row["net_amount"]), 2),
            status=str(row["status"]).strip().lower(),
        )
        db.add(order)
        ingested += 1

    await db.commit()

    return {
        "filename": file.filename,
        "total_rows_read": len(df) + len(rejected) + dupes_removed,
        "ingested": ingested,
        "duplicates_removed": dupes_removed,
        "rejected": rejected,
        "rejected_count": len(rejected),
    }


@router.post("/payments")
async def upload_payments(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload payments CSV. Returns ingestion summary."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV",
        )

    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    missing_cols = VALID_PAYMENT_COLUMNS - set(df.columns)
    if missing_cols:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required columns: {missing_cols}",
        )

    df, rejected, dupes_removed = _validate_payments(df)

    ingested = 0
    for _, row in df.iterrows():
        payment = Payment(
            user_id=current_user.id,
            transaction_ref=str(row["transaction_ref"]),
            processed_at=pd.to_datetime(row.get("processed_at"), errors="coerce", utc=True) if pd.notna(row.get("processed_at")) else None,
            order_reference=str(row["order_reference"]) if pd.notna(row.get("order_reference")) else None,
            currency=str(row["currency"]).upper(),
            amount=round(float(row["amount"]), 2),
            fee=round(float(row.get("fee") or 0), 2),
            net_settled=round(float(row["net_settled"]), 2),
            type=str(row["type"]).strip().lower(),
            status=str(row["status"]).strip().lower(),
        )
        db.add(payment)
        ingested += 1

    await db.commit()

    return {
        "filename": file.filename,
        "total_rows_read": len(df) + len(rejected) + dupes_removed,
        "ingested": ingested,
        "duplicates_removed": dupes_removed,
        "rejected": rejected,
        "rejected_count": len(rejected),
    }

