-- ============================================================
-- PROJECT: no-code-agent
-- DATABASE: motor_sales
-- FILE: 02-sample-data.sql
-- DESCRIPTION: Fiktivní testovací data
-- ============================================================

-- Umožní soubor spustit opakovaně při vývoji.
-- Vymaže stávající testovací data a resetuje ID.
TRUNCATE TABLE
    order_items,
    orders,
    inventory,
    motor_prices,
    customers,
    motors
RESTART IDENTITY CASCADE;


-- ============================================================
-- 1. MOTORS
-- ============================================================

INSERT INTO motors (
    article_number,
    model,
    motor_family,
    description,
    rated_power_kw,
    rated_speed_rpm,
    rated_voltage_v,
    rated_torque_nm,
    cooling_type,
    product_status
)
VALUES
(
    'MTR-DS4-100-AA',
    'DS4-100-AA',
    'DS4',
    'Kompaktní synchronní servomotor pro automatizační aplikace.',
    7.50,
    3000,
    400,
    23.87,
    'AIR',
    'ACTIVE'
),
(
    'MTR-DS4-132-AA',
    'DS4-132-AA',
    'DS4',
    'Synchronní servomotor pro průmyslovou automatizaci.',
    15.00,
    3000,
    400,
    47.75,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DS4-132-DD',
    'DS4-132-DD',
    'DS4',
    'Synchronní servomotor s vyšším momentem.',
    22.00,
    2000,
    400,
    105.04,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DS4-132-FF',
    'DS4-132-FF',
    'DS4',
    'Výkonná varianta servomotoru pro náročné aplikace.',
    30.00,
    1800,
    400,
    159.15,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DS4-160-AA',
    'DS4-160-AA',
    'DS4',
    'Synchronní motor pro aplikace s vyšším výkonem.',
    37.00,
    1500,
    400,
    235.55,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DST3-135-CC',
    'DST3-135-CC',
    'DST3',
    'Momentový motor pro přímé průmyslové pohony.',
    18.50,
    2000,
    400,
    88.33,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DST3-135-DD',
    'DST3-135-DD',
    'DST3',
    'Momentový synchronní motor s vysokým momentem.',
    30.00,
    1500,
    400,
    190.99,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DST3-135-FF',
    'DST3-135-FF',
    'DST3',
    'Výkonná varianta momentového motoru.',
    45.00,
    1200,
    400,
    358.10,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DS3-160-AA',
    'DS3-160-AA',
    'DS3',
    'Průmyslový synchronní motor pro standardní pohony.',
    22.00,
    1500,
    400,
    140.06,
    'AIR',
    'ACTIVE'
),
(
    'MTR-DS3-160-FF',
    'DS3-160-FF',
    'DS3',
    'Průmyslový motor s vyšším výkonem.',
    37.00,
    1500,
    400,
    235.55,
    'AIR',
    'ACTIVE'
),
(
    'MTR-DS2-200-AA',
    'DS2-200-AA',
    'DS2',
    'Motor pro těžké průmyslové aplikace.',
    45.00,
    1000,
    400,
    429.72,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DS2-200-FF',
    'DS2-200-FF',
    'DS2',
    'Výkonný průmyslový motor pro trvalý provoz.',
    75.00,
    1000,
    400,
    716.20,
    'WATER',
    'ACTIVE'
),
(
    'MTR-DSD2-100-LO',
    'DSD2-100-LO',
    'DSD2',
    'Dynamický servomotor s nízkou setrvačností.',
    5.50,
    4500,
    400,
    11.67,
    'AIR',
    'ACTIVE'
),
(
    'MTR-DSD2-100-BO',
    'DSD2-100-BO',
    'DSD2',
    'Servomotor pro vysoce dynamické aplikace.',
    8.00,
    4000,
    400,
    19.10,
    'AIR',
    'ACTIVE'
),
(
    'MTR-DSD2-100-XO',
    'DSD2-100-XO',
    'DSD2',
    'Speciální servomotor pro přesné polohování.',
    10.00,
    3500,
    400,
    27.28,
    'AIR',
    'DEVELOPMENT'
);


