FROM node:12.16.1

WORKDIR /opt/admin

COPY ../../etc/caddy/Caddyfile Caddyfile
RUN npm install -g yarn
RUN yarn
RUN npm run build:prod
RUN wget "https://caddyserver.com/download/linux/amd64?license=personal&telemetry=on" -O caddy_linux_amd64.tar.xz
RUN tar zxvf caddy_linux_amd64.tar.xz
RUN mv caddy /usr/local/bin

sed -i "s?\/sapspa\/src\/admin\/dist/?\/opt\/admin\/dist?g" Caddyfile

EXPOSE 23380
