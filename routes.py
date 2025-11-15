from flask import Blueprint, jsonify, Response
# Sadece 'get_menu_data' fonksiyonunu import ediyoruz
from utils import get_menu_data
import json

bp = Blueprint("bp", __name__)

@bp.route("/getlatestmenu", methods=["GET"])
def get_latest_menu():
    """
    En güncel menü verisini (tüm ayın) JSON cache dosyasından okur.
    Cache güncel değilse, utils.py'deki fonksiyon yeni veriyi oluşturur.
    """
    try:
        # Sadece HAFİF (cache okuyan) fonksiyonu çağırıyoruz.
        menu = get_menu_data() 
        
        # Menü verisi (menu_data.json) bir sebepten boşsa veya oluşturulamamışsa
        if not menu:
             return Response(
                json.dumps({"message": "Menü verisi oluşturulamadı veya boş."}, ensure_ascii=False),
                status=500, # Sunucu taraflı bir sorun olduğunu belirtir
                mimetype='application/json'
            )

        # Başarılı: Tüm menü sözlüğünü (cache'lenen) döndür
        return jsonify(menu)
            
    except Exception as e:
        # utils.py'de bir hata oluşursa (örn: SKS sitesi çöktü, PDF linki bulunamadı)
        # Bu hatayı yakalayıp düzgün bir JSON mesajı olarak döneriz.
        print(f"Hata oluştu: {e}")
        return Response(
            json.dumps({"error": f"Beklenmedik bir hata oluştu: {str(e)}"}, ensure_ascii=False),
            status=500, # Sunucu Hatası
            mimetype='application/json'
        )

@bp.route("/ktü/menu", methods=["GET"])
def ktü_menu():
    """
    KTÜ yemek menüsünü SKS sayfasından çekip JSON olarak döner.
    Bu, test amaçlı basit bir scraper fonksiyonudur.
    """
    try:
        menu = get_ktu_menu()
        if not menu:
            return Response(
                json.dumps({"message": "KTÜ menü verisi alınamadı veya boş."}, ensure_ascii=False),
                status=500,
                mimetype='application/json'
            )
        return jsonify(menu)
    except Exception as e:
        print(f"KTÜ menü çekilirken hata oluştu: {e}")
        return Response(
            json.dumps({"error": f"Beklenmedik bir hata oluştu: {str(e)}"}, ensure_ascii=False),
            status=500,
            mimetype='application/json'
        )