-- ============================================================
-- 2. CUSTOMERS
-- ============================================================

INSERT INTO customers (
    customer_number,
    company_name,
    country,
    customer_segment,
    active
)
VALUES
(
    'CUST-001',
    'Alpha Machines GmbH',
    'Germany',
    'Plastics machinery',
    TRUE
),
(
    'CUST-002',
    'Beta Automation s.r.o.',
    'Czechia',
    'Automation',
    TRUE
),
(
    'CUST-003',
    'Gamma Robotics GmbH',
    'Austria',
    'Robotics',
    TRUE
),
(
    'CUST-004',
    'Delta Drives Sp. z o.o.',
    'Poland',
    'Drive systems',
    TRUE
),
(
    'CUST-005',
    'Epsilon Packaging SAS',
    'France',
    'Packaging',
    TRUE
),
(
    'CUST-006',
    'Zeta Handling B.V.',
    'Netherlands',
    'Material handling',
    TRUE
),
(
    'CUST-007',
    'Eta Industrial Systems Ltd.',
    'United Kingdom',
    'Industrial systems',
    TRUE
),
(
    'CUST-008',
    'Theta Machine Tools S.p.A.',
    'Italy',
    'Machine tools',
    TRUE
),
(
    'CUST-009',
    'Iota Engineering AB',
    'Sweden',
    'Engineering',
    TRUE
),
(
    'CUST-010',
    'Kappa Production s.r.o.',
    'Slovakia',
    'Manufacturing',
    TRUE
);


-- ============================================================
-- 3. MOTOR PRICES
-- Historie katalogových cen a výrobních nákladů
-- ============================================================

INSERT INTO motor_prices (
    motor_id,
    valid_from,
    valid_to,
    list_price,
    production_cost,
    currency
)
SELECT
    id,
    '2024-01-01',
    '2024-12-31',
    CASE model
        WHEN 'DS4-100-AA'   THEN 2400
        WHEN 'DS4-132-AA'   THEN 3250
        WHEN 'DS4-132-DD'   THEN 4650
        WHEN 'DS4-132-FF'   THEN 5450
        WHEN 'DS4-160-AA'   THEN 6900
        WHEN 'DST3-135-CC'  THEN 4300
        WHEN 'DST3-135-DD'  THEN 6100
        WHEN 'DST3-135-FF'  THEN 7900
        WHEN 'DS3-160-AA'   THEN 4700
        WHEN 'DS3-160-FF'   THEN 7100
        WHEN 'DS2-200-AA'   THEN 8900
        WHEN 'DS2-200-FF'   THEN 13200
        WHEN 'DSD2-100-LO'  THEN 2100
        WHEN 'DSD2-100-BO'  THEN 2650
        WHEN 'DSD2-100-XO'  THEN 3150
    END,
    CASE model
        WHEN 'DS4-100-AA'   THEN 1650
        WHEN 'DS4-132-AA'   THEN 2250
        WHEN 'DS4-132-DD'   THEN 3250
        WHEN 'DS4-132-FF'   THEN 3850
        WHEN 'DS4-160-AA'   THEN 4900
        WHEN 'DST3-135-CC'  THEN 3000
        WHEN 'DST3-135-DD'  THEN 4300
        WHEN 'DST3-135-FF'  THEN 5550
        WHEN 'DS3-160-AA'   THEN 3300
        WHEN 'DS3-160-FF'   THEN 5050
        WHEN 'DS2-200-AA'   THEN 6350
        WHEN 'DS2-200-FF'   THEN 9450
        WHEN 'DSD2-100-LO'  THEN 1450
        WHEN 'DSD2-100-BO'  THEN 1850
        WHEN 'DSD2-100-XO'  THEN 2200
    END,
    'EUR'
FROM motors;


