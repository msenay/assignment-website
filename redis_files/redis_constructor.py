import redis


class RedisConstructor:
    r = redis.StrictRedis(host='localhost', port=6379, db=4)

    def set_datas(self, symbol, price):
        data = {'symbol': symbol, 'price': price}
        return self.r.mset(data)

    def set_data(self, frame):
        return self.r.set('price', frame)

    def get_data(self, key):
        return self.r.get(key)

    def get_datas(self):
        return self.r.mget('symbol', 'price')

    def publish(self, *args, **kwargs):
        return self.r.publish(*args, **kwargs)
