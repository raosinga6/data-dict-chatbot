
-- ── Schema definitions ───────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS hr;
CREATE SCHEMA IF NOT EXISTS finance;

-- ── Data dictionary tables ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS dd_tables (
    id          SERIAL PRIMARY KEY,
    schema_name VARCHAR(50)  NOT NULL,
    table_name  VARCHAR(100) NOT NULL,
    description TEXT,
    UNIQUE (schema_name, table_name)
);

CREATE TABLE IF NOT EXISTS dd_columns (
    id               SERIAL PRIMARY KEY,
    schema_name      VARCHAR(50)  NOT NULL,
    table_name       VARCHAR(100) NOT NULL,
    column_name      VARCHAR(100) NOT NULL,
    data_type        VARCHAR(50),
    description      TEXT,
    is_nullable      BOOLEAN DEFAULT TRUE,
    is_primary_key   BOOLEAN DEFAULT FALSE,
    is_foreign_key   BOOLEAN DEFAULT FALSE,
    references_table  VARCHAR(100),
    references_column VARCHAR(100),
    UNIQUE (schema_name, table_name, column_name)
);

CREATE TABLE IF NOT EXISTS dd_joins (
    id           SERIAL PRIMARY KEY,
    from_schema  VARCHAR(50)  NOT NULL,
    from_table   VARCHAR(100) NOT NULL,
    from_column  VARCHAR(100) NOT NULL,
    to_schema    VARCHAR(50)  NOT NULL,
    to_table     VARCHAR(100) NOT NULL,
    to_column    VARCHAR(100) NOT NULL,
    join_type    VARCHAR(20) DEFAULT 'INNER',
    description  TEXT
);

-- ── SALES schema seed ────────────────────────────────────────────
INSERT INTO dd_tables (schema_name, table_name, description) VALUES
('sales', 'orders',      'Customer purchase transactions'),
('sales', 'order_items', 'Line items within each order'),
('sales', 'customers',   'Customer master data'),
('sales', 'products',    'Product catalogue with pricing'),
('sales', 'regions',     'Sales regions and territories')
ON CONFLICT DO NOTHING;

INSERT INTO dd_columns (schema_name, table_name, column_name, data_type, description, is_nullable, is_primary_key, is_foreign_key, references_table, references_column) VALUES
-- orders
('sales','orders','order_id',     'uuid',      'Unique order identifier',         false, true,  false, null,        null),
('sales','orders','customer_id',  'uuid',      'FK to customers table',           false, false, true,  'customers', 'customer_id'),
('sales','orders','region_id',    'integer',   'FK to regions table',             true,  false, true,  'regions',   'region_id'),
('sales','orders','order_date',   'timestamp', 'Date and time order was placed',  false, false, false, null,        null),
('sales','orders','status',       'varchar',   'Order status: pending/shipped/delivered/cancelled', true, false, false, null, null),
('sales','orders','total_amount', 'numeric',   'Total order value in USD',        true,  false, false, null,        null),
('sales','orders','created_by',   'uuid',      'Employee who created the order',  true,  false, true,  'employees', 'employee_id'),
-- order_items
('sales','order_items','item_id',    'serial',  'Unique line item identifier',    false, true,  false, null,       null),
('sales','order_items','order_id',   'uuid',    'FK to orders table',             false, false, true,  'orders',   'order_id'),
('sales','order_items','product_id', 'uuid',    'FK to products table',           false, false, true,  'products', 'product_id'),
('sales','order_items','quantity',   'integer', 'Number of units ordered',        false, false, false, null,       null),
('sales','order_items','unit_price', 'numeric', 'Price per unit at time of sale', false, false, false, null,       null),
('sales','order_items','discount',   'numeric', 'Discount applied (0.0 to 1.0)',  true,  false, false, null,       null),
-- customers
('sales','customers','customer_id',  'uuid',    'Unique customer identifier',     false, true,  false, null, null),
('sales','customers','first_name',   'varchar', 'Customer first name',            false, false, false, null, null),
('sales','customers','last_name',    'varchar', 'Customer last name',             false, false, false, null, null),
('sales','customers','email',        'varchar', 'Customer email address',         false, false, false, null, null),
('sales','customers','region_id',    'integer', 'Customer home region',           true,  false, true,  'regions', 'region_id'),
('sales','customers','created_at',   'timestamp','Account creation date',         false, false, false, null, null),
('sales','customers','lifetime_value','numeric', 'Total revenue from customer',   true,  false, false, null, null),
-- products
('sales','products','product_id',   'uuid',    'Unique product identifier',       false, true,  false, null, null),
('sales','products','product_name', 'varchar', 'Display name of the product',     false, false, false, null, null),
('sales','products','category',     'varchar', 'Product category',                true,  false, false, null, null),
('sales','products','unit_price',   'numeric', 'Current selling price in USD',    false, false, false, null, null),
('sales','products','cost_price',   'numeric', 'Cost of goods sold per unit',     true,  false, false, null, null),
('sales','products','stock_qty',    'integer', 'Current inventory quantity',      true,  false, false, null, null),
-- regions
('sales','regions','region_id',   'integer', 'Unique region identifier',          false, true,  false, null, null),
('sales','regions','region_name', 'varchar', 'Region display name',               false, false, false, null, null),
('sales','regions','country',     'varchar', 'Country the region belongs to',     true,  false, false, null, null),
('sales','regions','manager_id',  'uuid',    'FK to employees — regional manager',true,  false, true,  'employees', 'employee_id')
ON CONFLICT DO NOTHING;