INSERT INTO motor_prices (
    motor_id,
    valid_from,
    valid_to,
    list_price,
    production_cost,
    currency
)
SELECT
    id,
    '2025-01-01',
    '2025-12-31',
    CASE model
        WHEN 'DS4-100-AA'   THEN 2520
        WHEN 'DS4-132-AA'   THEN 3400
        WHEN 'DS4-132-DD'   THEN 4850
        WHEN 'DS4-132-FF'   THEN 5700
        WHEN 'DS4-160-AA'   THEN 7200
        WHEN 'DST3-135-CC'  THEN 4500
        WHEN 'DST3-135-DD'  THEN 6400
        WHEN 'DST3-135-FF'  THEN 8250
        WHEN 'DS3-160-AA'   THEN 4900
        WHEN 'DS3-160-FF'   THEN 7450
        WHEN 'DS2-200-AA'   THEN 9300
        WHEN 'DS2-200-FF'   THEN 13800
        WHEN 'DSD2-100-LO'  THEN 2200
        WHEN 'DSD2-100-BO'  THEN 2780
        WHEN 'DSD2-100-XO'  THEN 3300
    END,
    CASE model
        WHEN 'DS4-100-AA'   THEN 1720
        WHEN 'DS4-132-AA'   THEN 2350
        WHEN 'DS4-132-DD'   THEN 3400
        WHEN 'DS4-132-FF'   THEN 4000
        WHEN 'DS4-160-AA'   THEN 5100
        WHEN 'DST3-135-CC'  THEN 3150
        WHEN 'DST3-135-DD'  THEN 4500
        WHEN 'DST3-135-FF'  THEN 5800
        WHEN 'DS3-160-AA'   THEN 3450
        WHEN 'DS3-160-FF'   THEN 5250
        WHEN 'DS2-200-AA'   THEN 6600
        WHEN 'DS2-200-FF'   THEN 9900
        WHEN 'DSD2-100-LO'  THEN 1520
        WHEN 'DSD2-100-BO'  THEN 1940
        WHEN 'DSD2-100-XO'  THEN 2320
    END,
    'EUR'
FROM motors;


INSERT INTO motor_prices (
    motor_id,
    valid_from,
    valid_to,
    list_price,
    production_cost,
    currency
)
SELECT
    id,
    '2026-01-01',
    NULL,
    CASE model
        WHEN 'DS4-100-AA'   THEN 2650
        WHEN 'DS4-132-AA'   THEN 3550
        WHEN 'DS4-132-DD'   THEN 5100
        WHEN 'DS4-132-FF'   THEN 5950
        WHEN 'DS4-160-AA'   THEN 7550
        WHEN 'DST3-135-CC'  THEN 4700
        WHEN 'DST3-135-DD'  THEN 6750
        WHEN 'DST3-135-FF'  THEN 8600
        WHEN 'DS3-160-AA'   THEN 5150
        WHEN 'DS3-160-FF'   THEN 7800
        WHEN 'DS2-200-AA'   THEN 9700
        WHEN 'DS2-200-FF'   THEN 14400
        WHEN 'DSD2-100-LO'  THEN 2320
        WHEN 'DSD2-100-BO'  THEN 2920
        WHEN 'DSD2-100-XO'  THEN 3500
    END,
    CASE model
        WHEN 'DS4-100-AA'   THEN 1810
        WHEN 'DS4-132-AA'   THEN 2450
        WHEN 'DS4-132-DD'   THEN 3550
        WHEN 'DS4-132-FF'   THEN 4170
        WHEN 'DS4-160-AA'   THEN 5350
        WHEN 'DST3-135-CC'  THEN 3300
        WHEN 'DST3-135-DD'  THEN 4750
        WHEN 'DST3-135-FF'  THEN 6050
        WHEN 'DS3-160-AA'   THEN 3620
        WHEN 'DS3-160-FF'   THEN 5500
        WHEN 'DS2-200-AA'   THEN 6900
        WHEN 'DS2-200-FF'   THEN 10300
        WHEN 'DSD2-100-LO'  THEN 1600
        WHEN 'DSD2-100-BO'  THEN 2040
        WHEN 'DSD2-100-XO'  THEN 2450
    END,
    'EUR'
FROM motors;


