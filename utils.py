import requests
import fitz
import tabula
import pandas as pd
import serpapi
import re
from datetime import datetime

def download_pdf(url, filename="menu.pdf"):
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)
    return filename

def extract_pdf_text(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def pdf_to_excel(path="menu.pdf",output = "output.xlsx"):
    tables = tabula.read_pdf(path, pages="all", multiple_tables=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for i, table in enumerate(tables):
            table.to_excel(writer, sheet_name=f"Sayfa_{i+1}", index=False)

def search_pdf_links(query="KBÜ yemek listesi"):
    SERPAPI_KEY = "30d1fe0270635bcfd931d6b5afe8d20d773f4542c176c0f703e1ec61ea8724b4"
    PDF_BASE_DOMAIN = "https://sks.karabuk.edu.tr/yuklenen/dosyalar/"
    client_serp = serpapi.Client(api_key=SERPAPI_KEY)

    result = client_serp.search({
        "q": query,
        "engine": "google"
    })
    links = []
    for item in result.get("organic_results", []):
        link = item.get("link")
        if link and link.startswith(PDF_BASE_DOMAIN) and link.endswith(".pdf"):
            links.append(link)
    return links

def extract_menus_from_excel(path):
    sheets = pd.read_excel(path, sheet_name=None , engine='openpyxl')
    all_data = {}

    date_pattern = re.compile(r'\b\d{2}\.\d{2}\.\d{4}\b')

    for sheet_name, df in sheets.items():
        for col in df.columns:
            col_values = df[col].dropna().astype(str).tolist()

            current_date = None

            for value in col_values:
                if date_pattern.search(value):
                    current_date = value.strip()
                    if current_date not in all_data:
                        all_data[current_date] = []
                elif current_date:
                    if len(value.strip()) < 2:
                        continue
                    all_data[current_date].append(value.strip())

    return all_data

def get_today_menu(menus):
    today = datetime.now().strftime("%d.%m.%Y")
    for key in menus:
        match = re.match(r"(\d{2}\.\d{2}\.\d{4})", key)
        if match:
            key_date = match.group(1)
            if key_date == today:
                return menus[key]
    return None


def set_new_list():
    links = search_pdf_links()
    download_pdf(links[0])
    return extract_menus_from_pdf("menu.pdf")


def extract_menus_from_pdf(pdf_path):
    """
    PDF'den yemek menülerini tarih bazlı olarak çıkarır.
    Hücrede birden fazla tarih veya yemek varsa düzgün şekilde ayırır.
    """
    tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
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

    return all_data

