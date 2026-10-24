/* =====================================================================
   E-COMMERCE SQL CASE STUDY  -  ADVANCED SQL  (MySQL 8.0)
   Views, stored procedures, RFM customer segmentation, cohort retention.
   Run after 01_create_and_load.sql. Safe to re-run.
   ===================================================================== */

USE ecommerce_db;


/* ---------------------------------------------------------------------
   1. VIEWS  -  reusable building blocks for reports and dashboards
   --------------------------------------------------------------------- */

-- One row per order line with customer and product details (removes repeated joins)
CREATE OR REPLACE VIEW vw_order_lines AS
SELECT od.order_id,
       o.order_date,
       o.customer_id,
       c.name AS customer_name,
       c.location,
       od.product_id,
       p.name AS product_name,
       p.category,
       od.quantity,
       od.price_per_unit,
       od.quantity * od.price_per_unit AS line_amount
FROM OrderDetails od
JOIN Orders o    ON od.order_id = o.order_id
JOIN Customers c ON o.customer_id = c.customer_id
JOIN Products p  ON od.product_id = p.product_id;

-- One row per customer, including customers who never ordered
CREATE OR REPLACE VIEW vw_customer_summary AS
SELECT c.customer_id,
       c.name,
       c.location,
       COUNT(o.order_id) AS total_orders,
       COALESCE(SUM(o.total_amount), 0) AS total_spent,
       ROUND(COALESCE(AVG(o.total_amount), 0), 2) AS avg_order_value,
       MIN(o.order_date) AS first_order_date,
       MAX(o.order_date) AS last_order_date
FROM Customers c
LEFT JOIN Orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.location;

-- Monthly KPIs
CREATE OR REPLACE VIEW vw_monthly_sales AS
SELECT DATE_FORMAT(order_date, '%Y-%m') AS month,
       COUNT(order_id) AS total_orders,
       COUNT(DISTINCT customer_id) AS active_customers,
       SUM(total_amount) AS total_sales,
       ROUND(AVG(total_amount), 2) AS avg_order_value
FROM Orders
GROUP BY month;

-- A1: Use the views
SELECT * FROM vw_monthly_sales ORDER BY month;

-- A2: Top 10 customers from the summary view
SELECT * FROM vw_customer_summary ORDER BY total_spent DESC LIMIT 10;


/* ---------------------------------------------------------------------
   2. STORED PROCEDURES  -  parameterised reports
   --------------------------------------------------------------------- */

DROP PROCEDURE IF EXISTS sp_customer_report;
DROP PROCEDURE IF EXISTS sp_top_products_by_month;
DROP PROCEDURE IF EXISTS sp_city_report;

DELIMITER $$

-- Full report for one customer: summary + every item bought
CREATE PROCEDURE sp_customer_report(IN p_customer_id INT)
BEGIN
    SELECT *
    FROM vw_customer_summary
    WHERE customer_id = p_customer_id;

    SELECT order_id, order_date, product_name, category, quantity, line_amount
    FROM vw_order_lines
    WHERE customer_id = p_customer_id
    ORDER BY order_date, order_id;
END $$

-- Best-selling products in a given month, e.g. CALL sp_top_products_by_month('2023-09', 3)
CREATE PROCEDURE sp_top_products_by_month(IN p_month CHAR(7), IN p_limit INT)
BEGIN
    SELECT product_name,
           category,
           SUM(quantity) AS units_sold,
           SUM(line_amount) AS revenue
    FROM vw_order_lines
    WHERE DATE_FORMAT(order_date, '%Y-%m') = p_month
    GROUP BY product_name, category
    ORDER BY revenue DESC
    LIMIT p_limit;
END $$

-- City report: KPIs and category split for one city
CREATE PROCEDURE sp_city_report(IN p_city VARCHAR(50))
BEGIN
    SELECT location,
           COUNT(*) AS total_customers,
           SUM(total_orders > 0) AS buying_customers,
           SUM(total_orders) AS total_orders,
           SUM(total_spent) AS total_revenue
    FROM vw_customer_summary
    WHERE location = p_city
    GROUP BY location;

    SELECT category,
           SUM(quantity) AS units_sold,
           SUM(line_amount) AS revenue
    FROM vw_order_lines
    WHERE location = p_city
    GROUP BY category
    ORDER BY revenue DESC;
END $$

DELIMITER ;

-- A3: Report for the top customer
CALL sp_customer_report(32);

