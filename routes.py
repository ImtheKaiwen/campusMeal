from flask import Blueprint,jsonify, Response
import json
from datetime import datetime
from utils import set_new_list,get_today_menu
bp = Blueprint("bp",__name__)

menu_cache = None
last_update = None

# @bp.route("/getlatestmenu", methods=["GET"])
# def get_latest_menu():
#     global menu_cache, last_update

#     # Menü hiç yoksa veya 1 günden eskiyse yenile
#     if not menu_cache or (datetime.now() - last_update).days >= 1:
#         menu_cache = set_new_list()
#         last_update = datetime.now()

#     today_menu = get_today_menu(menu_cache)

#     if today_menu:
#         return jsonify({
#             "date": datetime.now().strftime("%d.%m.%Y"),
#             "menu": today_menu
#         })
#     else:
#         return jsonify({
#             "message": "Bugün için menü bulunamadı."
#         }), 404
    
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