#!/bin/bash

####---- attension ----####
# example: ./start_agent.sh --master-ip=
####---- attension ----####

__VERSION__=0.1.0
BASE_DIR="$(dirname "$0")"/../
BASENAME=$(basename $0)
PYTHON_VERSION=3.7.5
PYENV_VERSION=1.2.16
CONSUL_VERSION=1.7.1
MASTER_IP=139.9.180.161
NODE_EXPORTER_VERSION=0.18.1
ELK_VERSION=7.4.2

USAGE="Usage: $BASENAME [OPTIONS]
A SAP system monitor agent script to install and start

Help for start_agent.sh

  --help                                    print this help
  --master                                  A IP address to master node, that is necessary
  --pyversion                               Python version that you want to install, Default is 3.7.5
  --version                                 print script version"

function usage()
{
        # usage
        echo "$USAGE" >&2
        exit 1
}

if [ $# -lt 1 ];then
	usage
fi

ARGS=`getopt -o vh -l help,version,master:,pyversion: -- "$@"`
eval set -- "$ARGS"
while true;
do
        case "$1" in
                --master)
                        MASTER_IP=$2
                        echo "MASTER_IP: "${MASTER_IP}
                        shift 2
                        ;;
                --pyversion)
                        PYTHON_VERSION=$2
                        echo "PYTHON_VERSION: "${PYTHON_VERSION}
                        shift 2
                        ;;
                -v|--version)
                        echo "version: "${__VERSION__}
                        shift
                        exit 0
                        ;;
                -h|--help)
                        usage
                        shift
                        exit 0
                        ;;
                --)
                        # no args
                        shift
                        break
                        ;;
                *)
                        echo "usage error"
                        usage
                        exit 1
                        ;;
        esac
done

# download pyenv
echo "download pyenv"
wget https://github.com/pyenv/pyenv/archive/v${PYENV_VERSION}.tar.gz -O ${BASE_DIR}script/download/pyenv.tar.gz
echo "install pyenv"
tar zxvf ${BASE_DIR}script/download/pyenv.tar.gz ${BASE_DIR}script/download/
mv ${BASE_DIR}script/download/pyenv-${PYENV_VERSION} ~/.pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
exec "$SHELL"
# install python3.7.5 via pyenv
mkdir ~/.pyenv/sources
mkdir ~/.pyenv/sources/${PYTHON_VERSION}
echo "download Python "$PYTHON_VERSION
wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz ~/.pyenv/sources/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz
echo "install Python "${PYTHON_VERSION}
pyenv install ${PYTHON_VERSION}
pyenv local ${PYTHON_VERSION}
# pip install -r requirements.txt
echo "Install Python requirements"
pip install -r ${BASE_DIR}src/agent/requirements.txt
# install nwrfc lib
echo "install nwrfc lib"
unzip ${BASE_DIR}lib/nwrfc750P_4-70002752.zip -d ${BASE_DIR}script/download/
mv ${BASE_DIR}script/download/nwrfcsdk /usr/sap/nwrfcsdk
touch /etc/ld.so.conf.d/nwrfcsdk.conf
echo "# include nwrfcsdk" >> /etc/ld.so.conf.d/nwrfcsdk.conf
echo "/usr/sap/nwrfcsdk/lib" >> /etc/ld.so.conf.d/nwrfcsdk.conf
ldconfig
# install pyrfc module
echo "install pyrfc module"
pip install ${BASE_DIR}lib/pyrfc-1.9.98-cp37-cp37m-linux_x86_64.whl
# download consul
echo "download consul"
wget https://releases.hashicorp.com/consul/${CONSUL_VERSION}/consul_${CONSUL_VERSION}_linux_amd64.zip -O ${BASE_DIR}script/download/consul.zip
unzip ${BASE_DIR}script/download/consul.zip -d /usr/local/bin
# start consul
echo "start consul"
nohup consul agent -data-dir=${BASE_DIR}data/consul -ui -client=0.0.0.0 -bind=0.0.0.0 -join=${MASTER_IP} -dns-port=23346 -http-port=23345 -retry-join "[::1]:23341" -serf-wan-port=23342 &
# start sapspa_agent.py
echo "start sapspa_agent.py"
uwsgi --http 0.0.0.0:23310 --wsgi-file ${BASE_DIR}src/agent/sapspa_agent.py --callable app_dispatch --daemonize /var/log/uwsgi_sapspa_agent.log
# download node_exporter
echo "download node_exporter"
wget https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz -O ${BASE_DIR}script/download/node_exporter.tar.gz
tar zxvf ${BASE_DIR}script/download/node_exporter.tar.gz /usr/local/bin
# start node_exporter
echo "start node_exporter"
nohup node_exporter --web.listen-address=":23311" &
# download ELK filebeat
wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-${CONSUL_VERSION}-linux-x86_64.tar.gz -O ${BASE_DIR}script/download/filebeat.tar.gz
tar zxvf ${BASE_DIR}script/download/filebeat.tar.gz ${BASE_DIR}script/download/
mv ${BASE_DIR}script/download/filebeat-${ELK_VERSION}-linux-x86_64 ${BASE_DIR}app/filebeat
# start filebeat
sed -i "s/localhost:23392/${MASTER_IP}:23392/g" ${BASE_DIR}etc/filebeat/filebeat.yml
nohup ${BASE_DIR}app/filebeat/filebeat -c ${BASE_DIR}etc/filebeat/filebeat.yml &
echo "start agent done"

