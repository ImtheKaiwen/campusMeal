import requests
import tabula
import pandas as pd # tabula, pandas dataframe'i döndürdüğü için gerekli
import serpapi
import re
from datetime import datetime
import os
import json
from bs4 import BeautifulSoup
# --- Sabit Dosya İsimleri ---
META_FILE = "menu_meta.json"
PDF_FILE = "menu.pdf"
# İşlenmiş veriyi saklayacağımız yer:
MENU_DATA_JSON = "menu_data.json"

# --- 1. PDF İndirme ve Arama ---

def download_pdf(url, filename=PDF_FILE):
    """Verilen URL'den PDF dosyasını indirir."""
    print(f"PDF indiriliyor: {url}")
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)
    print(f"{filename} dosyası başarıyla indirildi.")
    return filename

def search_pdf_links(query="KBÜ yemek listesi"):
    """Google'da arama yaparak en güncel PDF linkini bulur."""
    SERPAPI_KEY = "30d1fe0270635bcfd931d6b5afe8d20d773f4542c176c0f703e1ec61ea8724b4"
    PDF_BASE_DOMAIN = "https://sks.karabuk.edu.tr/yuklenen/dosyalar/"
    client_serp = serpapi.Client(api_key=SERPAPI_KEY)

    print("Google'da en güncel menü linki aranıyor...")
    result = client_serp.search({
        "q": query,
        "engine": "google"
    })
    
    links = []
    for item in result.get("organic_results", []):
        link = item.get("link")
        if link and link.startswith(PDF_BASE_DOMAIN) and link.endswith(".pdf"):
            links.append(link)
    
    if not links:
        raise Exception("Google aramasında SKS'den PDF linki bulunamadı.")
        
    print(f"En güncel link bulundu: {links[0]}")
    # En güncel olanın ilk link olduğunu varsayıyoruz
    return links[0]

# --- 2. PDF İşleme (Ağır İşlem) ---

def extract_menus_from_pdf(pdf_path):
    """
    PDF'den yemek menülerini tarih bazlı olarak çıkarır.
    (Bu sizin orijinal fonksiyonunuz, iyi çalışıyorsa dokunmayalım)
    """
    print(f"{pdf_path} dosyası 'tabula' ile işleniyor... (Bu işlem yavaş olabilir)")
    tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
    if not tables:
        print("PDF içinde 'tabula' tarafından okunabilen tablo bulunamadı.")
        return {}
        
    df = tables[0]
    date_day_pattern = re.compile(r'(\d{2}\.\d{2}\.\d{4})\s+(\w+)', re.UNICODE)
    all_data = {}
    for col in df.columns:
        col_values = df[col].astype(str).tolist()
        i = 0
        while i < len(col_values):
            cell = col_values[i].strip()
            if cell.lower() == "nan" or cell == "":
                i += 1
                continue

            matches = date_day_pattern.findall(cell)
            if not matches:
                i += 1
                continue

            if len(matches) == 1:
                date, day = matches[0]
                if date not in all_data:
                    all_data[date] = {"day": day, "dishes": []}
                j = i + 1
                while j < len(col_values) and not date_day_pattern.findall(col_values[j]):
                    val = col_values[j].strip()
                    if val.lower() != "nan" and val != "":
                        all_data[date]["dishes"].append(val)
                    j += 1
                i = j

            elif len(matches) == 2:
                (date1, day1), (date2, day2) = matches
                for d, day in [(date1, day1), (date2, day2)]:
                    if d not in all_data:
                        all_data[d] = {"day": day, "dishes": []}

                j = i + 1
                while j < len(col_values) and not date_day_pattern.findall(col_values[j]):
                    val = col_values[j].strip()
                    if val.lower() != "nan" and val != "":
                        # Orijinal mantığınızdaki ')' ve '|' ayırması
                        dishes = [d.strip()+')' for d in val.replace(')', ')|').split('|') if d.strip()]
                        mid = len(dishes)//2
                        all_data[date1]["dishes"].append(' '.join(dishes[:mid]))
                        all_data[date2]["dishes"].append(' '.join(dishes[mid:]))
                    j += 1
                i = j
            else:
                i += 1
                
    print("PDF başarıyla işlendi ve menü verisi çıkarıldı.")
    return all_data

# --- 3. Cache (JSON) Yönetimi ---

