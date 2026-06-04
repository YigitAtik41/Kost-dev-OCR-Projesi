from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt
import models
import schemas
import auth
import ocr_service  # OCR servisimizi içeri aktardık
from database import engine, SessionLocal
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Coddest - Akıllı Fiş Okuma ve Gider Paylaşım Platformu",
    description="Sistem Analizi ve Tasarımı Projesi Backend Servisi",
    version="1.0.0"
)

# Veritabanı bağlantısını her istekte açıp kapatmak için gerekli fonksiyon
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
    # Email sistemde var mı kontrolü (Raporda email benzersiz olmalı kuralı var)
    db_user = db.query(models.Kullanici).filter(models.Kullanici.email == kullanici.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Bu email adresi zaten kayıtlı.")
    
    # Şifreyi bcrypt ile hashliyoruz (Güvenlik kuralı)
    hashed_password = auth.get_password_hash(kullanici.sifre)
    
    # Yeni kullanıcıyı veritabanı modeline dönüştürüyoruz
    yeni_kullanici = models.Kullanici(
        ad=kullanici.ad,
        soyad=kullanici.soyad,
        email=kullanici.email,
        sifre=hashed_password
    )
    
    # Veritabanına kaydetme işlemi
    db.add(yeni_kullanici)
    db.commit()
    db.refresh(yeni_kullanici)
    
    return yeni_kullanici

# --- OTURUM YÖNETİMİ (JWT) ---

# Bu kod, Swagger UI arayüzünde "Authorize" butonunun çıkmasını sağlar
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="giris")

