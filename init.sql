SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;

CREATE DATABASE IF NOT EXISTS rareza_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rareza_db;

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    rating DECIMAL(2,1) DEFAULT 5.0,
    sales_count INT DEFAULT 0,
    location VARCHAR(100) DEFAULT 'Argentina',
    phone VARCHAR(30) DEFAULT NULL,
    shipping_street VARCHAR(255) DEFAULT NULL,
    shipping_colony VARCHAR(100) DEFAULT NULL,
    shipping_city VARCHAR(100) DEFAULT NULL,
    shipping_state VARCHAR(100) DEFAULT NULL,
    shipping_postal VARCHAR(20) DEFAULT NULL,
    facebook_id VARCHAR(64) DEFAULT NULL,
    facebook_name VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stores (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    name VARCHAR(100),
    bio TEXT,
    logo_path VARCHAR(255),
    country VARCHAR(100) DEFAULT 'Argentina',
    ship_nacional TINYINT(1) DEFAULT 1,
    cost_nacional DECIMAL(10,2) DEFAULT 5.00,
    ship_regional TINYINT(1) DEFAULT 0,
    cost_regional DECIMAL(10,2) DEFAULT 15.00,
    ship_intl TINYINT(1) DEFAULT 0,
    cost_intl DECIMAL(10,2) DEFAULT 0.00,
    free_over_on TINYINT(1) DEFAULT 0,
    free_over DECIMAL(10,2) DEFAULT 0.00,
    handling VARCHAR(50) DEFAULT '2 días hábiles',
    returns_policy VARCHAR(50) DEFAULT 'No acepta devoluciones',
    tracked TINYINT(1) DEFAULT 0,
    win_message VARCHAR(500) DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auctions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    seller_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    game VARCHAR(50),
    set_name VARCHAR(100),
    rarity VARCHAR(100),
    grade VARCHAR(50),
    `condition` VARCHAR(50),
    language VARCHAR(50) DEFAULT 'Español',
    notes TEXT,
    sale_type ENUM('subasta','fijo') DEFAULT 'subasta',
    start_price DECIMAL(10,2) DEFAULT 0.00,
    bid_increment DECIMAL(10,2) DEFAULT 50.00,
    buy_now_price DECIMAL(10,2) DEFAULT NULL,
    current_bid DECIMAL(10,2) DEFAULT 0.00,
    bid_count INT DEFAULT 0,
    watchers_count INT DEFAULT 0,
    accepts_offers TINYINT(1) DEFAULT 0,
    is_lot TINYINT(1) DEFAULT 0,
    duration_days INT DEFAULT 7,
    ends_at TIMESTAMP NOT NULL,
    status ENUM('active','ended','sold') DEFAULT 'active',
    hue INT DEFAULT 40,
    image_path VARCHAR(255),
    back_image_path VARCHAR(255),
    detail_image_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS max_bids (
    id INT PRIMARY KEY AUTO_INCREMENT,
    auction_id INT NOT NULL,
    bidder_id INT NOT NULL,
    max_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE,
    FOREIGN KEY (bidder_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_auction_bidder (auction_id, bidder_id)
);

CREATE TABLE IF NOT EXISTS bids (
    id INT PRIMARY KEY AUTO_INCREMENT,
    auction_id INT NOT NULL,
    bidder_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE,
    FOREIGN KEY (bidder_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watched (
    user_id INT NOT NULL,
    auction_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, auction_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sales (
    id INT PRIMARY KEY AUTO_INCREMENT,
    auction_id INT NOT NULL,
    seller_id INT NOT NULL,
    buyer_id INT NOT NULL,
    final_price DECIMAL(10,2) NOT NULL,
    status ENUM('pago','envio','enviado') DEFAULT 'pago',
    tracking VARCHAR(100),
    sale_date DATE DEFAULT (CURRENT_DATE),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(id),
    FOREIGN KEY (seller_id) REFERENCES users(id),
    FOREIGN KEY (buyer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sale_id INT NOT NULL,
    sender_id INT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_messages_sale (sale_id)
);

-- Seed users (password = "rareza123" for all)
INSERT INTO users (username, email, password_hash, display_name, rating, sales_count, location) VALUES
('cartasdelsur', 'cartasdelsur@rareza.com', '$2b$12$G7QLXDU.tH3bS8/nDLaQF.ePUE8VKRbNzgGvS2r/sG57Nzoybu.wy', 'CartasDelSur', 4.9, 1280, 'Argentina'),
('holomaniamc', 'holomaniamc@rareza.com', '$2b$12$G7QLXDU.tH3bS8/nDLaQF.ePUE8VKRbNzgGvS2r/sG57Nzoybu.wy', 'HolomaníaMX', 4.8, 842, 'México'),
('topdeckco', 'topdeckco@rareza.com', '$2b$12$G7QLXDU.tH3bS8/nDLaQF.ePUE8VKRbNzgGvS2r/sG57Nzoybu.wy', 'TopDeckCO', 5.0, 367, 'Colombia'),
('elcoleccionista', 'elcoleccionista@rareza.com', '$2b$12$G7QLXDU.tH3bS8/nDLaQF.ePUE8VKRbNzgGvS2r/sG57Nzoybu.wy', 'ElColeccionista', 4.7, 2110, 'Chile'),
('gradedperu', 'gradedperu@rareza.com', '$2b$12$G7QLXDU.tH3bS8/nDLaQF.ePUE8VKRbNzgGvS2r/sG57Nzoybu.wy', 'GradedPerú', 4.9, 540, 'Perú');

INSERT INTO stores (user_id, name, bio, country, ship_nacional, cost_nacional, ship_regional, cost_regional, ship_intl, free_over_on, free_over, handling, returns_policy, tracked) VALUES
(1, 'CartasDelSur', 'Coleccionista verificado · más de 1,200 ventas', 'Argentina', 1, 5.00, 1, 15.00, 0, 1, 120.00, '2 días hábiles', '7 días', 1),
(2, 'HolomaníaMX', 'Especialistas en cartas japonesas y holos raros', 'México', 1, 8.00, 1, 20.00, 0, 0, 0.00, '3 días hábiles', 'No acepta devoluciones', 1),
(3, 'TopDeckCO', 'Graduados PSA y BGS al mejor precio de Colombia', 'Colombia', 1, 6.00, 1, 18.00, 0, 1, 100.00, '1 día hábil', '14 días', 1),
(4, 'ElColeccionista', 'El mayor catálogo de cartas coleccionables de Chile', 'Chile', 1, 7.00, 1, 22.00, 1, 1, 150.00, '2 días hábiles', '7 días', 1),
(5, 'GradedPerú', 'Autenticidad garantizada · envío a todo LATAM', 'Perú', 1, 5.00, 1, 12.00, 0, 0, 0.00, '3 días hábiles', 'No acepta devoluciones', 0);

-- Seed auctions
INSERT INTO auctions (seller_id, title, game, set_name, rarity, grade, `condition`, language, sale_type, start_price, buy_now_price, current_bid, bid_count, watchers_count, accepts_offers, duration_days, ends_at, status, hue) VALUES
(1, 'Salamandra Ígnea — Holo 1ª Ed.', 'Pokémon', 'Llamas Eternas', 'Holo', 'PSA 9', 'Excelente', 'Español', 'subasta', 1000.00, 2600.00, 1850.00, 23, 142, 1, 7, DATE_ADD(NOW(), INTERVAL 3 HOUR), 'active', 28),
(2, 'Hechicera del Vacío', 'Magic', 'Sombras de Ixar', 'Mítica', 'Sin graduar', 'Casi nueva (NM)', 'Inglés', 'subasta', 200.00, 480.00, 320.00, 11, 63, 1, 7, DATE_ADD(NOW(), INTERVAL 5 HOUR), 'active', 268),
(3, 'Wyrm Carmesí', 'Yu-Gi-Oh', 'Furia Ancestral', 'Secret Rare', 'BGS 9.5', 'Gema mint', 'Español', 'subasta', 500.00, NULL, 940.00, 31, 208, 0, 7, DATE_ADD(NOW(), INTERVAL 47 MINUTE), 'active', 8),
(4, 'Zorro Solar', 'Pokémon', 'Eclipse Cósmico', 'Holo', 'PSA 10', 'Perfecta', 'Japonés', 'subasta', 2000.00, 5500.00, 4200.00, 44, 311, 1, 7, DATE_ADD(NOW(), INTERVAL 30 HOUR), 'active', 42),
(5, 'Ángel del Ocaso', 'Magic', 'Catedral Rota', 'Rara', 'CGC 9', 'Casi nueva', 'Inglés', 'subasta', 80.00, 220.00, 150.00, 7, 38, 1, 7, DATE_ADD(NOW(), INTERVAL 51 HOUR), 'active', 222),
(1, 'Tortuga Abisal', 'Pokémon', 'Profundidades', 'Reverse Holo', 'Sin graduar', 'Buena', 'Español', 'subasta', 30.00, 95.00, 60.00, 4, 25, 1, 7, DATE_ADD(NOW(), INTERVAL 8 HOUR), 'active', 196),
(2, 'Maga Astral', 'Yu-Gi-Oh', 'Constelaciones', 'Ultra Rare', 'PSA 8', 'Muy buena', 'Español', 'subasta', 100.00, NULL, 230.00, 14, 71, 0, 7, DATE_ADD(NOW(), INTERVAL 4 HOUR), 'active', 300),
(3, 'Coloso Rúnico', 'Magic', 'Forjas de Hierro', 'Mítica', 'Sin graduar', 'Casi nueva', 'Español', 'subasta', 200.00, 720.00, 510.00, 19, 96, 1, 7, DATE_ADD(NOW(), INTERVAL 38 HOUR), 'active', 32),
(4, 'Lince Eléctrico', 'Pokémon', 'Tormenta Solar', 'Holo', 'PSA 9', 'Excelente', 'Inglés', 'subasta', 400.00, 1050.00, 780.00, 26, 154, 1, 7, DATE_ADD(NOW(), INTERVAL 26 MINUTE), 'active', 50),
(5, 'Caballero del Trueno', 'Yu-Gi-Oh', 'Legión Divina', 'Secret Rare', 'BGS 9', 'Casi nueva', 'Español', 'subasta', 200.00, 600.00, 410.00, 17, 88, 0, 7, DATE_ADD(NOW(), INTERVAL 6 HOUR), 'active', 210),
(1, 'Liche Esmeralda (Foil)', 'Magic', 'Pantano Eterno', 'Rara Foil', 'CGC 9.5', 'Gema mint', 'Inglés', 'subasta', 800.00, NULL, 1320.00, 29, 177, 0, 7, DATE_ADD(NOW(), INTERVAL 26 HOUR), 'active', 150),
(2, 'Hada Lunar — Full Art', 'Pokémon', 'Noche Estelar', 'Full Art', 'PSA 10', 'Perfecta', 'Japonés', 'subasta', 1500.00, 3900.00, 3100.00, 38, 264, 1, 7, DATE_ADD(NOW(), INTERVAL 77 HOUR), 'active', 322),
(3, 'Golem de Cristal', 'Yu-Gi-Oh', 'Era de Titanes', 'Ultimate Rare', 'Sin graduar', 'Buena', 'Español', 'subasta', 50.00, 160.00, 95.00, 6, 41, 1, 7, DATE_ADD(NOW(), INTERVAL 9 HOUR), 'active', 188),
(4, 'Guardián de Obsidiana (Foil)', 'Magic', 'Murallas de Sombra', 'Mítica', 'PSA 9', 'Excelente', 'Inglés', 'subasta', 1500.00, 3200.00, 2450.00, 33, 198, 1, 7, DATE_ADD(NOW(), INTERVAL 12 HOUR), 'active', 18),
(5, 'Dragón de Brasas — Prismático', 'Pokémon', 'Aliento de Fuego', 'Secret', 'BGS 10', 'Gema mint', 'Español', 'subasta', 5000.00, 12500.00, 9800.00, 57, 489, 0, 7, DATE_ADD(NOW(), INTERVAL 18 HOUR), 'active', 14);

-- Bid history for first auction
INSERT INTO bids (auction_id, bidder_id, amount, created_at) VALUES
(1, 2, 1850.00, DATE_SUB(NOW(), INTERVAL 2 MINUTE)),
(1, 3, 1750.00, DATE_SUB(NOW(), INTERVAL 22 MINUTE)),
(1, 4, 1650.00, DATE_SUB(NOW(), INTERVAL 1 HOUR)),
(1, 5, 1500.00, DATE_SUB(NOW(), INTERVAL 2 HOUR));

INSERT INTO bids (auction_id, bidder_id, amount, created_at) VALUES
(3, 1, 940.00, DATE_SUB(NOW(), INTERVAL 5 MINUTE)),
(3, 4, 890.00, DATE_SUB(NOW(), INTERVAL 22 MINUTE)),
(3, 2, 840.00, DATE_SUB(NOW(), INTERVAL 1 HOUR));
