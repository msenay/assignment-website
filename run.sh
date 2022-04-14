export TZ=$APP_TIMEZONE
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && dpkg-reconfigure -f noninteractive tzdata
service redis-server start && python ./app.py