@app.post("/giris", response_model=schemas.Token)
def giris_yap(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Kullanıcıyı email adresiyle veritabanında bul (FastAPI form'da username kullanır, biz email'i oraya yazacağız)
    user = db.query(models.Kullanici).filter(models.Kullanici.email == form_data.username).first()
    
    # 2. Kullanıcı yoksa veya şifre yanlışsa hata ver
    if not user or not auth.verify_password(form_data.password, user.sifre):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yanlış e-posta veya şifre",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Her şey doğruysa JWT Biletini (Token) kes ve teslim et
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- KİMLİK KONTROLÜ VE KİLİTLİ SAYFALAR ---

# Bu fonksiyon, gelen bileti (token) okur ve kişinin kim olduğunu anlar
def aktif_kullaniciyi_getir(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    hata_mesaji = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı veya oturum süresi doldu.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Biletin içindeki veriyi auth.py'deki gizli anahtarımızla çözüyoruz
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise hata_mesaji
    except Exception:
        raise hata_mesaji
    
    # E-posta doğruysa kullanıcıyı veritabanından bul
    user = db.query(models.Kullanici).filter(models.Kullanici.email == email).first()
    if user is None:
        raise hata_mesaji
    return user

# İŞTE KİLİTLİ SAYFAMIZ (Depends(aktif_kullaniciyi_getir) kısmı burayı kilitler)
@app.get("/profil", response_model=schemas.KullaniciResponse)
def profilimi_goruntule(mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    return mevcut_kullanici

# --- GRUP VE ETKİNLİK YÖNETİMİ ---

@app.post("/gruplar", response_model=schemas.GrupResponse)
def grup_olustur(grup: schemas.GrupCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    # 1. Yeni grubu veritabanı modeline çevir
    yeni_grup = models.Grup(
        grup_adi=grup.grup_adi,
        olusturan_id=mevcut_kullanici.user_id,
        baslangic_tarihi=grup.baslangic_tarihi,
        bitis_tarihi=grup.bitis_tarihi,
        durum="Aktif"
    )
    
    # 2. Grubu veritabanına kaydet
    db.add(yeni_grup)
    db.commit()
    db.refresh(yeni_grup)
    
    # 3. Grubu kuran kişiyi otomatik olarak o gruba üye olarak ekle
    ilk_uye = models.GrupUyeleri(
        group_id=yeni_grup.group_id,
        user_id=mevcut_kullanici.user_id
    )
    db.add(ilk_uye)
    db.commit()
    
    return yeni_grup

@app.post("/gruplar/{group_id}/uyeler")
def gruba_uye_ekle(group_id: int, uye_data: schemas.UyeEkle, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    # Grubun var olup olmadığını kontrol et
    grup = db.query(models.Grup).filter(models.Grup.group_id == group_id).first()
    if not grup:
        raise HTTPException(status_code=404, detail="Grup bulunamadı.")
        
    # Sadece grubu oluşturan kişi üye ekleyebilir (Rapordaki yetki kuralı)
    if grup.olusturan_id != mevcut_kullanici.user_id:
        raise HTTPException(status_code=403, detail="Sadece grup yöneticisi üye ekleyebilir.")
        
    # Kullanıcı zaten grupta mı kontrol et
    mevcut_uye = db.query(models.GrupUyeleri).filter(models.GrupUyeleri.group_id == group_id, models.GrupUyeleri.user_id == uye_data.user_id).first()
    if mevcut_uye:
         raise HTTPException(status_code=400, detail="Bu kullanıcı zaten grupta.")

    # Yeni üyeyi ekle
    yeni_uye = models.GrupUyeleri(group_id=group_id, user_id=uye_data.user_id)
    db.add(yeni_uye)
    db.commit()
    
    return {"mesaj": "Kullanıcı gruba başarıyla eklendi."}


# --- AKILLI FİŞ OKUMA (OCR) SİSTEMİ ---

@app.post("/fis-oku")
async def fis_okuma_servisi(file: UploadFile = File(...), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    
    # 1. Yüklenen dosyanın resim olup olmadığını basitçe kontrol edelim
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir resim dosyası (PNG, JPG) yükleyin.")
    
    # 2. Resmin piksellerini (byte) okuyoruz
    resim_bytes = await file.read()
    
    # 3. Yazdığımız OCR motoruna resmi gönderiyoruz
    sonuc = ocr_service.fisi_analiz_et(resim_bytes)
    
    # 4. OCR başarısız olursa PDF Madde 4.9 (OCR fallback) gereği hata mesajı dönüyoruz
    if not sonuc["basarili"]:
        raise HTTPException(status_code=400, detail=sonuc["hata_mesaji"])
        
    return sonuc

@app.get("/gruplar/{group_id}/ozet", response_model=list[schemas.BorcDurumu])
def grup_ozeti(group_id: int, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    
    # 1. Grubun var olup olmadığını kontrol et
    grup = db.query(models.Grup).filter(models.Grup.group_id == group_id).first()
    if not grup:
        raise HTTPException(status_code=404, detail="Grup bulunamadı.")

    # 2. Gruptaki tüm üyeleri ve o gruba ait tüm harcamaları çek
    uyeler = db.query(models.GrupUyeleri).filter(models.GrupUyeleri.group_id == group_id).all()
    # (Not: Biz harcamaları kaydederken henüz fiş ID'si bağlamadığımız için basitlik adına tüm harcamaları gruptan bağımsız gibi düşünmeyelim diye ufak bir filtre yazıyoruz. Gerçekte harcama modeline group_id eklenmelidir ama şimdilik mevcut yapıyla çözeceğiz).
    
    # Tüm harcamaları alıyoruz (Proje büyüdüğünde burası group_id'ye göre filtrelenmeli)
    harcamalar = db.query(models.Harcama).all() 

    if not uyeler:
        raise HTTPException(status_code=400, detail="Grupta üye yok.")

    # 3. MATEMATİKSEL ALGORİTMA
    toplam_harcama = sum(h.toplam_tutar for h in harcamalar)
    kisi_sayisi = len(uyeler)
    kisi_basi_dusen = toplam_harcama / kisi_sayisi
    
    ozet_listesi = []
    
    for uye in uyeler:
        # Üyenin kimlik bilgilerini al
        kullanici = db.query(models.Kullanici).filter(models.Kullanici.user_id == uye.user_id).first()
        
        # Bu üyenin kendi cebinden yaptığı toplam ödemeyi hesapla
        onun_odedigi = sum(h.toplam_tutar for h in harcamalar if h.odeyen_id == uye.user_id)
        
        # Bakiye = Kendi cebinden çıkan - Aslında ödemesi gereken
        # Örnek: 100 TL harcadı, kişi başı 40 TL düşüyordu. Bakiye = +60 (Alacaklı)
        # Örnek: 0 TL harcadı, kişi başı 40 TL düşüyordu. Bakiye = -40 (Borçlu)
        bakiye = onun_odedigi - kisi_basi_dusen
        
        ozet_listesi.append({
            "user_id": kullanici.user_id,
            "ad": kullanici.ad,
            "soyad": kullanici.soyad,
            "bakiye": round(bakiye, 2)
        })
        
    return ozet_listesi


@app.post("/gruplar/{group_id}/harcamalar")
def harcama_ekle(group_id: int, harcama: schemas.HarcamaCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    
    # 1. Grubun olup olmadığına bakıyoruz
    grup = db.query(models.Grup).filter(models.Grup.group_id == group_id).first()
    if not grup:
        raise HTTPException(status_code=404, detail="Grup bulunamadı.")
        
    # 2. HOCALARIN İSTEDİĞİ KURAL: Harcama tarihi grup tarihleri arasında olmalı!
    if harcama.tarih < grup.baslangic_tarihi or harcama.tarih > grup.bitis_tarihi:
        raise HTTPException(status_code=400, detail="Hata: Harcama tarihi grubun aktif olduğu tarihler arasında olmalıdır!")

    # 3. Kurala uyuyorsa veritabanına kaydet
    yeni_harcama = models.Harcama(
        aciklama=harcama.aciklama,
        toplam_tutar=harcama.toplam_tutar,
        tarih=harcama.tarih,
        odeyen_id=mevcut_kullanici.user_id,
        receipt_id=group_id # Şimdilik harcamayı gruba bağlamak için bu alanı kullanıyoruz
    )
    db.add(yeni_harcama)
    db.commit()
    db.refresh(yeni_harcama)
    
    return yeni_harcama

# --- SPRINT 5: ÖDEME, İTİRAZ VE BİLDİRİM UÇ NOKTALARI ---

# 1. Ödeme Bildirimi (Borç Kapatma)
@app.post("/odemeler", response_model=schemas.OdemeResponse)
def odeme_yap(odeme: schemas.OdemeCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    # Ödemeyi kaydet
    yeni_odeme = models.OdemeIslemi(
        gonderen_id=mevcut_kullanici.user_id,
        alan_id=odeme.alan_id,
        tutar=odeme.tutar,
        odeme_tarihi=datetime.utcnow()
    )
    db.add(yeni_odeme)
    
    # Parayı alan kişiye otomatik bildirim gönder
    yeni_bildirim = models.Bildirim(
        user_id=odeme.alan_id,
        mesaj=f"{mevcut_kullanici.ad} {mevcut_kullanici.soyad} size {odeme.tutar} TL ödeme yaptı.",
        tarih=datetime.utcnow()
    )
    db.add(yeni_bildirim)
    
    db.commit()
    db.refresh(yeni_odeme)
    return yeni_odeme


# 2. Harcamaya İtiraz Etme (Dispute)
@app.post("/harcamalar/{expense_id}/itiraz", response_model=schemas.ItirazResponse)
def itiraz_et(expense_id: int, itiraz: schemas.ItirazCreate, db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    # Harcamayı bul
    harcama = db.query(models.Harcama).filter(models.Harcama.expense_id == expense_id).first()
    if not harcama:
        raise HTTPException(status_code=404, detail="Harcama bulunamadı.")
        
    # İtirazı kaydet
    yeni_itiraz = models.ItirazTalebi(
        expense_id=expense_id,
        itiraz_eden_id=mevcut_kullanici.user_id,
        aciklama=itiraz.aciklama,
        durum="Açık",
        olusturma_tarihi=datetime.utcnow()
    )
    db.add(yeni_itiraz)
    
    # Harcamayı giren kişiye bildirim gönder
    yeni_bildirim = models.Bildirim(
        user_id=harcama.odeyen_id,
        mesaj=f"DİKKAT: {mevcut_kullanici.ad}, girdiğiniz {harcama.toplam_tutar} TL'lik harcamaya itiraz etti! Nedeni: {itiraz.aciklama}",
        tarih=datetime.utcnow()
    )
    db.add(yeni_bildirim)
    
    db.commit()
    db.refresh(yeni_itiraz)
    return yeni_itiraz


# 3. Bildirimleri Görüntüleme
@app.get("/bildirimler", response_model=list[schemas.BildirimResponse])
def bildirimleri_getir(db: Session = Depends(get_db), mevcut_kullanici: models.Kullanici = Depends(aktif_kullaniciyi_getir)):
    # Kullanıcının bildirimlerini çek
    bildirimler = db.query(models.Bildirim).filter(models.Bildirim.user_id == mevcut_kullanici.user_id).all()
    
    # Kullanıcı bildirimlere baktığı an hepsini "Okundu" olarak işaretle
    for b in bildirimler:
        b.okundu_mu = True
    db.commit()
    
    return bildirimler