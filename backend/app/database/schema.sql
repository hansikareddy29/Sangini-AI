-- 1. Create SHGs Table
CREATE TABLE shgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    village VARCHAR(255),
    district VARCHAR(255),
    state VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create Members Table
CREATE TABLE members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shg_id UUID NOT NULL REFERENCES shgs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    preferred_language VARCHAR(50) DEFAULT 'en',
    availability BOOLEAN DEFAULT TRUE,
    daily_capacity INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create Products Table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL, -- e.g., 'kg', 'piece', 'jar'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create Member Products Table (Junction Table)
CREATE TABLE member_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    daily_capacity INTEGER DEFAULT 0,
    UNIQUE(member_id, product_id)
);

-- 5. Create Inventory Table
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    available_quantity INTEGER DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Create Orders Table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_phone VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, partially_allocated, allocated, completed
    deadline DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Create Order Items Table
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL
);

-- 8. Create Allocations Table
CREATE TABLE allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    allocated_quantity INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'assigned', -- assigned, in_progress, completed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert Dummy Data for Testing
INSERT INTO shgs (id, name, village) 
VALUES ('11111111-1111-1111-1111-111111111111', 'Mahila Shakti SHG', 'Raipur');

INSERT INTO members (id, shg_id, name, phone_number, daily_capacity)
VALUES 
('22222222-2222-2222-2222-222222222221', '11111111-1111-1111-1111-111111111111', 'Lakshmi', '+919999999991', 40),
('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'Radha', '+919999999992', 30);

INSERT INTO products (id, name, unit)
VALUES 
('33333333-3333-3333-3333-333333333331', 'Papad', 'piece'),
('33333333-3333-3333-3333-333333333332', 'Pickle', 'jar'),
('33333333-3333-3333-3333-333333333333', 'Handicraft', 'piece');

INSERT INTO member_products (member_id, product_id, daily_capacity)
VALUES 
('22222222-2222-2222-2222-222222222221', '33333333-3333-3333-3333-333333333331', 40), -- Lakshmi makes 40 Papads
('22222222-2222-2222-2222-222222222221', '33333333-3333-3333-3333-333333333332', 20), -- Lakshmi makes 20 Pickles
('22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333331', 30); -- Radha makes 30 Papads

INSERT INTO inventory (product_id, available_quantity)
VALUES 
('33333333-3333-3333-3333-333333333331', 80), -- 80 Papads in stock
('33333333-3333-3333-3333-333333333332', 45); -- 45 Pickles in stock
