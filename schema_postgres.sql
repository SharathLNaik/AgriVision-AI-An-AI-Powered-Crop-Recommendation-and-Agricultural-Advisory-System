-- =============================================================================
-- AgriVision AI - Enterprise PostgreSQL Schema DDL
-- Compatible with PostgreSQL 13+ / 14 / 15 / 16 / AWS RDS / Supabase / Neon
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS & FARMERS
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(60) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(30) DEFAULT 'farmer' NOT NULL, -- 'farmer', 'agronomist', 'admin'
    state VARCHAR(60),
    district VARCHAR(60),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

-- 2. FARM PLOTS (Georeferenced Land Parcels)
CREATE TABLE IF NOT EXISTS farm_plots (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    plot_name VARCHAR(100) NOT NULL,
    state VARCHAR(60) NOT NULL,
    district VARCHAR(60) NOT NULL,
    taluk VARCHAR(60),
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    land_size NUMERIC(8, 2) NOT NULL DEFAULT 2.00,
    land_unit VARCHAR(20) DEFAULT 'acres' NOT NULL, -- 'acres', 'hectares'
    water_source VARCHAR(60) DEFAULT 'Borewell',     -- 'Borewell', 'Canal', 'Rainfed', 'Drip'
    soil_type VARCHAR(60) DEFAULT 'Red Loamy',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_farm_plots_user_id ON farm_plots(user_id);
CREATE INDEX IF NOT EXISTS idx_farm_plots_district ON farm_plots(district);

-- 3. SOIL TEST REPORTS (Laboratory Soil Health Tracking)
CREATE TABLE IF NOT EXISTS soil_test_reports (
    id SERIAL PRIMARY KEY,
    plot_id INT REFERENCES farm_plots(id) ON DELETE CASCADE,
    test_date DATE NOT NULL DEFAULT CURRENT_DATE,
    nitrogen_n NUMERIC(6, 2) NOT NULL,        -- kg/ha
    phosphorus_p NUMERIC(6, 2) NOT NULL,      -- kg/ha
    potassium_k NUMERIC(6, 2) NOT NULL,       -- kg/ha
    ph NUMERIC(4, 2) NOT NULL,                -- standard pH scale (0-14)
    organic_carbon NUMERIC(5, 2),             -- %
    lab_name VARCHAR(120),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_soil_reports_plot_id ON soil_test_reports(plot_id);

-- 4. RECOMMENDATION & ADVISORY AUDIT LOG
CREATE TABLE IF NOT EXISTS recommendation_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    plot_id INT REFERENCES farm_plots(id) ON DELETE SET NULL,
    state VARCHAR(60) NOT NULL,
    district VARCHAR(60) NOT NULL,
    season VARCHAR(30) NOT NULL,              -- 'Kharif', 'Rabi', 'Zaid'
    land_size NUMERIC(8, 2) NOT NULL,
    land_unit VARCHAR(20) NOT NULL,
    water_availability VARCHAR(30) NOT NULL,  -- 'High', 'Medium', 'Low'
    previous_crop VARCHAR(60),
    recommended_crop VARCHAR(60) NOT NULL,
    crop_display_name VARCHAR(100) NOT NULL,
    confidence_score NUMERIC(5, 2) NOT NULL,  -- e.g. 98.40%
    model_used VARCHAR(60) DEFAULT 'Random Forest Classifier',
    estimated_yield_tons NUMERIC(8, 2),
    estimated_yield_range VARCHAR(60),
    cultivation_cost_inr NUMERIC(12, 2),
    gross_revenue_inr NUMERIC(12, 2),
    net_profit_inr NUMERIC(12, 2),
    roi_multiplier VARCHAR(30),
    weather_temp VARCHAR(30),
    weather_condition VARCHAR(60),
    weather_provider VARCHAR(100),
    weather_summary_json JSONB,
    crop_rotation_json JSONB,
    required_products_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rec_district ON recommendation_history(district);
CREATE INDEX IF NOT EXISTS idx_rec_crop ON recommendation_history(recommended_crop);
CREATE INDEX IF NOT EXISTS idx_rec_created_at ON recommendation_history(created_at);

-- 5. APMC MANDI PRICE BENCHMARKS
CREATE TABLE IF NOT EXISTS apmc_price_history (
    id SERIAL PRIMARY KEY,
    crop VARCHAR(60) NOT NULL,
    state VARCHAR(60) NOT NULL,
    district VARCHAR(60),
    modal_price_per_ton NUMERIC(10, 2) NOT NULL,
    min_price_per_ton NUMERIC(10, 2),
    max_price_per_ton NUMERIC(10, 2),
    record_date DATE NOT NULL DEFAULT CURRENT_DATE,
    source VARCHAR(120) DEFAULT 'Agmarknet APMC Modal Price'
);

CREATE INDEX IF NOT EXISTS idx_apmc_crop ON apmc_price_history(crop);
CREATE INDEX IF NOT EXISTS idx_apmc_date ON apmc_price_history(record_date);
