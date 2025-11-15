from flask import Flask, jsonify
from flask_cors import CORS
from routes import bp # routes.py dosyamızdan blueprint'i import ediyoruz
import os

app = Flask(__name__)
CORS(app) # Cross-Origin-Resource-Sharing'e izin ver

# routes.py'de tanımladığımız rotaları uygulamaya kaydediyoruz
app.register_blueprint(bp)

# Global hata yakalama
@app.errorhandler(Exception)
def handle_exception(e):
    """
    Uygulamanın herhangi bir yerinde yakalanamayan bir hata olursa
    bu fonksiyon çalışır ve düzgün bir JSON hatası döndürür.
    """
    print(f"Global Hata Yakalandı: {e}") 
    return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Sunucunun belirlediği PORT'u al, yoksa 5000 kullan
    port = int(os.environ.get("PORT", 5000))
    
    # --- EN ÖNEMLİ DEĞİŞİKLİK ---
    # debug=True modu sunucuda ASLA kullanılmamalıdır.
    # Ciddi bellek sızıntılarına ve güvenlik açıklarına neden olur.
    # Sunucuda çalıştırmak için debug=False olmalıdır.
    app.run(debug=False, host="0.0.0.0", port=port)
