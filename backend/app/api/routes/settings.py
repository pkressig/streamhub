from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.settings import AppSetting

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def get_all_settings(db: Session = Depends(get_db)):
    rows = db.query(AppSetting).all()
    return {r.key: r.value for r in rows}


@router.put("/{key}")
def put_setting(key: str, body: dict, db: Session = Depends(get_db)):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = body["value"]
    else:
        db.add(AppSetting(key=key, value=body["value"]))
    db.commit()
    return {"key": key, "value": body["value"]}
