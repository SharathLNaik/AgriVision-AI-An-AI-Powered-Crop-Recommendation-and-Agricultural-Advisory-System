import os
import json
import joblib
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from sentinel_api import Sentinel2Client
from weather_service import fetch_live_weather_forecast
from database import init_db, save_recommendation_to_db, get_recent_history, get_database_status

sentinel_client = Sentinel2Client()
init_db()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'models')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)

# Load Trained Artifacts
try:
    rf_model = joblib.load(os.path.join(MODEL_DIR, 'crop_rf.pkl'))
    svm_model = joblib.load(os.path.join(MODEL_DIR, 'crop_svm.pkl'))
    dnn_model = joblib.load(os.path.join(MODEL_DIR, 'crop_dnn.pkl'))
    scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
    label_encoder = joblib.load(os.path.join(MODEL_DIR, 'label_encoder.pkl'))

    with open(os.path.join(MODEL_DIR, 'metrics.json'), 'r') as f:
        metrics_data = json.load(f)

    with open(os.path.join(MODEL_DIR, 'crop_yield_summary.json'), 'r') as f:
        crop_yield_summary = json.load(f)

    with open(os.path.join(MODEL_DIR, 'district_profiles.json'), 'r') as f:
        district_profiles = json.load(f)

    print("All ML models and South Indian district profiles loaded successfully!")
except Exception as e:
    print("Error loading model artifacts:", e)
    rf_model, svm_model, dnn_model = None, None, None

# Crop Category & Market Prices (INR per Tonne average in South India)
CROP_MARKET_PRICES = {
    "rice": {"price_per_ton": 23000, "name": "Rice (Paddy)", "season_default": "Kharif"},
    "maize": {"price_per_ton": 21000, "name": "Maize (Corn)", "season_default": "Kharif"},
    "chickpea": {"price_per_ton": 54000, "name": "Chickpea (Bengal Gram)", "season_default": "Rabi"},
    "kidneybeans": {"price_per_ton": 62000, "name": "Kidney Beans (Rajma)", "season_default": "Rabi"},
    "pigeonpeas": {"price_per_ton": 68000, "name": "Pigeon Peas (Arhar/Tur)", "season_default": "Kharif"},
    "mothbeans": {"price_per_ton": 58000, "name": "Moth Beans", "season_default": "Zaid"},
    "mungbean": {"price_per_ton": 72000, "name": "Mung Bean (Green Gram)", "season_default": "Zaid"},
    "blackgram": {"price_per_ton": 70000, "name": "Black Gram (Urad)", "season_default": "Rabi"},
    "lentil": {"price_per_ton": 60000, "name": "Lentil", "season_default": "Rabi"},
    "pomegranate": {"price_per_ton": 85000, "name": "Pomegranate", "season_default": "Perennial"},
    "banana": {"price_per_ton": 25000, "name": "Banana", "season_default": "Perennial"},
    "mango": {"price_per_ton": 45000, "name": "Mango", "season_default": "Perennial"},
    "grapes": {"price_per_ton": 75000, "name": "Grapes", "season_default": "Perennial"},
    "watermelon": {"price_per_ton": 15000, "name": "Watermelon", "season_default": "Zaid"},
    "muskmelon": {"price_per_ton": 18000, "name": "Muskmelon", "season_default": "Zaid"},
    "apple": {"price_per_ton": 95000, "name": "Apple", "season_default": "Perennial"},
    "orange": {"price_per_ton": 40000, "name": "Orange", "season_default": "Perennial"},
    "papaya": {"price_per_ton": 22000, "name": "Papaya", "season_default": "Perennial"},
    "coconut": {"price_per_ton": 35000, "name": "Coconut", "season_default": "Perennial"},
    "cotton": {"price_per_ton": 62000, "name": "Cotton", "season_default": "Kharif"},
    "jute": {"price_per_ton": 48000, "name": "Jute", "season_default": "Kharif"},
    "coffee": {"price_per_ton": 140000, "name": "Coffee", "season_default": "Perennial"},
    "ragi": {"price_per_ton": 34000, "name": "Ragi (Finger Millet)", "season_default": "Kharif"},
    "sugarcane": {"price_per_ton": 3500, "name": "Sugarcane", "season_default": "Perennial"},
    "groundnut": {"price_per_ton": 65000, "name": "Groundnut (Peanut)", "season_default": "Kharif"}
}

