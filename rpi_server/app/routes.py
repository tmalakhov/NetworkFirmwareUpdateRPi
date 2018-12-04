## Web page URLs and their functions

# System imports
import datetime
import json
import os
import socket
import requests
import subprocess

# Server imports
from app import app
from app import UPLOAD_FOLDER
from app import GH_API, GH_UN, GH_PASS, GH_REPO, GH_OWNR

from flask import Flask
from flask import request
from flask import redirect
from flask import render_template
from flask import jsonify
from flask import url_for
from flask import send_from_directory

# DB imports
import sqlite3 as sql
from app import db

# Only .bin image files allowed
ALLOWED_EXTENSIONS = set(['bin'])

app = Flask(__name__,
            static_folder="./dist/static",
            template_folder="./dist")

# Set directory to save images to
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Enforce allowed filename extensions
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Upload a file from user's computer
@app.route('/api/upload', methods=['GET', 'POST'])
def upload():
    # Respond to POST requests
    if request.method == 'POST':

        # Check if request contains file
        if 'file' not in request.files:
            print('No file part')
            return redirect(url_for('index'))
        file = request.files['file']

        # Check if user selected an allowed file
        if file.filename == '' or not allowed_file(file.filename):
            print('File not selected or file extension not allowed')
            return redirect(url_for('index'))

        # Store the file
        if file:
            # Use timestamp to nearest second as filename
            filename = str(datetime.datetime.now())
            filename = filename[0:19]
            filename = filename.replace(" ","") + '.bin'

            # Check if upload path exists, make it
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            # Save file named by timestamp
            file.save(UPLOAD_FOLDER + '/' + filename)

            # Add to DB
            print('Adding file to DB...')
            db.add_img(filename)

            try:
                # Send file to microcontroller
                uploadMicroprocessor(UPLOAD_FOLDER + '/' + filename)
            except:
                print('Failed to connect to Microcontroller')

        # Close uploaded file
        file.close()

    return redirect(url_for('index'))

# Uploads a file to user/robot
@app.route('/api/download/<filename>')
def image_file(filename):
    # Upload saved image to requester
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# List all uploaded images, ordered recent first
@app.route('/api/history', methods=['GET'])
def history():
    # Get populated HTML page
    rows = db.list_imgs()
    # Return JSON
    response = jsonify(rows)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response

# Upload a file from server DB
@app.route('/api/uploadHistory', methods=['GET', 'POST'])
def uploadHistory():
    # Respond to POST requests
    if request.method == 'POST':

        # Parse filename
        filename = request.json['file']

        # Get requested file
        file = open(UPLOAD_FOLDER + '/' + filename)

        # Construct URL for api/upload
        url = request.url_root + 'api/upload'

        # Send file to upload()
        response = requests.post(url, files = {'file' : file})

    # Return to homepage
    return redirect(url_for('index'))

# Get GitHub images list
@app.route('/api/github', methods=['GET'])
def github():
    print('Getting GitHub releases...')
    # GET releases in JSON from GitHub
    request = requests.get(GH_API
                         + '/repos'
                         + '/' + GH_OWNR
                         + '/' + GH_REPO
                         + '/releases',
                         auth=(GH_UN, GH_PASS))

    print(request)
    response = jsonify(request.json())

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response

# Upload a file from GitHub
@app.route('/api/uploadGit', methods=['GET', 'POST'])
def uploadGit():
    # Respond to POST requests
    if request.method == 'POST':

        # Parse filename
        releaseID = str(request.json['id'])

        # GET requested asset
        print('Getting GitHub releases...')
        response = requests.get(GH_API
                         + '/repos'
                         + '/' + GH_OWNR
                         + '/' + GH_REPO
                         + '/releases'
                         + '/' + releaseID
                         + '/assets',
                         auth=(GH_UN, GH_PASS))

        # Parse file
        # TODO

        # Construct URL for api/upload
        url = request.url_root + 'api/upload'

        # Send file to upload()
#        response = requests.post(url, files = {'file' : file})

    # Return to homepage
    return redirect(url_for('index'))

# Send an image to the microcontroller
def uploadMicroprocessor(filepath):
    HOST = '192.168.0.10'  # IP address of the microprocessor
    PORT = 12579        # Port to listen on
    with socket.socket() as s:
        s.connect((HOST, PORT))

        # send file size first
        file_size = os.path.getsize(filepath)
        s.sendall(file_size.to_bytes(4, byteorder='little'))

        # Check clear to send
        cts = s.recv(4)
        cts = int.from_bytes(cts, byteorder='little')
        print(cts)

        # Send file if clear to send received
        if cts == file_size:
            with open(filepath, 'rb') as f:
                image = f.read()
                s.sendall(image)
                rcv = s.recv(4)
                rcv = int.from_bytes(rcv, byteorder='little')
                print(rcv)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    if app.debug:
        return requests.get('http://localhost:8080/{}'.format(path)).text
    return render_template("index.html")

@app.route('/')
@app.route('/index')
def index():

    if app.debug:
        return requests.get('http://localhost:8080/').text
    return render_template("index.html")
