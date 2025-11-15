from flask import Blueprint, jsonify, Response
from utils import set_new_list, get_today_menu
import json
bp = Blueprint("bp", __name__)

@bp.route("/getlatestmenu", methods=["GET"])
def get_latest_menu():
    menu = set_new_list()
    today_menu = get_today_menu(menu)

    if today_menu:
        return jsonify(menu)
    else:
        return Response(
            json.dumps({"message": "Bugün için menü bulunamadı."}, ensure_ascii=False),
            mimetype='application/json'
        )


