"""
AgriVision AI - Enterprise Database Layer
Built with SQLAlchemy 2.0 ORM.
Supports PostgreSQL, MySQL, and SQLite via configurable DATABASE_URL.

Enterprise Models:
- User (Farmers, Agronomists, Admins with role-based access)
- FarmPlot (Georeferenced farm plots with soil type and water source)
- SoilTestReport (Laboratory soil NPK, pH, and organic carbon historical tracking)
- RecommendationHistory (Auditable log of all AI crop recommendations, yields, economics, and weather snapshots)
- ApmcPriceHistory (Historical and modal commodity prices per tonne)
"""

import os
import json
import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime, Date, ForeignKey, Index, Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session

# Database URL Configuration:
# - PostgreSQL: postgresql://user:password@localhost:5432/agrivision_db
# - MySQL: mysql+pymysql://user:password@localhost:3306/agrivision_db
# - Default Local Fallback: SQLite
DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agrivision_enterprise.db')
DATABASE_URL = os.environ.get('DATABASE_URL', f"sqlite:///{DEFAULT_SQLITE_PATH}")

# Fix Heroku/Render postgres:// prefix to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()


# ==============================================================================
# 1. USER & FARMER MODEL
# ==============================================================================
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=True, index=True)
    role = Column(String(30), default='farmer', nullable=False)  # 'farmer', 'agronomist', 'admin'
    state = Column(String(60), nullable=True)
    district = Column(String(60), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    farm_plots = relationship("FarmPlot", back_populates="owner", cascade="all, delete-orphan")
    recommendations = relationship("RecommendationHistory", back_populates="user")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "state": self.state,
            "district": self.district,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ==============================================================================
# 2. FARM PLOT MODEL
# ==============================================================================
class FarmPlot(Base):
    __tablename__ = 'farm_plots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    plot_name = Column(String(100), nullable=False)
    state = Column(String(60), nullable=False)
    district = Column(String(60), nullable=False, index=True)
    taluk = Column(String(60), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    land_size = Column(Float, nullable=False, default=2.0)
    land_unit = Column(String(20), default='acres', nullable=False)
    water_source = Column(String(60), default='Borewell')  # 'Borewell', 'Canal', 'Rainfed', 'Drip'
    soil_type = Column(String(60), default='Red Loamy')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="farm_plots")
    soil_tests = relationship("SoilTestReport", back_populates="plot", cascade="all, delete-orphan")
    recommendations = relationship("RecommendationHistory", back_populates="plot")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plot_name": self.plot_name,
            "state": self.state,
            "district": self.district,
            "land_size": self.land_size,
            "land_unit": self.land_unit,
            "water_source": self.water_source,
            "soil_type": self.soil_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ==============================================================================
# 3. SOIL TEST REPORT MODEL (Field Lab Tracking)
# ==============================================================================
class SoilTestReport(Base):
    __tablename__ = 'soil_test_reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plot_id = Column(Integer, ForeignKey('farm_plots.id', ondelete='CASCADE'), nullable=False, index=True)
    test_date = Column(Date, default=datetime.date.today, nullable=False)
    nitrogen_n = Column(Float, nullable=False)       # kg/ha
    phosphorus_p = Column(Float, nullable=False)     # kg/ha
    potassium_k = Column(Float, nullable=False)      # kg/ha
    ph = Column(Float, nullable=False)
    organic_carbon = Column(Float, nullable=True)    # %
    lab_name = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    plot = relationship("FarmPlot", back_populates="soil_tests")

    def to_dict(self):
        return {
            "id": self.id,
            "plot_id": self.plot_id,
            "test_date": self.test_date.isoformat() if self.test_date else None,
            "N": self.nitrogen_n,
            "P": self.phosphorus_p,
            "K": self.potassium_k,
            "ph": self.ph,
            "organic_carbon": self.organic_carbon,
            "lab_name": self.lab_name
        }


# ==============================================================================
# 4. RECOMMENDATION & ADVISORY AUDIT LOG MODEL
# ==============================================================================
class RecommendationHistory(Base):
    __tablename__ = 'recommendation_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    plot_id = Column(Integer, ForeignKey('farm_plots.id', ondelete='SET NULL'), nullable=True, index=True)
    state = Column(String(60), nullable=False)
    district = Column(String(60), nullable=False, index=True)
    season = Column(String(30), nullable=False)
    land_size = Column(Float, nullable=False)
    land_unit = Column(String(20), nullable=False)
    water_availability = Column(String(30), nullable=False)
    previous_crop = Column(String(60), nullable=True)
    recommended_crop = Column(String(60), nullable=False, index=True)
    crop_display_name = Column(String(100), nullable=False)
    confidence_score = Column(Float, nullable=False)
    model_used = Column(String(60), default='Random Forest Classifier')
    estimated_yield_tons = Column(Float, nullable=True)
    estimated_yield_range = Column(String(60), nullable=True)
    cultivation_cost_inr = Column(Float, nullable=True)
    gross_revenue_inr = Column(Float, nullable=True)
    net_profit_inr = Column(Float, nullable=True)
    roi_multiplier = Column(String(30), nullable=True)
    weather_temp = Column(String(30), nullable=True)
    weather_condition = Column(String(60), nullable=True)
    weather_provider = Column(String(100), nullable=True)
    weather_summary_json = Column(Text, nullable=True)
    crop_rotation_json = Column(Text, nullable=True)
    required_products_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="recommendations")
    plot = relationship("FarmPlot", back_populates="recommendations")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "district": self.district,
            "state": self.state,
            "season": self.season,
            "land_size": self.land_size,
            "land_unit": self.land_unit,
            "water_availability": self.water_availability,
            "previous_crop": self.previous_crop,
            "recommended_crop": self.recommended_crop,
            "crop_display_name": self.crop_display_name,
            "confidence_score": round(self.confidence_score, 2),
            "estimated_yield_tons": self.estimated_yield_tons,
            "estimated_yield_range": self.estimated_yield_range,
            "cultivation_cost_inr": f"Rs. {int(self.cultivation_cost_inr):,}" if self.cultivation_cost_inr else "N/A",
            "gross_revenue_inr": f"Rs. {int(self.gross_revenue_inr):,}" if self.gross_revenue_inr else "N/A",
            "net_profit_inr": f"Rs. {int(self.net_profit_inr):,}" if self.net_profit_inr else "N/A",
            "roi_multiplier": self.roi_multiplier,
            "weather_temp": self.weather_temp,
            "weather_condition": self.weather_condition,
            "weather_provider": self.weather_provider,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p") if self.created_at else None
        }


