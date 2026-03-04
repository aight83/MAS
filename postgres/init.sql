-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Каталог продуктов
CREATE TABLE IF NOT EXISTS product_catalog (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Транзакции
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES product_catalog(id),
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Тестовые данные
INSERT INTO users (full_name, email) VALUES
    ('Санжар Алтынбай', 'sanzhar@example.com'),
    ('Айгерим Bekova', 'aigеrim@example.com'),
    ('Данияр Сейтов', 'daniyar@example.com');

INSERT INTO product_catalog (name, description, price, category) VALUES
    ('MacBook Pro', 'Ноутбук Apple 16 дюймов', 350000.00, 'Electronics'),
    ('iPhone 15', 'Смартфон Apple', 180000.00, 'Electronics'),
    ('Наушники Sony', 'Беспроводные наушники', 45000.00, 'Electronics');

INSERT INTO transactions (user_id, product_id, amount, status) VALUES
    (1, 1, 350000.00, 'completed'),
    (2, 2, 180000.00, 'completed'),
    (3, 3, 45000.00, 'pending'),
    (1, 3, 45000.00, 'completed');
