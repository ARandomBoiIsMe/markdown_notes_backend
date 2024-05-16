import sqlite3
from sqlite3 import Error

def connect_to_db():
    try:
        # Configures the returned rows to be structured as Python dictionaries
        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return {key: value for key, value in zip(fields, row)}

        connection = sqlite3.connect('markdown_project.db', check_same_thread=False)
        connection.row_factory = dict_factory # Used here

        connection.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT NOT NULL PRIMARY KEY,
                        password TEXT NOT NULL
                    );
                    """)

        connection.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY,
                        user TEXT DEFAULT NULL,
                        title VARCHAR(250) NOT NULL,
                        content TEXT NOT NULL,
                        view VARCHAR(8) NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        FOREIGN KEY (user) REFERENCES users(username)
                    );
                    """)

        connection.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT NOT NULL PRIMARY KEY,
                        user TEXT NOT NULL,
                        login_time DATETIME NOT NULL,
                        FOREIGN KEY (user) REFERENCES users(username)
                    );
                    """)

        return connection
    except Error as error:
        raise error

def get_user(connection, user):
    cursor = connection.cursor()

    query = "SELECT * FROM users WHERE username = ?"
    values = (user['username'],)

    cursor.execute(query, values)
    return cursor.fetchone()

def get_user_details(connection, user):
    cursor = connection.cursor()

    query = "SELECT users.username as username, notes.id as id, notes.title as title, "\
            "notes.content as content,  notes.created_at as created_at, "\
            "notes.view as view, notes.updated_at as updated_at "\
            "FROM users LEFT JOIN notes ON users.username = notes.user WHERE username = ?"
    values = (user,)

    cursor.execute(query, values)
    return cursor.fetchall()

def create_user(connection, user):
    user_ = get_user(connection, user)

    if user_:
        return 0

    cursor = connection.cursor()

    query = "INSERT INTO users (username, password) VALUES (?, ?)"
    values = (user['username'], user['password'])

    cursor.execute(query, values)
    connection.commit()

def create_note(connection, note, user, view, current_time):
    cursor = connection.cursor()

    query = "INSERT INTO notes (user, title, content, view, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
    values = (user, note['title'], note['content'], view, current_time, current_time)

    cursor.execute(query, values)
    connection.commit()

def get_note(connection, id):
    cursor = connection.cursor()

    query = "SELECT * FROM notes WHERE id = ?"
    values = (id,)

    cursor.execute(query, values)
    return cursor.fetchone()

def edit_note(connection, id, data, current_time):
    cursor = connection.cursor()

    query = "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?"
    values = (data['title'], data['content'], current_time, id,)

    cursor.execute(query, values)
    connection.commit()

def delete_note(connection, id):
    cursor = connection.cursor()

    query = "DELETE FROM notes WHERE id = ?"
    values = (id,)

    cursor.execute(query, values)
    connection.commit()

def get_session(connection, id):
    cursor = connection.cursor()

    query = "SELECT * FROM sessions WHERE session_id = ?"
    values = (id,)

    cursor.execute(query, values)
    return cursor.fetchone()

def store_session(connection, session, user, current_time):
    session_ = get_session(connection, session)

    # Deletes old user session
    if session_:
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session,))
        connection.commit()

    cursor = connection.cursor()

    query = "INSERT INTO sessions (session_id, user, login_time) VALUES (?, ?, ?)"
    values = (session, user['username'], current_time)

    cursor.execute(query, values)
    connection.commit()

def delete_session(connection, id):
    session_ = get_session(connection, id)

    if not session_:
        return 0

    cursor = connection.cursor()

    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (id,))
    connection.commit()

def close_connection(connection):
    connection.close()