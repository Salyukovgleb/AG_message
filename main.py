from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_socketio import SocketIO, emit
from db.baza import create_database, create_connection, insert_user_data, insert_contact_data, user_exists, get_mac_address
import os
import sqlite3
from sqlite3 import Error
from contextlib import closing

import json

app = Flask(__name__, static_url_path='/static', static_folder='static')
socketio = SocketIO(app)


app.secret_key = 'your_random_secret_key_here'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
chat_history_path = os.path.join(BASE_DIR, 'chat_history.json')


with open(chat_history_path, 'r') as file:
    chat_history = json.load(file)

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)
    return conn


def check_user_credentials(secret_word, password):
    database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
    conn = create_connection(database_path)

    if conn:
        try:
            cursor = conn.cursor()

            # Execute a SELECT query to check if the user with the provided credentials exists
            cursor.execute("SELECT * FROM authentication WHERE secret_word=? AND password=?", (secret_word, password))

            # Fetch one row (if exists)
            user = cursor.fetchone()

            if user:
                # User with the provided credentials found
                return True

        except Error as e:
            print(e)

        finally:
            conn.close()

    return False  # If no user found or an error occurred


def redirect_if_logged_in(route):
    if 'user_logged_in' in session and session['user_logged_in']:
        return render_template('index.html')
    return redirect(url_for(route))


@app.route('/')
def index():
    if 'user_logged_in' in session and session['user_logged_in']:
        database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
        with closing(create_connection(database_path)) as conn:
            contacts = conn.execute('SELECT name FROM contacts').fetchall()
            contacts_list = [{'name': contact[0]} for contact in contacts]  # Обращаемся к элементу по индексу

        print(contacts_list)
        return render_template('index.html', contacts=contacts_list)

    else:
        return redirect(url_for('signin'))



@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        secret_word = request.form['secret_word']
        password = request.form['password']

        if check_user_credentials(secret_word, password):
            session['user_logged_in'] = True
            return redirect_if_logged_in('index')

    return render_template('registration/signin.html')



@app.route('/main')
def main():
    return redirect_if_logged_in('index')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        secret_word = request.form['secret_word']

        if password != confirm_password:
            return render_template('registration/register.html', error='Passwords do not match')

        database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
        conn = create_connection(database_path)

        if conn:
            if not user_exists(conn, full_name):
                ip_address = request.remote_addr
                mac_address = get_mac_address(request.environ)

                insert_user_data(conn, full_name, password, secret_word, ip_address, mac_address)
                conn.close()
                return redirect_if_logged_in('index')

            conn.close()
            return render_template('registration/register.html', error='User already exists')

    return render_template('registration/register.html', error=None)


def get_user_id(conn, unique_number):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE unique_number=?", (unique_number,))
        user_id = cursor.fetchone()
        return user_id[0] if user_id else None
    except Exception as e:
        print(f"Error in get_user_id: {str(e)}")
        return None


def add_contact(conn, user_id, name, unique_number):
    try:
        with conn:
            insert_contact_data(conn, user_id, name, unique_number)
            print(f"Contact added successfully: name={name}, unique_number={unique_number}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during contact addition: {str(e)}")


@app.route('/add_contact', methods=['POST'])
def add_contact():
    data = request.json

    # Извлечение данных из запроса
    unique_number = data.get('unique_number')
    name = data.get('person_name')

    print(f"Received data: unique_number={unique_number}, name={name}")

    # Проверка, существует ли пользователь с указанным уникальным номером
    database_path = os.path.join(BASE_DIR, 'db', 'baza.db')

    try:
        with closing(create_connection(database_path)) as conn:
            if user_exists(conn, unique_number):
                # Если пользователь существует, добавьте его в контакты
                user_id = get_user_id(conn, unique_number)
                insert_contact_data(conn, user_id, name, unique_number)

                # Возвращение информации о добавленном контакте
                return jsonify({'message': 'Contact added successfully', 'name': name, 'unique_number': unique_number})
            else:
                print(f"User does not exist: unique_number={unique_number}")
                return jsonify({'error': 'User does not exist'})
    except Exception as e:
        print(f"Error during contact addition: {str(e)}")
        return jsonify({'error': str(e)})



@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    if 'user_logged_in' in session and session['user_logged_in']:
        database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
        with closing(create_connection(database_path)) as conn:
            # Измените запрос, если структура таблицы отличается
            contacts = conn.execute('SELECT name FROM contacts').fetchall()
            # Преобразование результатов запроса в список словарей
            contacts_list = [{'name': contact[0]} for contact in contacts]

        return jsonify(contacts=contacts_list)
    else:
        return jsonify({'error': 'Unauthorized'}), 401

@app.route('/get_chat_history/<contact_name>')
def get_chat_history(contact_name):
    try:
        with open(chat_history_path, 'r') as file:
            chat_history = json.load(file)
        # Фильтрация истории чата для конкретного контакта с учетом возможного отсутствия ключей
        history = [msg for msg in chat_history if msg.get('sender') == contact_name or msg.get('receiver') == contact_name]
        return jsonify(history)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка при чтении файла истории чата: {e}")
        return jsonify({"error": "История чата не найдена"}), 500





@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message')
    sender = data.get('sender')
    receiver = data.get('receiver')
    # Здесь код для сохранения сообщения в базе данных или файле
    return jsonify({'status': 'success'})

@socketio.on('send_message')
def handle_send_message(data):
    # Логика добавления сообщения в историю и отправки его всем клиентам
    emit('new_message', data, broadcast=True)

if __name__ == '__main__':
    create_database()
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)

