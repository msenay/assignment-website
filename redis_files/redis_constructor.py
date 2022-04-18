import redis


class RedisConstructor:
    """
        A class to set/get/publish data to Redis.
        ...
        Attributes
        ---------
        Methods
        -------
        set_datas(symbol, price):
            takes in coin's symbol and price and set them into redis server .
        set_data(price):
            takes in coin's price and set them into redis server .
        get_data(key):
            get data for a particular key
        get_datas():
            get datas from redis
        publish(*args, **kwargs):
            publish data to chosen channel
        """
    r = redis.StrictRedis(host='localhost', port=6379, db=4)

    def set_datas(self, symbol, price):
        data = {'symbol': symbol, 'price': price}
        return self.r.mset(data)

    def set_data(self, price):
        return self.r.set('price', price)

    def get_data(self, key):
        return self.r.get(key)

    def get_datas(self):
        return self.r.mget('symbol', 'price')

    def publish(self, *args, **kwargs):
        return self.r.publish(*args, **kwargs)
