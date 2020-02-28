#!/bin/bash

####---- attension ----####
# example: ./start_agent.sh --master-ip=
####---- attension ----####

__VERSION__=0.1.0
BASE_DIR="$(dirname "$0")"/../
BASE_DIR=`pwd`/$BASE_DIR
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

function install_pyenv()
{
        if command -v pyenv 1> /dev/null 2>&1; then
            echo "pyenv already exist"
        else
            # download pyenv
            echo "download pyenv"
            wget https://github.com/pyenv/pyenv/archive/v${PYENV_VERSION}.tar.gz -O ${BASE_DIR}script/download/pyenv.tar.gz
            echo "install pyenv"
            tar zxvf ${BASE_DIR}script/download/pyenv.tar.gz -C ${BASE_DIR}script/download/
            mv ${BASE_DIR}script/download/pyenv-${PYENV_VERSION} ~/.pyenv
            echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
            echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
            echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
            source ~/.bash_profile
        fi
}

function install_python3()
{
        # sudo apt-get update
        # sudo apt-get upgrade
        # sudo apt-get dist-upgrade
        # sudo apt-get install build-essential python-dev python-setuptools python-pip python-smbus
        # sudo apt-get install build-essential libncursesw5-dev libgdbm-dev libc6-dev
        # sudo apt-get install zlib1g-dev libsqlite3-dev tk-dev
        # sudo apt-get install libssl-dev openssl
        # sudo apt-get install libffi-dev
        if command -v python3.7 1> /dev/null 2>&1; then
            echo "python3 already exist"
            pyenv local ${PYTHON_VERSION}
        else
            # install python3.7.5 via pyenv
            mkdir ~/.pyenv/sources
            mkdir ~/.pyenv/sources/${PYTHON_VERSION}
#            echo "download Python "$PYTHON_VERSION
#            wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz ~/.pyenv/sources/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz
            echo "install Python "${PYTHON_VERSION}
            pyenv install -k ${PYTHON_VERSION}
            pyenv local ${PYTHON_VERSION}
        fi
}

function install_agent_requirements()
{
  # pip3 install -r requirements.txt
  echo "Install Python requirements"
  pip3 install -r ${BASE_DIR}src/agent/requirements.txt
}


function install_pyrfc()
{
  # install nwrfc lib
  echo "install nwrfc lib"
  unzip ${BASE_DIR}lib/nwrfc750P_4-70002752.zip -d ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/nwrfcsdk /usr/sap/nwrfcsdk
  touch /etc/ld.so.conf.d/nwrfcsdk.conf
  echo "# include nwrfcsdk" > /etc/ld.so.conf.d/nwrfcsdk.conf
  echo "/usr/sap/nwrfcsdk/lib" >> /etc/ld.so.conf.d/nwrfcsdk.conf
  ldconfig
  # install pyrfc module
  echo "install pyrfc module"
  pip3 install ${BASE_DIR}lib/pyrfc-1.9.98-cp37-cp37m-linux_x86_64.whl
}

function install_consul()
{
  # download consul
  echo "download consul"
  wget https://releases.hashicorp.com/consul/${CONSUL_VERSION}/consul_${CONSUL_VERSION}_linux_amd64.zip -O ${BASE_DIR}script/download/consul.zip
  unzip ${BASE_DIR}script/download/consul.zip -d /usr/local/bin
  # start consul
  # if process consul exist and ignore
  count=`ps -ef |grep consul |grep -v "grep" |wc -l`
  if [ 0 == $count ];then
        echo "start consul"
        nohup consul agent -data-dir=${BASE_DIR}data/consul -ui -client=0.0.0.0 -bind=0.0.0.0 -join=${MASTER_IP} -dns-port=23346 -http-port=23345 -retry-join "[::1]:23341" -serf-wan-port=23342 >/dev/null 2>&1 &
  fi
}

function install_sapspa_agent()
{
  # start sapspa_agent.py
  pyenv local ${PYTHON_VERSION}
  echo "start sapspa_agent.py"
  pip3 install uwsgi
  uwsgi --http 0.0.0.0:23310 --wsgi-file ${BASE_DIR}src/agent/sapspa_agent.py --callable app_dispatch --daemonize /var/log/uwsgi_sapspa_agent.log
}

function install_node_exporter()
{
  # download node_exporter
  echo "download node_exporter"
  wget https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz -O ${BASE_DIR}script/download/node_exporter.tar.gz
  tar zxvf ${BASE_DIR}script/download/node_exporter.tar.gz -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin
  # start node_exporter
  echo "start node_exporter"
  nohup node_exporter --web.listen-address=":23311" >/dev/null 2>&1 &
}

function install_filebeat()
{
  # download ELK filebeat
  wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-${ELK_VERSION}-linux-x86_64.tar.gz -O ${BASE_DIR}script/download/filebeat.tar.gz
  tar zxvf ${BASE_DIR}script/download/filebeat.tar.gz -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/filebeat-${ELK_VERSION}-linux-x86_64 ${BASE_DIR}app/filebeat
  # start filebeat
  sed -i "s?localhost:23392?${MASTER_IP}:23392?g" ${BASE_DIR}etc/filebeat/filebeat.yml
  sed -i 's?index: "filebeat?index: "'`hostname`'-filebeat?g' ${BASE_DIR}etc/filebeat/filebeat.yml
  cp -Rf ${BASE_DIR}etc/filebeat /etc/
  nohup ${BASE_DIR}app/filebeat/filebeat -c ${BASE_DIR}etc/filebeat/filebeat.yml >/dev/null 2>&1 &
}

install_pyenv
install_python3
install_agent_requirements
install_pyrfc
install_consul
install_sapspa_agent
install_node_exporter
install_filebeat

echo "start agent done"