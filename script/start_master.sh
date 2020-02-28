#!/bin/bash
####---- attension ----####
# example: ./start_master.sh --master-ip=
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
PROMETHEUS_VERSION=2.16.0
NODE_VERSION=12.16.1
MYSQL_ROOT_PASSWORD=''

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

function install_master_requirements()
{
  # pip3 install -r requirements.txt
  echo "Install Python requirements"
  pip3 install -r ${BASE_DIR}src/backend/requirements.txt
}

function install_pyrfc()
{
  # install nwrfc lib
  echo "install nwrfc lib"
  unzip ${BASE_DIR}lib/nwrfc750P_4-70002752.zip -d ${BASE_DIR}script/download/
  mkdir /usr/sap
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
  # kill all consul process and restart as master
  kill -9 $(ps -ef|grep consul|awk '{print $2}')
  nohup consul agent -bootstrap -data-dir=${BASE_DIR}data/consul -ui -client=0.0.0.0 -bind=0.0.0.0 -server -server-port=23340 -dns-port=23346 -http-port=23345 -serf-wan-port=23342 >/dev/null 2>&1 &
}

function install_mysql()
{
  # install mysql
  # https://dev.mysql.com/doc/mysql-sles-repo-quick-guide/en/
  echo -e "\033[31m Please install Mysql-Community-Server 5.7 Manually \033[0m"
  read -p "Please click any key when Mysql is intalled : " tmp
  read -p "Input Mysql root password : " MYSQL_ROOT_PASSWORD
}

function create_mysql_db_sapspa()
{
  # create_mysql_db_sapspa
  mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "CREATE DATABASE IF NOT EXISTS sapspa DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
  sed -i "s?root\@localhost?root\:${MYSQL_ROOT_PASSWORD}\@localhost?g" ${BASE_DIR}src/backend/.env
  cd ${BASE_DIR}src/backend/
  pyenv local ${PYTHON_VERSION}
  pip3 install pymysql
  flask db init
  flask db migrate
  flask db upgrade
}

function start_backend()
{
  # start backend
  echo "start backend"
  pip3 install gunicorn
  gunicorn -b :23381 --access-logfile - --error-logfile - sapspa:app --daemon
}

function start_admin()
{
  # start admin
  # download node
  echo "download node"
  wget https://nodejs.org/dist/v12.16.1/node-v${NODE_VERSION}-linux-x64.tar.xz  -O ${BASE_DIR}script/download/node.tar.xz
  xz -d ${BASE_DIR}script/download/node.tar.xz
  tar xvf ${BASE_DIR}script/download/node.tar -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/node-v${NODE_VERSION}-linux-x64 ${BASE_DIR}app/node
  echo 'export NODEJS_HOME="'${BASE_DIR}'app/node"' >> ~/.bash_profile
  echo 'export PATH="$PATH:${NODEJS_HOME}/bin:node_modules/.bin"' >> ~/.bash_profile
  source ~/.bash_profile
  npm install -g yarn
  cd ${BASE_DIR}src/admin
  echo "install node module"
  yarn
  npm run build:prod
  echo "download caddy http server"
  wget "https://caddyserver.com/download/linux/amd64?license=personal&telemetry=on" -O ${BASE_DIR}script/download/caddy_linux_amd64.tar.xz
  tar zxvf ${BASE_DIR}script/download/caddy_linux_amd64.tar.xz -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/caddy /usr/local/bin
  echo "start caddy"
  sed -i "s?\/sapspa\/src\/admin\/dist/?${BASE_DIR}src\/admin\/dist?g" ${BASE_DIR}etc/caddy/Caddyfile
  nohup caddy -conf ${BASE_DIR}etc/caddy/Caddyfile >/dev/null 2>&1 &
}

