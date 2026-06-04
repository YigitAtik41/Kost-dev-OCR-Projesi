from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Date, DateTime
from datetime import datetime
from database import Base

class Rol(Base):
    __tablename__ = "roller"
    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String)

class Kullanici(Base):
    __tablename__ = "kullanicilar"
    user_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String)
    soyad = Column(String)
    email = Column(String, unique=True, index=True)
    sifre = Column(String)
    kayit_tarihi = Column(DateTime, default=datetime.utcnow)

class Grup(Base):
    __tablename__ = "gruplar"
    group_id = Column(Integer, primary_key=True, index=True)
    grup_adi = Column(String)
    olusturan_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    baslangic_tarihi = Column(Date)
    bitis_tarihi = Column(Date)
    durum = Column(String)

class GrupUyeleri(Base):
    __tablename__ = "grup_uyeleri"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("gruplar.group_id"))
    user_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    katilim_tarihi = Column(DateTime, default=datetime.utcnow)

class FisBelgesi(Base):
    __tablename__ = "fis_belgeleri"
    receipt_id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("gruplar.group_id"))
    yukleyen_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    tarih = Column(Date)
    toplam_tutar = Column(Float)
    satici = Column(String)

class Harcama(Base):
    __tablename__ = "harcamalar"
    expense_id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("fis_belgeleri.receipt_id"), nullable=True)
    odeyen_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    aciklama = Column(String)
    toplam_tutar = Column(Float)
    tarih = Column(Date)

class BorcEslesmesi(Base):
    __tablename__ = "borc_eslesmeleri"
    debt_id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("harcamalar.expense_id"))
    borclu_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    alacakli_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    tutar = Column(Float)
    durum = Column(String)

class OdemeIslemi(Base):
    __tablename__ = "odeme_islemleri"
    payment_id = Column(Integer, primary_key=True, index=True)
    gonderen_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    alan_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    group_id = Column(Integer, ForeignKey("gruplar.group_id"))
    tutar = Column(Float)
    odeme_tarihi = Column(DateTime, default=datetime.utcnow)

class ItirazTalebi(Base):
    __tablename__ = "itiraz_talepleri"
    dispute_id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("harcamalar.expense_id"))
    acan_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    aciklama = Column(String)
    durum = Column(String)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)

class Bildirim(Base):
    __tablename__ = "bildirimler"
    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("kullanicilar.user_id"))
    mesaj = Column(String)
    okundu_mu = Column(Boolean, default=False)
    tarih = Column(DateTime, default=datetime.utcnow)