-- ── HR schema seed ───────────────────────────────────────────────
INSERT INTO dd_tables (schema_name, table_name, description) VALUES
('hr', 'employees',   'Employee records and personal details'),
('hr', 'departments', 'Company departments and cost centres'),
('hr', 'salaries',    'Employee compensation history'),
('hr', 'leave',       'Employee leave requests and balances')
ON CONFLICT DO NOTHING;

INSERT INTO dd_columns (schema_name, table_name, column_name, data_type, description, is_nullable, is_primary_key, is_foreign_key, references_table, references_column) VALUES
-- employees
('hr','employees','employee_id',   'uuid',    'Unique employee identifier',        false, true,  false, null,          null),
('hr','employees','first_name',    'varchar', 'Employee first name',               false, false, false, null,          null),
('hr','employees','last_name',     'varchar', 'Employee last name',                false, false, false, null,          null),
('hr','employees','email',         'varchar', 'Corporate email address',           false, false, false, null,          null),
('hr','employees','department_id', 'integer', 'FK to departments',                 true,  false, true,  'departments', 'department_id'),
('hr','employees','hire_date',     'date',    'Date employee joined the company',  false, false, false, null,          null),
('hr','employees','job_title',     'varchar', 'Employee job title',                true,  false, false, null,          null),
('hr','employees','manager_id',    'uuid',    'FK to employees — direct manager',  true,  false, true,  'employees',   'employee_id'),
('hr','employees','is_active',     'boolean', 'Whether employee is currently active', false, false, false, null,       null),
-- departments
('hr','departments','department_id',   'integer', 'Unique department identifier',  false, true,  false, null, null),
('hr','departments','department_name', 'varchar', 'Department display name',       false, false, false, null, null),
('hr','departments','cost_centre',     'varchar', 'Finance cost centre code',      true,  false, false, null, null),
('hr','departments','head_count',      'integer', 'Current number of employees',   true,  false, false, null, null),
-- salaries
('hr','salaries','salary_id',    'serial',  'Unique salary record identifier',    false, true,  false, null,        null),
('hr','salaries','employee_id',  'uuid',    'FK to employees',                    false, false, true,  'employees', 'employee_id'),
('hr','salaries','base_salary',  'numeric', 'Annual base salary in USD',          false, false, false, null,        null),
('hr','salaries','effective_date','date',   'Date this salary came into effect',  false, false, false, null,        null),
('hr','salaries','currency',     'varchar', 'Currency code e.g. USD SGD',         false, false, false, null,        null),
-- leave
('hr','leave','leave_id',     'serial',  'Unique leave record identifier',        false, true,  false, null,        null),
('hr','leave','employee_id',  'uuid',    'FK to employees',                       false, false, true,  'employees', 'employee_id'),
('hr','leave','leave_type',   'varchar', 'Type: annual / sick / maternity',       false, false, false, null,        null),
('hr','leave','start_date',   'date',    'Leave start date',                      false, false, false, null,        null),
('hr','leave','end_date',     'date',    'Leave end date',                        false, false, false, null,        null),
('hr','leave','status',       'varchar', 'Status: pending / approved / rejected', false, false, false, null,        null)
ON CONFLICT DO NOTHING;