# Crop-Specific Agronomic Rules for Dynamic Personalized "Why?" Explanations
CROP_AGRONOMY_RULES = {
    "rice": { "ideal_rain": 200, "ideal_ph": (5.5, 7.5), "ideal_temp": (20, 32), "why_text": "High moisture requirement (200+ mm); high Nitrogen responsiveness for heavy tillering." },
    "maize": { "ideal_rain": 120, "ideal_ph": (5.8, 7.2), "ideal_temp": (21, 30), "why_text": "Moderate rainfall & warm temperatures; excellent response to Nitrogen & Phosphorous." },
    "chickpea": { "ideal_rain": 80, "ideal_ph": (6.0, 7.8), "ideal_temp": (15, 26), "why_text": "Drought-resistant pulse that naturally fixes atmospheric Nitrogen into soil." },
    "kidneybeans": { "ideal_rain": 110, "ideal_ph": (5.7, 6.8), "ideal_temp": (18, 25), "why_text": "Prefers slightly acidic to neutral soils with moderate moisture and mild climate." },
    "pigeonpeas": { "ideal_rain": 140, "ideal_ph": (6.0, 7.5), "ideal_temp": (22, 32), "why_text": "Deep taproot system accesses sub-soil Potassium; excellent intercropping legume." },
    "mothbeans": { "ideal_rain": 60, "ideal_ph": (6.5, 8.0), "ideal_temp": (25, 35), "why_text": "Extremely drought-hardy summer legume suitable for arid/semi-arid drylands." },
    "mungbean": { "ideal_rain": 90, "ideal_ph": (6.2, 7.5), "ideal_temp": (25, 35), "why_text": "Short-duration pulse with minimal water requirements; enriches soil Nitrogen balance." },
    "blackgram": { "ideal_rain": 100, "ideal_ph": (6.0, 7.5), "ideal_temp": (24, 33), "why_text": "Ideal post-rice pulse crop that restores soil Nitrogen balance in South Indian farmlands." },
    "lentil": { "ideal_rain": 80, "ideal_ph": (6.0, 7.5), "ideal_temp": (15, 25), "why_text": "Cool-season leguminous pulse with low water consumption." },
    "pomegranate": { "ideal_rain": 100, "ideal_ph": (6.5, 7.8), "ideal_temp": (20, 34), "why_text": "Arid fruit crop requiring well-drained soil with high Potassium for fruit sizing." },
    "banana": { "ideal_rain": 200, "ideal_ph": (6.0, 7.5), "ideal_temp": (22, 32), "why_text": "Heavy Potassium consumer (K > 40); thrives in humid tropical South Indian climates." },
    "mango": { "ideal_rain": 120, "ideal_ph": (5.5, 7.5), "ideal_temp": (24, 35), "why_text": "Perennial fruit tree with deep root system; highly suited to warm South Indian weather." },
    "grapes": { "ideal_rain": 90, "ideal_ph": (6.5, 7.5), "ideal_temp": (15, 32), "why_text": "High Potassium & Phosphorous requirement with dry harvest weather preference." },
    "watermelon": { "ideal_rain": 70, "ideal_ph": (6.0, 7.0), "ideal_temp": (24, 35), "why_text": "Summer crop with high solar radiation efficiency & well-drained sandy loam preference." },
    "muskmelon": { "ideal_rain": 75, "ideal_ph": (6.0, 7.2), "ideal_temp": (24, 35), "why_text": "High temperature & low humidity preference during fruit maturation." },
    "apple": { "ideal_rain": 150, "ideal_ph": (5.5, 6.8), "ideal_temp": (10, 22), "why_text": "Requires cool chilling hours and well-drained loamy soil." },
    "orange": { "ideal_rain": 130, "ideal_ph": (6.0, 7.5), "ideal_temp": (15, 32), "why_text": "Citrus crop preferring well-drained soil with balanced Potassium & Calcium." },
    "papaya": { "ideal_rain": 140, "ideal_ph": (6.0, 7.0), "ideal_temp": (22, 32), "why_text": "Fast-growing tropical fruit crop requiring rich organic matter and good drainage." },
    "coconut": { "ideal_rain": 180, "ideal_ph": (5.2, 8.0), "ideal_temp": (24, 32), "why_text": "Coastal & tropical palm crop highly tolerant to sandy soil and high relative humidity." },
    "cotton": { "ideal_rain": 130, "ideal_ph": (6.5, 8.0), "ideal_temp": (24, 34), "why_text": "High thermal degree-day requirement; thrives in warm climates with deep clay/black soils." },
    "jute": { "ideal_rain": 190, "ideal_ph": (6.0, 7.2), "ideal_temp": (24, 34), "why_text": "Requires high humidity (80%+) and warm monsoon rainfall." },
    "coffee": { "ideal_rain": 220, "ideal_ph": (5.5, 6.5), "ideal_temp": (15, 26), "why_text": "Hill-station plantation crop requiring shade, high rainfall, and slightly acidic soil." },
    "ragi": { "ideal_rain": 130, "ideal_ph": (6.0, 7.5), "ideal_temp": (20, 32), "why_text": "Highly resilient staple millet of Karnataka; thrives in rainfed red loam & sandy soils." },
    "sugarcane": { "ideal_rain": 220, "ideal_ph": (6.5, 7.8), "ideal_temp": (22, 35), "why_text": "High biomass cash crop requiring high Nitrogen, water, and warm sunshine." },
    "groundnut": { "ideal_rain": 110, "ideal_ph": (6.2, 7.4), "ideal_temp": (24, 33), "why_text": "Oilseed legume requiring friable well-drained soil for pod expansion and calcium uptake." }
}

# 3-Season Sustainable Crop Rotation Strategy Map
ROTATION_MAP = {
    "rice": {
        "next_rabi": "blackgram",
        "rabi_reason": "Fixes atmospheric Nitrogen into rice stubble soil, restoring soil health after heavy paddy feeding.",
        "next_zaid": "mungbean",
        "zaid_reason": "Short-duration summer pulse with minimal irrigation needs, preparing soil for monsoon rice."
    },
    "maize": {
        "next_rabi": "chickpea",
        "rabi_reason": "Deep-root leguminous crop that breaks pest cycles and enriches soil Nitrogen.",
        "next_zaid": "watermelon",
        "zaid_reason": "Efficient water user for summer months with high return per acre."
    },
    "cotton": {
        "next_rabi": "blackgram",
        "rabi_reason": "Replenishes soil nutrients depleted by long-duration cotton crop.",
        "next_zaid": "mungbean",
        "zaid_reason": "Leguminous cover crop preventing soil erosion and weed growth."
    },
    "sugarcane": {
        "next_rabi": "chickpea",
        "rabi_reason": "Intercropping with pulses maximizes land productivity between sugarcane rows.",
        "next_zaid": "mungbean",
        "zaid_reason": "Enriches soil organic carbon during ratoon growth cycles."
    },
    "groundnut": {
        "next_rabi": "maize",
        "rabi_reason": "Grain crop that utilizes residual soil Nitrogen left behind by groundnut pods.",
        "next_zaid": "mungbean",
        "zaid_reason": "Short summer pulse ensuring year-round soil green cover."
    },
    "ragi": {
        "next_rabi": "chickpea",
        "rabi_reason": "Restores soil structure and Nitrogen balance in dryland agricultural zones.",
        "next_zaid": "mungbean",
        "zaid_reason": "Low-water legume ideally suited for post-millet summer rotations."
    },
    "chickpea": {
        "next_rabi": "blackgram",
        "rabi_reason": "Maintains leguminous soil balance with low moisture requirements.",
        "next_zaid": "mungbean",
        "zaid_reason": "Fallow season soil enrichment crop."
    },
    "pigeonpeas": {
        "next_rabi": "blackgram",
        "rabi_reason": "Follow-up leguminous pulse utilizing deep subsoil moisture.",
        "next_zaid": "muskmelon",
        "zaid_reason": "Profitable short-duration summer cash crop."
    },
    "banana": {
        "next_rabi": "mungbean",
        "rabi_reason": "Intercrop green manure to enhance organic matter between banana clumps.",
        "next_zaid": "blackgram",
        "zaid_reason": "Provides canopy ground cover reducing weed growth."
    },
    "mango": {
        "next_rabi": "blackgram",
        "rabi_reason": "Intercrop legume in orchard alleyways for natural bio-fertilization.",
        "next_zaid": "mungbean",
        "zaid_reason": "Cover crop preventing moisture evaporation during hot summer months."
    }
}
DEFAULT_ROTATION = {
    "next_rabi": "blackgram",
    "rabi_reason": "Leguminous pulse crop that restores Nitrogen & organic matter to farmland.",
    "next_zaid": "mungbean",
    "zaid_reason": "Short-duration summer pulse with minimal water requirements."
}

