"""SQLAlchemy database models for GreenGate."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


class User(Base):
    """MSME user account model."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    gstin = Column(String, nullable=True)
    iec_number = Column(String, nullable=True)
    state = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    scale = Column(String, nullable=True)
    location = Column(String, nullable=True)
    energy_source = Column(String, nullable=True)
    production_type = Column(String, nullable=True)
    exports_to_eu = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    reports = relationship("CarbonReport", back_populates="user")
    products = relationship("Product", back_populates="user")


class CarbonReport(Base):
    """Carbon compliance report model."""

    __tablename__ = "carbon_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    report_id = Column(String, unique=True, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    state = Column(String, nullable=False)
    annual_production_tonnes = Column(Float, nullable=False)
    eu_export_tonnes = Column(Float, nullable=False)
    total_co2_tonnes = Column(Float, nullable=False)
    scope1_co2_tonnes = Column(Float, nullable=False)
    scope2_co2_tonnes = Column(Float, nullable=False)
    co2_per_tonne_product = Column(Float, nullable=False)
    eu_embedded_co2_tonnes = Column(Float, nullable=False)
    cbam_liability_eur = Column(Float, nullable=False)
    cbam_liability_inr = Column(Float, nullable=False)
    vs_benchmark_pct = Column(Float, nullable=False)
    expected_energy = Column(Float, nullable=True)
    deviation_ratio = Column(Float, nullable=True)
    credibility_score = Column(Float, nullable=True)
    verification_status = Column(String, nullable=True)
    machinery_score = Column(Float, nullable=True)
    regional_energy_score = Column(Float, nullable=True)
    temporal_score = Column(Float, nullable=True)
    scope3_emissions = Column(Float, nullable=True)
    scope3_breakdown = Column(Text, nullable=True)
    estimated_emissions = Column(Float, nullable=True)
    twin_consistency_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    requires_evidence = Column(Boolean, default=False)
    evidence_files = Column(Text, nullable=True)
    verification_notes = Column(Text, nullable=True)
    full_input_json = Column(Text, nullable=True)
    full_output_json = Column(Text, nullable=True)
    recommendations_json = Column(Text, nullable=True)
    report_hash = Column(String, nullable=True)
    tx_hash = Column(String, nullable=True)
    block_number = Column(Integer, nullable=True)
    polygonscan_url = Column(String, nullable=True)
    is_blockchain_certified = Column(Boolean, default=False)
    blockchain_verified_at = Column(DateTime, nullable=True)
    blockchain_note = Column(Text, nullable=True)
    hash_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="reports")


class IndustryBenchmark(Base):
    """Curated hybrid benchmark dataset row for similarity-based matching."""

    __tablename__ = "industry_benchmarks"
    __table_args__ = (
        UniqueConstraint(
            "industry",
            "machinery_type",
            "energy_source",
            "scale",
            "region",
            name="uq_industry_benchmark_identity",
        ),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    industry = Column(String, nullable=False, index=True)
    machinery_type = Column(String, nullable=False, index=True)
    energy_source = Column(String, nullable=False, index=True)
    scale = Column(String, nullable=False, index=True)
    avg_intensity = Column(Float, nullable=False)
    best_in_class = Column(Float, nullable=False)
    region = Column(String, nullable=False, default="India", index=True)
    source = Column(String, nullable=False, default="curated")
    confidence = Column(String, nullable=False, default="medium")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CompanyProfile(Base):
    """Discovered company intelligence profile from external web sources."""

    __tablename__ = "company_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_name = Column(String, nullable=False, index=True)
    scraped_summary = Column(Text, nullable=True)
    factory_location = Column(String, nullable=True)
    estimated_production = Column(String, nullable=True)
    likely_machinery = Column(Text, nullable=True)
    export_markets = Column(Text, nullable=True)
    sources = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Product(Base):
    """Product-level supply chain discovery entity."""

    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_by = Column(String, nullable=True)
    product_name = Column(String, nullable=False, index=True)
    sector = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="products")
    nodes = relationship("SupplyChainNode", back_populates="product", cascade="all, delete-orphan")
    edges = relationship("SupplyChainEdge", back_populates="product", cascade="all, delete-orphan")
    carbon_report = relationship(
        "ProductCarbonReport",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SupplyChainNode(Base):
    """Node in a discovered product supply chain graph."""

    __tablename__ = "supply_chain_nodes"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    role = Column(String, nullable=False)
    location = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    discovered_source = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="nodes")
    factory_profile = relationship(
        "FactoryProfile",
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SupplyChainEdge(Base):
    """Directed edge between two supply chain nodes."""

    __tablename__ = "supply_chain_edges"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    from_node_id = Column(String, ForeignKey("supply_chain_nodes.id"), nullable=False)
    to_node_id = Column(String, ForeignKey("supply_chain_nodes.id"), nullable=False)
    relation = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="edges")


class FactoryProfile(Base):
    """Intelligence profile for a discovered factory node."""

    __tablename__ = "factory_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    node_id = Column(String, ForeignKey("supply_chain_nodes.id"), nullable=False, unique=True, index=True)
    company_name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    machinery_type = Column(String, nullable=True)
    production_capacity = Column(Float, nullable=True)
    energy_sources = Column(Text, nullable=True)
    scraped_sources = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    node = relationship("SupplyChainNode", back_populates="factory_profile")
    carbon_report = relationship(
        "FactoryCarbonReport",
        back_populates="factory_profile",
        uselist=False,
        cascade="all, delete-orphan",
    )


class FactoryCarbonReport(Base):
    """Verified carbon report generated for a specific factory profile."""

    __tablename__ = "factory_carbon_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    factory_profile_id = Column(
        String,
        ForeignKey("factory_profiles.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    scope1_emissions = Column(Float, nullable=False, default=0.0)
    scope2_emissions = Column(Float, nullable=False, default=0.0)
    scope3_emissions = Column(Float, nullable=False, default=0.0)
    total_emissions = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=True)
    verification_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    factory_profile = relationship("FactoryProfile", back_populates="carbon_report")


class ProductCarbonReport(Base):
    """Aggregated product-level carbon certificate from all factory emissions."""

    __tablename__ = "product_carbon_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, unique=True, index=True)
    scope1_total = Column(Float, nullable=False, default=0.0)
    scope2_total = Column(Float, nullable=False, default=0.0)
    scope3_total = Column(Float, nullable=False, default=0.0)
    total_emissions = Column(Float, nullable=False, default=0.0)
    emission_intensity = Column(Float, nullable=True)
    product_confidence = Column(Float, nullable=True)
    eu_benchmark = Column(Float, nullable=True)
    cbam_risk = Column(String, nullable=True)
    cbam_tax_per_ton = Column(Float, nullable=True)
    excess_emissions = Column(Float, nullable=True)
    factory_count = Column(Integer, nullable=False, default=0)
    product_quantity = Column(Float, nullable=True, default=1000.0)
    report_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    product = relationship("Product", back_populates="carbon_report")
