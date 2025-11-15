from flask import Blueprint, request, jsonify, Response
from utils import update_menu_cache, get_ktu_menu, get_kbu_menu
import json

bp = Blueprint("bp", __name__)

@bp.route("/menu", methods=["GET"])
def menu():
    uni = request.args.get("university", "KBÜ").upper()

    if uni == "KTÜ":
        fetch_fn = get_ktu_menu
    else:  
        fetch_fn = get_kbu_menu

    try:
        menu_data = update_menu_cache(fetch_fn, uni)
        if not menu_data:
            return Response(
                json.dumps({"message": f"{uni} menü verisi alınamadı veya boş."}, ensure_ascii=False),
                status=500,
                mimetype='application/json'
            )
        return jsonify(menu_data)
    except Exception as e:
        return Response(
            json.dumps({"error": f"Beklenmedik bir hata oluştu: {str(e)}"}, ensure_ascii=False),
            status=500,
            mimetype='application/json'
        )
