from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES


def error_response(status_code, return_code=None, message=None):
    payload = {'error': HTTP_STATUS_CODES.get(status_code, 'Unknown error')}
    payload['success'] = False
    payload['code'] = return_code and return_code or status_code
    if message:
        payload['message'] = message
    response = jsonify(payload)
    response.status_code = status_code
    return response

def success_response(data=None, message=None, total=None):
    payload = {}
    payload['success'] = True
    payload['code'] = 0
    if message:
        payload['message'] = message
    if data:
        payload['data'] = data
    if total:
        payload['total'] = total
    response = jsonify(payload)
    response.status_code = 200
    return response

def bad_request(message):
    return error_response(400, message)

def normal_request(message):
    return success_response(message=message)

def query_request(data, message=None, total=None):
    return success_response(data, message, total)
