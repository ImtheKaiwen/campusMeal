import requests
import tabula
import pandas as pd
import serpapi
import re
from datetime import datetime
import os
import json
from bs4 import BeautifulSoup
from flask import Blueprint, request, jsonify, Response, current_app

# --- Ayarlar ---
PDF_FILE = "menu_temp.pdf" # Geçici PDF dosyası adı

# --- PDF İşleme Fonksiyonları (KBÜ İçin) ---

def download_pdf(url, filename=PDF_FILE):
    try:
        print(f"PDF indiriliyor: {url}")
        r = requests.get(url, timeout=30, verify=False) # verify=False SSL hatalarını bazen çözer
        with open(filename, "wb") as f:
            f.write(r.content)
        print(f"{filename} dosyası başarıyla indirildi.")
        return filename
    except Exception as e:
        print(f"PDF indirme hatası: {e}")
        return None

def search_pdf_links(query="KBÜ yemek listesi"):
    SERPAPI_KEY = "30d1fe0270635bcfd931d6b5afe8d20d773f4542c176c0f703e1ec61ea8724b4" 
    
    # Artık katı bir klasör yolu yerine sadece domain kontrolü yapacağız
    TARGET_DOMAIN = "karabuk.edu.tr"
    
    try:
        client_serp = serpapi.Client(api_key=SERPAPI_KEY)
        print(f"Google'da '{query}' için PDF aranıyor...")
        
        # Arama sorgusunu biraz daha spesifikleştirelim
        current_month = datetime.now().strftime("%B %Y") # Örn: October 2025
        search_query = f"{query} {current_month} filetype:pdf"
        
        result = client_serp.search({"q": search_query, "engine": "google"})
        
        links = []
        if "organic_results" in result:
            for item in result["organic_results"]:
                link = item.get("link")
                # Link varsa, karabuk.edu.tr içeriyorsa ve pdf ile bitiyorsa al
                if link and TARGET_DOMAIN in link and link.lower().endswith(".pdf"):
                    links.append(link)
        
        if not links:
            print("Google API ile uygun formatta PDF linki bulunamadı.")
            # Fallback: Eğer API bulamazsa belki sabit bir link denenebilir (Opsiyonel)
            return None
            
        print(f"Link bulundu: {links[0]}")
        return links[0]
    except Exception as e:
        print(f"Google arama hatası (SerpApi): {e}")
        return None

def extract_menus_from_pdf(pdf_path):
    """
    PDF'ten menüyü okur. Resmi tatil günlerini ve birleşik sütunları düzgün ayrıştırır.
    """
    print(f"{pdf_path} dosyası 'tabula' ile işleniyor...")
    
    try:
        # java_options parametresi büyük dosyalar için bellek artırımı sağlar
        tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True, java_options="-Djava.awt.headless=true")
    except Exception as e:
        print(f"Tabula kütüphanesi hatası: {e}")
        return {}
    
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

            # --- DURUM 1: Tek Sütun (Normal) ---
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

            # --- DURUM 2: Birleşik Sütunlar (Resmi Tatil Kontrollü) ---
            elif len(matches) == 2:
                (date1, day1), (date2, day2) = matches
                for d, day in [(date1, day1), (date2, day2)]:
                    if d not in all_data:
                        all_data[d] = {"day": day, "dishes": []}
                
                # O günlere ait satırları topla
                raw_lines = []
                j = i + 1
                while j < len(col_values) and not date_day_pattern.findall(col_values[j]):
                    val = col_values[j].strip()
                    if val.lower() != "nan" and val != "":
                        raw_lines.append(val)
                    j += 1
                
                # Tatil hangi tarafta kontrol et
                holiday_side = -1 # 0: Sol, 1: Sağ
                for line in raw_lines:
                    if "RESMİ TATİL" in line.upper() or "RESMI TATIL" in line.upper():
                        parts = re.split(r'(RESM[İI]\s+TAT[İI]L)', line, flags=re.IGNORECASE)
                        parts = [p.strip() for p in parts if p.strip()]
                        if len(parts) > 0 and "RESMİ TATİL" in parts[0].upper():
                            holiday_side = 0
                        elif len(parts) > 1:
                            holiday_side = 1
                        break

                # Satırları dağıt
                for val in raw_lines:
                    val_upper = val.upper()
                    
                    # Eğer satırda 'RESMİ TATİL' yazıyorsa
                    if "RESMİ TATİL" in val_upper or "RESMI TATIL" in val_upper:
                        parts = re.split(r'(RESM[İI]\s+TAT[İI]L)', val, flags=re.IGNORECASE)
                        parts = [p.strip() for p in parts if p.strip()]
                        
                        if len(parts) >= 1: all_data[date1]["dishes"].append(parts[0])
                        if len(parts) >= 2: all_data[date2]["dishes"].append(" ".join(parts[1:]))
                            
                    # Normal yemek satırı
                    else:
                        dishes = [d.strip()+')' for d in val.replace(')', ')|').split('|') if d.strip()]
                        if not dishes: continue

                        if len(dishes) >= 2:
                            mid = len(dishes) // 2
                            all_data[date1]["dishes"].append(' '.join(dishes[:mid]))
                            all_data[date2]["dishes"].append(' '.join(dishes[mid:]))
                        elif len(dishes) == 1:
                            single_dish = dishes[0]
                            if holiday_side == 0: all_data[date2]["dishes"].append(single_dish)
                            elif holiday_side == 1: all_data[date1]["dishes"].append(single_dish)
                            else: all_data[date1]["dishes"].append(single_dish) # Varsayılan
                i = j
            
            else:
                i += 1
                
    print("PDF başarıyla işlendi.")
    return all_data