-- ── FINANCE schema seed ──────────────────────────────────────────
INSERT INTO dd_tables (schema_name, table_name, description) VALUES
('finance', 'accounts',     'Chart of accounts'),
('finance', 'transactions', 'General ledger transactions'),
('finance', 'budgets',      'Annual and quarterly budget allocations'),
('finance', 'invoices',     'Customer invoices and payment status')
ON CONFLICT DO NOTHING;

INSERT INTO dd_columns (schema_name, table_name, column_name, data_type, description, is_nullable, is_primary_key, is_foreign_key, references_table, references_column) VALUES
-- accounts
('finance','accounts','account_id',   'integer', 'Chart of accounts code',         false, true,  false, null, null),
('finance','accounts','account_name', 'varchar', 'Account display name',           false, false, false, null, null),
('finance','accounts','account_type', 'varchar', 'Type: asset/liability/revenue/expense', false, false, false, null, null),
('finance','accounts','is_active',    'boolean', 'Whether account is active',       false, false, false, null, null),
-- transactions
('finance','transactions','txn_id',       'uuid',      'Unique transaction identifier',   false, true,  false, null,       null),
('finance','transactions','account_id',   'integer',   'FK to accounts',                  false, false, true,  'accounts', 'account_id'),
('finance','transactions','txn_date',     'timestamp', 'Date transaction was recorded',   false, false, false, null,       null),
('finance','transactions','amount',       'numeric',   'Transaction amount in USD',       false, false, false, null,       null),
('finance','transactions','debit_credit', 'char',      'D = debit, C = credit',           false, false, false, null,       null),
('finance','transactions','description',  'text',      'Transaction description/memo',    true,  false, false, null,       null),
('finance','transactions','created_by',   'uuid',      'FK to employees who posted txn',  true,  false, true,  'employees','employee_id'),
-- budgets
('finance','budgets','budget_id',     'serial',  'Unique budget record identifier',  false, true,  false, null,          null),
('finance','budgets','department_id', 'integer', 'FK to departments',                false, false, true,  'departments', 'department_id'),
('finance','budgets','account_id',    'integer', 'FK to accounts',                   false, false, true,  'accounts',    'account_id'),
('finance','budgets','fiscal_year',   'integer', 'Fiscal year e.g. 2024',            false, false, false, null,          null),
('finance','budgets','quarter',       'integer', 'Quarter: 1 2 3 4',                 true,  false, false, null,          null),
('finance','budgets','amount',        'numeric', 'Budgeted amount in USD',           false, false, false, null,          null),
-- invoices
('finance','invoices','invoice_id',   'uuid',      'Unique invoice identifier',      false, true,  false, null,        null),
('finance','invoices','customer_id',  'uuid',      'FK to customers',                false, false, true,  'customers', 'customer_id'),
('finance','invoices','order_id',     'uuid',      'FK to orders',                   true,  false, true,  'orders',    'order_id'),
('finance','invoices','invoice_date', 'timestamp', 'Date invoice was issued',        false, false, false, null,        null),
('finance','invoices','due_date',     'date',      'Payment due date',               false, false, false, null,        null),
('finance','invoices','amount',       'numeric',   'Invoice total in USD',           false, false, false, null,        null),
('finance','invoices','status',       'varchar',   'Status: draft/sent/paid/overdue',false, false, false, null,        null)
ON CONFLICT DO NOTHING;

