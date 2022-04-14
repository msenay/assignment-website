import threading
import json
import websocket
import datetime
from redis_files.redis_constructor import RedisConstructor


class WsConnect(threading.Thread):
    def __init__(self, symbol):
        threading.Thread.__init__(self)
        self.socket = f'wss://stream.binance.com:9443/ws/{symbol}@trade'  # ethusdt@trade
        self.wsapp = websocket.WebSocketApp(self.socket, on_message=self.on_message, on_error=self.on_error)
        self.wsapp.run_forever()

    def on_message(cls, wsapp, message):
        json_message = json.loads(message)
        cls.handle_trades(json_message=json_message)

    @staticmethod
    def on_error(wsapp, error):
        print(error)

    @staticmethod
    def handle_trades(json_message):
        date_time = datetime.datetime.fromtimestamp(json_message['E'] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        print("SYMBOL: " + json_message['s'])
        print("PRICE: " + json_message['p'])
        print("QTY: " + json_message['q'])
        print("TIMESTAMP: " + str(date_time))
        print("-----------------------")

        # we can set this data to redis key and get the value from this key [CHOSEN]
        r = RedisConstructor()
        r.set_datas(json_message['s'], json_message['p'])
        # or we can write this live price to json.data and read whenever we want and show it to user

        # data = {"symbol": json_message['s'], "price": json_message['p']}
        # user_choice_json = json.dumps(data)
        # with open('json_data.json', 'w') as outfile:
        # outfile.write(user_choice_json)

        # or we can publish this then we can listen with redis_listener which is in redis_files
        # r.publish()
