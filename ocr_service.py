import pytesseract
from PIL import Image
import re
from datetime import datetime
import io

# Tesseract'ı nereye kurduğumuzu Python'a söylüyoruz (Senin kurduğun dizin)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def fisi_analiz_et(resim_bytes):
    try:
        # Gelen resmi PIL (Pillow) kütüphanesi ile açıyoruz
        image = Image.open(io.BytesIO(resim_bytes))
        
        # Tesseract ile resimdeki yazıları Türkçe dil desteği ile okuyoruz
        okunan_metin = pytesseract.image_to_string(image, lang='tur')
        
        # Okunan ham metni terminale yazdıralım ki test ederken ne okuduğunu görelim
        print("--- TESSERACT'IN OKUDUĞU HAM METİN ---")
        print(okunan_metin)
        print("--------------------------------------")
        
        # --- 1. TARİH BULMA (Regex) ---
        # 12.05.2026, 12/05/2026 veya 12-05-2026 formatlarını arar
        tarih_sablonu = r'(\d{2})[./-](\d{2})[./-](\d{4})'
        tarih_eslesme = re.search(tarih_sablonu, okunan_metin)
        
        bulunan_tarih = None
        if tarih_eslesme:
            gun, ay, yil = tarih_eslesme.groups()
            # Tarihi veritabanına uygun formata (YYYY-MM-DD) çeviriyoruz
            bulunan_tarih = datetime.strptime(f"{yil}-{ay}-{gun}", "%Y-%m-%d").date()

        # --- 2. TOPLAM TUTAR BULMA (Regex) ---
        # "TOPLAM", "TOP", "TPL" gibi kelimelerden sonra gelen sayıları arar (Örn: TOPLAM *150,50)
        tutar_sablonu = r'(?i)(?:TOPLAM|TOP|TPL|TUTAR)[^\d]*(\d+[.,]\d{2})'
        tutar_eslesme = re.search(tutar_sablonu, okunan_metin)
        
        bulunan_tutar = None
        if tutar_eslesme:
            # Bulunan tutarı string'den float'a çeviriyoruz (Örn: "150,50" -> 150.50)
            tutar_str = tutar_eslesme.group(1).replace(',', '.')
            bulunan_tutar = float(tutar_str)

        return {
            "basarili": True,
            "tarih": bulunan_tarih,
            "toplam_tutar": bulunan_tutar,
            "satici": "Belirlenemedi" # Satıcı adı bulmak çok karmaşıktır, şimdilik sabit tutuyoruz
        }

    except Exception as e:
        # Eğer okuma sırasında resim bozuksa vs. hata verirse sistemi çökertmiyoruz
        print(f"OCR Hatası: {e}")
        return {
            "basarili": False,
            "hata_mesaji": "Fiş okunamadı, lütfen manuel giriniz."
        }