def update_menu_data():
    """
    Bu, "AĞIR" fonksiyondur. 
    PDF'i indirir, Tabula ile işler ve sonucu JSON'a yazar.
    Sadece gerektiğinde (ayda bir) çalışmalıdır.
    """
    print("Yeni menü verisi oluşturuluyor... (Ağır işlem)")
    try:
        # 1. En güncel PDF linkini bul
        pdf_url = search_pdf_links()
        
        # 2. PDF'i indir
        download_pdf(pdf_url)
        
        # 3. PDF'i işle (En ağır kısım)
        menu_data = extract_menus_from_pdf(PDF_FILE)
        
        if not menu_data:
            print("PDF işlenemedi, menü verisi boş. Cache güncellenmiyor.")
            return {}
            
        # 4. İşlenmiş veriyi JSON'a kaydet (Türkçe karakterler için utf-8)
        with open(MENU_DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(menu_data, f, ensure_ascii=False, indent=2)
            
        # 5. Meta dosyasını güncelle
        today = datetime.now()
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump({"year": today.year, "month": today.month}, f)
            
        # 6. (YENİ) Başarıyla işlendi, artık PDF'e gerek yok.
        try:
            if os.path.exists(PDF_FILE):
                os.remove(PDF_FILE)
                print(f"{PDF_FILE} başarıyla işlendi ve silindi.")
        except Exception as e:
            # Silme işlemi başarısız olursa ana program çökmesin, sadece uyarı versin
            print(f"Uyarı: {PDF_FILE} silinirken bir hata oluştu: {e}")
            
        print("Yeni menü verisi başarıyla oluşturuldu ve cache'lendi.")
        return menu_data
        
    except Exception as e:
        print(f"Menü güncellenirken hata oluştu: {e}")
        # Hata durumunda boş bir sözlük veya eski veri döndürülebilir
        return {}

def get_menu_data():
    """
    Bu, "HAFİF" fonksiyondur. API bunu çağırır.
    Cache (JSON) dosyasının güncel olup olmadığını kontrol eder.
    Güncelse, sadece dosyadan okur. Değilse, ağır fonksiyonu tetikler.
    """
    today = datetime.now()
    needs_update = False

    # 1. Hiç JSON dosyası yoksa, güncelleme gerekir
    if not os.path.exists(MENU_DATA_JSON):
        print("Cache (menu_data.json) bulunamadı, güncelleme gerekiyor.")
        needs_update = True
    else:
        # 2. Meta dosyası yoksa veya ay/yıl uyuşmuyorsa güncelleme gerekir
        try:
            if not os.path.exists(META_FILE):
                print("Meta dosyası bulunamadı, güncelleme gerekiyor.")
                needs_update = True
            else:
                with open(META_FILE, "r") as f:
                    meta = json.load(f)
                if meta.get("year") != today.year or meta.get("month") != today.month:
                    print("Yeni ay/yıl algılandı, güncelleme gerekiyor.")
                    needs_update = True
        except json.JSONDecodeError:
            print("Meta dosyası bozuk, güncelleme gerekiyor.")
            needs_update = True

    # 3. Güncelleme kararı
    if needs_update:
        # Ağır işlemi çalıştır ve sonucu döndür
        return update_menu_data()
    else:
        # Sadece hızlıca cache'den oku
        print("Cache (menu_data.json) yükleniyor...")
        try:
            with open(MENU_DATA_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"HATA: {MENU_DATA_JSON} dosyası bozuk. Yeniden oluşturuluyor.")
            # JSON dosyası bozuksa, ağır işlemi tetikle
            return update_menu_data()

def get_ktu_menu():
    url = "https://sks.ktu.edu.tr/yemeklistesi"
    resp = requests.get(url)
    resp.encoding = "utf-8"
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return {}

    day_tr_map = {
        "Monday": "PAZARTESİ",
        "Tuesday": "SALI",
        "Wednesday": "ÇARŞAMBA",
        "Thursday": "PERŞEMBE",
        "Friday": "CUMA",
        "Saturday": "CUMARTESİ",
        "Sunday": "PAZAR"
    }

    result = {}

    rows = table.find_all("tr")
    for row in rows[1:]:  # Başlık satırını atla
        cols = row.find_all("td")
        if len(cols) < 6:
            continue

        date_str = cols[0].get_text(strip=True)
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            day_name = day_tr_map[date_obj.strftime("%A")]
        except:
            continue

        dishes = [
            cols[1].get_text(strip=True),
            cols[2].get_text(strip=True),
            cols[3].get_text(strip=True),
            cols[4].get_text(strip=True)
        ]

        result[date_str] = {
            "day": day_name,
            "dishes": dishes
        }

    return result
