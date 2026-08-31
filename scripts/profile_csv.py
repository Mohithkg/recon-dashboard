"""
Throwaway data profiling script.
Place orders.csv and payments.csv in this folder (or edit PATHS below),
then run:  python scripts/profile_csv.py
"""

import pandas as pd

PATHS = {
    "orders": "scripts/orders.csv",
    "payments": "scripts/payments.csv",
}

# Column names in your CSV files
ID_COLS = {"orders": "order_id", "payments": "transaction_ref"}
FOREIGN_COL = "order_reference"     # column on payments that references orders.order_id
STATUS_COLS_HINT = ["status", "type"]
AMOUNT_COLS_HINT = ["amount", "gross_amount", "net_amount", "discount", "fee", "net_settled"]


def find_col(df, hints):
    """Return the first column whose lowercased name contains any hint."""
    for col in df.columns:
        low = col.lower()
        if any(h in low for h in hints):
            return col
    return None


def find_all_cols(df, hints):
    return [c for c in df.columns if any(h in c.lower() for h in hints)]


def profile(name, df, id_col):
    print(f"\n{'='*60}")
    print(f" {name.upper()}")
    print(f"{'='*60}")

    print(f"\nRows: {len(df):,}")
    print(f"Columns ({len(df.columns)}):")
    for col in df.columns:
        print(f"  {col:<30} {str(df[col].dtype):<15}  nulls: {df[col].isna().sum():,}")

    # Duplicate IDs
    if id_col and id_col in df.columns:
        dupes = df[id_col].dropna().duplicated().sum()
        null_ids = df[id_col].isna().sum()
        print(f"\nID column '{id_col}':")
        print(f"  Duplicate IDs:  {dupes:,}")
        print(f"  Null IDs:       {null_ids:,}")

    # Status / type distinct values
    for col in find_all_cols(df, STATUS_COLS_HINT):
        print(f"\nDistinct values in '{col}' ({df[col].nunique()}):")
        print(f"  {df[col].value_counts(dropna=False).to_dict()}")

    # Amount stats
    for col in find_all_cols(df, AMOUNT_COLS_HINT):
        series = pd.to_numeric(df[col], errors="coerce")
        print(f"\nAmount column '{col}':")
        print(f"  min:   {series.min()}")
        print(f"  max:   {series.max()}")
        print(f"  mean:  {series.mean():.2f}")
        print(f"  nulls: {series.isna().sum():,}  (incl. non-numeric)")


def main():
    dfs = {}
    for name, path in PATHS.items():
        try:
            df = pd.read_csv(path)
            dfs[name] = df
        except FileNotFoundError:
            print(f"[WARN] {path} not found — skipping {name}")
            dfs[name] = None

    for name, df in dfs.items():
        if df is None:
            continue
        id_col = ID_COLS.get(name)
        # Fall back to first column if named differently
        if id_col not in df.columns:
            id_col = df.columns[0]
        profile(name, df, id_col)

    # Relational checks
    orders = dfs.get("orders")
    payments = dfs.get("payments")
    if orders is not None and payments is not None:
        print(f"\n{'='*60}")
        print(" RELATIONAL CHECKS")
        print(f"{'='*60}")

        order_id_col = ID_COLS["orders"]

        # Payments referencing non-existent orders
        if FOREIGN_COL in payments.columns:
            orphan_payments = payments[
                payments[FOREIGN_COL].notna()
                & ~payments[FOREIGN_COL].isin(orders[order_id_col])
            ]
            print(f"\nPayments with {FOREIGN_COL} but no matching order: {len(orphan_payments):,}")

        # Orders with no payment
        if FOREIGN_COL in payments.columns:
            orders_with_no_payment = orders[
                ~orders[order_id_col].isin(payments[FOREIGN_COL])
            ]
            print(f"Orders with no payment record: {len(orders_with_no_payment):,}")

        # Currency mismatch check
        if FOREIGN_COL in payments.columns and "currency" in orders.columns and "currency" in payments.columns:
            merged = orders.merge(
                payments[[FOREIGN_COL, "currency"]],
                left_on=order_id_col,
                right_on=FOREIGN_COL,
                how="inner",
                suffixes=("_order", "_payment"),
            )
            mismatches = merged[merged["currency_order"] != merged["currency_payment"]]
            print(f"Currency mismatches between order and payment: {len(mismatches):,}")


if __name__ == "__main__":
    main()
