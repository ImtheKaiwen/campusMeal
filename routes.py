from flask import Blueprint, jsonify, Response
from utils import set_new_list, get_today_menu

bp = Blueprint("bp", __name__)

@bp.route("/getlatestmenu", methods=["GET"])
def get_latest_menu():
    try:
        menu = set_new_list()
        today_menu = get_today_menu(menu)
        if today_menu:
            return jsonify(menu)
        else:
            return Response(
                jsonify({"message": "Bugün için menü bulunamadı."}).get_data(as_text=True),
                mimetype='application/json'
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
