
from __future__ import annotations
import io
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, File, HTTPException, UploadFile
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

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{APP_DIR / 'data.db'}")
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI(title="Arazi Takip V3", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USERS = {
    "muhendis1": {"password": "1234", "name": "Mühendis 1", "role": "engineer"},
    "muhendis2": {"password": "1234", "name": "Mühendis 2", "role": "engineer"},
    "ofis": {"password": "1234", "name": "Ofis", "role": "office"},
}

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
    greenhouses: Mapped[list["Greenhouse"]] = relationship(back_populates="business")

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
    business: Mapped[Business] = relationship(back_populates="greenhouses")
    visits: Mapped[list["Visit"]] = relationship(back_populates="greenhouse")

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
    weather_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
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
    greenhouse: Mapped[Greenhouse] = relationship(back_populates="visits")
    photos: Mapped[list["VisitPhoto"]] = relationship(back_populates="visit")

class VisitPhoto(Base):
    __tablename__ = "visit_photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"))
    file_path: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    visit: Mapped[Visit] = relationship(back_populates="photos")

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
                Greenhouse(business_id=b2.id, greenhouse_name="Blok B", crop_name="Hıyar", area_decare=2.8, map_lat=37.78, map_lon=29.08, status_color="blue"),
            ])
            db.commit()
seed()

class LoginIn(BaseModel):
    username: str
    password: str

class BusinessIn(BaseModel):
    business_name: str
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

class VisitStartIn(BaseModel):
    business_id: int
    greenhouse_id: int
    username: str
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
    weather_source: Optional[str] = ""
    visit_lat: Optional[float] = None
    visit_lon: Optional[float] = None

@app.get("/", response_class=HTMLResponse)
def root():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post("/api/login")
def login(data: LoginIn):
    user = USERS.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Hatalı kullanıcı adı / şifre")
    return {"user": {"username": data.username, "name": user["name"], "role": user["role"]}}

@app.get("/api/businesses")
def list_businesses():
    with SessionLocal() as db:
        rows = db.scalars(select(Business).order_by(Business.id.desc())).all()
        return [{"id": r.id, "business_name": r.business_name, "district": r.district, "contact_name": r.contact_name, "phone": r.phone, "notes": r.notes} for r in rows]

@app.post("/api/businesses")
def create_business(data: BusinessIn):
    with SessionLocal() as db:
        row = Business(business_name=data.business_name, district=data.district, contact_name=data.contact_name, phone=data.phone, notes=data.notes)
        db.add(row); db.commit(); db.refresh(row)
        return {"id": row.id}

@app.get("/api/greenhouses")
def list_greenhouses():
    with SessionLocal() as db:
        rows = db.scalars(select(Greenhouse).order_by(Greenhouse.id.desc())).all()
        return [{
            "id": g.id,
            "business_id": g.business_id,
            "business_name": g.business.business_name,
            "greenhouse_name": g.greenhouse_name,
            "crop_name": g.crop_name,
            "area_decare": g.area_decare,
            "lat": g.map_lat,
            "lon": g.map_lon,
            "status": {"blue":"registered","orange":"visited","green":"active","red":"critical"}.get(g.status_color, "registered"),
            "critical_flag": g.critical_flag
        } for g in rows]

@app.post("/api/greenhouses")
def create_greenhouse(data: GreenhouseIn):
    with SessionLocal() as db:
        row = Greenhouse(
            business_id=data.business_id,
            greenhouse_name=data.greenhouse_name,
            crop_name=data.crop_name,
            area_decare=data.area_decare,
            map_lat=data.map_lat,
            map_lon=data.map_lon,
            status_color="blue"
        )
        db.add(row); db.commit(); db.refresh(row)
        return {"id": row.id}

@app.get("/api/greenhouses/{greenhouse_id}/navigation")
def navigation_links(greenhouse_id: int):
    with SessionLocal() as db:
        g = db.get(Greenhouse, greenhouse_id)
        if not g:
            raise HTTPException(status_code=404, detail="Sera bulunamadı")
        return {
            "apple_maps": f"https://maps.apple.com/?daddr={g.map_lat},{g.map_lon}",
            "google_maps": f"https://www.google.com/maps/dir/?api=1&destination={g.map_lat},{g.map_lon}"
        }