-- ============================================================
-- 4. INVENTORY
-- Aktuální stav skladu
-- ============================================================

INSERT INTO inventory (
    motor_id,
    warehouse,
    quantity_available,
    quantity_reserved
)
SELECT
    id,
    'Brno',
    CASE model
        WHEN 'DS4-100-AA'   THEN 28
        WHEN 'DS4-132-AA'   THEN 30
        WHEN 'DS4-132-DD'   THEN 14
        WHEN 'DS4-132-FF'   THEN 8
        WHEN 'DS4-160-AA'   THEN 5
        WHEN 'DST3-135-CC'  THEN 12
        WHEN 'DST3-135-DD'  THEN 9
        WHEN 'DST3-135-FF'  THEN 4
        WHEN 'DS3-160-AA'   THEN 17
        WHEN 'DS3-160-FF'   THEN 6
        WHEN 'DS2-200-AA'   THEN 3
        WHEN 'DS2-200-FF'   THEN 2
        WHEN 'DSD2-100-LO'  THEN 35
        WHEN 'DSD2-100-BO'  THEN 24
        WHEN 'DSD2-100-XO'  THEN 5
    END,
    CASE model
        WHEN 'DS4-100-AA'   THEN 5
        WHEN 'DS4-132-AA'   THEN 12
        WHEN 'DS4-132-DD'   THEN 8
        WHEN 'DS4-132-FF'   THEN 3
        WHEN 'DS4-160-AA'   THEN 2
        WHEN 'DST3-135-CC'  THEN 4
        WHEN 'DST3-135-DD'  THEN 5
        WHEN 'DST3-135-FF'  THEN 2
        WHEN 'DS3-160-AA'   THEN 6
        WHEN 'DS3-160-FF'   THEN 3
        WHEN 'DS2-200-AA'   THEN 1
        WHEN 'DS2-200-FF'   THEN 1
        WHEN 'DSD2-100-LO'  THEN 10
        WHEN 'DSD2-100-BO'  THEN 8
        WHEN 'DSD2-100-XO'  THEN 3
    END
FROM motors;


-- ============================================================
-- 5. ORDERS
-- Objednávky z období 2024–2026
-- ============================================================

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2024-001',
    id,
    '2024-01-15',
    '2024-02-28',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-001';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2024-002',
    id,
    '2024-03-12',
    '2024-04-30',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-002';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2024-003',
    id,
    '2024-05-20',
    '2024-07-05',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-003';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2024-004',
    id,
    '2024-08-08',
    '2024-09-20',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-004';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2024-005',
    id,
    '2024-11-04',
    '2024-12-16',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-005';


INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2025-001',
    id,
    '2025-01-10',
    '2025-02-25',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-006';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2025-002',
    id,
    '2025-02-18',
    '2025-04-04',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-001';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2025-003',
    id,
    '2025-04-11',
    '2025-05-30',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-007';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2025-004',
    id,
    '2025-06-06',
    '2025-07-22',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-002';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2025-005',
    id,
    '2025-08-14',
    '2025-10-02',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-008';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2025-006',
    id,
    '2025-10-03',
    '2025-11-21',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-009';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2025-007',
    id,
    '2025-12-01',
    '2026-01-20',
    'CANCELLED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-010';


INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-001',
    id,
    '2026-01-08',
    '2026-02-20',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-001';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-002',
    id,
    '2026-02-12',
    '2026-03-30',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-002';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-003',
    id,
    '2026-03-18',
    '2026-05-05',
    'DELIVERED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-003';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-004',
    id,
    '2026-04-22',
    '2026-06-10',
    'CONFIRMED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-004';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-005',
    id,
    '2026-05-15',
    '2026-07-01',
    'CONFIRMED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-005';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-006',
    id,
    '2026-06-18',
    '2026-08-15',
    'CONFIRMED',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-006';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-007',
    id,
    '2026-07-08',
    '2026-09-01',
    'OPEN',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-007';

