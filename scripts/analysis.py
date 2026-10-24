"""
Shared pandas versions of the key SQL analyses, used by make_charts.py and make_dashboard.py.
Each function mirrors a query in sql/02_analysis_queries.sql or sql/03_advanced_sql.sql.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load():
    customers = pd.read_csv(DATA / "customers.csv")
    products = pd.read_csv(DATA / "products.csv")
    orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date"])
    details = pd.read_csv(DATA / "orderdetails.csv")
    return customers, products, orders, details


def order_lines(customers, products, orders, details):
    """Same as view vw_order_lines."""
    lines = (details.merge(orders, on="order_id")
                    .merge(customers.rename(columns={"name": "customer_name"}), on="customer_id")
                    .merge(products.rename(columns={"name": "product_name"}), on="product_id"))
    lines["line_amount"] = lines["quantity"] * lines["price_per_unit"]
    return lines


def monthly_sales(orders):
    """Same as view vw_monthly_sales + Q10 percent change."""
    m = (orders.assign(month=orders["order_date"].dt.strftime("%Y-%m"))
               .groupby("month")
               .agg(total_orders=("order_id", "count"),
                    active_customers=("customer_id", "nunique"),
                    total_sales=("total_amount", "sum"),
                    avg_order_value=("total_amount", "mean"))
               .reset_index())
    m["avg_order_value"] = m["avg_order_value"].round(2)
    m["percent_change"] = (m["total_sales"].pct_change() * 100).round(2)
    return m


def new_customers(orders):
    """Q14: customers by month of first purchase."""
    first = orders.groupby("customer_id")["order_date"].min().dt.strftime("%Y-%m")
    return first.value_counts().sort_index().rename_axis("month").reset_index(name="new_customers")


def _ntile(order, n=4):
    """MySQL NTILE(n) over an already-sorted index."""
    size = len(order)
    base, extra = divmod(size, n)
    tiles = np.concatenate([np.full(base + (1 if i < extra else 0), i + 1) for i in range(n)])
    return pd.Series(tiles, index=order)


def rfm(customers, orders):
    """Same as view vw_customer_rfm."""
    last_date = orders["order_date"].max()
    r = (orders.groupby("customer_id")
               .agg(last_order=("order_date", "max"),
                    frequency=("order_id", "count"),
                    monetary=("total_amount", "sum"))
               .reset_index())
    r["recency_days"] = (last_date - r["last_order"]).dt.days
    r["r_score"] = _ntile(r.sort_values(["recency_days", "customer_id"], ascending=[False, True]).index)
    r["f_score"] = _ntile(r.sort_values(["frequency", "customer_id"]).index)
    r["m_score"] = _ntile(r.sort_values(["monetary", "customer_id"]).index)

    def segment(row):
        if row.r_score >= 3 and row.f_score >= 3 and row.m_score >= 3:
            return "Champions"
        if row.r_score >= 3 and row.f_score >= 2:
            return "Loyal / Potential"
        if row.r_score <= 2 and row.f_score >= 3:
            return "At Risk"
        if row.r_score == 1:
            return "Lost"
        return "Needs Attention"

    r["rfm_segment"] = r.apply(segment, axis=1)
    return r.merge(customers, on="customer_id").drop(columns="last_order")


def cohort_retention(orders):
    """Same as query A8, pivoted: rows = cohort month, columns = months since first order, values = % retained."""
    o = orders.copy()
    o["order_month"] = o["order_date"].dt.to_period("M")
    o["cohort"] = o.groupby("customer_id")["order_month"].transform("min")
    o["month_number"] = (o["order_month"] - o["cohort"]).apply(lambda d: d.n)
    active = o.groupby(["cohort", "month_number"])["customer_id"].nunique().unstack(fill_value=0)
    # months that have not happened yet for a cohort are NaN, not 0
    last = o["order_month"].max()
    for cohort in active.index:
        active.loc[cohort, active.columns > (last - cohort).n] = None
    active.index = active.index.astype(str)
    pct = active.div(active[0], axis=0) * 100
    return active, pct.round(1)
