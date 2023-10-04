from simple_facerec import SimpleFacerec
from flask import Flask, request, jsonify, make_response
import os
import uuid

face_recognition = SimpleFacerec()
face_recognition.load_encoding_images("image/")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'image/'

@app.route('/uploader', methods = ['POST'])
def upload_file():
    try:
        if 'imageFile' not in request.files:
            return make_response(jsonify({"message": "please send file"}), 400)
        file = request.files['imageFile']
        file_name = str(uuid.uuid4())+".jpg"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
        try:
            face_recognition.load_encoding_images("image/")
        except:
            if os.path.exists("image/" + file_name):
                os.remove("image/" + file_name)
                face_recognition.load_encoding_images("image/")
                return make_response(jsonify({"message": "unable to save faces in the database"}), 400)
        return make_response(jsonify({"message": "face recognition success"}), 201)
    except:
        return make_response(jsonify({"message": "have somthing error"}), 400)

@app.route('/checker', methods = ['POST'])
def checker_file():
    try:
        if 'imageFile' not in request.files:
            return make_response(jsonify({"message": "please send file"}), 400)
        file = request.files['imageFile']
        is_match = face_recognition.detect_known_faces(file)
        if is_match:
            return make_response(jsonify({"message": "have your face in database"}), 200)
        else:
            return make_response(jsonify({"message": "not have your face in database"}), 404)
    except:
        return make_response(jsonify({"message": "have somthing error"}), 400)

if __name__ == '__main__':
    app.run(host='192.168.1.45', port=25565)