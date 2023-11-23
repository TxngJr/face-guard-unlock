import os
import face_recognition
from datetime import datetime
from bson.binary import Binary
from pymongo import MongoClient
from flask import Flask, request, jsonify, make_response, redirect, render_template, session
import numpy as np

database = MongoClient('mongodb://localhost:27017/')['testkub']
room_access_history_collection = database.room_access_history
face_collection = database.face

app = Flask(__name__)
app.secret_key = '432rkjk34htht34f'
app.config['UPLOAD_FOLDER'] = 'static/images/'


@app.route("/login", methods=['GET'])
def login_page():
    is_admin = session.get("is_admin", False)
    if is_admin:
        return redirect("/room_access_history")
    message = session.pop("message", False)
    return render_template('login_page.html', message=message, is_admin=is_admin)


@app.route("/login_api", methods=['POST'])
def login_api():
    is_admin = session.get("is_admin", False)
    if is_admin:
        return redirect("/room_access_history")
    if not request.form['username'] == "admin" or not request.form['password'] == "12345":
        session['message'] = "Username or Password Wrong"
        return redirect("/login")
    session['is_admin'] = True
    return redirect("/room_access_history")


@app.route("/logout_api", methods=['GET'])
def logout_api():
    session['is_admin'] = False
    return redirect("/login")


@app.route("/room_access_history", methods=['GET'])
def room_access_history_page():
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['message'] = "Please Login first"
        return redirect("/login")
    room_access_history_all = list(room_access_history_collection.find({}))
    message = session.pop("message", False)
    return render_template('room_access_history_page.html', data=room_access_history_all, message=message)


@app.route("/register_face", methods=['GET'])
def register_face_page():
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['message'] = "Please Login first"
        return redirect("/login")
    message = session.pop("message", False)
    image_list = [filename for filename in os.listdir('static/images') if filename.endswith('.jpg')]
    return render_template('register_face_page.html', image_list=image_list, message=message)


@app.route('/register_face_api', methods=['POST'])
def register_face_api():
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['message'] = "Please Login first"
        return redirect("/login")
    uploaded_files = request.files.getlist('imageFile')
    failed_files = []
    for file in uploaded_files:
        if file.filename != '':
            try:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                image = face_recognition.load_image_file(file)
                encoding = face_recognition.face_encodings(image)[0]
                document = {
                    "image_id": file.filename,
                    "embedding": Binary(encoding)
                }
                inserted_id = face_collection.insert_one(document).inserted_id
                session['message'] = "Face uploaded successfully"
            except:
                if os.path.exists("static/images/" + file.filename):
                    os.remove("static/images/" + file.filename)
                failed_files.append(file.filename)
    if failed_files:
        session['message'] = "Some files failed to upload: {}".format(', '.join(failed_files))
    else:
        session['message'] = "All files uploaded successfully!"
    return redirect("/register_face")

@app.route('/remove_face_api', methods=['POST'])
def remove_face_api():
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['message'] = "Please Login first"
        return redirect("/login")
    try:
        image_name = request.form['image_name']
        image_path = os.path.join('static/images', image_name)
        if os.path.exists(image_path):
            os.remove(image_path)
        is_delete_face = face_collection.delete_one({"image_id": image_name})
        if not is_delete_face:
            session['message'] = "Failed to delete face"
            return redirect("/register_face")
        is_delete_room_access_history = room_access_history_collection.delete_many({"name": image_name.split('.')[0]})
        if not is_delete_room_access_history:
            session['message'] = "Failed to delete face"
            return redirect("/register_face")
        session['message'] = "Successfully deleted face"
        return redirect("/register_face")
    except:
        session['message'] = "Failed to delete face"
        return redirect("/register_face")


@app.route('/check_face_api', methods=['POST'])
def check_face_api():
    try:
        file = request.files['imageFile']

        unknown_image = face_recognition.load_image_file(file)
        unknown_encoding = face_recognition.face_encodings(unknown_image)[0]
        documents = face_collection.find()

        known_encodings = []
        for doc in documents:
            known_encodings.append(np.frombuffer(doc["embedding"]))
        results = face_recognition.compare_faces(known_encodings, unknown_encoding)
        print(results)
        for i, matched in enumerate(results):
            if matched:
                return make_response('', 200)
        return make_response('', 400)
    except:
        return make_response('', 400)


@app.errorhandler(404)
def page_not_found(error):
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['message'] = "Please Login first"
        return redirect("/login")
    session['message'] = "This page does not exist"
    return redirect("/room_access_history")


if __name__ == '__main__':
    app.run(debug=True)
