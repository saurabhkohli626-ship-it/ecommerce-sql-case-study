"""
Writes and executes notebooks/ecommerce_analysis.ipynb (pandas version of the SQL case study).

Usage:  python scripts/make_notebook.py
"""
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "notebooks" / "ecommerce_analysis.ipynb"

md = nbformat.v4.new_markdown_cell
code = nbformat.v4.new_code_cell

cells = [
    md("# E-Commerce Analysis with Python (pandas)\n\n"
       "The same business questions as the SQL case study (`sql/02_analysis_queries.sql`), answered with pandas. "
       "Each section shows the SQL idea it matches, so the two can be compared side by side.\n\n"
       "**Data:** 100 customers, 8 products, 200 orders, 519 order lines (Mar 2023 – Feb 2024)."),

    md("## 1. Setup and load data"),
    code("import pandas as pd\n"
         "import matplotlib.pyplot as plt\n\n"
         "plt.rcParams.update({'figure.figsize': (9, 4), 'axes.spines.top': False, 'axes.spines.right': False,\n"
         "                     'axes.grid': True, 'grid.alpha': 0.3, 'font.family': 'Arial'})\n"
         "BLUE, ORANGE = '#2a78d6', '#eb6834'\n\n"
         "customers = pd.read_csv('../data/customers.csv')\n"
         "products  = pd.read_csv('../data/products.csv')\n"
         "orders    = pd.read_csv('../data/orders.csv', parse_dates=['order_date'])\n"
         "details   = pd.read_csv('../data/orderdetails.csv')\n\n"
         "for name, df in [('customers', customers), ('products', products), ('orders', orders), ('orderdetails', details)]:\n"
         "    print(f'{name:<13} {df.shape[0]:>4} rows  {df.shape[1]} columns')"),
    code("orders.head()"),

    md("## 2. Data quality checks\n"
       "Before analysis: missing values, duplicates, broken keys, and whether order totals add up."),
    code("print('Missing values:', sum(df.isna().sum().sum() for df in [customers, products, orders, details]))\n"
         "print('Duplicate order lines:', details.duplicated().sum())\n"
         "print('Orders with unknown customer:', (~orders['customer_id'].isin(customers['customer_id'])).sum())\n"
         "print('Lines with unknown product  :', (~details['product_id'].isin(products['product_id'])).sum())\n\n"
         "details['line_amount'] = details['quantity'] * details['price_per_unit']\n"
         "line_totals = details.groupby('order_id')['line_amount'].sum()\n"
         "mismatch = (orders.set_index('order_id')['total_amount'] != line_totals).sum()\n"
         "print('Orders whose total != sum of lines:', mismatch)"),
    md("The 24 repeated order lines are real (the order totals include them), so they are kept - "
       "the same decision as in the MySQL schema."),

    md("## 3. One joined table\n"
       "Like the SQL view `vw_order_lines`: every order line with its customer and product."),
    code("lines = (details.merge(orders, on='order_id')\n"
         "                .merge(customers.rename(columns={'name': 'customer_name'}), on='customer_id')\n"
         "                .merge(products.rename(columns={'name': 'product_name'}), on='product_id'))\n"
         "lines['month'] = lines['order_date'].dt.strftime('%Y-%m')\n"
         "lines.head(3)"),

    md("## 4. Customer insights"),
    md("**Q1. Top 3 cities by number of customers** — SQL: `GROUP BY location ORDER BY COUNT(*) DESC LIMIT 3`"),
    code("customers['location'].value_counts().head(3)"),
    md("**Q2. How many orders does each customer place?** — SQL: CTE + `GROUP BY number_of_orders`"),
    code("orders_per_customer = orders.groupby('customer_id').size()\n"
         "segment = pd.cut(orders_per_customer, bins=[0, 1, 4, 100],\n"
         "                 labels=['One-time buyer', 'Occasional shopper (2-4)', 'Regular customer (5+)'])\n"
         "print(segment.value_counts())\n"
         "print('Never ordered:', len(customers) - orders_per_customer.size)"),
    md("**Q4. Top 5 customers by spend**"),
    code("(orders.groupby('customer_id')\n"
         "       .agg(total_orders=('order_id', 'count'), total_spent=('total_amount', 'sum'))\n"
         "       .nlargest(5, 'total_spent')\n"
         "       .join(customers.set_index('customer_id')))"),
    md("**Q5. Revenue by city**"),
    code("city = lines.groupby('location')['line_amount'].sum().sort_values()\n"
         "ax = city.div(1e5).plot.barh(color=BLUE, title='Revenue by city (₹ lakh)')\n"
         "ax.bar_label(ax.containers[0], fmt='%.1f', padding=3); ax.set_ylabel('');"),

    md("## 5. Product analysis"),
    md("**Q6. Products with average quantity 2 per order, by revenue** — SQL: `HAVING AVG(quantity) = 2`"),
    code("prod = lines.groupby('product_name').agg(avg_quantity=('quantity', 'mean'),\n"
         "                                          units_sold=('quantity', 'sum'),\n"
         "                                          revenue=('line_amount', 'sum'))\n"
         "prod[prod['avg_quantity'] == 2].sort_values('revenue', ascending=False)"),
    md("**Q7–Q8. Category reach and revenue share**"),
    code("cat = lines.groupby('category').agg(unique_customers=('customer_id', 'nunique'),\n"
         "                                   units_sold=('quantity', 'sum'),\n"
         "                                   revenue=('line_amount', 'sum'))\n"
         "cat['revenue_share_%'] = (cat['revenue'] / cat['revenue'].sum() * 100).round(2)\n"
         "cat.sort_values('revenue', ascending=False)"),
    md("**Q9. Product ranking** — SQL: `RANK() OVER (ORDER BY revenue DESC)`"),
    code("prod['revenue_rank'] = prod['revenue'].rank(ascending=False, method='min').astype(int)\n"
         "prod.sort_values('revenue_rank')"),

    md("## 6. Sales trends"),
    md("**Q10–Q13. Monthly sales, % change, AOV and running total** — SQL: `LAG()` and `SUM() OVER`"),
    code("monthly = (orders.assign(month=orders['order_date'].dt.strftime('%Y-%m'))\n"
         "                 .groupby('month')\n"
         "                 .agg(orders=('order_id', 'count'), sales=('total_amount', 'sum'), aov=('total_amount', 'mean')))\n"
         "monthly['pct_change'] = (monthly['sales'].pct_change() * 100).round(2)   # LAG()\n"
         "monthly['running_total'] = monthly['sales'].cumsum()                       # SUM() OVER\n"
         "monthly['aov'] = monthly['aov'].round(0)\n"
         "monthly"),
    code("ax = monthly['sales'].div(1e5).plot(marker='o', color=BLUE, title='Monthly sales (₹ lakh)')\n"
         "ax.set_xlabel(''); ax.set_ylim(0);\n"
         "print('Top 3 months:'); print(monthly['sales'].nlargest(3))"),
    md("**Q14. New customers per month**"),
    code("first_month = orders.groupby('customer_id')['order_date'].min().dt.strftime('%Y-%m')\n"
         "new_cust = first_month.value_counts().sort_index()\n"
         "ax = new_cust.plot.bar(color=ORANGE, title='New customers per month')\n"
         "ax.bar_label(ax.containers[0], padding=2); ax.set_xlabel('');"),

    md("## 7. Inventory"),
    md("**Q15–Q16. Sales frequency and low-engagement products (< 40% of customers)**"),
    code("inv = lines.groupby('product_name').agg(order_lines=('order_id', 'count'),\n"
         "                                         unique_customers=('customer_id', 'nunique'))\n"
         "inv['reach_%'] = inv['unique_customers'] / len(customers) * 100\n"
         "print('Top 5 by sales frequency:'); print(inv.nlargest(5, 'order_lines'))\n"
         "print('\\nLow engagement (< 40% of customers):'); print(inv[inv['reach_%'] < 40])"),

    md("## 8. RFM segmentation\n"
       "Recency (days since last order), Frequency (orders), Monetary (spend), each scored 1–4. "
       "Same rules as the SQL view `vw_customer_rfm` (NTILE(4) with customer_id as tie-breaker)."),
    code("last_date = orders['order_date'].max()\n"
         "rfm = orders.groupby('customer_id').agg(last_order=('order_date', 'max'),\n"
         "                                        frequency=('order_id', 'count'),\n"
         "                                        monetary=('total_amount', 'sum')).reset_index()\n"
         "rfm['recency_days'] = (last_date - rfm['last_order']).dt.days\n\n"
         "def ntile(sorted_index, n=4):\n"
         "    \"\"\"Same as SQL NTILE(n): split the sorted rows into n equal buckets.\"\"\"\n"
         "    return pd.Series([i * n // len(sorted_index) + 1 for i in range(len(sorted_index))], index=sorted_index)\n\n"
         "rfm['r_score'] = ntile(rfm.sort_values(['recency_days', 'customer_id'], ascending=[False, True]).index)\n"
         "rfm['f_score'] = ntile(rfm.sort_values(['frequency', 'customer_id']).index)\n"
         "rfm['m_score'] = ntile(rfm.sort_values(['monetary', 'customer_id']).index)\n\n"
         "def segment(r):\n"
         "    if r.r_score >= 3 and r.f_score >= 3 and r.m_score >= 3: return 'Champions'\n"
         "    if r.r_score >= 3 and r.f_score >= 2: return 'Loyal / Potential'\n"
         "    if r.r_score <= 2 and r.f_score >= 3: return 'At Risk'\n"
         "    if r.r_score == 1: return 'Lost'\n"
         "    return 'Needs Attention'\n\n"
         "rfm['segment'] = rfm.apply(segment, axis=1)\n"
         "summary = rfm.groupby('segment').agg(customers=('customer_id', 'count'), revenue=('monetary', 'sum'))\n"
         "summary['revenue_share_%'] = (summary['revenue'] / summary['revenue'].sum() * 100).round(2)\n"
         "summary.sort_values('revenue', ascending=False)"),

    md("## 9. Cohort retention\n"
       "Cohort = month of first order. Each cell = % of that cohort that ordered again N months later."),
    code("o = orders.copy()\n"
         "o['order_month'] = o['order_date'].dt.to_period('M')\n"
         "o['cohort'] = o.groupby('customer_id')['order_month'].transform('min')\n"
         "o['month_number'] = (o['order_month'] - o['cohort']).apply(lambda d: d.n)\n"
         "cohort = o.groupby(['cohort', 'month_number'])['customer_id'].nunique().unstack()\n"
         "retention = (cohort.div(cohort[0], axis=0) * 100).round(0)\n"
         "retention.iloc[:, :7]"),
    code("repeat = (orders.groupby('customer_id').size() > 1)\n"
         "print(f'Repeat purchase rate: {repeat.mean():.1%} of buying customers ordered more than once')"),

    md("## 10. Key findings\n\n"
       "- **Revenue ₹1.98 Cr** from 200 orders; average order value ≈ ₹98,915.\n"
       "- **Electronics = 64.5% of revenue**; Laptop and DSLR together ≈ 69%.\n"
       "- **Chennai** is the top revenue city (₹38.9 L); Delhi has the most customers.\n"
       "- **23 Champion customers bring 52.8% of revenue** – protect them with loyalty benefits.\n"
       "- **69% repeat rate**, but **new-customer acquisition fell** from 18 in Apr 2023 to 1–4 a month after Oct 2023.\n"
       "- **16 customers never ordered** – target them with a first-order offer.\n\n"
       "All numbers match the MySQL results in `results/query_results.md`."),
]

nb = nbformat.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "language_info": {"name": "python"},
})
OUT.parent.mkdir(exist_ok=True)
NotebookClient(nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(OUT.parent)}}).execute()
nbformat.write(nb, OUT)
print("saved", OUT.relative_to(ROOT))
