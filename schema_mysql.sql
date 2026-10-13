-- =============================================================================
-- AgriVision AI - Enterprise MySQL Schema DDL
-- Compatible with MySQL 8.0+ / MariaDB 10.5+ / AWS RDS Aurora MySQL
-- Character Set: utf8mb4, Engine: InnoDB
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 1. USERS & FARMERS
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(60) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NULL,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'farmer',
    state VARCHAR(60) NULL,
    district VARCHAR(60) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_username (username),
    INDEX idx_users_email (email),
    INDEX idx_users_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. FARM PLOTS (Georeferenced Land Parcels)
CREATE TABLE IF NOT EXISTS farm_plots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    plot_name VARCHAR(100) NOT NULL,
    state VARCHAR(60) NOT NULL,
    district VARCHAR(60) NOT NULL,
    taluk VARCHAR(60) NULL,
    latitude DECIMAL(9, 6) NULL,
    longitude DECIMAL(9, 6) NULL,
    land_size DECIMAL(8, 2) NOT NULL DEFAULT 2.00,
    land_unit VARCHAR(20) NOT NULL DEFAULT 'acres',
    water_source VARCHAR(60) NOT NULL DEFAULT 'Borewell',
    soil_type VARCHAR(60) NOT NULL DEFAULT 'Red Loamy',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_farm_plots_user_id (user_id),
    INDEX idx_farm_plots_district (district),
    CONSTRAINT fk_farm_plots_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. SOIL TEST REPORTS (Laboratory Soil Health Tracking)
CREATE TABLE IF NOT EXISTS soil_test_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plot_id INT NOT NULL,
    test_date DATE NOT NULL,
    nitrogen_n DECIMAL(6, 2) NOT NULL,
    phosphorus_p DECIMAL(6, 2) NOT NULL,
    potassium_k DECIMAL(6, 2) NOT NULL,
    ph DECIMAL(4, 2) NOT NULL,
    organic_carbon DECIMAL(5, 2) NULL,
    lab_name VARCHAR(120) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_soil_reports_plot_id (plot_id),
    CONSTRAINT fk_soil_reports_plot FOREIGN KEY (plot_id) REFERENCES farm_plots(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. RECOMMENDATION & ADVISORY AUDIT LOG
CREATE TABLE IF NOT EXISTS recommendation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    plot_id INT NULL,
    state VARCHAR(60) NOT NULL,
    district VARCHAR(60) NOT NULL,
    season VARCHAR(30) NOT NULL,
    land_size DECIMAL(8, 2) NOT NULL,
    land_unit VARCHAR(20) NOT NULL,
    water_availability VARCHAR(30) NOT NULL,
    previous_crop VARCHAR(60) NULL,
    recommended_crop VARCHAR(60) NOT NULL,
    crop_display_name VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(5, 2) NOT NULL,
    model_used VARCHAR(60) NOT NULL DEFAULT 'Random Forest Classifier',
    estimated_yield_tons DECIMAL(8, 2) NULL,
    estimated_yield_range VARCHAR(60) NULL,
    cultivation_cost_inr DECIMAL(12, 2) NULL,
    gross_revenue_inr DECIMAL(12, 2) NULL,
    net_profit_inr DECIMAL(12, 2) NULL,
    roi_multiplier VARCHAR(30) NULL,
    weather_temp VARCHAR(30) NULL,
    weather_condition VARCHAR(60) NULL,
    weather_provider VARCHAR(100) NULL,
    weather_summary_json JSON NULL,
    crop_rotation_json JSON NULL,
    required_products_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rec_district (district),
    INDEX idx_rec_crop (recommended_crop),
    INDEX idx_rec_created_at (created_at),
    CONSTRAINT fk_rec_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_rec_plot FOREIGN KEY (plot_id) REFERENCES farm_plots(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. APMC MANDI PRICE BENCHMARKS
CREATE TABLE IF NOT EXISTS apmc_price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crop VARCHAR(60) NOT NULL,
    state VARCHAR(60) NOT NULL,
    district VARCHAR(60) NULL,
    modal_price_per_ton DECIMAL(10, 2) NOT NULL,
    min_price_per_ton DECIMAL(10, 2) NULL,
    max_price_per_ton DECIMAL(10, 2) NULL,
    record_date DATE NOT NULL,
    source VARCHAR(120) NOT NULL DEFAULT 'Agmarknet APMC Modal Price',
    INDEX idx_apmc_crop (crop),
    INDEX idx_apmc_date (record_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