# Cultivation Cost Breakdown per Acre (INR) for South Indian crops
CROP_CULTIVATION_COSTS = {
    "rice": {"seeds": 2200, "fertilizer": 4800, "pesticides": 3200, "machinery": 4500, "labor_irrigation": 6300, "cost_per_acre": 21000},
    "maize": {"seeds": 2800, "fertilizer": 4200, "pesticides": 2500, "machinery": 3800, "labor_irrigation": 4700, "cost_per_acre": 18000},
    "chickpea": {"seeds": 1900, "fertilizer": 3100, "pesticides": 2200, "machinery": 3200, "labor_irrigation": 3600, "cost_per_acre": 14000},
    "cotton": {"seeds": 3800, "fertilizer": 6200, "pesticides": 5400, "machinery": 4800, "labor_irrigation": 6800, "cost_per_acre": 27000},
    "banana": {"seeds": 12000, "fertilizer": 14500, "pesticides": 6800, "machinery": 7500, "labor_irrigation": 14200, "cost_per_acre": 55000},
    "groundnut": {"seeds": 4200, "fertilizer": 3900, "pesticides": 2800, "machinery": 3500, "labor_irrigation": 4600, "cost_per_acre": 19000},
    "blackgram": {"seeds": 1600, "fertilizer": 2800, "pesticides": 1900, "machinery": 2900, "labor_irrigation": 3300, "cost_per_acre": 12500},
    "mungbean": {"seeds": 1500, "fertilizer": 2600, "pesticides": 1800, "machinery": 2800, "labor_irrigation": 3100, "cost_per_acre": 11800},
    "pomegranate": {"seeds": 15000, "fertilizer": 16000, "pesticides": 8500, "machinery": 8000, "labor_irrigation": 14500, "cost_per_acre": 62000},
    "mango": {"seeds": 8000, "fertilizer": 9500, "pesticides": 5200, "machinery": 6000, "labor_irrigation": 8300, "cost_per_acre": 37000},
    "sugarcane": {"seeds": 7500, "fertilizer": 8800, "pesticides": 4200, "machinery": 5500, "labor_irrigation": 9000, "cost_per_acre": 35000}
}
DEFAULT_CULTIVATION_COST = {"seeds": 2500, "fertilizer": 4500, "pesticides": 3000, "machinery": 4000, "labor_irrigation": 5000, "cost_per_acre": 19000}

# Recommended Agricultural Products per Crop
CROP_PRODUCT_RECOMMENDATIONS = {
    "rice": [
        {"name": "BPT 5204 High-Yield Paddy Seeds (10kg)", "category": "Seeds", "rating": "4.8★", "base_price": 1200},
        {"name": "IFFCO Nano Urea Liquid (500ml Bottle)", "category": "Fertilizer", "rating": "4.9★", "base_price": 240},
        {"name": "DAP 18-46-0 Granular Fertilizer (50kg Bag)", "category": "Fertilizer", "rating": "4.7★", "base_price": 1350},
        {"name": "Chlorpyrifos 50% EC Systemic Insecticide (1L)", "category": "Pesticide", "rating": "4.6★", "base_price": 680},
        {"name": "Trichoderma Viride Bio-Fungicide (1kg)", "category": "Bio-Booster", "rating": "4.8★", "base_price": 320}
    ],
    "maize": [
        {"name": "Pioneer P3396 Hybrid Maize Seeds (4kg)", "category": "Seeds", "rating": "4.8★", "base_price": 1850},
        {"name": "IFFCO NPK 10-26-26 Complex (50kg)", "category": "Fertilizer", "rating": "4.7★", "base_price": 1470},
        {"name": "Atrazine 50% WP Selective Herbicide (500g)", "category": "Herbicide", "rating": "4.6★", "base_price": 420},
        {"name": "Coragen Insecticide for Armyworm Control (60ml)", "category": "Pesticide", "rating": "4.9★", "base_price": 950}
    ],
    "cotton": [
        {"name": "Rashi RCH 659 BG II Bt Cotton Seeds (475g)", "category": "Seeds", "rating": "4.9★", "base_price": 860},
        {"name": "Bayer Confidor Insecticide (100ml)", "category": "Pesticide", "rating": "4.8★", "base_price": 540},
        {"name": "Single Super Phosphate SSP Fertilizer (50kg)", "category": "Fertilizer", "rating": "4.5★", "base_price": 480},
        {"name": "Chelated Micronutrient Spray Booster (1L)", "category": "Bio-Booster", "rating": "4.7★", "base_price": 620}
    ],
    "groundnut": [
        {"name": "Kadiri-6 High-Oil Groundnut Pods (30kg)", "category": "Seeds", "rating": "4.8★", "base_price": 2800},
        {"name": "Gypsum Soil Conditioner & Calcium (50kg)", "category": "Fertilizer", "rating": "4.7★", "base_price": 380},
        {"name": "Rhizobium Bio-Fertilizer Culture (500g)", "category": "Bio-Fertilizer", "rating": "4.8★", "base_price": 180}
    ]
}
DEFAULT_PRODUCTS = [
    {"name": "Certified High-Yield Hybrid Seeds (5kg)", "category": "Seeds", "rating": "4.7★", "base_price": 1100},
    {"name": "IFFCO Nano Urea Liquid (500ml Bottle)", "category": "Fertilizer", "rating": "4.9★", "base_price": 240},
    {"name": "NPK 19-19-19 Soluble Micronutrient (1kg)", "category": "Fertilizer", "rating": "4.8★", "base_price": 280},
    {"name": "Neem Shield Organic Bio-Pesticide (1L)", "category": "Pesticide", "rating": "4.6★", "base_price": 450}
]

