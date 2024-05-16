from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from flask import Flask, request, jsonify, make_response, redirect
from flask_cors import CORS

from utils import database, authentication

CONNECTION = database.connect_to_db()

app = Flask(__name__)
CORS(app)

@app.post("/register")
def register():
    user = request.get_json()

    if (not user.get('username') or not user.get('password')):
        return jsonify({"message": "Incomplete user data."}), 400

    user['password'] = generate_password_hash(user['password'], 'scrypt')

    response = database.create_user(CONNECTION, user)
    if response == 0:
        return jsonify({"message": "User already has an account."}), 409

    return jsonify({"message": "User registered successfully."}), 200

@app.post("/login")
def login():
    data = request.get_json()

    if not data.get('username') or not data.get('password'):
        return jsonify({"message": "Incomplete credentials."}), 400

    user = database.get_user(CONNECTION, data)
    if not user:
        return jsonify({"message": "Invalid credentials."}), 401

    if not check_password_hash(user['password'], data['password']):
        return jsonify({"message": "Invalid credentials."}), 401

    session = authentication.create_session_id()

    database.store_session(CONNECTION, session, user, datetime.now())

    response = make_response(jsonify({"message": "User logged in successfully."}), 200)
    response.set_cookie('session_id', session)

    return response

@app.get("/logout")
def logout():
    session_id_ = None
    if request.cookies:
        session_id_ = request.cookies.get('session_id')

    result = database.delete_session(CONNECTION, session_id_)
    if result == 0:
        return jsonify({'message': 'You are not logged in.'}), 400

    response = make_response(jsonify({"message": "User logged out successfully."}), 200)
    response.delete_cookie('session_id')

    return response

@app.post('/note/save')
def add_note():
    view = None

    if not request.args:
        view = 'private'
    else:
        view = request.args.get('view')

    if not view or view not in ['private', 'public']:
        return jsonify({"message": "Incomplete request data."}), 400

    session_id_ = None
    if request.cookies:
        session_id_ = request.cookies.get('session_id')

    session = database.get_session(CONNECTION, session_id_)

    if not session and view == 'private':
        return jsonify({'message': 'Log in to create private notes.'}), 401

    note = request.get_json()
    if not note.get('content') or not note.get('title'):
        return jsonify({"message": "Incomplete note data."}), 400

    user = None
    view_ = None

    if not session and view == 'public':
        view_ = view

    elif session:
        user = session['user']
        view_ = view

    database.create_note(
        CONNECTION,
        note,
        user,
        view_,
        datetime.now()
    )

    return jsonify({"message": "Note added successfully."}), 200

@app.post('/note/upload')
def upload_note():
    if 'file' not in request.files:
        return jsonify({'message': 'Encountered error when receiving file. Try again.'}), 400

    file = request.files['file']
    filename = file.filename

    if filename == '':
        return jsonify({'message': 'No file selected. Try again.'}), 400

    if filename.rsplit('.', 1)[1].lower() not in ['txt', 'md']:
        return jsonify(
            {
                'message': 'Invalid file format. Only \'txt\' and \'md\' files allowed. Try again.'
            }
        ), 400

    # Save the file, get its text, then delete it
    # ------------------
    file.save(secure_filename(filename))

    content = None
    with open(filename, 'r') as f:
        content = f.read()

    import os
    os.remove(filename)
    # ------------------

    return jsonify(
        {
            'message': 'File received successfully.',
            'content': content,
            'title': filename.split('.')[0]
        }
    ), 200

@app.get('/note/<id>')
def get_note(id):
    note = database.get_note(CONNECTION, id)
    if not note:
        return jsonify({'message': 'Note does not exist.'}), 404

    session_id_ = None
    if request.cookies:
        session_id_ = request.cookies.get('session_id')

    session = database.get_session(CONNECTION, session_id_)
    if ((not session or session['user'] != note['user']) and note['view'] == 'private'):
        return jsonify({'message': 'Unauthorized viewing of private notes is not allowed.'}), 401

    return jsonify(
        {
            'note': {
                'id': note['id'],
                'title': note['title'],
                'content': note['content'],
                'created_at': note['created_at'],
                'updated_at': note['updated_at']
            }
        }
    ), 200

@app.put('/note/<id>')
def edit_note(id):
    note = database.get_note(CONNECTION, id)
    if not note:
        return jsonify({'message': 'Note does not exist.'}), 404

    session_id_ = None
    if request.cookies:
        session_id_ = request.cookies.get('session_id')

    session = database.get_session(CONNECTION, session_id_)
    if (not session or session['user'] != note['user']):
        return jsonify({'message': 'Unauthorized editing of private notes is not allowed.'}), 401

    data = request.get_json()
    if not data.get('content') or not data.get('title'):
        return jsonify({"message": "Incomplete update details."}), 400

    database.edit_note(
        CONNECTION,
        id,
        data,
        datetime.now()
    )

    return jsonify({"message": "Note edited successfully."}), 200

@app.delete('/note/<id>')
def delete_note(id):
    note = database.get_note(CONNECTION, id)
    if not note:
        return jsonify({'message': 'Note does not exist.'}), 404

    session_id_ = None
    if request.cookies:
        session_id_ = request.cookies.get('session_id')

    session = database.get_session(CONNECTION, session_id_)
    if (not session or session['user'] != note['user']):
        return jsonify({'message': 'Unauthorized deletion of private notes is not allowed.'}), 401

    database.delete_note(CONNECTION, id)

    return jsonify({"message": "Note deleted successfully."}), 200

@app.get('/user/me')
def get_self():
    session_id_ = None
    if request.cookies:
        session_id_ = request.cookies.get('session_id')

    session = database.get_session(CONNECTION, session_id_)
    if not session:
        return jsonify({'message': 'Log in to view all notes made on your account.'}), 401

    me = database.get_user_details(CONNECTION, session['user'])

    return jsonify(
        {
            'name': me[0]['username'],
            'notes': [
                {
                    'id': note['id'],
                    'title': note['title'],
                    'content': note['content'],
                    'created_at': note['created_at'],
                    'updated_at': note['updated_at']
                } for note in me if note['id']
            ]
        }
    ), 200

@app.get('/user/<username>')
def get_user(username):
    session_id_ = None
    if request.cookies:
        session_id_ = request.cookies.get('session_id')

    session = database.get_session(CONNECTION, session_id_)
    if session and session['user'] == username:
        return redirect('/user/me')

    user = database.get_user_details(CONNECTION, username)
    if not user:
        return jsonify({'message': 'User not found.'}), 404

    return jsonify(
        {
            'name': user[0]['username'],
            'notes': [
                {
                    'id': note['id'],
                    'title': note['title'],
                    'content': note['content'],
                    'created_at': note['created_at'],
                    'updated_at': note['updated_at']
                } for note in user if note['view'] == 'public'
            ]
        }
    ), 200

if __name__ == '__main__':
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )