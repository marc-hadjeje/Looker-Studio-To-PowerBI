CREATE SCHEMA IF NOT EXISTS `ferrous-gate-496806-b7.retail_star`
OPTIONS(location="US", description="Retail star schema dataset for BI demos");

CREATE OR REPLACE TABLE `ferrous-gate-496806-b7.retail_star.dim_product` (
  product_key INT64,
  product_id STRING,
  product_name STRING,
  category STRING,
  subcategory STRING,
  brand STRING,
  unit_cost NUMERIC,
  unit_price NUMERIC,
  is_active BOOL
);

INSERT INTO `ferrous-gate-496806-b7.retail_star.dim_product` VALUES
(1,'P-1001','Laptop Pro 14','Electronics','Computers','Northwind',650,999,true),
(2,'P-1002','Wireless Mouse','Electronics','Accessories','Northwind',8,19,true),
(3,'P-1003','4K Monitor 27','Electronics','Monitors','Contoso',180,329,true),
(4,'P-1004','Office Chair Ergo','Furniture','Office','Fabrikam',90,199,true),
(5,'P-1005','Standing Desk 140','Furniture','Office','Fabrikam',210,449,true),
(6,'P-1006','Coffee Beans 1kg','Grocery','Beverages','Adventure',9,18,true),
(7,'P-1007','Sparkling Water 12pk','Grocery','Drinks','Adventure',3,7,true),
(8,'P-1008','Running Shoes X','Sports','Footwear','ProSport',45,99,true),
(9,'P-1009','Yoga Mat','Sports','Fitness','ProSport',10,29,true),
(10,'P-1010','Novel - The Summit','Books','Fiction','LitHouse',4,14,true),
(11,'P-1011','Cookbook Everyday','Books','Cooking','LitHouse',6,24,true),
(12,'P-1012','Smartphone Max','Electronics','Phones','Northwind',420,799,true);

CREATE OR REPLACE TABLE `ferrous-gate-496806-b7.retail_star.dim_customer` (
  customer_key INT64,
  customer_id STRING,
  full_name STRING,
  gender STRING,
  age_group STRING,
  city STRING,
  region STRING,
  segment STRING,
  signup_date DATE,
  is_loyalty_member BOOL
);

INSERT INTO `ferrous-gate-496806-b7.retail_star.dim_customer` VALUES
(1,'C-2001','Amina Laurent','F','25-34','Paris','Ile-de-France','Consumer',DATE '2023-03-14',true),
(2,'C-2002','Lucas Bernard','M','35-44','Lyon','Auvergne-Rhone-Alpes','Consumer',DATE '2022-11-08',false),
(3,'C-2003','Sofia Martin','F','18-24','Marseille','Provence-Alpes-Cote d Azur','Consumer',DATE '2024-01-20',true),
(4,'C-2004','Noah Petit','M','45-54','Lille','Hauts-de-France','Corporate',DATE '2021-06-18',false),
(5,'C-2005','Emma Robert','F','35-44','Nantes','Pays de la Loire','Consumer',DATE '2023-09-02',true),
(6,'C-2006','Leo Richard','M','25-34','Toulouse','Occitanie','Home Office',DATE '2022-04-11',true),
(7,'C-2007','Chloe Simon','F','55+','Bordeaux','Nouvelle-Aquitaine','Corporate',DATE '2020-12-01',false),
(8,'C-2008','Hugo Moreau','M','18-24','Nice','Provence-Alpes-Cote d Azur','Consumer',DATE '2024-02-05',false),
(9,'C-2009','Mila Michel','F','25-34','Rennes','Bretagne','Home Office',DATE '2023-07-19',true),
(10,'C-2010','Adam Leroy','M','35-44','Strasbourg','Grand Est','Consumer',DATE '2021-10-30',true);

CREATE OR REPLACE TABLE `ferrous-gate-496806-b7.retail_star.dim_store` (
  store_key INT64,
  store_id STRING,
  store_name STRING,
  city STRING,
  region STRING,
  country STRING,
  store_format STRING,
  opened_date DATE
);

INSERT INTO `ferrous-gate-496806-b7.retail_star.dim_store` VALUES
(1,'S-3001','Paris Central','Paris','Ile-de-France','France','Flagship',DATE '2018-05-01'),
(2,'S-3002','Lyon Presquile','Lyon','Auvergne-Rhone-Alpes','France','Mall',DATE '2019-09-15'),
(3,'S-3003','Marseille Prado','Marseille','Provence-Alpes-Cote d Azur','France','Mall',DATE '2020-02-20'),
(4,'S-3004','Lille Europe','Lille','Hauts-de-France','France','Street',DATE '2017-11-10'),
(5,'S-3005','Nantes Centre','Nantes','Pays de la Loire','France','Street',DATE '2021-04-08'),
(6,'S-3999','E-Commerce Hub','Paris','Ile-de-France','France','Online',DATE '2016-01-01');