# Required 4-Category Agricultural Input Products for Every South Indian Crop
CROP_REQUIRED_PRODUCTS = {
    "rice": {
        "seeds": "BPT 5204 (Samba Mahsuri) Hybrid Seeds",
        "fertilizer": "IFFCO Nano Urea & DAP (18-46-0) Granular",
        "bio_boost": "Trichoderma Viride & VAM Bio-Inoculant",
        "crop_protection": "Chlorpyrifos 50% EC & Neem Shield 10000 PPM"
    },
    "maize": {
        "seeds": "Pioneer P3396 High-Yield Hybrid Seeds",
        "fertilizer": "IFFCO NPK 10-26-26 Complex + Urea",
        "bio_boost": "Azospirillum & PSB Bio-Fertilizer Culture",
        "crop_protection": "Coragen 18.5% SC (Armyworm Specialist)"
    },
    "chickpea": {
        "seeds": "JG 11 / JAKI 9218 Certified Bengal Gram",
        "fertilizer": "Single Super Phosphate (SSP) & MOP Potash",
        "bio_boost": "Rhizobium Legume Inoculant & VAM Culture",
        "crop_protection": "Emamectin Benzoate 5% SG Pod-Borer Shield"
    },
    "kidneybeans": {
        "seeds": "Chitra / Varun Certified Rajma Seeds",
        "fertilizer": "NPK 12-32-16 Complex & Nano Zinc",
        "bio_boost": "Rhizobium Phaseoli & Humic Acid 12%",
        "crop_protection": "Mancozeb 75% WP & Neem Bio-Pesticide"
    },
    "pigeonpeas": {
        "seeds": "ICPH 2740 / BRG-2 Arhar Hybrid Seeds",
        "fertilizer": "DAP 18-46-0 & Gypsum Soil Conditioner",
        "bio_boost": "Rhizobium & Trichoderma Harzianum",
        "crop_protection": "Profenofos 50% EC & Bacillus Thuringiensis"
    },
    "mothbeans": {
        "seeds": "RMO 40 / RMO 257 Drought-Resistant Seeds",
        "fertilizer": "DAP 18-46-0 Starter Granules",
        "bio_boost": "Phosphate Solubilizing Bacteria (PSB)",
        "crop_protection": "Organic Neem Seed Kernel Extract (NSKE 5%)"
    },
    "mungbean": {
        "seeds": "IPM 02-3 / Shiny Moong Certified Seeds",
        "fertilizer": "Single Super Phosphate (SSP) & Micronutrients",
        "bio_boost": "Rhizobium Culture & Liquid Bio-NPK",
        "crop_protection": "Dimethoate 30% EC (Whitefly & Thrips Shield)"
    },
    "blackgram": {
        "seeds": "VBN 8 / ADT 5 High-Yield Urad Seeds",
        "fertilizer": "DAP 18-46-0 & Foliar 2% DAP Nutrient Spray",
        "bio_boost": "Rhizobium & Phosphobacteria Carrier Mix",
        "crop_protection": "Imidacloprid 17.8% SL & Yellow Mosaic Shield"
    },
    "lentil": {
        "seeds": "IPL 316 / KLS 218 Improved Lentil Seeds",
        "fertilizer": "NPK 20-20-0 & Sulfur 90% Bentonite",
        "bio_boost": "Rhizobium Leguminosarum & Seaweed Extract",
        "crop_protection": "Carbendazim 50% WP (Wilt & Root Rot Guard)"
    },
    "pomegranate": {
        "seeds": "Bhagwa Grafted High-Yield Saplings",
        "fertilizer": "Water-Soluble 0-52-34 & Calcium Nitrate",
        "bio_boost": "VAM & Pseudomonas Fluorescens Bio-Agent",
        "crop_protection": "Bordeaux Mixture 1% & Streptocycline Guard"
    },
    "banana": {
        "seeds": "Grand Naine (G9) Tissue Culture Plantlets",
        "fertilizer": "MOP (0-0-60 Potash) & Urea Fertigation Mix",
        "bio_boost": "Arbuscular Mycorrhizal Fungi (AMF) & Humic 98%",
        "crop_protection": "Propiconazole 25% EC (Sigatoka Leaf Shield)"
    },
    "mango": {
        "seeds": "Alphonso / Banganapalli Grafted Clones",
        "fertilizer": "Organic FYM & NPK 10-26-26 Complex",
        "bio_boost": "Paclobutrazol Flower Booster & Trichoderma",
        "crop_protection": "Imidacloprid 17.8% SL & Sulfur 80% WDG Spray"
    },
    "grapes": {
        "seeds": "Thomson Seedless Certified Rootstock",
        "fertilizer": "Potassium Schoenite & Chelated Zinc/Boron",
        "bio_boost": "Gibberellic Acid (GA3) & Bio-Stimulants",
        "crop_protection": "Azoxystrobin 23% SC (Downy Mildew Protector)"
    },
    "watermelon": {
        "seeds": "Namdhari NS 295 / Black Ball F1 Hybrid",
        "fertilizer": "Water-Soluble NPK 19-19-19 & Potassium Nitrate",
        "bio_boost": "Fulvic Acid Bio-Booster & Root Stimulant",
        "crop_protection": "Thiamethoxam 25% WG & Copper Oxychloride"
    },
    "muskmelon": {
        "seeds": "Kundan / Madhuras F1 Sweet Melon Seeds",
        "fertilizer": "13-40-13 Starter & 0-0-50 Potassium Sulfate",
        "bio_boost": "Seaweed Ascophyllum Nodosum Extract",
        "crop_protection": "Difenoconazole 25% EC & Neem Bio-Spray"
    },
    "apple": {
        "seeds": "Rootstock M9 / MM106 Certified Scion",
        "fertilizer": "Calcium Nitrate & Boron Chelate Foliar Feed",
        "bio_boost": "Mycorrhizal Root Inoculant & Humic Complex",
        "crop_protection": "Captan 50% WP & Mancozeb Apple Scab Shield"
    },
    "orange": {
        "seeds": "Nagpur Mandarin / Sweet Orange Saplings",
        "fertilizer": "NPK 19-19-19 Soluble & Zinc Sulfate Monohydrate",
        "bio_boost": "Citrus Bio-Enzyme & Pseudomonas Putida",
        "crop_protection": "Copper Hydroxide 77% WP Citrus Canker Protector"
    },
    "papaya": {
        "seeds": "Red Lady 786 Taiwan Hybrid Seeds",
        "fertilizer": "SSP Phosphate, Urea & Muriate of Potash",
        "bio_boost": "Trichoderma Harzianum & Organic Vermicompost",
        "crop_protection": "Acetamiprid 20% SP (Aphid & Ring Spot Guard)"
    },
    "coconut": {
        "seeds": "Tall x Dwarf (TxD) Certified Hybrid Seedlings",
        "fertilizer": "Potash MOP, Rock Phosphate & Magnesium Sulfate",
        "bio_boost": "K-Mobilizing Bacteria & Azospirillum Co-Culture",
        "crop_protection": "Rhynchophorus Pheromone Trap & Borax Soil Drench"
    },
    "cotton": {
        "seeds": "Rashi RCH 659 BG II Bt Cotton Seeds",
        "fertilizer": "Single Super Phosphate (SSP) & Urea Split Dose",
        "bio_boost": "Chelated Micronutrient Spray Booster (1L)",
        "crop_protection": "Bayer Confidor Insecticide (Bollworm Shield)"
    },
    "jute": {
        "seeds": "JRO 524 (Navin) Certified Tossa Jute Seeds",
        "fertilizer": "NPK 20-10-10 Balanced Basal Nutrition",
        "bio_boost": "Azotobacter Nitrogen Fixing Bio-Inoculant",
        "crop_protection": "Carbaryl 50% WP Semi-Looper Insect Shield"
    },
    "coffee": {
        "seeds": "Arabica S.795 / Robusta Certified Seedlings",
        "fertilizer": "NPK 17-17-17 Estate Complex & Dolomite Lime",
        "bio_boost": "Trichoderma Viride Shade Garden Compost",
        "crop_protection": "Bordeaux Mixture 0.5% (Leaf Rust Berry Shield)"
    },
    "ragi": {
        "seeds": "GPU 28 / Indaf 8 High-Yield Millet Seeds",
        "fertilizer": "Urea 50kg & SSP 100kg Rainfed Basal Dressing",
        "bio_boost": "Azospirillum Brasilense Seed Coating Culture",
        "crop_protection": "Mancozeb 75% WP Blast Resistant Foliar Spray"
    },
    "sugarcane": {
        "seeds": "Co 86032 (Nayana) Certified Tissue Setts",
        "fertilizer": "Urea, DAP & MOP Split 3-Stage Nutrition",
        "bio_boost": "Gluconacetobacter Diazotrophicus Nitrogen Bio-Agent",
        "crop_protection": "Chlorantraniliprole 0.4% G Shoot Borer Guard"
    },
    "groundnut": {
        "seeds": "Kadiri-6 / TMV 2 High-Oil Groundnut Pods",
        "fertilizer": "Gypsum Soil Conditioner (Calcium & Sulfur) + DAP",
        "bio_boost": "Rhizobium Bio-Fertilizer Culture (500g)",
        "crop_protection": "Hexaconazole 5% EC (Tikka Leaf Spot Shield)"
    }
}
DEFAULT_REQUIRED_PRODUCTS = {
    "seeds": "Certified High-Yield Hybrid Seeds",
    "fertilizer": "IFFCO Nano Urea & DAP (18-46-0) Complex",
    "bio_boost": "Trichoderma Viride & Bio-NPK Soil Booster",
    "crop_protection": "Neem Shield Organic Bio-Pesticide & Fungicide"
}

