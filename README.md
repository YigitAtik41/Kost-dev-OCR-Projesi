# Akıllı Fiş Okuma ve Grup Gider Paylaşım Platformu (CODDEST)

Bu proje, OCR teknolojisi kullanarak fişleri okuyan ve grup içi harcamaları otomatik olarak hesaplayıp borç dağılımı yapan bir backend API sistemidir.

## Kurulum Öncesi Gereksinimler

Projenin bilgisayarınızda sorunsuz çalışması için aşağıdaki kurulumların yapılmış olması gerekmektedir:
1. **Python 3.8 veya üzeri**
2. **Tesseract OCR:** Fiş okuma yapay zekasının çalışması için bilgisayarınızda kurulu olmalıdır.
   - Windows için [Tesseract Installer](https://github.com/UB-Mannheim/tesseract/wiki) adresinden indirip kurun.
   - Kurulumdan sonra `C:\Program Files\Tesseract-OCR\tesseract.exe` yolunun doğru olduğundan emin olun (Kod içinde bu yol belirtilmiştir).

## Projeyi Çalıştırma Adımları

**1. Sanal Ortam Oluşturun:**
Terminali açın, projenin bulunduğu klasöre gidin ve aşağıdaki komutu çalıştırın:
`python -m venv venv`

**2. Sanal Ortamı Aktif Edin:**
- Windows için:
`.\venv\Scripts\activate`
- Mac/Linux için:
`source venv/bin/activate`

**3. Gerekli Kütüphaneleri Kurun:**
`pip install -r requirements.txt`

**4. Sunucuyu Başlatın:**
`uvicorn main:app --reload`

## Sistemi Test Etme (Swagger UI)

Sunucu çalıştıktan sonra tarayıcınızı açın ve şu adrese gidin:
**👉 http://127.0.0.1:8000/docs**

Tüm uç noktalarımızı (Endpoints) buradan test edebilirsiniz. 

**Nasıl Test Edilir?**
1. `POST /kullanicilar/kayit` kısmından sisteme bir kullanıcı kaydedin.
2. Sayfanın sağ üstündeki yeşil **Authorize** butonuna tıklayın.
3. Açılan pencerede kaydettiğiniz e-posta ve şifrenizi girerek giriş yapın (Swagger token atama işlemini arka planda otomatik halledecektir).
4. Artık sistemdeki fiş yükleme, grup oluşturma ve ödeme gibi tüm işlemleri yetkili olarak test edebilirsiniz!