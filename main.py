
from __future__ import annotations
import hashlib
import io
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{APP_DIR / 'data.db'}"
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI(title="Arazi Takip V3 Güvenli Düzenle/Sil", version="3.2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

USERS = {
    "muhendis1": {"password_hash": sha256("1234"), "name": "Mühendis 1", "role": "engineer"},
    "muhendis2": {"password_hash": sha256("1234"), "name": "Mühendis 2", "role": "engineer"},
    "ofis": {"password_hash": sha256("1234"), "name": "Ofis", "role": "office"},
}
SESSIONS: dict[str, dict] = {}

class Base(DeclarativeBase):
    pass

class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_name: Mapped[str] = mapped_column(String(200))
    district: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Greenhouse(Base):
    __tablename__ = "greenhouses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    greenhouse_name: Mapped[str] = mapped_column(String(200))
    crop_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    area_decare: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    map_lat: Mapped[float] = mapped_column(Float)
    map_lon: Mapped[float] = mapped_column(Float)
    status_color: Mapped[str] = mapped_column(String(20), default="blue")
    critical_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    critical_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_visit_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Visit(Base):
    __tablename__ = "visits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    greenhouse_id: Mapped[int] = mapped_column(ForeignKey("greenhouses.id"))
    username: Mapped[str] = mapped_column(String(80))
    visit_date: Mapped[str] = mapped_column(String(20))
    visit_start_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    visit_end_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    visit_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    weather_temp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    weather_humidity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    visit_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    visit_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_temp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    soil_moisture: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    soil_ec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phenology_stage: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    diagnosis_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fertilization_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spraying_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class VisitPhoto(Base):
    __tablename__ = "visit_photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"))
    file_path: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

def seed():
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Business)) == 0:
            b1 = Business(business_name="ABC Tarım", district="Elmalı", contact_name="Ali Yılmaz", phone="05000000000")
            b2 = Business(business_name="Bereket Sera", district="Kumluca", contact_name="Mehmet Demir", phone="05000000001")
            db.add_all([b1, b2]); db.flush()
            db.add_all([
                Greenhouse(business_id=b1.id, greenhouse_name="Sera 1", crop_name="Domates", area_decare=4.5, map_lat=36.54, map_lon=30.01, status_color="orange"),
                Greenhouse(business_id=b1.id, greenhouse_name="Sera 2", crop_name="Biber", area_decare=3.2, map_lat=36.57, map_lon=30.10, status_color="green"),
                Greenhouse(business_id=b2.id, greenhouse_name="Blok A", crop_name="Domates", area_decare=6.0, map_lat=36.31, map_lon=30.29, status_color="red", critical_flag=True, critical_note="Kritik sera notu"),
            ])
            db.commit()
seed()

