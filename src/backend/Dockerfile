FROM python:3.7.5

WORKDIR /opt/backend
COPY . /opt/backend/

RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt

RUN unzip nwrfc750P_4-70002752.zip
RUN mkdir /usr/sap
RUN mkdir /sapmnt
RUN mv nwrfcsdk /usr/sap/
RUN touch /etc/ld.so.conf.d/nwrfcsdk.conf
RUN echo "# include nwrfcsdk" > /etc/ld.so.conf.d/nwrfcsdk.conf
RUN echo "/usr/sap/nwrfcsdk/lib" >> /etc/ld.so.conf.d/nwrfcsdk.conf
RUN ldconfig
RUN venv/bin/pip install pyrfc-1.9.98-cp37-cp37m-linux_x86_64.whl
RUN venv/bin/pip install gunicorn pymysql
RUN sed -i "s?root\@localhost?root\:root\@mysql?g" .env

ENV FLASK_APP sapspa.py

EXPOSE 23381

CMD ./boot.sh

