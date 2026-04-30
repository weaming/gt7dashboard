#!/usr/bin/env bash

docker rm -f gt7-dashboard
docker run -d --restart unless-stopped \
    --name gt7-dashboard \
    -p 5006:5006/tcp \
    -p 33740:33740/udp \
    -v $DL/gt7data/:/usr/src/app/data \
    -e BOKEH_ALLOW_WS_ORIGIN='*' \
    -e GT7_PLAYSTATION_IP=192.168.1.100 \
    -e TZ=Asia/Shanghai \
    -e GT7_ADD_BRAKEPOINTS=true \
    gt7-dashboard