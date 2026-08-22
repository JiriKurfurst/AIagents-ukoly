-- ============================================================
-- PROJECT: no-code-agent
-- DATABASE: motor_sales
-- FILE: 01-schema.sql
-- ============================================================

-- ============================================================
-- TABLE: motors
-- ============================================================

CREATE TABLE motors (
    id                  SERIAL PRIMARY KEY,

    article_number      VARCHAR(30) UNIQUE NOT NULL,
    model               VARCHAR(100) NOT NULL,
    motor_family        VARCHAR(50) NOT NULL,

    description         TEXT,

    rated_power_kw      NUMERIC(10,2) NOT NULL,
    rated_speed_rpm     INTEGER NOT NULL,
    rated_voltage_v     INTEGER NOT NULL,
    rated_torque_nm     NUMERIC(10,2),

    cooling_type        VARCHAR(30),

    product_status      VARCHAR(30) DEFAULT 'ACTIVE',

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: customers
-- ============================================================

CREATE TABLE customers (

    id                  SERIAL PRIMARY KEY,

    customer_number     VARCHAR(30) UNIQUE NOT NULL,

    company_name        VARCHAR(150) NOT NULL,

    country             VARCHAR(80),

    customer_segment    VARCHAR(80),

    active              BOOLEAN DEFAULT TRUE,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: orders
-- ============================================================

CREATE TABLE orders (

    id                      SERIAL PRIMARY KEY,

    order_number            VARCHAR(30) UNIQUE NOT NULL,

    customer_id             INTEGER NOT NULL,

    order_date              DATE NOT NULL,

    delivery_date           DATE,

    order_status            VARCHAR(30),

    currency                VARCHAR(5) DEFAULT 'EUR',

    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_customer
        FOREIGN KEY(customer_id)
        REFERENCES customers(id)
);

-- ============================================================
-- TABLE: order_items
-- ============================================================

CREATE TABLE order_items (

    id                      SERIAL PRIMARY KEY,

    order_id                INTEGER NOT NULL,

    motor_id                INTEGER NOT NULL,

    quantity                INTEGER NOT NULL,

    delivered_quantity      INTEGER DEFAULT 0,

    unit_price              NUMERIC(12,2),

    discount_percent        NUMERIC(5,2) DEFAULT 0,

    CONSTRAINT fk_order
        FOREIGN KEY(order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_motor
        FOREIGN KEY(motor_id)
        REFERENCES motors(id)
);

-- ============================================================
-- TABLE: motor_prices
-- ============================================================

CREATE TABLE motor_prices (

    id                  SERIAL PRIMARY KEY,

    motor_id            INTEGER NOT NULL,

    valid_from          DATE NOT NULL,

    valid_to            DATE,

    list_price          NUMERIC(12,2),

    production_cost     NUMERIC(12,2),

    currency            VARCHAR(5) DEFAULT 'EUR',

    CONSTRAINT fk_motor_price
        FOREIGN KEY(motor_id)
        REFERENCES motors(id)
);

-- ============================================================
-- TABLE: inventory
-- ============================================================

CREATE TABLE inventory (

    id                      SERIAL PRIMARY KEY,

    motor_id                INTEGER NOT NULL,

    warehouse               VARCHAR(50),

    quantity_available      INTEGER DEFAULT 0,

    quantity_reserved       INTEGER DEFAULT 0,

    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_inventory_motor
        FOREIGN KEY(motor_id)
        REFERENCES motors(id)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_motor_model
ON motors(model);

CREATE INDEX idx_motor_family
ON motors(motor_family);

CREATE INDEX idx_orders_date
ON orders(order_date);

CREATE INDEX idx_orders_customer
ON orders(customer_id);

CREATE INDEX idx_order_items_motor
ON order_items(motor_id);

CREATE INDEX idx_inventory_motor
ON inventory(motor_id);