# ==============================================================================
# 5. APMC MANDI PRICE BENCHMARK MODEL
# ==============================================================================
class ApmcPriceHistory(Base):
    __tablename__ = 'apmc_price_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop = Column(String(60), nullable=False, index=True)
    state = Column(String(60), nullable=False)
    district = Column(String(60), nullable=True)
    modal_price_per_ton = Column(Float, nullable=False)
    min_price_per_ton = Column(Float, nullable=True)
    max_price_per_ton = Column(Float, nullable=True)
    record_date = Column(Date, default=datetime.date.today, nullable=False, index=True)
    source = Column(String(120), default='Agmarknet APMC Modal Price')

    def to_dict(self):
        return {
            "id": self.id,
            "crop": self.crop,
            "state": self.state,
            "district": self.district,
            "modal_price_per_ton": self.modal_price_per_ton,
            "record_date": self.record_date.isoformat() if self.record_date else None,
            "source": self.source
        }


# Add Indexes for Performance
Index('idx_rec_district_crop', RecommendationHistory.district, RecommendationHistory.recommended_crop)
Index('idx_rec_created', RecommendationHistory.created_at)


# ==============================================================================
# DATABASE SERVICE METHODS
# ==============================================================================
def init_db():
    """
    Initializes database schema (creates tables if they do not exist)
    and seeds standard demo farmer profile.
    """
    Base.metadata.create_all(bind=engine)
    
    # Seed standard test/demo user if table is empty
    session = SessionLocal()
    try:
        user_count = session.query(User).count()
        if user_count == 0:
            demo_user = User(
                username="karnataka_farmer",
                email="farmer@karnataka.gov.in",
                full_name="Basavaraj Patil",
                phone="+91 98450 12345",
                role="farmer",
                state="Karnataka",
                district="Mysuru"
            )
            session.add(demo_user)
            session.flush()

            demo_plot = FarmPlot(
                user_id=demo_user.id,
                plot_name="Cauvery Basin Parcel A",
                state="Karnataka",
                district="Mysuru",
                taluk="T. Narasipura",
                land_size=3.0,
                land_unit="acres",
                water_source="Canal & Borewell",
                soil_type="Red Sandy Loam"
            )
            session.add(demo_plot)
            session.flush()

            demo_soil = SoilTestReport(
                plot_id=demo_plot.id,
                test_date=datetime.date.today(),
                nitrogen_n=82.0,
                phosphorus_p=44.0,
                potassium_k=45.0,
                ph=6.7,
                organic_carbon=0.55,
                lab_name="District Soil Health Laboratory, Mysuru"
            )
            session.add(demo_soil)
            session.commit()
            print("[Database] Initialized tables and seeded demo farmer profile successfully.")
    except Exception as e:
        session.rollback()
        print(f"[Database] Initialization error: {e}")
    finally:
        session.close()


