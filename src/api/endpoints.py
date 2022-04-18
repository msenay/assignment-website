from flask import current_app as app
from flask import jsonify, request, render_template
from src.api.controllers.binance_controller import WsConnect
from redis_files.redis_constructor import RedisConstructor

user_price = 0


@app.route("/websocket", methods=['POST'])
def websock():
    if request.method == "POST":
        global user_price
        entry_content = request.get_json()  # { "symbol":"BTC", "price" : "42000" }
        user_price = entry_content['price']
        x = WsConnect(entry_content["symbol"])
        x.start()
        r = RedisConstructor()
        market_price = r.get_data("price")
        print(r.get_data("price"))
        return jsonify({"results": market_price})
    else:
        return jsonify({"status": False, "message": "Method Not Allowed! ['POST'] Only"}), 405


@app.route("/live_price", methods=['GET'])
def screen():
    if request.method == "GET":
        y = RedisConstructor()
        if user_price == 0:
            return jsonify({"Symbol": y.get_datas()[0].decode(), "price": y.get_datas()[1].decode()})
        else:
            print(y.get_datas())
            return jsonify({"Symbol": y.get_datas()[0].decode(), "price": y.get_datas()[1].decode(),
                           "user": user_price})
    return jsonify({"status": False, "message": "Method Not Allowed! ['GET'] Only"}), 405


@app.route("/", methods=['GET'])
def home():
    return render_template('web.html')
