from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

# Sisteme kayıt olurken kullanıcıdan isteyeceğimiz veriler
class KullaniciCreate(BaseModel):
    ad: str
    soyad: str
    email: str
    sifre: str

# Sistemin dışarıya (Arayüze) döneceği kullanıcı verisi (Şifreyi gizliyoruz!)
class KullaniciResponse(BaseModel):
    user_id: int
    ad: str
    soyad: str
    email: str
    kayit_tarihi: datetime

    class Config:
        from_attributes = True


# --- JWT TOKEN ŞEMALARI ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None        


# --- GRUP ŞEMALARI ---

# Kullanıcı grup kurarken sadece bu bilgileri gönderecek
class GrupCreate(BaseModel):
    grup_adi: str
    baslangic_tarihi: date
    bitis_tarihi: date

# Sistem grubu oluşturduktan sonra bu bilgileri geri dönecek
class GrupResponse(BaseModel):
    group_id: int
    grup_adi: str
    olusturan_id: int
    baslangic_tarihi: date
    bitis_tarihi: date
    durum: str

    class Config:
        from_attributes = True

# Gruba üye eklerken kullanılacak şema
class UyeEkle(BaseModel):
    user_id: int

# --- BORÇ VE DENGE ŞEMALARI ---

class BorcDurumu(BaseModel):
    user_id: int
    ad: str
    soyad: str
    bakiye: float # Pozitifse alacaklı, negatifse borçlu 

# --- HARCAMA ŞEMALARI ---
from datetime import date

class HarcamaCreate(BaseModel):
    aciklama: str
    toplam_tutar: float
    tarih: date

# --- SPRINT 5: EKSİK ŞEMALAR ---

# 1. Ödeme (Borç Kapatma) Şemaları
class OdemeCreate(BaseModel):
    alan_id: int
    tutar: float

class OdemeResponse(BaseModel):
    payment_id: int
    gonderen_id: int
    alan_id: int
    tutar: float
    odeme_tarihi: datetime

    class Config:
        from_attributes = True # Eğer eski Pydantic sürümü kullanıyorsan orm_mode = True yapabilirsin

# 2. İtiraz (Dispute) Şemaları
class ItirazCreate(BaseModel):
    expense_id: int
    aciklama: str

class ItirazResponse(BaseModel):
    dispute_id: int
    expense_id: int
    itiraz_eden_id: int
    aciklama: str
    durum: str
    olusturma_tarihi: datetime

    class Config:
        from_attributes = True

# 3. Bildirim Şeması
class BildirimResponse(BaseModel):
    notification_id: int
    user_id: int
    mesaj: str
    okundu_mu: bool
    tarih: datetime

    class Config:
        from_attributes = True