-- A4: Top 3 products in the peak month
CALL sp_top_products_by_month('2023-09', 3);

-- A5: City report for Chennai (highest-revenue city)
CALL sp_city_report('Chennai');


/* ---------------------------------------------------------------------
   3. RFM CUSTOMER SEGMENTATION
      Recency   = days since last order (vs the last date in the data)
      Frequency = number of orders
      Monetary  = total amount spent
      Each is scored 1-4 with NTILE(4); 4 is best.
   --------------------------------------------------------------------- */

CREATE OR REPLACE VIEW vw_customer_rfm AS
WITH rfm AS (
    SELECT customer_id,
           DATEDIFF((SELECT MAX(order_date) FROM Orders), MAX(order_date)) AS recency_days,
           COUNT(order_id) AS frequency,
           SUM(total_amount) AS monetary
    FROM Orders
    GROUP BY customer_id
),
scored AS (
    SELECT rfm.*,
           NTILE(4) OVER (ORDER BY recency_days DESC, customer_id) AS r_score,
           NTILE(4) OVER (ORDER BY frequency, customer_id)         AS f_score,
           NTILE(4) OVER (ORDER BY monetary, customer_id)          AS m_score
    FROM rfm
)
SELECT s.customer_id,
       c.name,
       c.location,
       s.recency_days,
       s.frequency,
       s.monetary,
       s.r_score,
       s.f_score,
       s.m_score,
       CONCAT(s.r_score, s.f_score, s.m_score) AS rfm_code,
       CASE
           WHEN s.r_score >= 3 AND s.f_score >= 3 AND s.m_score >= 3 THEN 'Champions'
           WHEN s.r_score >= 3 AND s.f_score >= 2                   THEN 'Loyal / Potential'
           WHEN s.r_score <= 2 AND s.f_score >= 3                   THEN 'At Risk'
           WHEN s.r_score = 1                                       THEN 'Lost'
           ELSE 'Needs Attention'
       END AS rfm_segment
FROM scored s
JOIN Customers c ON s.customer_id = c.customer_id;

-- A6: RFM score of every buying customer
SELECT * FROM vw_customer_rfm ORDER BY monetary DESC;

-- A7: Size and value of each RFM segment
SELECT rfm_segment,
       COUNT(*) AS customers,
       ROUND(AVG(recency_days), 0) AS avg_recency_days,
       ROUND(AVG(frequency), 2) AS avg_orders,
       SUM(monetary) AS total_revenue,
       ROUND(SUM(monetary) * 100.0 / (SELECT SUM(total_amount) FROM Orders), 2) AS revenue_share_pct
FROM vw_customer_rfm
GROUP BY rfm_segment
ORDER BY total_revenue DESC;


/* ---------------------------------------------------------------------
   4. COHORT RETENTION
      Cohort = month of a customer's first order.
      For each cohort: how many of its customers ordered again 1, 2, 3 ... months later.
   --------------------------------------------------------------------- */

-- A8: Cohort retention table (long format)
WITH first_order AS (
    SELECT customer_id, MIN(order_date) AS first_order_date
    FROM Orders
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT
           DATE_FORMAT(f.first_order_date, '%Y-%m') AS cohort_month,
           o.customer_id,
           TIMESTAMPDIFF(MONTH,
                         DATE_FORMAT(f.first_order_date, '%Y-%m-01'),
                         DATE_FORMAT(o.order_date, '%Y-%m-01')) AS month_number
    FROM Orders o
    JOIN first_order f ON o.customer_id = f.customer_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS customers
    FROM activity
    WHERE month_number = 0
    GROUP BY cohort_month
)
SELECT a.cohort_month,
       cs.customers AS cohort_size,
       a.month_number,
       COUNT(DISTINCT a.customer_id) AS active_customers,
       ROUND(COUNT(DISTINCT a.customer_id) * 100.0 / cs.customers, 1) AS retention_pct
FROM activity a
JOIN cohort_size cs ON a.cohort_month = cs.cohort_month
GROUP BY a.cohort_month, cs.customers, a.month_number
ORDER BY a.cohort_month, a.month_number;

-- A9: Repeat purchase rate - share of buying customers with more than one order
SELECT COUNT(*) AS buying_customers,
       SUM(total_orders > 1) AS repeat_customers,
       ROUND(SUM(total_orders > 1) * 100.0 / COUNT(*), 2) AS repeat_rate_pct
FROM vw_customer_summary
WHERE total_orders > 0;
