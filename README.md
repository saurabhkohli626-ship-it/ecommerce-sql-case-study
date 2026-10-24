# 🛒 E-Commerce SQL Case Study (MySQL)

SQL analysis of an Indian e-commerce company's customers, products, orders and order lines
(Mar 2023 – Feb 2024). The goal is to give the **marketing, sales and supply-chain teams**
actionable insights on customers, products, sales trends and inventory.

**Tools:** MySQL 8.0 · MySQL Workbench · Python (pandas) for data prep

---

## 📂 Project Structure

```
ecommerce-sql-case-study/
├── data/
│   ├── ecommerce_data.xlsx        # original dataset (4 sheets)
│   ├── customers.csv  products.csv  orders.csv  orderdetails.csv
├── sql/
│   ├── 01_create_and_load.sql     # creates ecommerce_db, tables, inserts all rows
│   └── 02_analysis_queries.sql    # 20 business questions answered in SQL
├── results/
│   └── query_results.md           # output of every query
└── scripts/
    └── build_project.py           # Excel -> CSV + load script + tested results
```

## 🗄️ Dataset & Schema

| Table | Rows | Columns |
|---|---|---|
| **Customers** | 100 | customer_id (PK), name, location |
| **Products** | 8 | product_id (PK), name, category, price |
| **Orders** | 200 | order_id (PK), order_date, customer_id (FK), total_amount |
| **OrderDetails** | 519 | order_id (FK), product_id (FK), quantity, price_per_unit |

```
Customers 1───* Orders 1───* OrderDetails *───1 Products
```

**Data checks done:** no missing values, every foreign key matches, `price_per_unit` always equals
the product price, and each order's `total_amount` equals the sum of its order lines.

## ▶️ How to Run (MySQL Workbench)

1. Open MySQL Workbench and connect to your local server.
2. **File → Open SQL Script →** `sql/01_create_and_load.sql` → click ⚡ **Execute**.
   This creates the `ecommerce_db` database and loads all 927 rows.
3. Open `sql/02_analysis_queries.sql` → ⚡ **Execute** (or run one query at a time with `Ctrl+Enter`).

To rebuild the files from the Excel sheet: `pip install pandas openpyxl tabulate` then
`python scripts/build_project.py`.

## ❓ Business Questions Answered

| # | Area | Question | SQL concepts |
|---|---|---|---|
| Q1 | Customer | Top 3 cities by number of customers | GROUP BY, ORDER BY, LIMIT |
| Q2 | Customer | Distribution of customers by number of orders (+ segments) | CTE, CASE |
| Q3 | Customer | Customers who never ordered | LEFT JOIN, IS NULL |
| Q4 | Customer | Top 5 customers by spend | JOIN, aggregation |
| Q5 | Customer | Revenue by city | JOIN, COUNT DISTINCT |
| Q6 | Product | Products with avg quantity 2 but high revenue | HAVING |
| Q7 | Product | Unique customers per category | multi-table JOIN |
| Q8 | Product | Revenue share by category | subquery |
| Q9 | Product | Product revenue ranking | RANK() window function |
| Q10 | Sales | Month-on-month % change in sales | LAG() |
| Q11 | Sales | Average order value change by month | LAG() |
| Q12 | Sales | Top 3 peak sales months | DATE_FORMAT |
| Q13 | Sales | Running total of sales | SUM() OVER |
| Q14 | Sales | New customers per month and growth % | CTE + MIN + LAG |
| Q15 | Inventory | Top 5 products by sales frequency | aggregation |
| Q16 | Inventory | Products bought by < 40 % of customers | HAVING + subquery |
| Q17 | Inventory | Monthly units sold by category | multi-level GROUP BY |

Full output: [results/query_results.md](results/query_results.md)

## 💡 Key Insights

**Customers**
- **Delhi (16), Chennai (15) and Jaipur (11)** have the most customers – best cities for targeted campaigns.
- **Chennai is the #1 revenue city (₹38.9 L)**, almost double the next city (Lucknow ₹22.1 L).
- **16 of 100 customers never ordered** – a ready list for a first-purchase coupon campaign.
- Of the 84 buyers, **50 are occasional (2–4 orders), 26 are one-time and only 8 are regular (5+)** –
  a loyalty programme could move occasional buyers up.

**Products**
- **Electronics brings 64.5 % of revenue**, Photography 30.5 %, Wearable Tech only 5 %.
- **Laptop 15" Pro (₹75.6 L) and Digital SLR Camera (₹60.4 L)** together make ~69 % of all revenue.
- Smartphone and Wireless Earbuds sell **2 units per order on average**, but each reaches fewer than
  40 % of customers – good candidates for cross-sell and bundles.

**Sales**
- Total revenue ₹1.98 Cr over 12 months. **Peak months: Sep 2023 (₹29.3 L), Dec 2023 (₹27.7 L), Jul 2023 (₹25.7 L)**.
- Sales swing strongly month to month (e.g. +141 % in Dec, −44 % in Jan) – plan stock and
  promotions around these peaks.
- **New-customer acquisition is falling**: 18 new customers in Apr 2023 vs only 1–4 per month
  from Oct 2023 – growth now depends on repeat buyers, so acquisition spend needs a review.

**Inventory**
- **Digital SLR Camera is ordered most often (78 order lines)**, followed by Bluetooth Headphones and
  E-Book Reader (68 each) – keep these well stocked.
- Smartphone (36 customers) and Wireless Earbuds (38) are low-engagement products – avoid over-stocking.

## 👤 Author

**Saurabh Kohli** – Aspiring Data Analyst · GitHub: [saurabhkohli626-ship-it](https://github.com/saurabhkohli626-ship-it)
