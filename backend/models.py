from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    battery_kwh = Column(Float, nullable=False)
    consumption_km_per_soc = Column(Float, nullable=False)  # km per 1% SOC
    charge_rate_soc_per_min = Column(Float, nullable=False) # % per minute

class Query(Base):
    __tablename__ = "queries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, server_default=func.now())
    start_lon = Column(Float); start_lat = Column(Float)
    end_lon = Column(Float);   end_lat = Column(Float)
    start_soc = Column(Float); arrival_soc = Column(Float)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("queries.id"))
    plan_type = Column(String(32))  # fastest / cheapest
    total_time_min = Column(Float)
    total_cost_eur = Column(Float)
    route_geojson = Column(JSON)
    steps = Column(JSON)

class StationCache(Base):
    __tablename__ = "stations_cache"
    ocm_id = Column(Integer, primary_key=True)
    name = Column(String(255))
    lon = Column(Float); lat = Column(Float)
    power_kw = Column(Float)
    last_seen_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    raw = Column(JSON)
