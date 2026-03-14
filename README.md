
# Arazi Takip V3

Bu sürümde mevcut:
- Türkiye haritasında sera pinleri
- pin kümelenmesi ve zoom
- işletme ekleme
- haritadan / mevcut konumdan sera kaydı
- GPS ile otomatik konum alma
- Open-Meteo ile otomatik hava verisi
- ziyaret başlat / ara kaydet / tamamla
- fotoğraf yükleme
- sera bazlı grafikler
- PDF ziyaret raporu
- günlük Excel raporu
- WhatsApp ile PDF paylaşımı
- cloud uyumlu yapı
- PostgreSQL için DATABASE_URL desteği

## Yerelde çalıştırma
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Render start command
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```
