# sapspa

## SAP monitor and analysis bundle project

## task list
### 1. backend future
- [ ] backend app list
- [ ] backend subapp list
- [ ] backend host list
- [ ] backend instance list and relation redirect
- [ ] admin and backend basic auth
- [x] 22330 port support /api /mapi /admin

### 2. agent future
- [x] common readtable rfc function
- [x] usercount status data
- [x] workprocess status
- [ ] background job status **_V_OP_**
- [x] dump status
- [ ] instance status
- [ ] transport status
- [ ] rfc resource status
- [x] Consul

### 3. build es and kibana
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
- [ ] mysql monitor

### 5. docker-compose deploy script
- [ ] backend
- [ ] agent
- [ ] InfluxDB? openTSDB? **_prometheus_**?
- [ ] consul and consul webui
- [ ] 

### 6. unitest and ci

### 7. hana database monitor and report
- [ ] todo...



```
maybe some code here

./consul agent -bind 127.0.0.1 -data-dir=consuldata -ui -bootstrap -server -datacenter=dc1
```