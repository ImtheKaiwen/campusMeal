from flask import Flask
from flask_cors import CORS
from routes import bp
app = Flask(__name__)
app.register_blueprint(bp)
CORS(app)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
