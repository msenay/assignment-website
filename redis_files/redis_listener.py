import threading
import redis


class Listener(threading.Thread):
    """
        A class to represent a listener in order to listen a particular channel in Redis.

        ...

        Attributes
        ----------
        r : redis connection

        """
    def __init__(self, r):
        threading.Thread.__init__(self)
        self.redis = r
        self.pub_sub = self.redis.pubsub()
        self.pub_sub.subscribe('channel')
        self.last_price = ""

    @staticmethod
    def final_price(item):
        print(item['channel'])
        return item['channel']

    def run(self):
        for item in self.pub_sub.listen():
            if item['data'] == b"KILL":
                self.pub_sub.unsubscribe()
                print(self, "unsubscribed and finished")
                break
            else:
                if type(item['data']) != int:
                    self.last_price = item['data']
                    self.final_price(item)


if __name__ == "__main__":
    r = redis.StrictRedis(host='localhost', port=6379, db=4)
    client = Listener(r)
    client.start()
