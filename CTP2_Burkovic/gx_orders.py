"""CTP 2 - Exercise 3: expectation suite for ShopFast orders (GX Core 1.x), 12 expectations.
Run from the 02_CTP2 folder:  python gx_orders_starter.py
"""
import pandas as pd
import great_expectations as gx

KIT = "../shopfast-kit/data/"   # adapt if your kit is elsewhere
orders = pd.read_csv(KIT + "orders.csv", dtype=str)
customers = pd.read_csv(KIT + "customers.csv", dtype=str)
orders["total_amount_eur"] = pd.to_numeric(orders["total_amount_eur"], errors="coerce")
orders["order_date_dt"] = pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="coerce")  # typed copy for range checks

context = gx.get_context(mode="file")                       # creates ./gx/ (config + Data Docs)
source = context.data_sources.add_or_update_pandas("shopfast")
asset = source.add_dataframe_asset(name="orders")
batch_def = asset.add_batch_definition_whole_dataframe("all_orders")

suite = context.suites.add_or_update(gx.ExpectationSuite(name="orders_suite"))
E = gx.expectations
for e in [
    E.ExpectTableRowCountToBeBetween(min_value=1000, max_value=100000),
    E.ExpectColumnValuesToNotBeNull(column="order_id"),
    E.ExpectColumnValuesToBeUnique(column="order_id"),
    # Rule 4 - Referential integrity: an order without a customer cannot be invoiced or delivered. Missing id = critical.
    E.ExpectColumnValuesToNotBeNull(column="customer_id"),
    # Rule 5 - Foreign key: every customer_id must exist in customers.csv (14 orphan orders today -> High, quarantine rows).
    E.ExpectColumnValuesToBeInSet(column="customer_id", value_set=sorted(set(customers["customer_id"].dropna()))),
    # Rule 6 - Completeness: revenue reports are by day, an order without a date disappears from them.
    E.ExpectColumnValuesToNotBeNull(column="order_date"),
    # Rule 7 - Validity: one agreed date format (ISO) so that sorting and date maths work.
    E.ExpectColumnValuesToMatchRegex(column="order_date", regex=r"^\d{4}-\d{2}-\d{2}$"),
    # Rule 8 - Accuracy: an order cannot be dated after today (5 orders in 2027 today).
    E.ExpectColumnValuesToBeBetween(column="order_date_dt", max_value=pd.Timestamp.today().normalize()),
    # Rule 9 - Validity: status is a closed list; 'SHIPPED', 'Delivered', 'canceled' break counts per status.
    E.ExpectColumnValuesToBeInSet(column="status", value_set=["pending", "shipped", "delivered", "cancelled", "returned"]),
    # Rule 10 - Validity: the 3 sales channels seen in the data (web, mobile_app, marketplace); a new channel must be a decision.
    E.ExpectColumnValuesToBeInSet(column="channel", value_set=["web", "mobile_app", "marketplace"]),
    # Rule 11 - Consistency: ShopFast only ships to FR, BE, DE, ES (ISO-2 codes).
    E.ExpectColumnValuesToBeInSet(column="shipping_country", value_set=["FR", "BE", "DE", "ES"]),
    # Rule 12 - Accuracy: amount strictly positive (6 orders <= 0 today) and below 5000 EUR (the largest real order is about 1,400 EUR;
    # a x100 error or a typo would be caught here).
    E.ExpectColumnValuesToBeBetween(column="total_amount_eur", min_value=0, max_value=5000, strict_min=True),
]:
    suite.add_expectation(e)
suite.save()

vd = context.validation_definitions.add_or_update(gx.ValidationDefinition(name="orders_validation", data=batch_def, suite=suite))
checkpoint = context.checkpoints.add_or_update(gx.Checkpoint(name="orders_checkpoint", validation_definitions=[vd],
                                                             actions=[gx.checkpoint.UpdateDataDocsAction(name="docs")]))
result = checkpoint.run(batch_parameters={"dataframe": orders})

print("\nSuite passed:", result.success)
for vr in result.run_results.values():
    for r in vr.results:
        cfg = r.expectation_config
        print(f"{'PASS' if r.success else 'FAIL'}  {cfg.type:<45} {cfg.kwargs.get('column', ''):<18} unexpected={r.result.get('unexpected_count', '-')}")
print("\nOpen the report: gx/uncommitted/data_docs/local_site/index.html")
