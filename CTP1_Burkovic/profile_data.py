"""Quick profile of every CSV/Excel file in shopfast-kit/data to help fill the data inventory.

Usage (venv activated), from the folder that contains shopfast-kit:
    python profile_data.py
    python profile_data.py path\\to\\data
"""
import sys
from pathlib import Path

import pandas as pd

data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("shopfast-kit/data")
PII_HINTS = ["name", "email", "phone", "address", "birth", "dob", "ip", "iban", "card", "ssn", "zip", "postal"]

files = sorted(p for p in data_dir.iterdir() if p.suffix.lower() in {".csv", ".xlsx", ".xls"})
print(f"{len(files)} files found in {data_dir}\n")

for f in files:
    df = pd.read_csv(f, low_memory=False) if f.suffix.lower() == ".csv" else pd.read_excel(f)
    print("=" * 70)
    print(f"{f.name}: {len(df)} rows, {df.shape[1]} columns")
    print("Columns:", ", ".join(df.columns))

    pii = [c for c in df.columns if any(h in c.lower() for h in PII_HINTS)]
    print("Possible personal data columns:", pii or "none obvious")

    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    empty_str = {c: int((df[c].astype(str).str.strip() == "").sum())
                 for c in df.columns if df[c].dtype == object}
    empty_str = {c: n for c, n in empty_str.items() if n > 0}
    print("Missing values:", dict(nulls) or "none")
    if empty_str:
        print("Empty strings:", empty_str)

    print("Fully duplicated rows:", int(df.duplicated().sum()))
    first = df.columns[0]
    print(f"Duplicate values in first column '{first}':", int(df[first].duplicated().sum()))

    for c in df.columns:
        if df[c].dtype == object and 1 < df[c].nunique() <= 15:
            print(f"  Values of '{c}':", dict(df[c].value_counts(dropna=False)))
    print()
