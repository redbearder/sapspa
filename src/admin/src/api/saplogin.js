import request from '@/utils/request'

export function fetchLoginList(query) {
  return request({
    url: '/logins',
    method: 'get',
    params: query
  })
}

export function createLogin(data) {
  return request({
    url: '/logins',
    method: 'post',
    data
  })
}

export function updateLogin(loginid, data) {
  return request({
    url: `/logins/${loginid}`,
    method: 'put',
    data
  })
}

export function deleteLogin(loginid) {
  return request({
    url: `/logins/${loginid}`,
    method: 'delete'
  })
}
