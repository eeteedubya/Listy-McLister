# functions for the app
from jinja2 import Template
import re
import os
import openai
from flask import Flask, render_template, request, flash, url_for, session, redirect, jsonify
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
import json

import cv2
import numpy as np


# import app
app = Flask(__name__)
DB_HOST = '127.0.0.1'
DB_NAME = 'mclisty_db'
DB_USER = 'etw'
DB_PASS = 'admin'

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=5433)

net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")

classes = []
with open('coco.names', 'r') as f:
    classes = [line.strip() for line in f.readlines()]


@app.route('/getlists', methods=['GET'])
def get_user_list_names():
    print("getting list names")
    sql_query_user_lists = '''
        SELECT (listname)
        FROM listnames
        WHERE listnames.userid = (SELECT id FROM users WHERE username = '{}');  
        '''.format(session['username'])
    cursor2 = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor2.execute(sql_query_user_lists)
    # conn.commit()
    user_list_names = cursor2.fetchall()
    print(user_list_names)
    return user_list_names


@app.route('/addlistname', methods = ['GET' , 'POST'])
def add_user_list_name():
    new_list_name = request.form['new_listName']
    sql_query_user_lists = '''
    INSERT INTO listnames(listname,userid)
    VALUES ('{}', (SELECT id FROM users WHERE username = '{}') );
    '''.format(new_list_name, session['username'])
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(sql_query_user_lists)
    conn.commit()
    return redirect(url_for('listitems'))

@app.route('/choose_list', methods = ['GET' , 'POST'])
def choose_list():
    if request.method == "POST":
        print("POST")
        # session['chosenList'] = request.form['radio-group']
        selectedRadio = request.form['radio-group']
        session['chosenList'] = selectedRadio
        print(session['chosenList'])
        print(selectedRadio)
        return redirect(url_for('listitems'))
    return redirect(url_for('listitems'))
    

def detect_objects(image):
    # Load the image
    img = cv2.imread(image)

    # Get the image dimensions
    height, width, _ = img.shape

    # Create a blob from the image
    blob = cv2.dnn.blobFromImage(img, 1/255, (416, 416), (0, 0, 0), True, crop=False)

    # Set the input for the neural network
    net.setInput(blob)

    # Get the output layer names
    output_layers_names = net.getUnconnectedOutLayersNames()

    # Run the forward pass to get the output of the output layers
    outputs = net.forward(output_layers_names)

    # Initialize lists to store the detected classes, confidences, and bounding boxes
    class_ids = []
    confidences = []
    boxes = []

    # Loop over each output and detect the objects
    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > 0.5:
                # Calculate the coordinates of the bounding box
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = int(center_x - w/2)
                y = int(center_y - h/2)

                # Add the class id, confidence, and bounding box coordinates to their respective lists
                class_ids.append(class_id)
                confidences.append(float(confidence))
                boxes.append([x, y, w, h])

    # Apply non-max suppression to remove overlapping bounding boxes
    indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    # Initialize a list to store the detected items
    items = []

    # Loop over the indices and add the class names to the items list
    for i in indices:
        # i = i[0]
        items.append(classes[class_ids[i]])
    # print(items)
    return items




@app.route('/detect', methods=['POST'])
def detect():
    # Get the uploaded file from the request
    file = request.files['image']

    # Save the file to disk
    filename = file.filename
    file.save(filename)

    # Detect the objects in the image
    items = detect_objects(filename)

    # Return the detected items as a JSON response
    # return jsonify({'items': items})
 
    print(items)
    # return items
    return render_template('listitems.html', pic_items=items)