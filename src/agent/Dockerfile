FROM python:3.7.5

ARG MASTER_IP

WORKDIR /opt/agent
COPY . /opt/agent/

RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install uwsgi

ENV FLASK_APP sapspa_agent.py

RUN unzip nwrfc750P_4-70002752.zip
RUN mkdir /usr/sap
RUN mkdir /sapmnt
RUN mv nwrfcsdk /usr/sap/
RUN touch /etc/ld.so.conf.d/nwrfcsdk.conf
RUN echo "# include nwrfcsdk" > /etc/ld.so.conf.d/nwrfcsdk.conf
RUN echo "/usr/sap/nwrfcsdk/lib" >> /etc/ld.so.conf.d/nwrfcsdk.conf
RUN ldconfig
RUN venv/bin/pip install pyrfc-1.9.98-cp37-cp37m-linux_x86_64.whl
RUN sed -i "s?{master_ip}?$MASTER_IP?g" sapspa_agent.py

EXPOSE 23310

CMD venv/bin/uwsgi --http 0.0.0.0:23310 --wsgi-file sapspa_agent.py --callable app_dispatch


