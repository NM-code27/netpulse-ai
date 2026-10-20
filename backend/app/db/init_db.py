from app.db.session import Base, engine, SessionLocal
from app.db.models import Entity
from app.data.topology_seed import TOPOLOGY


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Entity).count() > 0:
            return
        for e in TOPOLOGY["entities"]:
            extra = {k: v for k, v in e.items() if k not in {"id", "type", "name", "region", "tier", "parent_id"}}
            db.add(Entity(
                id=e["id"], type=e["type"], name=e["name"],
                region=e.get("region"), tier=e.get("tier"),
                parent_id=e.get("parent_id"), extra=extra,
            ))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized and topology seeded.")