@app.get("/api/greenhouses/{greenhouse_id}/latest-visit")
def latest_visit(greenhouse_id: int):
    with SessionLocal() as db:
        g = db.get(Greenhouse, greenhouse_id)
        if not g:
            raise HTTPException(status_code=404, detail="Sera bulunamadı")
        v = db.scalars(
            select(Visit).where(Visit.greenhouse_id == greenhouse_id).order_by(Visit.id.desc()).limit(1)
        ).first()
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
def get_weather(lat: float, lon: float):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&timezone=auto"
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        c = r.json().get("current", {})
        return {"temperature": c.get("temperature_2m"), "humidity": c.get("relative_humidity_2m"), "source": "open-meteo"}
    except Exception:
        return {"temperature": None, "humidity": None, "source": "unavailable"}

@app.post("/api/visits/start")
def start_visit(data: VisitStartIn):
    with SessionLocal() as db:
        now = datetime.utcnow()
        v = Visit(
            business_id=data.business_id,
            greenhouse_id=data.greenhouse_id,
            username=data.username,
            visit_date=date.today().isoformat(),
            visit_start_at=now,
            visit_status="active",
            recipient_email=data.recipient_email,
            visit_lat=data.visit_lat,
            visit_lon=data.visit_lon
        )
        db.add(v)
        g = db.get(Greenhouse, data.greenhouse_id)
        if g:
            g.status_color = "green"
            g.last_visit_at = now
        db.commit(); db.refresh(v)
        return {"id": v.id}

@app.patch("/api/visits/{visit_id}")
def update_visit(visit_id: int, data: VisitUpdateIn):
    with SessionLocal() as db:
        v = db.get(Visit, visit_id)
        if not v:
            raise HTTPException(status_code=404, detail="Ziyaret bulunamadı")
        for k in ["soil_temp","soil_moisture","soil_ec","phenology_stage","diagnosis_notes","fertilization_text","spraying_text","weather_temp","weather_humidity","weather_source","visit_lat","visit_lon"]:
            setattr(v, k, getattr(data, k))
        db.commit()
        return {"ok": True}

@app.post("/api/visits/{visit_id}/complete")
def complete_visit(visit_id: int):
    with SessionLocal() as db:
        v = db.get(Visit, visit_id)
        if not v:
            raise HTTPException(status_code=404, detail="Ziyaret bulunamadı")
        v.visit_status = "completed"
        v.visit_end_at = datetime.utcnow()
        if v.greenhouse:
            v.greenhouse.status_color = "red" if v.greenhouse.critical_flag else "orange"
            v.greenhouse.last_visit_at = datetime.utcnow()
        db.commit()
        return {"ok": True}

@app.post("/api/visits/{visit_id}/photos")
def upload_photo(visit_id: int, file: UploadFile = File(...)):
    with SessionLocal() as db:
        v = db.get(Visit, visit_id)
        if not v:
            raise HTTPException(status_code=404, detail="Ziyaret bulunamadı")
        suffix = Path(file.filename or "photo.jpg").suffix or ".jpg"
        filename = f"visit_{visit_id}_{int(datetime.utcnow().timestamp())}{suffix}"
        target = UPLOAD_DIR / filename
        target.write_bytes(file.file.read())
        p = VisitPhoto(visit_id=visit_id, file_path=f"/uploads/{filename}")
        db.add(p); db.commit(); db.refresh(p)
        return {"id": p.id, "url": p.file_path}

@app.get("/api/dashboard")
def dashboard():
    with SessionLocal() as db:
        total_businesses = db.scalar(select(func.count()).select_from(Business)) or 0
        total_greenhouses = db.scalar(select(func.count()).select_from(Greenhouse)) or 0
        active_visits = db.scalar(select(func.count()).select_from(Visit).where(Visit.visit_status=="active")) or 0
        completed_today = db.scalar(select(func.count()).select_from(Visit).where(Visit.visit_status=="completed", Visit.visit_date==date.today().isoformat())) or 0
        critical = db.scalar(select(func.count()).select_from(Greenhouse).where(Greenhouse.critical_flag == True)) or 0
        recent = db.scalars(select(Visit).order_by(Visit.id.desc()).limit(10)).all()
        return {
            "total_businesses": total_businesses,
            "total_greenhouses": total_greenhouses,
            "active_visits": active_visits,
            "completed_today": completed_today,
            "critical_greenhouses": critical,
            "recent_visits": [{
                "id": v.id,
                "username": v.username,
                "visit_status": v.visit_status,
                "visit_date": v.visit_date,
                "business_name": v.greenhouse.business.business_name if v.greenhouse else "",
                "greenhouse_name": v.greenhouse.greenhouse_name if v.greenhouse else ""
            } for v in recent]
        }

