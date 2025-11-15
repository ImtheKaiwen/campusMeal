import requests
import tabula
import pandas as pd
import serpapi
import re
from datetime import datetime
import os
import json
from bs4 import BeautifulSoup

# --- Sabit Dosya İsimleri ---
META_FILE = "menu_meta.json"
PDF_FILE = "menu.pdf"
MENU_DATA_JSON = "menu_data.json"

# --- PDF İndirme ve İşleme Fonksiyonları ---

def download_pdf(url, filename=PDF_FILE):
    print(f"PDF indiriliyor: {url}")
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)
    print(f"{filename} dosyası başarıyla indirildi.")
    return filename

def search_pdf_links(query="KBÜ yemek listesi"):
    SERPAPI_KEY = "30d1fe0270635bcfd931d6b5afe8d20d773f4542c176c0f703e1ec61ea8724b4"
    PDF_BASE_DOMAIN = "https://sks.karabuk.edu.tr/yuklenen/dosyalar/"
    client_serp = serpapi.Client(api_key=SERPAPI_KEY)

    print("Google'da en güncel menü linki aranıyor...")
    result = client_serp.search({"q": query, "engine": "google"})
    
    links = []
    for item in result.get("organic_results", []):
        link = item.get("link")
        if link and link.startswith(PDF_BASE_DOMAIN) and link.endswith(".pdf"):
            links.append(link)
    
    if not links:
        raise Exception("Google aramasında SKS'den PDF linki bulunamadı.")
        
    print(f"En güncel link bulundu: {links[0]}")
    return links[0]

def extract_menus_from_pdf(pdf_path):
    print(f"{pdf_path} dosyası 'tabula' ile işleniyor...")
    tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
    if not tables:
        print("PDF içinde tablo bulunamadı.")
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

# --- Cache Yönetimi (Tek JSON) ---

def update_menu_cache(fetch_fn, university: str):
    """
    fetch_fn -> üniversiteye özel menü çekme fonksiyonu
    university -> seçilen üniversite ismi
    Menü verisi güncel değilse çalıştırır, tek bir JSON'a yazar.
    """
    today = datetime.now()
    needs_update = False

    if not os.path.exists(MENU_DATA_JSON) or not os.path.exists(META_FILE):
        needs_update = True
    else:
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("year") != today.year or meta.get("month") != today.month or meta.get("university") != university:
                needs_update = True
        except json.JSONDecodeError:
            needs_update = True

    if needs_update:
        menu_data = fetch_fn()
        if menu_data:
            with open(MENU_DATA_JSON, "w", encoding="utf-8") as f:
                json.dump(menu_data, f, ensure_ascii=False, indent=2)
            with open(META_FILE, "w", encoding="utf-8") as f:
                json.dump({"year": today.year, "month": today.month, "university": university}, f)
            print(f"{university} menüsü güncellendi ve cache'e yazıldı.")
        else:
            print(f"{university} menü verisi çekilemedi, cache güncellenmedi.")
        return menu_data
    else:
        with open(MENU_DATA_JSON, "r", encoding="utf-8") as f:
            return json.load(f)


# --- Üniversiteye Özel Menü Fonksiyonu (Örnek: KTU) ---

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
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 6:
            continue

        date_str = cols[0].get_text(strip=True)
        try:
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            day_name = day_tr_map[date_obj.strftime("%A")]
        except:
            continue

        dishes = [cols[i].get_text(strip=True) for i in range(1,5)]

        result[date_str] = {"day": day_name, "dishes": dishes}

    return result



def get_kbu_menu():
    """KBÜ menüsünü PDF’den çekip sözlük olarak döndürür."""
    try:
        pdf_url = search_pdf_links("KBÜ yemek listesi")
        download_pdf(pdf_url)
        menu_data = extract_menus_from_pdf(PDF_FILE)
        if os.path.exists(PDF_FILE):
            os.remove(PDF_FILE)
        return menu_data
    except Exception as e:
        print(f"KBÜ menü çekilirken hata oluştu: {e}")
        return {}