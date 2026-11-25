"""CTP 2 - Exercise 1: profile customers.csv with pandas and build quality_scorecard.csv.
Run from the 02_CTP2 folder:  python profile_customers.py
"""
import pandas as pd

KIT = "../shopfast-kit/data/"
TODAY = pd.Timestamp.today().normalize()

df = pd.read_csv(KIT + "customers.csv", dtype=str)   # dtype=str: keep the raw text (e.g. 01300)
orders = pd.read_csv(KIT + "orders.csv", dtype=str)
n = len(df)
print("Rows:", n)
print(df.head())

# --- Completeness: how many empty values per column? ---
print("\nEmpty values per column:\n", df.isna().sum())

# --- Uniqueness: is customer_id unique? ---
print("\nDuplicated customer_id rows:", df["customer_id"].duplicated(keep=False).sum())

# TODO 1 (Uniqueness): normalise email (strip + lower case) and count people registered twice
deduped = df.drop_duplicates()                       # remove the 8 exact copies first
email_norm = deduped["email"].str.strip().str.lower()
dup_email = int(email_norm.dropna().duplicated().sum())
print(f"\nPeople registered twice (same normalised email, after exact dedupe): {dup_email}")

# TODO 2 (Validity): count emails that do not match the regex
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"
bad_email = int((df["email"].notna() & ~df["email"].fillna("").str.match(EMAIL_RE)).sum())
print("Invalid emails (not empty, wrong syntax):", bad_email)

# TODO 3 (Consistency): list the distinct values of country
print("\nDistinct country values:\n", df["country"].value_counts(dropna=False))
ISO2 = {"FR", "DE", "ES", "BE"}
bad_country = int((df["country"].notna() & ~df["country"].isin(ISO2)).sum())
print("Spellings of 4 countries:", df["country"].nunique(), "| rows not ISO-2:", bad_country)

# TODO 4 (Consistency): signup_date not in YYYY-MM-DD
ISO_DATE = r"^\d{4}-\d{2}-\d{2}$"
bad_signup = int((~df["signup_date"].fillna("").str.match(ISO_DATE)).sum())
bad_birth_fmt = int((~df["birth_date"].fillna("").str.match(ISO_DATE)).sum())
print("\nsignup_date not ISO:", bad_signup, "| birth_date not ISO:", bad_birth_fmt)

# TODO 5 (Validity): loyalty_tier outside bronze / silver / gold / platinum
TIERS = {"bronze", "silver", "gold", "platinum"}
bad_tier = int((~df["loyalty_tier"].isin(TIERS)).sum())
print("loyalty_tier outside the 4 allowed values:", bad_tier)

# TODO 6 (Accuracy): birth dates in the future / under 18 / before 1906 (only ISO dates can be checked)
birth = pd.to_datetime(df["birth_date"], format="%Y-%m-%d", errors="coerce")
bad_birth = int(((birth > TODAY - pd.DateOffset(years=18)) | (birth < pd.Timestamp("1906-01-01"))).sum())
print("Implausible birth dates (ISO ones only):", bad_birth)

# TODO 7 (Validity): French postal codes that do not have 5 digits
fr = df["country"].str.strip().str.lower().isin(["fr", "france", "fra"])
bad_postal = int((fr & ~df["postal_code"].fillna("").str.match(r"^\d{5}$")).sum())
print("French postal codes without 5 digits:", bad_postal, "of", int(fr.sum()))

# Timeliness: how old is the newest order? (orders in the future are ignored: they are an accuracy problem)
odate = pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="coerce")
newest = odate[odate <= TODAY].max()
age_days = (TODAY - newest).days
print(f"\nNewest valid order: {newest.date()} ({age_days} days old, rule: < 1 day)")

# --- Scorecard ---
n_deduped = len(deduped)
rows = [
    ("Completeness", "Every customer has an email", "email", "count of empty email", int(df["email"].isna().sum()), n, "high", "Owner",
     "Cannot contact the customer or detect duplicates; the Owner decides the threshold and fixes the sign-up form"),
    ("Completeness", "Every customer has a country", "country", "count of empty country", int(df["country"].isna().sum()), n, "medium", "Steward",
     "Breaks VAT and delivery statistics; Steward can often infer it from the address or postcode"),
    ("Uniqueness", "customer_id is unique", "customer_id", "duplicated customer_id minus first occurrence", int(df["customer_id"].duplicated().sum()), n, "high", "Custodian",
     "Exact copies of rows: a loading problem, so the Custodian fixes the pipeline"),
    ("Uniqueness", "One account per person", "email", "duplicates of lower-cased trimmed email, after removing exact copies", dup_email, n_deduped, "high", "Steward",
     "Same person registered twice splits orders and loyalty; Steward merges, Owner defines the merge rule"),
    ("Validity", "Email looks like an email", "email", "regex ^[^@\\s]+@[^@\\s]+\\.[a-zA-Z]{2,}$ on non-empty emails", bad_email, n, "high", "Steward",
     "Bounced marketing emails and failed invoices (double @, missing domain, leading space)"),
    ("Validity", "loyalty_tier is bronze, silver, gold or platinum", "loyalty_tier", "value not in the allowed set (case and spaces matter)", bad_tier, n, "low", "Steward",
     "Only distorts a chart; fix with a lower-case and trim transform"),
    ("Validity", "French postal code has 5 digits", "postal_code", "FR rows whose postal_code is not 5 digits (lost leading zero)", bad_postal, int(fr.sum()), "medium", "Custodian",
     "Wrong delivery address; caused by reading the column as a number, so the Custodian fixes the import"),
    ("Consistency", "Country is an ISO-2 code (FR, DE, ES, BE)", "country", "non-empty value not in {FR, DE, ES, BE}", bad_country, n, "medium", "Steward",
     "17 spellings (18 counting empty) for 4 countries break every group-by country"),
    ("Consistency", "signup_date is written YYYY-MM-DD", "signup_date", "value not matching ^\\d{4}-\\d{2}-\\d{2}$", bad_signup, n, "medium", "Custodian",
     "Mixed formats (dd/mm/yyyy, mm-dd-yyyy) make date maths wrong; standardise at load time"),
    ("Consistency", "birth_date is written YYYY-MM-DD", "birth_date", "value not matching ^\\d{4}-\\d{2}-\\d{2}$", bad_birth_fmt, n, "medium", "Custodian",
     "Same problem as signup_date; also blocks the accuracy check on these rows"),
    ("Accuracy", "Birth date is plausible (1906 to today - 18 years)", "birth_date", "ISO dates in the future, under 18 or before 1906", bad_birth, n, "high", "Owner",
     "Age-restricted offers and the law (minors): the Owner decides what to do with impossible dates"),
    ("Timeliness", "Orders loaded within 24 h", "orders.order_date", "now - max(order_date) < 1 day (1 = check failed)", int(age_days >= 1), 1, "high", "Custodian",
     f"Newest valid order is {age_days} days old; the nightly load is late or stopped"),
]
sc = pd.DataFrame(rows, columns=["dimension", "rule_in_plain_words", "column", "how_you_measured_it", "failing_rows", "total_rows",
                                 "severity_high_medium_low", "who_should_fix_owner_steward_custodian", "why"])
sc.insert(6, "score_pct", (100 * (1 - sc["failing_rows"] / sc["total_rows"])).round(1))
sc.to_csv("quality_scorecard.csv", index=False)
print("\n", sc[["dimension", "rule_in_plain_words", "failing_rows", "total_rows", "score_pct", "severity_high_medium_low"]].to_string(index=False))
print("\nWritten: quality_scorecard.csv")
