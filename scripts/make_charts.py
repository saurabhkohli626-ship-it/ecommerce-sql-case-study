"""
Creates the PNG charts in images/ that are shown in the README.

Usage:  python scripts/make_charts.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import analysis

OUT = analysis.ROOT / "images"
OUT.mkdir(exist_ok=True)

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
BLUES = ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 10,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT_2,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlecolor": TEXT,
    "axes.titlelocation": "left",
    "axes.titlepad": 14,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": TEXT_2,
    "ytick.color": TEXT_2,
    "axes.axisbelow": True,
})


def lakh(v):
    return f"₹{v / 1e5:.1f} L"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)
    print("saved", name)


def hbar(series, title, name, fmt=lakh, color=BLUE, note=None):
    """Horizontal bar chart, largest at the top, value label at the end of each bar."""
    s = series.sort_values()
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(s) + 1.4))
    bars = ax.barh(s.index, s.values, color=color, height=0.62)
    ax.bar_label(bars, labels=[fmt(v) for v in s.values], padding=4, color=TEXT, fontsize=9)
    ax.set_title(title)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_xlim(0, s.max() * 1.18)
    if note:
        fig.text(0.01, 0.01, note, color=TEXT_2, fontsize=8.5)
    save(fig, name)


def main():
    customers, products, orders, details = analysis.load()
    lines = analysis.order_lines(customers, products, orders, details)

    # 1. Monthly sales trend
    m = analysis.monthly_sales(orders)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(m["month"], m["total_sales"], color=BLUE, linewidth=2, marker="o", markersize=6)
    for _, row in m.nlargest(3, "total_sales").iterrows():
        ax.annotate(lakh(row.total_sales), (row.month, row.total_sales), textcoords="offset points",
                    xytext=(0, 9), ha="center", color=TEXT, fontsize=9, fontweight="bold")
    ax.set_title("Monthly sales - peaks in Jul, Sep and Dec 2023")
    ax.set_ylabel("Total sales (₹ lakh)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1e5:.0f}")
    ax.set_ylim(0, m["total_sales"].max() * 1.15)
    ax.grid(axis="x", visible=False)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    save(fig, "01_monthly_sales.png")

    # 2. Revenue by category
    hbar(lines.groupby("category")["line_amount"].sum(),
         "Revenue by category - Electronics brings 64%", "02_revenue_by_category.png")

    # 3. Revenue by product
    hbar(lines.groupby("product_name")["line_amount"].sum(),
         "Revenue by product - Laptop and DSLR lead", "03_revenue_by_product.png")

    # 4. Revenue by city
    hbar(lines.groupby("location")["line_amount"].sum(),
         "Revenue by city - Chennai is far ahead", "04_revenue_by_city.png")

    # 5. Orders per customer
    per_customer = orders.groupby("customer_id").size().value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(per_customer.index.astype(str), per_customer.values, color=BLUE, width=0.62)
    ax.bar_label(bars, padding=3, color=TEXT, fontsize=9)
    ax.set_title("How many orders each customer placed")
    ax.set_xlabel("Number of orders")
    ax.set_ylabel("Customers")
    ax.grid(axis="x", visible=False)
    fig.text(0.01, 0.01, "16 of 100 customers never ordered (not shown).", color=TEXT_2, fontsize=8.5)
    save(fig, "05_orders_per_customer.png")

    # 6. New customers per month
    n = analysis.new_customers(orders)
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(n["month"], n["new_customers"], color=ORANGE, width=0.62)
    ax.bar_label(bars, padding=3, color=TEXT, fontsize=9)
    ax.set_title("New customers per month - acquisition has dropped sharply")
    ax.set_ylabel("New customers")
    ax.grid(axis="x", visible=False)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    save(fig, "06_new_customers.png")

    # 7. RFM segments
    r = analysis.rfm(customers, orders)
    seg = r.groupby("rfm_segment").agg(customers=("customer_id", "count"), revenue=("monetary", "sum"))
    share = seg["revenue"] / seg["revenue"].sum() * 100
    labels = {k: f"{share[k]:.1f}% of revenue  ·  {seg.loc[k, 'customers']} customers" for k in seg.index}
    hbar(share, "RFM segments - 23 Champions bring over half the revenue", "07_rfm_segments.png",
         fmt=lambda v: labels[share[share == v].index[0]])

    # 8. Cohort retention heatmap
    active, pct = analysis.cohort_retention(orders)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    cmap = LinearSegmentedColormap.from_list("blues", BLUES)
    cmap.set_bad(SURFACE)
    shown = pct.drop(columns=0)
    im = ax.imshow(shown.values.astype(float), cmap=cmap, vmin=0, vmax=40, aspect="auto")
    for i in range(shown.shape[0]):
        for j in range(shown.shape[1]):
            v = shown.iat[i, j]
            if v == v:  # not NaN
                ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                        color="white" if v >= 25 else TEXT)
    ax.set_xticks(range(shown.shape[1]), [str(c) for c in shown.columns])
    ax.set_yticks(range(shown.shape[0]),
                  [f"{idx}  (n={active.loc[idx, 0]:.0f})" for idx in active.index])
    ax.set_xlabel("Months after first order")
    ax.set_title("Cohort retention - % of each month's new customers who ordered again")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="% retained")
    save(fig, "08_cohort_retention.png")


if __name__ == "__main__":
    main()
