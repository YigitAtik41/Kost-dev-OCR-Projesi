from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from jose import jwt
import webbrowser
import threading
import time
import uvicorn
import models
import schemas
import auth
import ocr_service
from database import engine, SessionLocal
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Coddest - Akıllı Fiş Okuma ve Gider Paylaşım Platformu",
    description="Sistem Analizi ve Tasarımı Projesi Backend Servisi",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def tarayiciyi_ac():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000/arayuz")

@app.on_event("startup")
def startup_event():
    threading.Thread(target=tarayiciyi_ac).start()

@app.get("/arayuz", include_in_schema=False)
def arayuz_sayfasini_getir():
    return FileResponse("index.html")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def ana_sayfa():
    return {"mesaj": "Coddest API başarıyla çalışıyor! Hoş geldiniz."}

# --- KULLANICI İŞLEMLERİ ---
@app.post("/kullanicilar/kayit", response_model=schemas.KullaniciResponse)
def kayit_ol(kullanici: schemas.KullaniciCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Kullanici).filter(models.Kullanici.email == kullanici.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")
    
    hashed_password = auth.get_password_hash(kullanici.sifre)
    yeni_kullanici = models.Kullanici(ad=kullanici.ad, soyad=kullanici.soyad, email=kullanici.email, sifre=hashed_password)
    
    db.add(yeni_kullanici)
    db.commit()
    db.refresh(yeni_kullanici)
    return yeni_kullanici

# --- OTURUM YÖNETİMİ ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="giris")

@app.post("/giris", response_model=schemas.Token)
def giris_yap(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Kullanici).filter(models.Kullanici.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.sifre):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yanlış e-posta veya şifre", headers={"WWW-Authenticate": "Bearer"})
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

def aktif_kullaniciyi_getir(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    hata_mesaji = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kimlik doğrulanamadı veya oturum süresi doldu.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise hata_mesaji
    except Exception:
        raise hata_mesaji
    
    user = db.query(models.Kullanici).filter(models.Kullanici.email == email).first()
    if user is None: raise hata_mesaji
    return user

@app.get("/profil", response_model=schemas.KullaniciResponse)
def profilimi_goruntule(mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    return mevcut_kullanici

# --- GRUP VE ETKİNLİK YÖNETİMİ ---
@app.post("/gruplar", response_model=schemas.GrupResponse)
def grup_olustur(grup: schemas.GrupCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    yeni_grup = models.Grup(grup_adi=grup.grup_adi, olusturan_id=mevcut_kullanici.user_id, baslangic_tarihi=grup.baslangic_tarihi, bitis_tarihi=grup.bitis_tarihi, durum="Aktif")
    db.add(yeni_grup)
    db.commit()
    db.refresh(yeni_grup)
    
    ilk_uye = models.GrupUyeleri(group_id=yeni_grup.group_id, user_id=mevcut_kullanici.user_id)
    db.add(ilk_uye)
    db.commit()
    return yeni_grup

@app.get("/gruplar", response_model=list[schemas.GrupResponse])
def gruplarimi_getir(db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    uye_oldugu_gruplar = db.query(models.GrupUyeleri).filter(models.GrupUyeleri.user_id == mevcut_kullanici.user_id).all()
    grup_idleri = [uye.group_id for uye in uye_oldugu_gruplar]
    gruplar = db.query(models.Grup).filter(models.Grup.group_id.in_(grup_idleri)).all()
    return gruplar

@app.delete("/gruplar/{group_id}")
def grup_sil(group_id: int, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    grup = db.query(models.Grup).filter(models.Grup.group_id == group_id).first()
    if not grup: raise HTTPException(status_code=404, detail="Grup bulunamadı.")
    if grup.olusturan_id != mevcut_kullanici.user_id: raise HTTPException(status_code=403, detail="Sadece grubu oluşturan kişi silebilir.")
        
    db.query(models.GrupUyeleri).filter(models.GrupUyeleri.group_id == group_id).delete()
    db.query(models.Harcama).filter(models.Harcama.receipt_id == group_id).delete()
    
    db.delete(grup)
    db.commit()
    return {"mesaj": "Grup ve içindeki harcamalar başarıyla silindi."}

@app.post("/gruplar/{group_id}/uyeler")
def gruba_uye_ekle(group_id: int, uye_data: schemas.UyeEkle, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    grup = db.query(models.Grup).filter(models.Grup.group_id == group_id).first()
    if not grup: raise HTTPException(status_code=404, detail="Grup bulunamadı.")
    if grup.olusturan_id != mevcut_kullanici.user_id: raise HTTPException(status_code=403, detail="Sadece grup yöneticisi üye ekleyebilir.")
        
    mevcut_uye = db.query(models.GrupUyeleri).filter(models.GrupUyeleri.group_id == group_id, models.GrupUyeleri.user_id == uye_data.user_id).first()
    if mevcut_uye: raise HTTPException(status_code=400, detail="Bu kullanıcı zaten grupta.")

    yeni_uye = models.GrupUyeleri(group_id=group_id, user_id=uye_data.user_id)
    db.add(yeni_uye)
    db.commit()
    return {"mesaj": "Kullanıcı gruba başarıyla eklendi."}

# --- AKILLI FİŞ OKUMA ---
@app.post("/fis-oku")
async def fis_okuma_servisi(file: UploadFile = File(...), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    if not file.content_type.startswith("image/"): raise HTTPException(status_code=400, detail="Geçerli bir resim dosyası yükleyin.")
    resim_bytes = await file.read()
    sonuc = ocr_service.fisi_analiz_et(resim_bytes)
    if not sonuc["basarili"]: raise HTTPException(status_code=400, detail=sonuc["hata_mesaji"])
    return sonuc

@app.get("/gruplar/{group_id}/ozet", response_model=list[schemas.BorcDurumu])
def grup_ozeti(group_id: int, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    grup = db.query(models.Grup).filter(models.Grup.group_id == group_id).first()
    if not grup: raise HTTPException(status_code=404, detail="Grup bulunamadı.")
    uyeler = db.query(models.GrupUyeleri).filter(models.GrupUyeleri.group_id == group_id).all()
    harcamalar = db.query(models.Harcama).filter(models.Harcama.receipt_id == group_id).all() 

    if not uyeler: raise HTTPException(status_code=400, detail="Grupta üye yok.")

    toplam_harcama = sum(h.toplam_tutar for h in harcamalar)
    kisi_basi_dusen = toplam_harcama / len(uyeler)
    ozet_listesi = []
    
    for uye in uyeler:
        kullanici = db.query(models.Kullanici).filter(models.Kullanici.user_id == uye.user_id).first()
        onun_odedigi = sum(h.toplam_tutar for h in harcamalar if h.odeyen_id == uye.user_id)
        ozet_listesi.append({"user_id": kullanici.user_id, "ad": kullanici.ad, "soyad": kullanici.soyad, "bakiye": round(onun_odedigi - kisi_basi_dusen, 2)})
    return ozet_listesi

# --- HARCAMA YÖNETİMİ ---
@app.post("/gruplar/{group_id}/harcamalar")
def harcama_ekle(group_id: int, harcama: schemas.HarcamaCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    grup = db.query(models.Grup).filter(models.Grup.group_id == group_id).first()
    if not grup: raise HTTPException(status_code=404, detail="Grup bulunamadı.")
        
    if harcama.tarih < grup.baslangic_tarihi or harcama.tarih > grup.bitis_tarihi:
        giren_tarih = harcama.tarih.strftime("%d.%m.%Y")
        grup_bas = grup.baslangic_tarihi.strftime("%d.%m.%Y")
        grup_bit = grup.bitis_tarihi.strftime("%d.%m.%Y")
        hata_metni = f"Tarih Hatası: Girdiğiniz {giren_tarih} tarihi, grubun aktif olduğu ({grup_bas} - {grup_bit}) aralığında değil!"
        raise HTTPException(status_code=400, detail=hata_metni)

    yeni_harcama = models.Harcama(aciklama=harcama.aciklama, toplam_tutar=harcama.toplam_tutar, tarih=harcama.tarih, odeyen_id=mevcut_kullanici.user_id, receipt_id=group_id)
    db.add(yeni_harcama)
    db.commit()
    db.refresh(yeni_harcama)
    return yeni_harcama

@app.get("/harcamalar")
def harcamalarimi_getir(db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    return db.query(models.Harcama).filter(models.Harcama.odeyen_id == mevcut_kullanici.user_id).all()

@app.delete("/harcamalar/{expense_id}")
def harcama_sil(expense_id: int, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    harcama = db.query(models.Harcama).filter(models.Harcama.expense_id == expense_id).first()
    if not harcama: raise HTTPException(status_code=404, detail="Harcama bulunamadı.")
    if harcama.odeyen_id != mevcut_kullanici.user_id: raise HTTPException(status_code=403, detail="Sadece harcamayı ekleyen kişi bu harcamayı silebilir.")
        
    db.delete(harcama)
    db.commit()
    return {"mesaj": "Harcama başarıyla silindi."}

# --- ÖDEME, İTİRAZ VE BİLDİRİM ---
@app.post("/odemeler", response_model=schemas.OdemeResponse)
def odeme_yap(odeme: schemas.OdemeCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    yeni_odeme = models.OdemeIslemi(gonderen_id=mevcut_kullanici.user_id, alan_id=odeme.alan_id, tutar=odeme.tutar, odeme_tarihi=datetime.utcnow())
    db.add(yeni_odeme)
    db.add(models.Bildirim(user_id=odeme.alan_id, mesaj=f"{mevcut_kullanici.ad} {mevcut_kullanici.soyad} size {odeme.tutar} TL ödeme yaptı.", tarih=datetime.utcnow()))
    db.commit()
    db.refresh(yeni_odeme)
    return yeni_odeme

@app.post("/harcamalar/{expense_id}/itiraz", response_model=schemas.ItirazResponse)
def itiraz_et(expense_id: int, itiraz: schemas.ItirazCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    harcama = db.query(models.Harcama).filter(models.Harcama.expense_id == expense_id).first()
    if not harcama: raise HTTPException(status_code=404, detail="Harcama bulunamadı.")
        
    yeni_itiraz = models.ItirazTalebi(expense_id=expense_id, itiraz_eden_id=mevcut_kullanici.user_id, aciklama=itiraz.aciklama, durum="Açık", olusturma_tarihi=datetime.utcnow())
    db.add(yeni_itiraz)
    db.add(models.Bildirim(user_id=harcama.odeyen_id, mesaj=f"DİKKAT: {mevcut_kullanici.ad}, girdiğiniz {harcama.toplam_tutar} TL'lik harcamaya itiraz etti! Nedeni: {itiraz.aciklama}", tarih=datetime.utcnow()))
    db.commit()
    db.refresh(yeni_itiraz)
    return yeni_itiraz

@app.get("/bildirimler", response_model=list[schemas.BildirimResponse])
def bildirimleri_getir(db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    bildirimler = db.query(models.Bildirim).filter(models.Bildirim.user_id == mevcut_kullanici.user_id).all()
    for b in bildirimler: b.okundu_mu = True
    db.commit()
    return bildirimler

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)