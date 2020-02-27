import request from '@/utils/request'

export function fetchAppList(query) {
  return request({
    url: '/apps',
    method: 'get',
    params: query
  })
}

export function fetchApp(appid) {
  return request({
    url: `/apps/${appid}`,
    method: 'get'
  })
}

export function createApp(data) {
  return request({
    url: '/apps',
    method: 'post',
    data
  })
}

export function updateApp(appid, data) {
  return request({
    url: `/apps/${appid}`,
    method: 'put',
    data
  })
}

export function deleteApp(appid) {
  return request({
    url: `/apps/${appid}`,
    method: 'delete'
  })
}
