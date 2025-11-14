from flask import Flask, jsonify
from flask_cors import CORS
from routes import bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(bp)

# Global hata yakalama
@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
