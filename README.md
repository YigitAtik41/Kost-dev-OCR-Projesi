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
`python main.py`

*(Sunucu başlatıldığı anda proje web arayüzü varsayılan tarayıcınızda otomatik olarak açılacaktır.)*

## Sistemi Test Etme (Web Arayüzü & API)

Sistem ayağa kalktığında **http://127.0.0.1:8000/arayuz** adresi otomatik olarak açılır ve projenin kullanıcı dostu ön yüzü karşınıza çıkar.

**Arayüz Üzerinden Test:**
1. Açılan ekrandan sisteme yeni bir kullanıcı kaydedin.
2. Aynı bilgilerle giriş yapın (Yetkilendirme token'ı otomatik alınacaktır).
3. Akıllı fiş yükleme alanından (JPG/PNG) bir fiş seçip "Yapay Zeka ile Analiz Et" butonuna tıklayarak OCR sistemini test edebilirsiniz.

**Geliştirici Dokümantasyonu (Swagger UI):**
Arayüzden bağımsız olarak arka plandaki tüm API uç noktalarını (Endpoints) teknik düzeyde incelemek isterseniz, tarayıcınızda manuel olarak şu adrese gidebilirsiniz:
**👉 http://127.0.0.1:8000/docs**