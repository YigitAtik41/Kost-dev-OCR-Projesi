import pytesseract
from PIL import Image, ImageEnhance
import re
from datetime import datetime
import io

# Tesseract'ın kurulu olduğu yol
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def fisi_analiz_et(resim_bytes):
    try:
        image = Image.open(io.BytesIO(resim_bytes))
        
        # --- GÖRÜNTÜ İYİLEŞTİRME ---
        image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        okunan_metin = pytesseract.image_to_string(image, lang='tur')
        
        print("--- TESSERACT'IN OKUDUĞU HAM METİN ---")
        print(okunan_metin)
        print("--------------------------------------")
        
        # --- 1. TARİH BULMA ---
        tarih_sablonu = r'(\d{2})[./-](\d{2})[./-](\d{4})'
        tarih_eslesme = re.search(tarih_sablonu, okunan_metin)
        
        bulunan_tarih = None
        if tarih_eslesme:
            gun, ay, yil = tarih_eslesme.groups()
            bulunan_tarih = datetime.strptime(f"{yil}-{ay}-{gun}", "%Y-%m-%d").date()

        # --- 2. TOPLAM TUTAR BULMA ---
        bulunan_tutar = None
        
        # YÖNTEM A: Doğrudan "Toplam" yazısını ve yanındaki sayıyı bulmaya çalış
        tutar_sablonu = r'(?i)(?:TOPLAM|TOPLAN|GENEL|TOP|TPL|TUTAR)[^\d\n]*\n?[^\d]*(\d+[.,]\d{2})'
        tutar_eslesme = re.search(tutar_sablonu, okunan_metin)
        
        if tutar_eslesme:
            tutar_str = tutar_eslesme.group(1).replace(',', '.')
            bulunan_tutar = float(tutar_str)
            
        # YÖNTEM B (MATEMATİKSEL FALLBACK): Eğer Toplam rakamı silik çıkmış ve okunamamışsa!
        # Alınan Para'dan Para Üstünü çıkararak toplamı kendimiz hesaplıyoruz.
        if bulunan_tutar is None:
            alinan_sablon = r'(?i)ALINAN[^0-9]*(\d+[.,]\d{2})'
            para_ustu_sablon = r'(?i)PARA\s*(?:ÜSTÜ|USTU)[^0-9]*(\d+[.,]\d{2})'
            
            alinan_eslesme = re.search(alinan_sablon, okunan_metin)
            para_ustu_eslesme = re.search(para_ustu_sablon, okunan_metin)
            
            if alinan_eslesme and para_ustu_eslesme:
                alinan_float = float(alinan_eslesme.group(1).replace(',', '.'))
                para_ustu_float = float(para_ustu_eslesme.group(1).replace(',', '.'))
                # İkisini birbirinden çıkarıp virgülden sonra 2 basamağa yuvarlıyoruz
                bulunan_tutar = round(alinan_float - para_ustu_float, 2)
                print(f"B PLAN DEVREDE: Toplam okunamadı, Alınan({alinan_float}) - Üstü({para_ustu_float}) ile {bulunan_tutar} hesaplandı.")

        return {
            "basarili": True,
            "tarih": bulunan_tarih,
            "toplam_tutar": bulunan_tutar,
            "satici": "Belirlenemedi"
        }

    except Exception as e:
        print(f"OCR Hatası: {e}")
        return {
            "basarili": False,
            "hata_mesaji": "Fiş okunamadı, lütfen manuel giriniz."
        }