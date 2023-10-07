from datetime import datetime
from simple_facerec import SimpleFacerec
from flask import Flask, request, jsonify, make_response, redirect, render_template, session
import os
from pymongo import MongoClient

database = MongoClient('mongodb://localhost:27017/')['testkub']
room_access_history = database.room_access_history

face_recognition = SimpleFacerec()
face_recognition.load_encoding_images("image/")

app = Flask(__name__)
app.secret_key = '432rkjk34htht34f'
app.config['UPLOAD_FOLDER'] = 'image/'


@app.route("/login", methods=['GET'])
def login_page():
    is_admin = session.get("is_admin", False)
    if is_admin:
        return redirect("/room_access_history")
    authentication_message = session.pop("authentication_message", "")
    return render_template('login_page.html', authentication_message=authentication_message)


@app.route("/login_api", methods=['POST'])
def login_api():
    is_admin = session.get("is_admin", False)
    if is_admin:
        return redirect("/room_access_history")
    if not request.form['username'] == "admin" or not request.form['password'] == "12345":
        session['authentication_message'] = False
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
        session['authentication_message'] = True
        return redirect("/login")
    room_access_history_all = list(room_access_history.find({}))
    if not room_access_history_all:
        return make_response(jsonify({"message": "have somthing error"}))
    return render_template('room_access_history_page.html', data=room_access_history_all)


@app.route("/register_face", methods=['GET'])
def register_face_page():
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['authentication_message'] = True
        return redirect("/login")
    status = session.pop('status', "")
    return render_template('register_face_page.html', status=status)


@app.route('/register_face_api', methods=['POST'])
def register_face_api():
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['authentication_message'] = True
        return redirect("/login")
    try:
        student_id = request.form['StudentID']
        file = request.files['imageFile']
        if len(student_id) < 10 or not file:
            session['status'] = False
            return redirect("/register_face")
        file_name = str(student_id) + ".jpg"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
        try:
            face_recognition.load_encoding_images("image/")
            session['status'] = True
            return redirect("/register_face")
        except:
            if os.path.exists("image/" + file_name):
                os.remove("image/" + file_name)
                face_recognition.load_encoding_images("image/")
            session['status'] = False
            return redirect("/register_face")
    except:
        session['status'] = "failed"
        return redirect("/register_face")


@app.route('/check_face_api', methods=['POST'])
def check_face_api():
    try:
        if 'imageFile' not in request.files:
            return make_response(jsonify({"message": "please send file"}), 400)
        file = request.files['imageFile']
        student_id = face_recognition.detect_known_faces(file)
        if not student_id:
            return make_response(jsonify({"message": "not have your face in database"}), 404)
        is_save = room_access_history.insert_one({"name": student_id, "datetime": datetime.now()})
        if not is_save:
            return make_response(jsonify({"message": "have somthing error"}), 400)
        return make_response(jsonify({"message": "have your face in database"}), 200)
    except:
        return make_response(jsonify({"message": "have somthing error"}), 400)


@app.errorhandler(404)
def page_not_found(error):
    is_admin = session.get("is_admin", False)
    if not is_admin:
        session['authentication_message'] = True
        return redirect("/login")
    return redirect("/room_access_history")


if __name__ == '__main__':
    app.run(host='192.168.1.45', port=25565)
