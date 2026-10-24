/* =====================================================================
   E-COMMERCE SQL CASE STUDY  -  ANALYSIS QUERIES  (MySQL 8.0)
   Database : ecommerce_db
   Tables   : Customers, Products, Orders, OrderDetails
   Run 01_create_and_load.sql first, then run this file.
   ===================================================================== */

USE ecommerce_db;


/* ---------------------------------------------------------------------
   0. DATA EXPLORATION
   --------------------------------------------------------------------- */

-- Q0a: Row count of every table
SELECT 'Customers' AS table_name, COUNT(*) AS total_rows FROM Customers
UNION ALL SELECT 'Products', COUNT(*) FROM Products
UNION ALL SELECT 'Orders', COUNT(*) FROM Orders
UNION ALL SELECT 'OrderDetails', COUNT(*) FROM OrderDetails;

-- Q0b: Date range covered by the orders
SELECT MIN(order_date) AS first_order_date,
       MAX(order_date) AS last_order_date,
       COUNT(DISTINCT customer_id) AS customers_who_ordered
FROM Orders;


/* ---------------------------------------------------------------------
   1. CUSTOMER INSIGHTS
   --------------------------------------------------------------------- */

-- Q1: Market Segmentation - top 3 cities with the highest number of customers
SELECT location,
       COUNT(customer_id) AS number_of_customers
FROM Customers
GROUP BY location
ORDER BY number_of_customers DESC
LIMIT 3;

-- Q2: Engagement Depth - how many customers placed 1, 2, 3 ... orders
WITH customer_orders AS (
    SELECT customer_id, COUNT(order_id) AS number_of_orders
    FROM Orders
    GROUP BY customer_id
)
SELECT number_of_orders,
       COUNT(customer_id) AS customer_count
FROM customer_orders
GROUP BY number_of_orders
ORDER BY number_of_orders;

-- Q2b: Same distribution grouped into segments
--      One-time buyer = 1 order, Occasional = 2-4 orders, Regular = 5+ orders
WITH customer_orders AS (
    SELECT customer_id, COUNT(order_id) AS number_of_orders
    FROM Orders
    GROUP BY customer_id
)
SELECT CASE
           WHEN number_of_orders = 1 THEN 'One-time buyer'
           WHEN number_of_orders BETWEEN 2 AND 4 THEN 'Occasional shopper'
           ELSE 'Regular customer'
       END AS customer_segment,
       COUNT(customer_id) AS customer_count
FROM customer_orders
GROUP BY customer_segment
ORDER BY customer_count DESC;

-- Q3: Customers who never placed an order
SELECT c.customer_id, c.name, c.location
FROM Customers c
LEFT JOIN Orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;

-- Q4: Top 5 customers by total spend
SELECT c.customer_id,
       c.name,
       c.location,
       COUNT(o.order_id) AS total_orders,
       SUM(o.total_amount) AS total_spent
FROM Customers c
JOIN Orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.location
ORDER BY total_spent DESC
LIMIT 5;

-- Q5: Revenue by city
SELECT c.location,
       COUNT(DISTINCT c.customer_id) AS buying_customers,
       COUNT(o.order_id) AS total_orders,
       SUM(o.total_amount) AS total_revenue
FROM Customers c
JOIN Orders o ON c.customer_id = o.customer_id
GROUP BY c.location
ORDER BY total_revenue DESC;


/* ---------------------------------------------------------------------
   2. PRODUCT ANALYSIS
   --------------------------------------------------------------------- */

-- Q6: High-value products - average quantity per order is 2, sorted by revenue
SELECT od.product_id,
       p.name,
       AVG(od.quantity) AS avg_quantity,
       SUM(od.quantity * od.price_per_unit) AS total_revenue
FROM OrderDetails od
JOIN Products p ON od.product_id = p.product_id
GROUP BY od.product_id, p.name
HAVING AVG(od.quantity) = 2
ORDER BY total_revenue DESC;

-- Q7: Category-wise customer reach - unique customers per product category
SELECT p.category,
       COUNT(DISTINCT o.customer_id) AS unique_customers
FROM Products p
JOIN OrderDetails od ON p.product_id = od.product_id
JOIN Orders o ON od.order_id = o.order_id
GROUP BY p.category
ORDER BY unique_customers DESC;

-- Q8: Revenue and units sold by category
SELECT p.category,
       SUM(od.quantity) AS units_sold,
       SUM(od.quantity * od.price_per_unit) AS total_revenue,
       ROUND(SUM(od.quantity * od.price_per_unit) * 100.0
             / (SELECT SUM(quantity * price_per_unit) FROM OrderDetails), 2) AS revenue_share_pct
