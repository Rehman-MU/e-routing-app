import random
from db import Base, engine, SessionLocal
from models import Vehicle

def run():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    if db.query(Vehicle).count() == 0:
        for i in range(1, 6):
            v = Vehicle(
                name=f"EV-{i}",
                battery_kwh=random.choice([55, 64, 70, 77, 82]),
                consumption_km_per_soc=random.uniform(4.0, 8.0),    # km per 1% SOC
                charge_rate_soc_per_min=random.uniform(1.0, 3.0),  # % per min
            )
            db.add(v)
        db.commit()
        print("Seeded 5 vehicles.")
    else:
        print("Vehicles already present.")
    db.close()

if __name__ == "__main__":
    run()
