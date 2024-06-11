import os
from flask import Flask, request
from flask_cors import CORS
from flask_restx import Api, Resource, Namespace

app = Flask(__name__)