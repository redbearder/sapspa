import request from '@/utils/request'

export function fetchInstanceList(query) {
  return request({
    url: '/instances',
    method: 'get',
    params: query
  })
}

export function fetchInstance(instanceid) {
  return request({
    url: `/instances/${instanceid}`,
    method: 'get'
  })
}

export function fetchInstanceStatus(instanceid) {
  return request({
    url: `/instances/${instanceid}/status`,
    method: 'get'
  })
}

export function startInstance(instanceid) {
  return request({
    url: `/instances/${instanceid}/status`,
    method: 'post'
  })
}

export function stopInstance(instanceid) {
  return request({
    url: `/instances/${instanceid}/status`,
    method: 'delete'
  })
}

export function createInstance(data) {
  return request({
    url: '/instances',
    method: 'post',
    data
  })
}

export function updateInstance(instanceid, data) {
  return request({
    url: `/instances/${instanceid}`,
    method: 'put',
    data
  })
}

export function deleteInstance(instanceid) {
  return request({
    url: `/instances/${instanceid}`,
    method: 'delete'
  })
}

export function fetchInstanceListInSubApp(subappid, query) {
  return request({
    url: `/subapps/${subappid}/instances`,
    method: 'get',
    params: query
  })
}

export function fetchInstanceListInHost(hostid, query) {
  return request({
    url: `/hosts/${hostid}/instances`,
    method: 'get',
    params: query
  })
}
