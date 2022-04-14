FROM python:slim-bullseye
COPY . /app
WORKDIR /app

# timezone conf
ENV TZ=Europe/Istanbul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && dpkg-reconfigure -f noninteractive tzdata
# upgrade pip && -r requirements.txt
RUN apt update && apt install redis-server -y
RUN pip install --upgrade pip
RUN pip install -r requirements.txt  --default-timeout=300 future

# exec change mode shell script ... run.sh
RUN chmod +x run.sh

EXPOSE 5000
CMD ./run.sh