INSERT INTO orders (
    order_number,
    customer_id,
    order_date,
    delivery_date,
    order_status,
    currency
)
SELECT
    'ORD-2026-008',
    id,
    '2026-07-22',
    '2026-09-15',
    'OPEN',
    'EUR'
FROM customers
WHERE customer_number = 'CUST-008';


-- ============================================================
-- 6. ORDER ITEMS
-- Vazby mezi objednávkami a motory
-- ============================================================

-- ORD-2024-001
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    10,
    10,
    3150,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-132-AA'
WHERE o.order_number = 'ORD-2024-001';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    5,
    5,
    4500,
    2
FROM orders o
JOIN motors m ON m.model = 'DS4-132-DD'
WHERE o.order_number = 'ORD-2024-001';


-- ORD-2024-002
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    14,
    14,
    2320,
    2
FROM orders o
JOIN motors m ON m.model = 'DS4-100-AA'
WHERE o.order_number = 'ORD-2024-002';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    8,
    8,
    2050,
    2
FROM orders o
JOIN motors m ON m.model = 'DSD2-100-LO'
WHERE o.order_number = 'ORD-2024-002';


-- ORD-2024-003
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    6,
    6,
    5950,
    3
FROM orders o
JOIN motors m ON m.model = 'DST3-135-DD'
WHERE o.order_number = 'ORD-2024-003';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    4,
    4,
    7650,
    4
FROM orders o
JOIN motors m ON m.model = 'DST3-135-FF'
WHERE o.order_number = 'ORD-2024-003';


-- ORD-2024-004
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    7,
    7,
    4550,
    2
FROM orders o
JOIN motors m ON m.model = 'DS3-160-AA'
WHERE o.order_number = 'ORD-2024-004';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    3,
    3,
    8650,
    3
FROM orders o
JOIN motors m ON m.model = 'DS2-200-AA'
WHERE o.order_number = 'ORD-2024-004';


-- ORD-2024-005
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    12,
    12,
    2580,
    2
FROM orders o
JOIN motors m ON m.model = 'DSD2-100-BO'
WHERE o.order_number = 'ORD-2024-005';


-- ORD-2025-001
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    9,
    9,
    3300,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-132-AA'
WHERE o.order_number = 'ORD-2025-001';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    5,
    5,
    4350,
    3
FROM orders o
JOIN motors m ON m.model = 'DST3-135-CC'
WHERE o.order_number = 'ORD-2025-001';


-- ORD-2025-002
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    16,
    16,
    3260,
    4
FROM orders o
JOIN motors m ON m.model = 'DS4-132-AA'
WHERE o.order_number = 'ORD-2025-002';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    8,
    8,
    4680,
    4
FROM orders o
JOIN motors m ON m.model = 'DS4-132-DD'
WHERE o.order_number = 'ORD-2025-002';


-- ORD-2025-003
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    11,
    11,
    2130,
    3
FROM orders o
JOIN motors m ON m.model = 'DSD2-100-LO'
WHERE o.order_number = 'ORD-2025-003';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    7,
    7,
    2680,
    4
FROM orders o
JOIN motors m ON m.model = 'DSD2-100-BO'
WHERE o.order_number = 'ORD-2025-003';


-- ORD-2025-004
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    10,
    10,
    5530,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-132-FF'
WHERE o.order_number = 'ORD-2025-004';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    4,
    4,
    6980,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-160-AA'
WHERE o.order_number = 'ORD-2025-004';


-- ORD-2025-005
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    6,
    6,
    6200,
    3
FROM orders o
JOIN motors m ON m.model = 'DST3-135-DD'
WHERE o.order_number = 'ORD-2025-005';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    3,
    3,
    8050,
    4
FROM orders o
JOIN motors m ON m.model = 'DST3-135-FF'
WHERE o.order_number = 'ORD-2025-005';


-- ORD-2025-006
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    5,
    5,
    7200,
    3
FROM orders o
JOIN motors m ON m.model = 'DS3-160-FF'
WHERE o.order_number = 'ORD-2025-006';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    2,
    2,
    13400,
    3