# --- Cache Yönetimi ---

def update_menu_cache(fetch_fn, university: str):
    safe_uni = university.lower().replace("ü", "u").replace("ö", "o").replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ğ", "g")
    DATA_FILE = f"menu_data_{safe_uni}.json"
    META_FILE = f"menu_meta_{safe_uni}.json"
    
    today = datetime.now()
    needs_update = False

    if not os.path.exists(DATA_FILE) or not os.path.exists(META_FILE):
        needs_update = True
    else:
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("year") != today.year or meta.get("month") != today.month:
                needs_update = True
        except (json.JSONDecodeError, KeyError):
            needs_update = True

    if needs_update:
        print(f"{university} için veri güncelleniyor...")
        menu_data = fetch_fn()
        
        if menu_data:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(menu_data, f, ensure_ascii=False, indent=2)
            
            with open(META_FILE, "w", encoding="utf-8") as f:
                json.dump({"year": today.year, "month": today.month, "university": university, "last_update": str(today)}, f)
            
            print(f"{university} menüsü '{DATA_FILE}' dosyasına kaydedildi.")
            return menu_data
        else:
            print(f"{university} menü verisi çekilemedi.")
            if os.path.exists(DATA_FILE):
                 print("Eski cache dosyasından veri dönülüyor...")
                 with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
    else:
        print(f"{university} verisi güncel, '{DATA_FILE}' dosyasından okunuyor.")
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

# --- Üniversite Menü Fonksiyonları ---

def get_ktu_menu():
    print("KTÜ Web sitesinden veri çekiliyor...")
    url = "https://sks.ktu.edu.tr/yemeklistesi"
    try:
        resp = requests.get(url, timeout=10, verify=False)
        resp.encoding = "utf-8"
        html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return {}

        day_tr_map = {
            "Monday": "PAZARTESİ", "Tuesday": "SALI", "Wednesday": "ÇARŞAMBA",
            "Thursday": "PERŞEMBE", "Friday": "CUMA", "Saturday": "CUMARTESİ", "Sunday": "PAZAR"
        }

        result = {}
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 5: continue

            date_str = cols[0].get_text(strip=True)
            try:
                date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                day_name = day_tr_map.get(date_obj.strftime("%A"), "GÜN")
            except:
                continue

            dishes = [cols[i].get_text(strip=True) for i in range(1,5)]
            result[date_str] = {"day": day_name, "dishes": dishes}

        return result
    except Exception as e:
        print(f"KTÜ hatası: {e}")
        return {}

def get_kbu_menu():
    """KBÜ menüsünü PDF’den çeker."""
    
    # 1. Google'dan Linki Bul ve İndir (Hata olursa devam et)
    try:
        # Yıl ve Ay bilgisini ekleyerek aramayı netleştiriyoruz
        date_query = datetime.now().strftime("%B %Y")
        query = f"KBÜ yemek listesi {date_query}"
        
        pdf_url = search_pdf_links(query) 
        
        if pdf_url:
            download_pdf(pdf_url, PDF_FILE)
        else:
            print("Link bulunamadı, varsa yerel dosya kullanılacak.")
            
    except Exception as e:
        print(f"Link arama/indirme sürecinde hata: {e}")

    # 2. Dosyayı İşle (İndirildiyse veya zaten varsa)
    if os.path.exists(PDF_FILE):
        print(f"Yerel dosya ({PDF_FILE}) bulundu, işleniyor...")
        try:
            menu_data = extract_menus_from_pdf(PDF_FILE)
            # İsteğe bağlı: Geçici dosyayı temizle
            os.remove(PDF_FILE)
            return menu_data
        except Exception as e:
             print(f"PDF işlenirken hata: {e}")
             return {}
    else:
        print(f"İşlenecek PDF dosyası ({PDF_FILE}) bulunamadı.")
        return {}