def require_user(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Oturum gerekli")
    token = authorization.split(" ", 1)[1]
    user = SESSIONS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz oturum")
    return user

class LoginIn(BaseModel):
    username: str
    password: str
class BusinessIn(BaseModel):
    business_name: str
    district: Optional[str] = ""
    contact_name: Optional[str] = ""
    phone: Optional[str] = ""
    notes: Optional[str] = ""
class BusinessUpdateIn(BaseModel):
    business_name: Optional[str] = ""
    district: Optional[str] = ""
    contact_name: Optional[str] = ""
    phone: Optional[str] = ""
    notes: Optional[str] = ""
class GreenhouseIn(BaseModel):
    business_id: int
    greenhouse_name: str
    crop_name: Optional[str] = ""
    area_decare: Optional[float] = 0
    map_lat: float
    map_lon: float
class GreenhouseUpdateIn(BaseModel):
    greenhouse_name: Optional[str] = ""
    crop_name: Optional[str] = ""
    area_decare: Optional[float] = None
    critical_flag: Optional[bool] = None
class VisitStartIn(BaseModel):
    business_id: int
    greenhouse_id: int
    recipient_email: Optional[str] = ""
    visit_lat: Optional[float] = None
    visit_lon: Optional[float] = None
class VisitUpdateIn(BaseModel):
    soil_temp: Optional[str] = ""
    soil_moisture: Optional[str] = ""
    soil_ec: Optional[str] = ""
    phenology_stage: Optional[str] = ""
    diagnosis_notes: Optional[str] = ""
    fertilization_text: Optional[str] = ""
    spraying_text: Optional[str] = ""
    weather_temp: Optional[str] = ""
    weather_humidity: Optional[str] = ""
    visit_lat: Optional[float] = None
    visit_lon: Optional[float] = None

@app.get("/", response_class=HTMLResponse)
def root():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post("/api/login")
def login(data: LoginIn):
    user = USERS.get(data.username)
    if not user or user["password_hash"] != sha256(data.password):
        raise HTTPException(status_code=401, detail="Hatalı kullanıcı adı / şifre")
    token = secrets.token_urlsafe(32)
    session = {"username": data.username, "name": user["name"], "role": user["role"]}
    SESSIONS[token] = session
    return {"token": token, "user": session}

@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    token = authorization.split(" ", 1)[1]
    SESSIONS.pop(token, None)
    return {"ok": True}

@app.get("/api/me")
def me(authorization: Optional[str] = Header(default=None)):
    return {"user": require_user(authorization)}

@app.get("/api/businesses")
def list_businesses(authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        rows = db.scalars(select(Business).order_by(Business.id.desc())).all()
        return [{"id": r.id, "business_name": r.business_name, "district": r.district, "contact_name": r.contact_name, "phone": r.phone, "notes": r.notes} for r in rows]

@app.post("/api/businesses")
def create_business(data: BusinessIn, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        row = Business(business_name=data.business_name, district=data.district, contact_name=data.contact_name, phone=data.phone, notes=data.notes)
        db.add(row); db.commit(); db.refresh(row)
        return {"id": row.id}

@app.patch("/api/businesses/{business_id}")
def update_business(business_id: int, data: BusinessUpdateIn, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        row = db.get(Business, business_id)
        if not row:
            raise HTTPException(status_code=404, detail="İşletme bulunamadı")
        row.business_name = data.business_name or row.business_name
        row.district = data.district if data.district is not None else row.district
        row.contact_name = data.contact_name if data.contact_name is not None else row.contact_name
        row.phone = data.phone if data.phone is not None else row.phone
        row.notes = data.notes if data.notes is not None else row.notes
        db.commit()
        return {"ok": True}

@app.delete("/api/businesses/{business_id}")
def delete_business(business_id: int, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        greenhouses = db.scalars(select(Greenhouse).where(Greenhouse.business_id == business_id)).all()
        for g in greenhouses:
            visits = db.scalars(select(Visit).where(Visit.greenhouse_id == g.id)).all()
            for v in visits:
                photos = db.scalars(select(VisitPhoto).where(VisitPhoto.visit_id == v.id)).all()
                for p in photos:
                    db.delete(p)
                db.delete(v)
            db.delete(g)
        row = db.get(Business, business_id)
        if row:
            db.delete(row)
        db.commit()
        return {"ok": True}

@app.get("/api/greenhouses")
def list_greenhouses(authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        rows = db.scalars(select(Greenhouse).order_by(Greenhouse.id.desc())).all()
        businesses = {b.id: b.business_name for b in db.scalars(select(Business)).all()}
        return [{
            "id": g.id,
            "business_id": g.business_id,
            "business_name": businesses.get(g.business_id, ""),
            "greenhouse_name": g.greenhouse_name,
            "crop_name": g.crop_name,
            "area_decare": g.area_decare,
            "lat": g.map_lat,
            "lon": g.map_lon,
            "status": {"blue":"registered","orange":"visited","green":"active","red":"critical"}.get(g.status_color, "registered"),
            "critical_flag": g.critical_flag
        } for g in rows]

@app.post("/api/greenhouses")
def create_greenhouse(data: GreenhouseIn, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        row = Greenhouse(business_id=data.business_id, greenhouse_name=data.greenhouse_name, crop_name=data.crop_name, area_decare=data.area_decare, map_lat=data.map_lat, map_lon=data.map_lon, status_color="blue")
        db.add(row); db.commit(); db.refresh(row)
        return {"id": row.id}

@app.patch("/api/greenhouses/{greenhouse_id}")
def update_greenhouse(greenhouse_id: int, data: GreenhouseUpdateIn, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        row = db.get(Greenhouse, greenhouse_id)
        if not row:
            raise HTTPException(status_code=404, detail="Sera bulunamadı")
        row.greenhouse_name = data.greenhouse_name or row.greenhouse_name
        if data.crop_name is not None:
            row.crop_name = data.crop_name
        if data.area_decare is not None:
            row.area_decare = data.area_decare
        if data.critical_flag is not None:
            row.critical_flag = data.critical_flag
            row.status_color = "red" if data.critical_flag else row.status_color
        db.commit()
        return {"ok": True}

@app.delete("/api/greenhouses/{greenhouse_id}")
def delete_greenhouse(greenhouse_id: int, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        visits = db.scalars(select(Visit).where(Visit.greenhouse_id == greenhouse_id)).all()
        for v in visits:
            photos = db.scalars(select(VisitPhoto).where(VisitPhoto.visit_id == v.id)).all()
            for p in photos:
                db.delete(p)
            db.delete(v)
        row = db.get(Greenhouse, greenhouse_id)
        if row:
            db.delete(row)
        db.commit()
        return {"ok": True}

@app.get("/api/greenhouses/{greenhouse_id}/navigation")
def navigation_links(greenhouse_id: int, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        g = db.get(Greenhouse, greenhouse_id)
        if not g:
            raise HTTPException(status_code=404, detail="Sera bulunamadı")
        return {"apple_maps": f"https://maps.apple.com/?daddr={g.map_lat},{g.map_lon}", "google_maps": f"https://www.google.com/maps/dir/?api=1&destination={g.map_lat},{g.map_lon}"}

@app.get("/api/greenhouses/{greenhouse_id}/latest-visit")
def latest_visit(greenhouse_id: int, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        v = db.scalars(select(Visit).where(Visit.greenhouse_id == greenhouse_id).order_by(Visit.id.desc()).limit(1)).first()
        if not v:
            return {"has_visit": False}
        return {
            "has_visit": True,
            "visit_id": v.id,
            "visit_date": v.visit_date,
            "username": v.username,
            "visit_status": v.visit_status,
            "weather_temp": v.weather_temp,
            "weather_humidity": v.weather_humidity,
            "soil_temp": v.soil_temp,
            "soil_moisture": v.soil_moisture,
            "soil_ec": v.soil_ec,
            "diagnosis_notes": v.diagnosis_notes,
            "fertilization_text": v.fertilization_text,
            "spraying_text": v.spraying_text,
        }

@app.get("/api/weather")
def get_weather(lat: float, lon: float, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&timezone=auto", timeout=12)
        c = r.json().get("current", {})
        return {"temperature": c.get("temperature_2m"), "humidity": c.get("relative_humidity_2m"), "source":"open-meteo"}
    except Exception:
        return {"temperature": None, "humidity": None, "source":"unavailable"}

@app.post("/api/visits/start")
def start_visit(data: VisitStartIn, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with SessionLocal() as db:
        now = datetime.utcnow()
        v = Visit(business_id=data.business_id, greenhouse_id=data.greenhouse_id, username=user["username"], visit_date=date.today().isoformat(), visit_start_at=now, visit_status="active", recipient_email=data.recipient_email, visit_lat=data.visit_lat, visit_lon=data.visit_lon)
        db.add(v)
        g = db.get(Greenhouse, data.greenhouse_id)
        if g:
            g.status_color = "green"
            g.last_visit_at = now
        db.commit(); db.refresh(v)
        return {"id": v.id}

@app.patch("/api/visits/{visit_id}")
def update_visit(visit_id: int, data: VisitUpdateIn, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        v = db.get(Visit, visit_id)
        if not v:
            raise HTTPException(status_code=404, detail="Ziyaret bulunamadı")
        for k in ["soil_temp","soil_moisture","soil_ec","phenology_stage","diagnosis_notes","fertilization_text","spraying_text","weather_temp","weather_humidity","visit_lat","visit_lon"]:
            setattr(v, k, getattr(data, k))
        db.commit()
        return {"ok": True}

@app.post("/api/visits/{visit_id}/complete")
def complete_visit(visit_id: int, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        v = db.get(Visit, visit_id)
        if not v:
            raise HTTPException(status_code=404, detail="Ziyaret bulunamadı")
        v.visit_status = "completed"
        v.visit_end_at = datetime.utcnow()
        g = db.get(Greenhouse, v.greenhouse_id)
        if g:
            g.status_color = "red" if g.critical_flag else "orange"
            g.last_visit_at = datetime.utcnow()
        db.commit()
        return {"ok": True}

@app.post("/api/visits/{visit_id}/photos")
def upload_photo(visit_id: int, file: UploadFile = File(...), authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    suffix = Path(file.filename or "photo.jpg").suffix or ".jpg"
    filename = f"visit_{visit_id}_{int(datetime.utcnow().timestamp())}{suffix}"
    target = UPLOAD_DIR / filename
    target.write_bytes(file.file.read())
    with SessionLocal() as db:
        p = VisitPhoto(visit_id=visit_id, file_path=f"/uploads/{filename}")
        db.add(p); db.commit(); db.refresh(p)
        return {"id": p.id, "url": p.file_path}

@app.get("/api/dashboard")
def dashboard(authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        total_businesses = db.scalar(select(func.count()).select_from(Business)) or 0
        total_greenhouses = db.scalar(select(func.count()).select_from(Greenhouse)) or 0
        active_visits = db.scalar(select(func.count()).select_from(Visit).where(Visit.visit_status=="active")) or 0
        completed_today = db.scalar(select(func.count()).select_from(Visit).where(Visit.visit_status=="completed", Visit.visit_date==date.today().isoformat())) or 0
        critical = db.scalar(select(func.count()).select_from(Greenhouse).where(Greenhouse.critical_flag == True)) or 0
        business_map = {b.id: b.business_name for b in db.scalars(select(Business)).all()}
        gh_map = {g.id: g.greenhouse_name for g in db.scalars(select(Greenhouse)).all()}
        recent = db.scalars(select(Visit).order_by(Visit.id.desc()).limit(10)).all()
        return {"total_businesses":total_businesses,"total_greenhouses":total_greenhouses,"active_visits":active_visits,"completed_today":completed_today,"critical_greenhouses":critical,"recent_visits":[{"id":v.id,"username":v.username,"visit_status":v.visit_status,"visit_date":v.visit_date,"business_name":business_map.get(v.business_id,""),"greenhouse_name":gh_map.get(v.greenhouse_id,"")} for v in recent]}

@app.get("/api/analytics/greenhouse/{greenhouse_id}")
def greenhouse_analytics(greenhouse_id: int, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        rows = db.scalars(select(Visit).where(Visit.greenhouse_id == greenhouse_id).order_by(Visit.id.asc())).all()
        def conv(x):
            try: return float(x)
            except: return None
        return {"labels":[r.visit_date for r in rows],"soil_temp":[conv(r.soil_temp) for r in rows],"soil_moisture":[conv(r.soil_moisture) for r in rows],"soil_ec":[conv(r.soil_ec) for r in rows]}

@app.get("/api/reports/daily/excel")
def daily_excel(authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        rows = db.scalars(select(Visit).where(Visit.visit_date == date.today().isoformat()).order_by(Visit.id.desc())).all()
        wb = Workbook(); ws = wb.active; ws.title = "Gunluk Rapor"
        ws.append(["Tarih","Mühendis","İşletme","Sera","Hava","Toprak Sıcaklığı","Toprak Nemi","EC","Gübreleme","İlaçlama","Not"])
        business_map = {b.id: b.business_name for b in db.scalars(select(Business)).all()}
        gh_map = {g.id: g.greenhouse_name for g in db.scalars(select(Greenhouse)).all()}
        for v in rows:
            ws.append([v.visit_date, v.username, business_map.get(v.business_id,""), gh_map.get(v.greenhouse_id,""), f"{v.weather_temp or ''} / {v.weather_humidity or ''}", v.soil_temp or "", v.soil_moisture or "", v.soil_ec or "", v.fertilization_text or "", v.spraying_text or "", v.diagnosis_notes or ""])
        output = io.BytesIO(); wb.save(output); output.seek(0)
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="gunluk_rapor.xlsx"'})

@app.get("/api/reports/visit/{visit_id}/pdf")
def visit_pdf(visit_id: int, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    with SessionLocal() as db:
        v = db.get(Visit, visit_id)
        if not v:
            raise HTTPException(status_code=404, detail="Ziyaret bulunamadı")
        business = db.get(Business, v.business_id)
        greenhouse = db.get(Greenhouse, v.greenhouse_id)
        out = io.BytesIO(); doc = SimpleDocTemplate(out, pagesize=A4); styles = getSampleStyleSheet()
        story = [Paragraph("Arazi Takip Ziyaret Raporu", styles["Title"]), Spacer(1,12)]
        data = [["Tarih", v.visit_date],["Mühendis",v.username],["İşletme", business.business_name if business else ""],["Sera", greenhouse.greenhouse_name if greenhouse else ""],["Hava", f"{v.weather_temp or ''} / {v.weather_humidity or ''}"],["Toprak Sıcaklığı", v.soil_temp or ""],["Toprak Nemi", v.soil_moisture or ""],["EC", v.soil_ec or ""]]
        t = Table(data, colWidths=[160,320]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.lightgreen),("GRID",(0,0),(-1,-1),0.4,colors.grey),("PADDING",(0,0),(-1,-1),6)]))
        story += [t, Spacer(1,12), Paragraph("Gübreleme Programı", styles["Heading2"]), Paragraph((v.fertilization_text or "-").replace("\n","<br/>"), styles["BodyText"]), Spacer(1,8), Paragraph("İlaçlama Programı", styles["Heading2"]), Paragraph((v.spraying_text or "-").replace("\n","<br/>"), styles["BodyText"]), Spacer(1,8), Paragraph("Teşhis / Gözlem", styles["Heading2"]), Paragraph((v.diagnosis_notes or "-").replace("\n","<br/>"), styles["BodyText"])]
        doc.build(story); out.seek(0)
        return StreamingResponse(out, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename=\"ziyaret_{visit_id}.pdf\"'})



# --- V4 EKLEMELERI ---
class PasswordChange(BaseModel):
    username: str
    old_password: str
    new_password: str

@app.post("/change_password")
def change_password(data: PasswordChange):
    user = USERS.get(data.username)
    if not user:
        raise HTTPException(404,"user not found")
    if user["password_hash"] != sha256(data.old_password):
        raise HTTPException(403,"wrong password")
    USERS[data.username]["password_hash"] = sha256(data.new_password)
    return {"status":"ok"}