-- ── Join relationships ────────────────────────────────────────────
INSERT INTO dd_joins (from_schema, from_table, from_column, to_schema, to_table, to_column, join_type, description) VALUES
('sales','orders',      'customer_id', 'sales','customers',  'customer_id', 'INNER', 'Orders to customer details'),
('sales','orders',      'region_id',   'sales','regions',    'region_id',   'LEFT',  'Orders to region'),
('sales','orders',      'created_by',  'hr',   'employees',  'employee_id', 'LEFT',  'Orders to creating employee'),
('sales','order_items', 'order_id',    'sales','orders',     'order_id',    'INNER', 'Line items to parent order'),
('sales','order_items', 'product_id',  'sales','products',   'product_id',  'INNER', 'Line items to product details'),
('sales','customers',   'region_id',   'sales','regions',    'region_id',   'LEFT',  'Customers to their region'),
('sales','regions',     'manager_id',  'hr',   'employees',  'employee_id', 'LEFT',  'Region to its manager'),
('hr',   'employees',   'department_id','hr',  'departments','department_id','LEFT', 'Employees to department'),
('hr',   'employees',   'manager_id',  'hr',   'employees',  'employee_id', 'LEFT',  'Employee to their manager'),
('hr',   'salaries',    'employee_id', 'hr',   'employees',  'employee_id', 'INNER', 'Salary records to employee'),
('hr',   'leave',       'employee_id', 'hr',   'employees',  'employee_id', 'INNER', 'Leave records to employee'),
('finance','transactions','account_id','finance','accounts', 'account_id',  'INNER', 'Transactions to account'),
('finance','transactions','created_by','hr',  'employees',   'employee_id', 'LEFT',  'Transactions to posting employee'),
('finance','budgets',   'department_id','hr', 'departments', 'department_id','INNER','Budgets to department'),
('finance','budgets',   'account_id',  'finance','accounts', 'account_id',  'INNER', 'Budgets to account'),
('finance','invoices',  'customer_id', 'sales','customers',  'customer_id', 'INNER', 'Invoices to customer'),
('finance','invoices',  'order_id',    'sales','orders',     'order_id',    'LEFT',  'Invoices to originating order')
ON CONFLICT DO NOTHING;

-- ── Actual business tables for local testing ─────────────────────
CREATE TABLE IF NOT EXISTS sales.regions (
    region_id   SERIAL PRIMARY KEY,
    region_name VARCHAR(100),
    country     VARCHAR(100),
    manager_id  UUID
);

CREATE TABLE IF NOT EXISTS sales.customers (
    customer_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name     VARCHAR(100),
    last_name      VARCHAR(100),
    email          VARCHAR(200),
    region_id      INTEGER REFERENCES sales.regions(region_id),
    created_at     TIMESTAMP DEFAULT NOW(),
    lifetime_value NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS sales.orders (
    order_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id  UUID REFERENCES sales.customers(customer_id),
    region_id    INTEGER REFERENCES sales.regions(region_id),
    order_date   TIMESTAMP DEFAULT NOW(),
    status       VARCHAR(50) DEFAULT 'pending',
    total_amount NUMERIC(12,2)
);

-- Sample data
INSERT INTO sales.regions (region_name, country) VALUES
('North Asia',    'Singapore'),
('South Asia',    'India'),
('ANZ',           'Australia'),
('North America', 'USA'),
('Europe',        'UK')
ON CONFLICT DO NOTHING;

INSERT INTO sales.customers (first_name, last_name, email, region_id, lifetime_value) VALUES
('Arun',    'Kumar',   'arun@example.com',   1, 15000.00),
('Priya',   'Sharma',  'priya@example.com',  2, 8500.00),
('James',   'Wilson',  'james@example.com',  3, 22000.00),
('Sarah',   'Chen',    'sarah@example.com',  4, 31000.00),
('Michael', 'Brown',   'mike@example.com',   5, 12000.00)
ON CONFLICT DO NOTHING;

INSERT INTO sales.orders (customer_id, region_id, order_date, status, total_amount)
SELECT
    c.customer_id,
    c.region_id,
    NOW() - (random() * interval '365 days'),
    (ARRAY['pending','shipped','delivered'])[floor(random()*3+1)],
    round((random() * 5000 + 500)::numeric, 2)
FROM sales.customers c, generate_series(1,5)
ON CONFLICT DO NOTHING;