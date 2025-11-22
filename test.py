import tabula
import pandas as pd
import re

def extract_menus_from_pdf(pdf_path):
    print(f"{pdf_path} dosyası 'tabula' ile işleniyor...")
    
    # lattice=True genellikle tablo çizgileri belirginse daha iyi sonuç verir, 
    # ama senin kodundaki parametrelerle devam ediyorum.
    tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
    
    if not tables:
        print("PDF içinde tablo bulunamadı.")
        return {}
        
    df = tables[0]
    
    # Regex: Tarih (01.01.2025) ve Gün (PAZARTESİ) yakalar
    date_day_pattern = re.compile(r'(\d{2}\.\d{2}\.\d{4})\s+(\w+)', re.UNICODE)
    
    all_data = {}
    
    for col in df.columns:
        col_values = df[col].astype(str).tolist()
        i = 0
        while i < len(col_values):
            cell = col_values[i].strip()
            
            # Boş veya NaN hücreleri atla
            if cell.lower() == "nan" or cell == "":
                i += 1
                continue

            matches = date_day_pattern.findall(cell)
            
            # Eğer hücrede tarih yoksa bir sonrakine geç
            if not matches:
                i += 1
                continue

            # ---------------------------------------------------------
            # DURUM 1: Tek sütunda tek gün varsa (Standart Durum)
            # ---------------------------------------------------------
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

            # ---------------------------------------------------------
            # DURUM 2: Tabula iki sütunu birleştirdiyse (Sorunlu Kısım)
            # ---------------------------------------------------------
            elif len(matches) == 2:
                (date1, day1), (date2, day2) = matches
                
                # Tarihleri sözlüğe ekle
                for d, day in [(date1, day1), (date2, day2)]:
                    if d not in all_data:
                        all_data[d] = {"day": day, "dishes": []}
                
                # --- ADIM 1: O bloğa ait tüm satırları önce bir listeye alalım ---
                raw_lines = []
                j = i + 1
                while j < len(col_values) and not date_day_pattern.findall(col_values[j]):
                    val = col_values[j].strip()
                    if val.lower() != "nan" and val != "":
                        raw_lines.append(val)
                    j += 1
                
                # --- ADIM 2: Tatil Kontrolü (Hangi taraf tatil?) ---
                # 0: Sol taraf (date1) tatil
                # 1: Sağ taraf (date2) tatil
                # -1: Tatil yok
                holiday_side = -1 
                
                for line in raw_lines:
                    line_upper = line.upper()
                    if "RESMİ TATİL" in line_upper or "RESMI TATIL" in line_upper:
                        # "RESMİ TATİL" yazısını ayırıp nerede durduğuna bakalım
                        # Regex, metni 'RESMİ TATİL'e göre böler
                        parts = re.split(r'(RESM[İI]\s+TAT[İI]L)', line, flags=re.IGNORECASE)
                        parts = [p.strip() for p in parts if p.strip()]
                        
                        # Eğer 'RESMİ TATİL' listenin başındaysa -> Sol taraf tatildir
                        # Örnek: ['RESMİ TATİL', 'ET DÖNER(450)'] -> Sol Tatil
                        if len(parts) > 0 and "RESMİ TATİL" in parts[0].upper():
                            holiday_side = 0
                        # Eğer başka bir şeyden sonra geliyorsa -> Sağ taraf tatildir (Nadir durum)
                        elif len(parts) > 1:
                            holiday_side = 1
                        break

                # --- ADIM 3: Satırları Dağıtma ---
                for val in raw_lines:
                    val_upper = val.upper()
                    
                    # A) Satırda bizzat "RESMİ TATİL" yazıyorsa:
                    if "RESMİ TATİL" in val_upper or "RESMI TATIL" in val_upper:
                        parts = re.split(r'(RESM[İI]\s+TAT[İI]L)', val, flags=re.IGNORECASE)
                        parts = [p.strip() for p in parts if p.strip()]
                        
                        # Parçaları sırayla günlere ata
                        # Genellikle: parts[0] -> date1, parts[1] -> date2 (varsa)
                        if len(parts) >= 1:
                            all_data[date1]["dishes"].append(parts[0])
                        if len(parts) >= 2:
                            all_data[date2]["dishes"].append(" ".join(parts[1:]))
                            
                    # B) Normal yemek satırıysa:
                    else:
                        # Yemekleri parantezlere göre ayır
                        dishes = [d.strip()+')' for d in val.replace(')', ')|').split('|') if d.strip()]
                        
                        if not dishes:
                            continue

                        # Eğer satırda 2 tane belirgin yemek varsa (Örn: Çorba | Çorba) -> Bölüştür
                        if len(dishes) >= 2:
                            mid = len(dishes) // 2
                            dish1 = ' '.join(dishes[:mid])
                            dish2 = ' '.join(dishes[mid:])
                            all_data[date1]["dishes"].append(dish1)
                            all_data[date2]["dishes"].append(dish2)
                        
                        # Eğer satırda TEK bir yemek varsa (Sorun çıkaran kısım burasıydı):
                        elif len(dishes) == 1:
                            single_dish = dishes[0]
                            
                            if holiday_side == 0:
                                # Sol taraf tatilse, bu tek yemek SAĞA (date2) aittir.
                                all_data[date2]["dishes"].append(single_dish)
                            elif holiday_side == 1:
                                # Sağ taraf tatilse, bu tek yemek SOLA (date1) aittir.
                                all_data[date1]["dishes"].append(single_dish)
                            else:
                                # Tatil yoksa ve tek satır varsa, Tabula genelde bunu sola yapıştırmıştır
                                # ama doğrusu bu belirsizdir. Standart olarak sola ekliyoruz (eski mantık)
                                # ya da yarıya bölemiyoruz.
                                all_data[date1]["dishes"].append(single_dish)

                i = j
            
            else:
                # 2'den fazla tarih varsa (beklenmeyen durum) atla
                i += 1
                
    print("PDF başarıyla işlendi ve menü verisi çıkarıldı.")
    return all_data

print(extract_menus_from_pdf("menu1.pdf"))