CREATE OR REPLACE TABLE `ferrous-gate-496806-b7.retail_star.dim_channel` (
  channel_key INT64,
  channel_name STRING,
  channel_group STRING
);

INSERT INTO `ferrous-gate-496806-b7.retail_star.dim_channel` VALUES
(1,'In-Store','Offline'),
(2,'Website','Online'),
(3,'Mobile App','Online'),
(4,'Marketplace','Online');

CREATE OR REPLACE TABLE `ferrous-gate-496806-b7.retail_star.dim_date` AS
WITH dates AS (
  SELECT d AS full_date
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE '2025-01-01', DATE '2025-03-31')) d
)
SELECT
  CAST(FORMAT_DATE('%Y%m%d', full_date) AS INT64) AS date_key,
  full_date,
  EXTRACT(YEAR FROM full_date) AS year,
  EXTRACT(QUARTER FROM full_date) AS quarter,
  EXTRACT(MONTH FROM full_date) AS month,
  FORMAT_DATE('%B', full_date) AS month_name,
  EXTRACT(WEEK FROM full_date) AS week_of_year,
  EXTRACT(DAY FROM full_date) AS day_of_month,
  FORMAT_DATE('%A', full_date) AS day_name,
  EXTRACT(ISOWEEK FROM full_date) AS iso_week,
  CASE WHEN EXTRACT(DAYOFWEEK FROM full_date) IN (1,7) THEN true ELSE false END AS is_weekend
FROM dates;

CREATE OR REPLACE TABLE `ferrous-gate-496806-b7.retail_star.fact_sales` (
  sales_key INT64,
  order_id STRING,
  order_line_id INT64,
  date_key INT64,
  product_key INT64,
  customer_key INT64,
  store_key INT64,
  channel_key INT64,
  quantity INT64,
  unit_price NUMERIC,
  gross_amount NUMERIC,
  discount_amount NUMERIC,
  net_sales_amount NUMERIC,
  cost_amount NUMERIC,
  profit_amount NUMERIC
);

INSERT INTO `ferrous-gate-496806-b7.retail_star.fact_sales`
WITH base AS (
  SELECT
    txn AS sales_key,
    CONCAT('ORD-', CAST(100000 + txn AS STRING)) AS order_id,
    1 AS order_line_id,
    CAST(FORMAT_DATE('%Y%m%d', DATE_ADD(DATE '2025-01-01', INTERVAL MOD(txn, 90) DAY)) AS INT64) AS date_key,
    1 + MOD(txn, 12) AS product_key,
    1 + MOD(txn * 3, 10) AS customer_key,
    1 + MOD(txn * 5, 6) AS store_key,
    1 + MOD(txn * 7, 4) AS channel_key,
    1 + MOD(txn, 5) AS quantity,
    CASE
      WHEN MOD(txn, 10) IN (0,1) THEN 0.15
      WHEN MOD(txn, 10) IN (2,3,4) THEN 0.10
      WHEN MOD(txn, 10) IN (5,6,7) THEN 0.05
      ELSE 0.00
    END AS discount_rate
  FROM UNNEST(GENERATE_ARRAY(1, 500)) txn
),
joined AS (
  SELECT
    b.sales_key,
    b.order_id,
    b.order_line_id,
    b.date_key,
    b.product_key,
    b.customer_key,
    b.store_key,
    b.channel_key,
    b.quantity,
    p.unit_price,
    p.unit_cost,
    CAST(b.quantity * p.unit_price AS NUMERIC) AS gross_amount,
    CAST(b.quantity * p.unit_price * b.discount_rate AS NUMERIC) AS discount_amount
  FROM base b
  JOIN `ferrous-gate-496806-b7.retail_star.dim_product` p
    ON p.product_key = b.product_key
)
SELECT
  sales_key,
  order_id,
  order_line_id,
  date_key,
  product_key,
  customer_key,
  store_key,
  channel_key,
  quantity,
  unit_price,
  gross_amount,
  discount_amount,
  CAST(gross_amount - discount_amount AS NUMERIC) AS net_sales_amount,
  CAST(quantity * unit_cost AS NUMERIC) AS cost_amount,
  CAST((gross_amount - discount_amount) - (quantity * unit_cost) AS NUMERIC) AS profit_amount
FROM joined;