def save_recommendation_to_db(data, rec_result):
    """
    Persists a generated recommendation into the database.
    """
    session = SessionLocal()
    try:
        top_rec = rec_result.get('recommendations', [{}])[0]
        weather_meta = rec_result.get('weather_meta', {})
        forecast = rec_result.get('weather_forecast', [{}])
        first_day = forecast[0] if forecast else {}
        fm = top_rec.get('financial_margins', {})
        
        # Parse currency strings to numeric floats
        def parse_cost(val):
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                cleaned = val.replace('Rs.', '').replace('INR', '').replace(',', '').strip()
                try:
                    return float(cleaned)
                except Exception:
                    return 0.0
            return 0.0

        rec_entry = RecommendationHistory(
            state=data.get('state', 'Karnataka'),
            district=data.get('district', 'Mysuru'),
            season=data.get('season', 'Kharif'),
            land_size=float(data.get('land_size', 2.0)),
            land_unit=data.get('land_unit', 'acres'),
            water_availability=data.get('water_availability', 'Medium'),
            previous_crop=data.get('previous_crop', 'none'),
            recommended_crop=top_rec.get('crop_key', 'rice'),
            crop_display_name=top_rec.get('crop_display_name', 'Rice (Paddy)'),
            confidence_score=float(top_rec.get('confidence_percent', 95.0)),
            model_used=top_rec.get('model_used', 'Random Forest Classifier'),
            estimated_yield_tons=float(top_rec.get('estimated_harvest', {}).get('total_tons_avg', 0.0)),
            estimated_yield_range=top_rec.get('estimated_harvest', {}).get('harvest_range_tons', ''),
            cultivation_cost_inr=parse_cost(fm.get('cultivation_cost', 0)),
            gross_revenue_inr=parse_cost(fm.get('gross_revenue', 0)),
            net_profit_inr=parse_cost(fm.get('net_profit_range', 0)),
            roi_multiplier=fm.get('roi_multiplier', '1.0x'),
            weather_temp=weather_meta.get('current_temperature', first_day.get('temp', '28°C')),
            weather_condition=first_day.get('condition', 'Partly Cloudy'),
            weather_provider=weather_meta.get('provider', 'Open-Meteo High-Resolution NWP (Live)'),
            weather_summary_json=json.dumps(forecast[:3]),
            crop_rotation_json=json.dumps(rec_result.get('crop_rotation', {})),
            required_products_json=json.dumps(top_rec.get('required_products', {}))
        )

        session.add(rec_entry)
        session.commit()
        rec_id = rec_entry.id
        return rec_id
    except Exception as e:
        session.rollback()
        print(f"[Database] Failed to save recommendation: {e}")
        return None
    finally:
        session.close()


def get_recent_history(limit=10, district=None):
    """
    Retrieves recent recommendation records.
    """
    session = SessionLocal()
    try:
        query = session.query(RecommendationHistory).order_by(RecommendationHistory.created_at.desc())
        if district:
            query = query.filter(RecommendationHistory.district == district)
        records = query.limit(limit).all()
        return [r.to_dict() for r in records]
    except Exception as e:
        print(f"[Database] Failed to fetch history: {e}")
        return []
    finally:
        session.close()


def get_database_status():
    """
    Returns engine metadata, connection status, and table record counts.
    """
    session = SessionLocal()
    try:
        user_cnt = session.query(User).count()
        plot_cnt = session.query(FarmPlot).count()
        soil_cnt = session.query(SoilTestReport).count()
        rec_cnt = session.query(RecommendationHistory).count()
        
        db_name = engine.url.database or "agrivision_enterprise.db"
        dialect = engine.url.get_backend_name().upper()

        return {
            "status": "connected",
            "dialect": dialect,
            "database_name": db_name,
            "database_url_masked": f"{dialect.lower()}://***@{engine.url.host or 'localhost'}/{db_name}",
            "tables": {
                "users": user_cnt,
                "farm_plots": plot_cnt,
                "soil_test_reports": soil_cnt,
                "recommendation_history": rec_cnt
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        session.close()
