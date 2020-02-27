from flask import Blueprint

bp = Blueprint("mapi", __name__)

from app.mapi import urls