@app.get("/api/analytics/greenhouse/{greenhouse_id}")
def greenhouse_analytics(greenhouse_id: int):
    with SessionLocal() as db:
        rows = db.scalars(select(Visit).where(Visit.greenhouse_id == greenhouse_id).order_by(Visit.id.asc())).all()
        def conv(x):
            try:
                return float(x)
            except Exception:
                return None
        return {
            "labels": [r.visit_date for r in rows],
            "soil_temp": [conv(r.soil_temp) for r in rows],
            "soil_moisture": [conv(r.soil_moisture) for r in rows],
            "soil_ec": [conv(r.soil_ec) for r in rows],
        }

@app.get("/api/reports/daily/excel")
def daily_excel(report_date: Optional[str] = None):
    report_date = report_date or date.today().isoformat()
    with SessionLocal() as db:
        rows = db.scalars(select(Visit).where(Visit.visit_date == report_date).order_by(Visit.id.desc())).all()
        wb = Workbook()
        ws = wb.active
        ws.title = "Gunluk Rapor"
        ws.append(["Tarih","Mühendis","İşletme","Sera","Hava","Toprak Sıcaklığı","Toprak Nemi","EC","Gübreleme","İlaçlama","Not"])
        for v in rows:
            ws.append([
                v.visit_date, v.username,
                v.greenhouse.business.business_name if v.greenhouse else "",
                v.greenhouse.greenhouse_name if v.greenhouse else "",
                f"{v.weather_temp or ''} / {v.weather_humidity or ''}",
                v.soil_temp or "", v.soil_moisture or "", v.soil_ec or "",
                v.fertilization_text or "", v.spraying_text or "", v.diagnosis_notes or ""
            ])
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 18
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="gunluk_rapor_{report_date}.xlsx"'}
        )

@app.get("/api/reports/visit/{visit_id}/pdf")
def visit_pdf(visit_id: int):
    with SessionLocal() as db:
        v = db.get(Visit, visit_id)
        if not v:
            raise HTTPException(status_code=404, detail="Ziyaret bulunamadı")
        out = io.BytesIO()
        doc = SimpleDocTemplate(out, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("Arazi Takip Ziyaret Raporu", styles["Title"]), Spacer(1, 12)]
        data = [
            ["Tarih", v.visit_date],
            ["Mühendis", v.username],
            ["İşletme", v.greenhouse.business.business_name if v.greenhouse else ""],
            ["Sera", v.greenhouse.greenhouse_name if v.greenhouse else ""],
            ["Hava", f"{v.weather_temp or ''} / {v.weather_humidity or ''}"],
            ["Toprak Sıcaklığı", v.soil_temp or ""],
            ["Toprak Nemi", v.soil_moisture or ""],
            ["EC", v.soil_ec or ""]
        ]
        t = Table(data, colWidths=[160, 320])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), colors.lightgreen),
            ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("PADDING", (0,0), (-1,-1), 6)
        ]))
        story += [
            t, Spacer(1, 12),
            Paragraph("Gübreleme Programı", styles["Heading2"]),
            Paragraph((v.fertilization_text or "-").replace("\n","<br/>"), styles["BodyText"]),
            Spacer(1,8),
            Paragraph("İlaçlama Programı", styles["Heading2"]),
            Paragraph((v.spraying_text or "-").replace("\n","<br/>"), styles["BodyText"]),
            Spacer(1,8),
            Paragraph("Teşhis / Gözlem", styles["Heading2"]),
            Paragraph((v.diagnosis_notes or "-").replace("\n","<br/>"), styles["BodyText"])
        ]
        doc.build(story)
        out.seek(0)
        return StreamingResponse(
            out,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="ziyaret_{visit_id}.pdf"'}
        )