# Online Stores Comparison Engine
ONLINE_STORES = [
    {"store": "DeHaat Agri Store", "badge": "Official Partner", "delivery": "1-2 Days", "discount_pct": 8, "stock": "In Stock"},
    {"store": "AgroStar Mart", "badge": "Verified Seller", "delivery": "2-3 Days", "discount_pct": 5, "stock": "In Stock"},
    {"store": "BigHaat Store", "badge": "Direct Agri", "delivery": "2-4 Days", "discount_pct": 10, "stock": "In Stock"},
    {"store": "IFFCO Bazar", "badge": "Govt Co-op", "delivery": "1-3 Days", "discount_pct": 12, "stock": "Limited Stock"},
    {"store": "Amazon AgriHub", "badge": "Prime Delivery", "delivery": "1 Day", "discount_pct": 4, "stock": "In Stock"}
]

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "status": "online",
        "system": "AgriVision AI - South India Crop & Yield System",
        "south_india_records": 52965,
        "models_ready": rf_model is not None,
        "available_states": list(district_profiles.keys())
    })

@app.route('/api/districts', methods=['GET'])
def get_districts():
    state = request.args.get('state', 'Tamil Nadu')
    if state in district_profiles:
        return jsonify({
            "state": state,
            "districts": district_profiles[state]
        })
    return jsonify({"error": f"State '{state}' not found in South India profiles"}), 404