FROM Products p
JOIN OrderDetails od ON p.product_id = od.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;

-- Q9: Product ranking by revenue (window function)
SELECT p.product_id,
       p.name,
       p.category,
       SUM(od.quantity) AS units_sold,
       SUM(od.quantity * od.price_per_unit) AS total_revenue,
       RANK() OVER (ORDER BY SUM(od.quantity * od.price_per_unit) DESC) AS revenue_rank
FROM Products p
JOIN OrderDetails od ON p.product_id = od.product_id
GROUP BY p.product_id, p.name, p.category
ORDER BY revenue_rank;


/* ---------------------------------------------------------------------
   3. SALES OPTIMIZATION
   --------------------------------------------------------------------- */

-- Q10: Sales trend - month-on-month % change in total sales
WITH monthly_sales AS (
    SELECT DATE_FORMAT(order_date, '%Y-%m') AS month,
           SUM(total_amount) AS total_sales
    FROM Orders
    GROUP BY month
)
SELECT month,
       total_sales,
       ROUND((total_sales - LAG(total_sales) OVER (ORDER BY month)) * 100.0
             / LAG(total_sales) OVER (ORDER BY month), 2) AS percent_change
FROM monthly_sales
ORDER BY month;

-- Q11: Average order value (AOV) and its month-on-month change
WITH monthly_aov AS (
    SELECT DATE_FORMAT(order_date, '%Y-%m') AS month,
           ROUND(AVG(total_amount), 2) AS avg_order_value
    FROM Orders
    GROUP BY month
)
SELECT month,
       avg_order_value,
       ROUND(avg_order_value - LAG(avg_order_value) OVER (ORDER BY month), 2) AS change_in_value
FROM monthly_aov
ORDER BY change_in_value DESC;

-- Q12: Peak sales periods - top 3 months by sales
SELECT DATE_FORMAT(order_date, '%Y-%m') AS month,
       COUNT(order_id) AS total_orders,
       SUM(total_amount) AS total_sales
FROM Orders
GROUP BY month
ORDER BY total_sales DESC
LIMIT 3;

-- Q13: Running (cumulative) total of sales by month
WITH monthly_sales AS (
    SELECT DATE_FORMAT(order_date, '%Y-%m') AS month,
           SUM(total_amount) AS total_sales
    FROM Orders
    GROUP BY month
)
SELECT month,
       total_sales,
       SUM(total_sales) OVER (ORDER BY month) AS running_total
FROM monthly_sales
ORDER BY month;

-- Q14: Customer acquisition - new customers (first purchase) per month and growth %
WITH first_purchase AS (
    SELECT customer_id, MIN(order_date) AS first_order_date
    FROM Orders
    GROUP BY customer_id
),
monthly_new AS (
    SELECT DATE_FORMAT(first_order_date, '%Y-%m') AS first_purchase_month,
           COUNT(customer_id) AS new_customers
    FROM first_purchase
    GROUP BY first_purchase_month
)
SELECT first_purchase_month,
       new_customers,
       ROUND((new_customers - LAG(new_customers) OVER (ORDER BY first_purchase_month)) * 100.0
             / LAG(new_customers) OVER (ORDER BY first_purchase_month), 2) AS growth_pct
FROM monthly_new
ORDER BY first_purchase_month;


/* ---------------------------------------------------------------------
   4. INVENTORY MANAGEMENT
   --------------------------------------------------------------------- */

-- Q15: Inventory refresh rate - top 5 products by sales frequency (number of order lines)
SELECT od.product_id,
       p.name,
       COUNT(od.order_id) AS sales_frequency,
       SUM(od.quantity) AS units_sold
FROM OrderDetails od
JOIN Products p ON od.product_id = p.product_id
GROUP BY od.product_id, p.name
ORDER BY sales_frequency DESC
LIMIT 5;

-- Q16: Low-engagement products - bought by less than 40% of the customer base
SELECT p.product_id,
       p.name,
       COUNT(DISTINCT o.customer_id) AS unique_customer_count
FROM Products p
JOIN OrderDetails od ON p.product_id = od.product_id
JOIN Orders o ON od.order_id = o.order_id
GROUP BY p.product_id, p.name
HAVING COUNT(DISTINCT o.customer_id) < 0.40 * (SELECT COUNT(*) FROM Customers)
ORDER BY unique_customer_count;

-- Q17: Monthly units sold per category (demand planning)
SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS month,
       p.category,
       SUM(od.quantity) AS units_sold
FROM Orders o
JOIN OrderDetails od ON o.order_id = od.order_id
JOIN Products p ON od.product_id = p.product_id
GROUP BY month, p.category
ORDER BY month, units_sold DESC;
