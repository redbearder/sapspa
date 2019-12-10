import request from '@/utils/request'

export function fetchSubappList(query) {
  return request({
    url: '/subapps',
    method: 'get',
    params: query
  })
}

export function fetchSubapp(subappid) {
  return request({
    url: `/subapps/${subappid}`,
    method: 'get'
  })
}

export function createSubapp(data) {
  return request({
    url: '/subapps',
    method: 'post',
    data
  })
}

export function updateSubapp(subappid, data) {
  return request({
    url: `/subapps/${subappid}`,
    method: 'put',
    data
  })
}

export function deleteSubapp(subappid) {
  return request({
    url: `/subapps/${subappid}`,
    method: 'delete'
  })
}
