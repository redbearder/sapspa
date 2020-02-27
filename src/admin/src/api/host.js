import request from '@/utils/request'

export function fetchHostList(query) {
  return request({
    url: '/hosts',
    method: 'get',
    params: query
  })
}

export function fetchHost(hostid) {
  return request({
    url: `/hosts/${hostid}`,
    method: 'get'
  })
}

export function createHost(data) {
  return request({
    url: '/hosts',
    method: 'post',
    data
  })
}

export function updateHost(hostid, data) {
  return request({
    url: `/hosts/${hostid}`,
    method: 'put',
    data
  })
}

export function deleteHost(hostid) {
  return request({
    url: `/hosts/${hostid}`,
    method: 'delete'
  })
}
