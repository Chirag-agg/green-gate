"""Script to seed top Indian Tier-1 material suppliers into the GreenGate database."""

import json
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, CompanyProfile, FactoryCarbonReport

# Ensure tables exist
Base.metadata.create_all(bind=engine)

TOP_SUPPLIERS = [
    {
        "company_name": "Tata Steel",
        "factory_location": "Jamshedpur, Jharkhand",
        "estimated_production": "12 Million Tonnes/Year",
        "likely_machinery": "Blast Furnace, Basic Oxygen Furnace",
        "export_markets": "Europe, Asia, Middle East",
        "sources": "Tata Steel Integrated Report 2023-24",
        "scope1": 2.2, # tonnes CO2 per tonne steel
        "scope2": 0.4,
        "scope3": 0.3,
        "verification_status": "Verified Target",
        "confidence": 0.95
    },
    {
        "company_name": "JSW Steel",
        "factory_location": "Vijayanagar, Karnataka",
        "estimated_production": "18 Million Tonnes/Year",
        "likely_machinery": "Blast Furnace, Corex",
        "export_markets": "Europe, USA, Middle East",
        "sources": "JSW Steel Sustainability Report 2023",
        "scope1": 2.3,
        "scope2": 0.35,
        "scope3": 0.3,
        "verification_status": "Verified Target",
        "confidence": 0.90
    },
    {
        "company_name": "SAIL",
        "factory_location": "Bhilai, Chhattisgarh",
        "estimated_production": "3.1 Million Tonnes/Year",
        "likely_machinery": "Blast Furnace",
        "export_markets": "Asia",
        "sources": "SAIL Annual Report 2023",
        "scope1": 2.5,
        "scope2": 0.3,
        "scope3": 0.2,
        "verification_status": "Estimated",
        "confidence": 0.85
    },
    {
        "company_name": "Hindalco",
        "factory_location": "Renukoot, Uttar Pradesh",
        "estimated_production": "345,000 Tonnes/Year (Aluminium)",
        "likely_machinery": "Smelter, Captive Power Plant",
        "export_markets": "Europe, Asia, Americas",
        "sources": "Hindalco ESG Report 2023",
        "scope1": 13.5, # High due to captive coal
        "scope2": 0.5,
        "scope3": 2.1,
        "verification_status": "Verified Target",
        "confidence": 0.92
    },
     {
        "company_name": "Vedanta",
        "factory_location": "Jharsuguda, Odisha",
        "estimated_production": "1.75 Million Tonnes/Year (Aluminium)",
        "likely_machinery": "Smelter, Captive Power Plant",
        "export_markets": "Global",
        "sources": "Vedanta Sustainability Report 2023",
        "scope1": 14.2,
        "scope2": 0.4,
        "scope3": 1.9,
        "verification_status": "Verified Target",
        "confidence": 0.90
    },
    {
        "company_name": "NALCO",
        "factory_location": "Angul, Odisha",
        "estimated_production": "460,000 Tonnes/Year (Aluminium)",
        "likely_machinery": "Smelter",
        "export_markets": "Asia, Europe",
        "sources": "NALCO Annual Report 2023",
        "scope1": 13.8,
        "scope2": 0.4,
        "scope3": 1.8,
        "verification_status": "Estimated",
        "confidence": 0.88
    },
    {
        "company_name": "UltraTech Cement",
        "factory_location": "Multiple, India",
        "estimated_production": "130 Million Tonnes/Year",
        "likely_machinery": "Rotary Kiln",
        "export_markets": "Middle East, Asia",
        "sources": "UltraTech Sustainability Report 2023",
        "scope1": 0.55,
        "scope2": 0.05,
        "scope3": 0.1,
        "verification_status": "Verified Target",
        "confidence": 0.95
    },
     {
        "company_name": "Ambuja Cements",
        "factory_location": "Multiple, India",
        "estimated_production": "31 Million Tonnes/Year",
        "likely_machinery": "Rotary Kiln",
        "export_markets": "Asia",
        "sources": "Ambuja Cements Sustainable Development Report 2023",
        "scope1": 0.52,
        "scope2": 0.04,
        "scope3": 0.09,
        "verification_status": "Verified Target",
        "confidence": 0.93
    }
]

def seed_database():
    db: Session = SessionLocal()
    try:
        print("Seeding Top Indian Tier-1 Suppliers into Database...")
        seeded_count = 0
        
        for data in TOP_SUPPLIERS:
            # Check if exists
            existing = db.query(CompanyProfile).filter(
                CompanyProfile.company_name == data["company_name"]
            ).first()
            
            if existing:
                print(f"  - {data['company_name']} already exists in CompanyProfile. Skipping.")
                continue
                
            # Create Company Profile
            profile = CompanyProfile(
                company_name=data["company_name"],
                scraped_summary=f"Trusted supplier intelligence seeded from: {data['sources']}",
                factory_location=data["factory_location"],
                estimated_production=data["estimated_production"],
                likely_machinery=data["likely_machinery"],
                export_markets=data["export_markets"],
                sources=data["sources"]
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
            # Since we can't seed FactoryCarbonReport directly without a linked SupplyChainNode, 
            # we will rely on our intelligence service to pull from CompanyProfile when these MSMEs 
            # declare them.
            
            print(f"  + Seeded Company Profile for: {data['company_name']}")
            seeded_count += 1
            
        print(f"Seeding complete. Added {seeded_count} suppliers.")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