FROM orders o
JOIN motors m ON m.model = 'DS2-200-FF'
WHERE o.order_number = 'ORD-2025-006';


-- Zrušená objednávka, nesmí se počítat jako prodej
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    20,
    0,
    3350,
    2
FROM orders o
JOIN motors m ON m.model = 'DS4-132-AA'
WHERE o.order_number = 'ORD-2025-007';


-- ORD-2026-001
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    15,
    15,
    3400,
    4
FROM orders o
JOIN motors m ON m.model = 'DS4-132-AA'
WHERE o.order_number = 'ORD-2026-001';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    6,
    6,
    6500,
    4
FROM orders o
JOIN motors m ON m.model = 'DST3-135-DD'
WHERE o.order_number = 'ORD-2026-001';


-- ORD-2026-002
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    12,
    12,
    3450,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-132-AA'
WHERE o.order_number = 'ORD-2026-002';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    9,
    9,
    4950,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-132-DD'
WHERE o.order_number = 'ORD-2026-002';


-- ORD-2026-003
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    8,
    8,
    3480,
    2
FROM orders o
JOIN motors m ON m.model = 'DS4-132-AA'
WHERE o.order_number = 'ORD-2026-003';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    5,
    5,
    5750,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-132-FF'
WHERE o.order_number = 'ORD-2026-003';


-- ORD-2026-004
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    10,
    0,
    5000,
    2
FROM orders o
JOIN motors m ON m.model = 'DS4-132-DD'
WHERE o.order_number = 'ORD-2026-004';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    4,
    0,
    7350,
    3
FROM orders o
JOIN motors m ON m.model = 'DS4-160-AA'
WHERE o.order_number = 'ORD-2026-004';


-- ORD-2026-005
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    7,
    0,
    6600,
    2
FROM orders o
JOIN motors m ON m.model = 'DST3-135-DD'
WHERE o.order_number = 'ORD-2026-005';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    3,
    0,
    8400,
    2
FROM orders o
JOIN motors m ON m.model = 'DST3-135-FF'
WHERE o.order_number = 'ORD-2026-005';


-- ORD-2026-006
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    6,
    0,
    9500,
    2
FROM orders o
JOIN motors m ON m.model = 'DS2-200-AA'
WHERE o.order_number = 'ORD-2026-006';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    2,
    0,
    14100,
    2
FROM orders o
JOIN motors m ON m.model = 'DS2-200-FF'
WHERE o.order_number = 'ORD-2026-006';


-- ORD-2026-007
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    18,
    0,
    2250,
    2
FROM orders o
JOIN motors m ON m.model = 'DSD2-100-LO'
WHERE o.order_number = 'ORD-2026-007';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    10,
    0,
    2840,
    2
FROM orders o
JOIN motors m ON m.model = 'DSD2-100-BO'
WHERE o.order_number = 'ORD-2026-007';


-- ORD-2026-008
INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    5,
    0,
    3400,
    2
FROM orders o
JOIN motors m ON m.model = 'DSD2-100-XO'
WHERE o.order_number = 'ORD-2026-008';

INSERT INTO order_items (
    order_id,
    motor_id,
    quantity,
    delivered_quantity,
    unit_price,
    discount_percent
)
SELECT
    o.id,
    m.id,
    7,
    0,
    5000,
    3
FROM orders o
JOIN motors m ON m.model = 'DS3-160-AA'
WHERE o.order_number = 'ORD-2026-008';


-- ============================================================
-- 7. CONTROL OUTPUT
-- Tyto dotazy se objeví v logu inicializace PostgreSQL.
-- ============================================================

SELECT 'motors' AS table_name, COUNT(*) AS row_count
FROM motors

UNION ALL

SELECT 'customers', COUNT(*)
FROM customers

UNION ALL

SELECT 'orders', COUNT(*)
FROM orders

UNION ALL

SELECT 'order_items', COUNT(*)
FROM order_items

UNION ALL

SELECT 'motor_prices', COUNT(*)
FROM motor_prices

UNION ALL

SELECT 'inventory', COUNT(*)
FROM inventory;