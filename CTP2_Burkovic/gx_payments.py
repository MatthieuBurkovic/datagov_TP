"""CTP 2 - Exercise 4: replay the 'cents' incident.
A naive suite (not null / unique / allowed values) PASSES on payments_batch_2.csv although every amount is 100x too big.
Only value-range and distribution expectations catch it.
"""
import pandas as pd
import great_expectations as gx

KIT = "../shopfast-kit/data/"
files = {"payments (history)": KIT + "payments.csv", "payments_batch_2 (new)": "payments_batch_2.csv"}

context = gx.get_context(mode="file")
source = context.data_sources.add_or_update_pandas("shopfast_payments")
asset = source.add_dataframe_asset(name="payments")
batch_def = asset.add_batch_definition_whole_dataframe("whole")
E = gx.expectations

naive = [E.ExpectColumnValuesToNotBeNull(column="payment_id"), E.ExpectColumnValuesToBeUnique(column="payment_id"),
         E.ExpectColumnValuesToNotBeNull(column="amount"), E.ExpectColumnValuesToBeInSet(column="currency", value_set=["EUR"]),
         E.ExpectColumnValuesToBeInSet(column="method", value_set=["card", "paypal", "apple_pay", "bank_transfer"])]
smart = naive + [
    # 1) Range per value: history is 13.70 - 1,400.79 EUR. Cents make every value 100x bigger (min 980, max 37,996).
    E.ExpectColumnValuesToBeBetween(column="amount", min_value=0, max_value=5000, strict_min=True),
    # 2) Mean in a plausible band: history mean is about 236 EUR, the cents batch is about 18,900.
    E.ExpectColumnMeanToBeBetween(column="amount", min_value=100, max_value=400),
    # 3) Median in a plausible band: history median is about 184 EUR, the cents batch is about 18,500. Robust to a few outliers.
    E.ExpectColumnMedianToBeBetween(column="amount", min_value=100, max_value=300),
    # 4) Decimals: euros are written with a decimal point (e.g. 217.38); cents arrive as whole numbers (e.g. 7879).
    E.ExpectColumnValuesToMatchRegex(column="amount_txt", regex=r"^\d+\.\d{1,2}$"),
]

def run(name, expectations, df):
    suite = context.suites.add_or_update(gx.ExpectationSuite(name=name))
    for e in expectations: suite.add_expectation(e.copy() if hasattr(e, "copy") else e)
    suite.save()
    return batch_def.get_batch(batch_parameters={"dataframe": df}).validate(suite)

for label, path in files.items():
    df = pd.read_csv(path, dtype=str); df["amount_txt"] = df["amount"]; df["amount"] = pd.to_numeric(df["amount"])
    for suite_name, exps in [("naive_payments", naive), ("smart_payments", smart)]:
        res = run(suite_name, exps, df)
        failed = [r.expectation_config.type for r in res.results if not r.success]
        print(f"{label:<24} {suite_name:<15} success={res.success}  failed={failed}")

# Missing guard at ShopFast: a TEST (and behind it a data contract with the payments team). The Owner existed on paper, but nobody
# wrote down that "amount is in euros with 2 decimals" and nothing checked the values' range, so a valid-looking 100x error loaded silently.