@app.route('/api/farmer-recommend', methods=['POST'])
def farmer_recommend():
    """
    End-to-End 10-Step Smart Agriculture Workflow API
    """
    try:
        data = request.get_json() or {}
        state = data.get('state', 'Tamil Nadu')
        district = data.get('district', 'Thanjavur')
        land_size = float(data.get('land_size', 2.0))
        land_unit = data.get('land_unit', 'acres').lower()
        water_avail = data.get('water_availability', 'Medium')
        prev_crop = (data.get('previous_crop') or 'none').lower().strip()
        has_soil_report = data.get('has_soil_report', False)
        farmer_budget = float(data.get('farmer_budget', 50000.0))
        
        # Convert land size to Acres for cost calculations and Hectares for Yield calculations
        acre_size = land_size * 2.47105 if land_unit == 'hectares' else land_size
        ha_size = land_size / 2.47105 if land_unit == 'acres' else land_size
        
        # Get baseline soil & climate for district
        state_profiles = district_profiles.get(state, district_profiles['Tamil Nadu'])
        dist_data = state_profiles.get(district)
        if not dist_data:
            for d_k, d_v in state_profiles.items():
                if d_k.lower() == district.lower() or d_k.lower().startswith(district.lower()[:4]) or district.lower().startswith(d_k.lower()[:4]):
                    dist_data = d_v
                    break
        if not dist_data:
            dist_data = list(state_profiles.values())[0]
        dist_data = dist_data.copy()
        
        # Override with custom soil test if provided
        if has_soil_report and 'custom_soil' in data:
            c = data['custom_soil']
            dist_data['N'] = float(c.get('N', dist_data['N']))
            dist_data['P'] = float(c.get('P', dist_data['P']))
            dist_data['K'] = float(c.get('K', dist_data['K']))
            dist_data['ph'] = float(c.get('ph', dist_data['ph']))

        # Adjust parameters based on Water Availability & Previous Crop
        if water_avail == 'High':
            dist_data['rainfall'] *= 1.25
            dist_data['humidity'] = min(95.0, dist_data['humidity'] + 8)
        elif water_avail == 'Low':
            dist_data['rainfall'] *= 0.70
            dist_data['humidity'] = max(40.0, dist_data['humidity'] - 12)
            
        if prev_crop in ['rice', 'cotton', 'sugarcane']:
            dist_data['N'] = max(20.0, dist_data['N'] * 0.85) # depleted N
        elif prev_crop in ['blackgram', 'mungbean', 'chickpea', 'groundnut']:
            dist_data['N'] = min(140.0, dist_data['N'] * 1.20) # enriched N

        # Build feature vector [N, P, K, temp, humidity, ph, rainfall]
        features = np.array([[
            dist_data['N'],
            dist_data['P'],
            dist_data['K'],
            dist_data['temperature'],
            dist_data['humidity'],
            dist_data['ph'],
            dist_data['rainfall']
        ]])

        # Predict Class Probabilities using Random Forest
        probs = rf_model.predict_proba(features)[0]
        sorted_indices = np.argsort(probs)[::-1]
        
        NON_SOUTH_INDIAN_CROPS = {'jute', 'apple'}
        valid_indices = [idx for idx in sorted_indices if label_encoder.classes_[idx].lower() not in NON_SOUTH_INDIAN_CROPS]
        top_indices = valid_indices[:4]
        
        recommendations = []

        for rank, idx in enumerate(top_indices):
            crop_name = label_encoder.classes_[idx]
            raw_prob = probs[idx]
            
            if rank == 0:
                badge = "Highly Suitable"
                badge_class = "badge-success"
            elif rank == 1 or raw_prob > 0.15:
                badge = "Suitable"
                badge_class = "badge-info"
            else:
                badge = "Moderately Suitable"
                badge_class = "badge-warning"

            meta = CROP_MARKET_PRICES.get(crop_name, {"price_per_ton": 30000, "name": crop_name.title(), "season_default": "Kharif"})
            
            # Retrieve Yield range from authentic South Indian crop stats
            yield_info = crop_yield_summary.get(crop_name, {"mean_yield": 3.8, "min_yield": 2.5, "max_yield": 5.2})
            min_y_ha = yield_info['min_yield']
            max_y_ha = yield_info['max_yield']
            avg_y_ha = yield_info['mean_yield']

            # Calculate harvest range for farmer's land
            tot_min_tons = round(min_y_ha * ha_size, 2)
            tot_max_tons = round(max_y_ha * ha_size, 2)
            
            # Calculate Revenue range (INR)
            price = meta['price_per_ton']
            rev_min = int(tot_min_tons * price)
            rev_max = int(tot_max_tons * price)

            # Cultivation Cost Breakdown for crop
            cost_meta = CROP_CULTIVATION_COSTS.get(crop_name, DEFAULT_CULTIVATION_COST)
            cost_per_acre = cost_meta['cost_per_acre']
            total_cultivation_cost = int(cost_per_acre * acre_size)

            itemized_costs = {
                "seeds": int(cost_meta['seeds'] * acre_size),
                "fertilizer": int(cost_meta['fertilizer'] * acre_size),
                "pesticides": int(cost_meta['pesticides'] * acre_size),
                "machinery": int(cost_meta['machinery'] * acre_size),
                "labor_irrigation": int(cost_meta['labor_irrigation'] * acre_size),
                "cost_per_acre": cost_per_acre,
                "total_cost": total_cultivation_cost
            }

            # Net Profit Financials
            net_profit_min = rev_min - total_cultivation_cost
            net_profit_max = rev_max - total_cultivation_cost
            avg_net_profit = (net_profit_min + net_profit_max) / 2.0
            profit_margin_pct = round((avg_net_profit / ((rev_min + rev_max) / 2.0)) * 100, 1) if (rev_min + rev_max) > 0 else 0
            roi_multiplier = round(((rev_min + rev_max) / 2.0) / total_cultivation_cost, 2) if total_cultivation_cost > 0 else 1.0

            # Products & Store Price Comparisons
            prods = CROP_PRODUCT_RECOMMENDATIONS.get(crop_name, DEFAULT_PRODUCTS)
            req_products = CROP_REQUIRED_PRODUCTS.get(crop_name, {
                "seeds": f"Certified High-Yield Hybrid {meta['name']} Seeds",
                "fertilizer": "IFFCO Nano Urea & DAP (18-46-0) Complex",
                "bio_boost": "Trichoderma Viride & Bio-NPK Soil Booster",
                "crop_protection": "Neem Shield Organic Bio-Pesticide & Fungicide"
            }).copy()
            req_products["items"] = prods

            store_matrix = []
            for st in ONLINE_STORES:
                discount_mult = (100 - st['discount_pct']) / 100.0
                total_store_pkg_cost = int(total_cultivation_cost * discount_mult)
                store_matrix.append({
                    "store_name": st['store'],
                    "badge": st['badge'],
                    "delivery_time": st['delivery'],
                    "discount_label": f"{st['discount_pct']}% OFF",
                    "estimated_package_cost": f"₹{total_store_pkg_cost:,}",
                    "stock_status": st['stock']
                })

            # Budget Fit Check
            budget_surplus_deficit = int(farmer_budget - total_cultivation_cost)
            is_within_budget = budget_surplus_deficit >= 0
            budget_status_label = "Within Budget" if is_within_budget else "Budget Deficit"
            budget_status_class = "status-within-budget" if is_within_budget else "status-deficit-budget"

            # Crop-Specific Agronomic Rules & Dynamic "Why?" Explanations
            rule = CROP_AGRONOMY_RULES.get(crop_name, {})
            reasons = []
            
            ideal_rain = rule.get('ideal_rain', 150)
            if dist_data['rainfall'] >= ideal_rain:
                reasons.append({"factor": "Moisture Match", "text": f"{meta['name']} thrives with field rainfall ({dist_data['rainfall']:.0f}mm vs min {ideal_rain}mm required)."})
            else:
                reasons.append({"factor": "Water Adaptation", "text": f"Adapted for available moisture ({dist_data['rainfall']:.0f}mm rainfall); supplemental drip irrigation recommended."})

            ideal_temp = rule.get('ideal_temp', (20, 32))
            if ideal_temp[0] <= dist_data['temperature'] <= ideal_temp[1]:
                reasons.append({"factor": "Thermal Range", "text": f"Field temperature ({dist_data['temperature']:.1f}°C) matches optimal growth window ({ideal_temp[0]}-{ideal_temp[1]}°C)."})
            else:
                reasons.append({"factor": "Thermal Tolerance", "text": f"Tolerates regional temperature ({dist_data['temperature']:.1f}°C)."})

            ideal_ph = rule.get('ideal_ph', (6.0, 7.5))
            if ideal_ph[0] <= dist_data['ph'] <= ideal_ph[1]:
                reasons.append({"factor": "Soil pH Ideal", "text": f"Soil pH ({dist_data['ph']:.1f}) is within {meta['name']}'s preferred range ({ideal_ph[0]}-{ideal_ph[1]})."})
            else:
                reasons.append({"factor": "Soil Adjustment", "text": f"Soil pH ({dist_data['ph']:.1f}) is acceptable with normal bio-fertilizer balance."})

            if 'why_text' in rule:
                reasons.append({"factor": "Agronomic Benefit", "text": rule['why_text']})

            def format_inr(val):
                if val >= 100000 or val <= -100000:
                    return f"₹{val/100000:.2f} Lakh"
                return f"₹{val:,}"

            recommendations.append({
                "crop_key": crop_name,
                "crop_display_name": meta['name'],
                "badge": badge,
                "badge_class": badge_class,
                "confidence_percentage": round(raw_prob * 100, 1),
                "yield_per_ha_range": f"{min_y_ha:.1f} - {max_y_ha:.1f} Tonnes/Ha",
                "total_harvest_range": f"{tot_min_tons:.1f} - {tot_max_tons:.1f} Metric Tonnes",
                "revenue_range_inr": f"₹{rev_min:,} - ₹{rev_max:,}",
                "revenue_formatted": f"{format_inr(rev_min)} – {format_inr(rev_max)}",
                "season": meta['season_default'],
                "why_reasons": reasons,
                # Step 5: Cultivation Cost
                "itemized_costs": itemized_costs,
                "total_cultivation_cost_inr": f"₹{total_cultivation_cost:,}",
                # Step 6: Required Products (Structured 4 Categories + Item list)
                "required_products": req_products,
                # Step 7: Store Price Matrix
                "store_price_matrix": store_matrix,
                # Step 8: Budget Fit
                "budget_check": {
                    "farmer_budget_inr": f"₹{int(farmer_budget):,}",
                    "total_cost_inr": f"₹{total_cultivation_cost:,}",
                    "difference_inr": f"₹{abs(budget_surplus_deficit):,}",
                    "is_within_budget": is_within_budget,
                    "status_label": budget_status_label,
                    "status_class": budget_status_class,
                    "summary_text": f"Surplus of ₹{budget_surplus_deficit:,} available" if is_within_budget else f"Budget deficit of ₹{abs(budget_surplus_deficit):,}. Kisan Credit Card (KCC) options available."
                },
                # Step 9: Net Profit Financials
                "financial_margins": {
                    "gross_revenue": f"{format_inr(rev_min)} – {format_inr(rev_max)}",
                    "cultivation_cost": f"₹{total_cultivation_cost:,}",
                    "net_profit_range": f"{format_inr(net_profit_min)} – {format_inr(net_profit_max)}",
                    "profit_margin_percent": f"{profit_margin_pct}%",
                    "roi_multiplier": f"{roi_multiplier}x ROI"
                }
            })

        # Top Recommended Crop Rotation Plan
        top_crop = recommendations[0]['crop_key']
        rotation_info = ROTATION_MAP.get(top_crop, DEFAULT_ROTATION)
        
        crop_rotation_plan = {
            "kharif_season": recommendations[0]['crop_display_name'],
            "rabi_season": CROP_MARKET_PRICES.get(rotation_info['next_rabi'], {}).get('name', 'Black Gram (Urad)'),
            "rabi_reason": rotation_info['rabi_reason'],
            "zaid_season": CROP_MARKET_PRICES.get(rotation_info['next_zaid'], {}).get('name', 'Mung Bean (Green Gram)'),
            "zaid_reason": rotation_info['zaid_reason']
        }

        # Genuine Real-Time 5-Day Weather Forecast via Open-Meteo High-Resolution NWP API
        live_weather_res = fetch_live_weather_forecast(district, state, dist_data)
        weather_forecast = live_weather_res["forecast"]
        weather_meta = {
            "is_live": live_weather_res.get("is_live", True),
            "provider": live_weather_res.get("provider", "Open-Meteo High-Resolution NWP (Live)"),
            "licensing": live_weather_res.get("licensing", "Open-Meteo (CC BY 4.0 - Free Non-Commercial Access)"),
            "district": district,
            "gps": live_weather_res.get("gps", ""),
            "current_temperature": live_weather_res.get("current_temperature", ""),
            "current_humidity": live_weather_res.get("current_humidity", ""),
            "last_updated": live_weather_res.get("last_updated", "")
        }

        # Farm Alerts
        alerts = []
        if dist_data['rainfall'] > 220:
            alerts.append({"type": "warning", "icon": "", "title": "Heavy Rain Alert", "text": "High seasonal rainfall predicted. Ensure field drainage channels are clear to prevent waterlogging."})
        elif dist_data['rainfall'] < 120:
            alerts.append({"type": "info", "icon": "", "title": "Irrigation Planning", "text": "Low rainfall area. Drip or sprinkler irrigation recommended for maximum yield efficiency."})

        if prev_crop in ['rice', 'cotton']:
            alerts.append({"type": "success", "icon": "", "title": "Soil Nitrogen Advisory", "text": f"Previous crop was {prev_crop.title()}. Rotating with pulses will naturally fix nitrogen for next season."})

        response_payload = {
            "success": True,
            "mode": "farmer",
            "district": district,
            "state": state,
            "location": f"{district}, {state}",
            "land_size": land_size,
            "land_unit": land_unit,
            "water_availability": water_avail,
            "previous_crop": prev_crop,
            "budget": farmer_budget,
            "farmer_budget": farmer_budget,
            "land_size_formatted": f"{land_size} {land_unit.title()} ({ha_size:.2f} Hectares / {acre_size:.2f} Acres)",
            "soil_profile": dist_data,
            "input_soil_climate": dist_data,
            "recommendations": recommendations,
            "crop_rotation": crop_rotation_plan,
            "weather_forecast": weather_forecast,
            "weather_meta": weather_meta,
            "alerts": alerts
        }

        # Persist to Enterprise Database (PostgreSQL / MySQL / SQLite)
        try:
            db_id = save_recommendation_to_db(data, response_payload)
            response_payload["saved_to_database"] = True
            response_payload["db_record_id"] = db_id
        except Exception as db_err:
            print(f"[Database Error]: {db_err}")
            response_payload["saved_to_database"] = False

        return jsonify(response_payload)

    except Exception as e:
        print("Error in farmer_recommend API:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_recommendation_history():
    """
    Enterprise Database API: Retrieve past farmer recommendation logs
    """
    limit = request.args.get('limit', default=10, type=int)
    district = request.args.get('district', default=None, type=str)
    history = get_recent_history(limit=limit, district=district)
    return jsonify({
        "success": True,
        "count": len(history),
        "history": history
    })

@app.route('/api/database-status', methods=['GET'])
def get_db_status():
    """
    Enterprise Database API: Check connection status, engine type, and record counts
    """
    return jsonify(get_database_status())

@app.route('/api/predict-crop', methods=['POST'])
def predict_crop_advanced():
    """
    Advanced Expert Mode API
    Full parameter control for N, P, K, pH, temp, humidity, rain, ndvi, and algorithm selection
    """
    try:
        data = request.get_json() or {}
        n = float(data.get('N', 90))
        p = float(data.get('P', 40))
        k = float(data.get('K', 40))
        temp = float(data.get('temperature', 26.5))
        hum = float(data.get('humidity', 75))
        ph = float(data.get('ph', 6.5))
        rain = float(data.get('rainfall', 200))
        model_choice = data.get('algorithm', 'rf').lower()

        features = np.array([[n, p, k, temp, hum, ph, rain]])

        if model_choice == 'svm':
            scaled_feat = scaler.transform(features)
            probs = svm_model.predict_proba(scaled_feat)[0]
            model_used_name = "Support Vector Machine (SVM)"
            acc_metric = metrics_data['crop_classification']['svm']['accuracy']
        elif model_choice == 'dnn':
            scaled_feat = scaler.transform(features)
            probs = dnn_model.predict_proba(scaled_feat)[0]
            model_used_name = "Deep Neural Network (DNN)"
            acc_metric = metrics_data['crop_classification']['deep_neural_network']['accuracy']
        else:
            probs = rf_model.predict_proba(features)[0]
            model_used_name = "Random Forest Classifier"
            acc_metric = metrics_data['crop_classification']['random_forest']['accuracy']

        sorted_indices = np.argsort(probs)[::-1]
        NON_SOUTH_INDIAN_CROPS = {'jute', 'apple'}
        valid_indices = [idx for idx in sorted_indices if label_encoder.classes_[idx].lower() not in NON_SOUTH_INDIAN_CROPS]
        top_indices = valid_indices[:5]
        
        results = []

        for idx in top_indices:
            crop_name = label_encoder.classes_[idx]
            prob = probs[idx]
            meta = CROP_MARKET_PRICES.get(crop_name, {"name": crop_name.title(), "price_per_ton": 30000})
            yield_meta = crop_yield_summary.get(crop_name, {"mean_yield": 3.8, "min_yield": 2.2, "max_yield": 5.5})
            
            results.append({
                "crop_key": crop_name,
                "crop_name": meta['name'],
                "probability": round(float(prob), 4),
                "confidence_percent": round(float(prob) * 100, 2),
                "estimated_yield_ha": f"{yield_meta['mean_yield']} t/ha ({yield_meta['min_yield']} - {yield_meta['max_yield']})"
            })

        return jsonify({
            "success": True,
            "mode": "expert",
            "model_used": model_used_name,
            "model_accuracy": f"{acc_metric * 100:.2f}%",
            "predictions": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    return jsonify(metrics_data)

if __name__ == '__main__':
    print("Launching AgriVision AI Server on http://localhost:5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
