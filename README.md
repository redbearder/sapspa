# sapspa

## SAP monitor and analysis bundle project
<font color=red size=5 face="微软雅黑">Reserved PORT **23300 - 23399**</font>

## Task list
### 1. backend future
- [ ] backend app list
- [ ] backend subapp list
- [ ] backend host list
- [ ] backend instance list and relation redirect
- [ ] admin and backend basic auth
- [x] 23381 port support /api /mapi
- [x] 23380 port support /admin

### 2. agent future
- [x] common readtable rfc function , port 23310
- [x] usercount status data
- [x] workprocess status
- [ ] background job status **_V_OP_**
- [x] dump status
- [x] instance status
- [ ] transport status
- [ ] rfc resource status
- [x] Consul, port 8300: 23340, 8302: 23342, 8301: 23341, 8600: 23346, 8500: 23345
- [x] node_exporter, port 23311

### 3. build es and kibana
- [x] es, port 23392, 23393
- [x] kibana, port 23356
- [x] filebeat and live reload

### 4. grafana dashboard
- [ ] usercount list and user type dist
- [ ] workprocess list and type
- [ ] background job status
- [ ] dump status SNAP
- [ ] instance status
- [ ] transport status
- [ ] rfc resource status
- [x] os monitor
- [ ] mysql monitor
- [ ] es monitor
- [x] grafana, port 23330

### 5. docker-compose deploy script
- [ ] backend
- [ ] agent
- [ ] InfluxDB? openTSDB? **_prometheus_**?
- [ ] consul and consul webui
- [ ] 

### 6. bash deploy script
- [ ] todo...

### 7. unitest and ci
- [ ] todo...

### 8. hana database monitor and report
- [ ] todo...



```
maybe some code here

./consul agent -bind 127.0.0.1 -data-dir=consuldata -ui -bootstrap -server -datacenter=dc1
```