function install_prometheus()
{
  #download prometheus
  echo "download prometheus"
  wget https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz -O ${BASE_DIR}script/download/prometheus.tar.gz
  tar zxvf ${BASE_DIR}script/download/prometheus.tar.gz -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/prometheus-${PROMETHEUS_VERSION}.linux-amd64 ${BASE_DIR}app/prometheus
  #start prometheus
  echo "start prometheus"
  cp ${BASE_DIR}etc/prometheus/prometheus.yml ${BASE_DIR}app/prometheus/prometheus.yml
  nohup ${BASE_DIR}app/prometheus/prometheus --web.listen-address="0.0.0.0:23390" >/dev/null 2>&1 &
}

function create_user_search()
{
  # create user search
  echo "create user search"
  useradd -d /home/search -m search
}

function install_elasticsearch()
{
  # download ELK elasticsearch
  echo "download ELK elasticsearch"
  wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ELK_VERSION}-linux-x86_64.tar.gz -O ${BASE_DIR}script/download/elasticsearch.tar.gz
  tar zxvf ${BASE_DIR}script/download/elasticsearch.tar.gz -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/elasticsearch-${ELK_VERSION} ${BASE_DIR}app/elasticsearch
  # edit elasticsearch supervisor config
  sed -i "s?\/home\/search\/elasticsearch-7.4.2?${BASE_DIR}app\/elasticsearch?g" ${BASE_DIR}etc/supervisord/supervisord.d/es.ini
  cp ${BASE_DIR}etc/elasticsearch/elasticsearch.yml ${BASE_DIR}app/elasticsearch/config/elasticsearch.yml
}

function install_kibana()
{
  # download ELK kibana
  echo "download ELK kibana"
  wget https://artifacts.elastic.co/downloads/kibana/kibana-${ELK_VERSION}-linux-x86_64.tar.gz -O ${BASE_DIR}script/download/kibana.tar.gz
  tar zxvf ${BASE_DIR}script/download/kibana.tar.gz -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/kibana-${ELK_VERSION}-linux-x86_64 ${BASE_DIR}app/kibana
  # edit kibana supervisor config
  sed -i "s?\/home\/search\/kibana-7.4.2-linux-x86_64?${BASE_DIR}app\/kibana?g" ${BASE_DIR}etc/supervisord/supervisord.d/kibana.ini
  cp ${BASE_DIR}etc/kibana/kibana.yml ${BASE_DIR}app/kibana/config/kibana.yml
}

function install_grafana()
{
  # download ELK grafana
  echo "download ELK grafana"
  wget https://dl.grafana.com/oss/release/grafana-6.6.2.linux-amd64.tar.gz  -O ${BASE_DIR}script/download/grafana.tar.gz
  tar zxvf ${BASE_DIR}script/download/grafana.tar.gz -C ${BASE_DIR}script/download/
  mv ${BASE_DIR}script/download/grafana-6.6.2 ${BASE_DIR}app/grafana
  # edit grafana supervisor config
  sed -i "s?\/home\/search\/grafana-6.6.2?${BASE_DIR}app\/grafana?g" ${BASE_DIR}etc/supervisord/supervisord.d/grafana.ini
  mkdir ${BASE_DIR}app/grafana/conf
  cp ${BASE_DIR}etc/grafana/defaults.ini ${BASE_DIR}app/grafana/conf/defaults.ini
}

install_pyenv
install_python3
install_master_requirements
install_pyrfc
install_consul
install_mysql
create_mysql_db_sapspa
start_backend
start_admin
install_prometheus
create_user_search
install_elasticsearch
install_kibana
install_grafana

# install supervisord
echo "install supervisord"
pyenv local ${PYTHON_VERSION}
pip3 install supervisor
cp -Rf ${BASE_DIR}etc/supervisord /etc/
mkdir /var/run/supervisor
mkdir /var/log/supervisor
# start supervisord
echo "start supervisord"
kill -9 $(ps -ef|grep supervisord|awk '{print $2}')
supervisord -c /etc/supervisord/supervisord.conf
supervisorctl -c /etc/supervisord/supervisord.conf reload
supervisorctl -c /etc/supervisord/supervisord.conf start all
supervisorctl -c /etc/supervisord/supervisord.conf restart all
echo "start master done"

