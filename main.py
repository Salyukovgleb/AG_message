from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_socketio import SocketIO, emit
from db.baza import create_database, create_connection, insert_user_data, insert_contact_data, user_exists, get_mac_address, insert_message, get_messages, get_user_id_by_name
import os
import sqlite3
from sqlite3 import Error
from contextlib import closing
from datetime import datetime
import json

# Assuming you have functions `encrypt_message` and `decrypt_message` in `db.baza`
from db.baza import encrypt_message, decrypt_message


app = Flask(__name__, static_url_path='/static', static_folder='static')
socketio = SocketIO(app)

app.secret_key = 'your_random_secret_key_here'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))






@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

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
    print('Logging out')  # Для отладки
    session.clear()
    return redirect(url_for('signin'))


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        secret_word = request.form['secret_word']
        password = request.form['password']
        print(f"Trying to authenticate user: {secret_word}")

        auth_success, user_name = check_user_credentials(secret_word, password)
        if auth_success:
            print(f"User authenticated: {user_name}")
            session['user_logged_in'] = True
            session['username'] = user_name
            return redirect(url_for('index'))
        else:
            print("Authentication failed")
            return render_template('registration/signin.html', error="Invalid credentials")
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

@app.route('/delete_contact', methods=['POST'])
def delete_contact():
    data = request.json
    contact_name = data.get('name')

    database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
    with closing(create_connection(database_path)) as conn:
        # Замените этот SQL запрос на запрос, который удаляет контакт из вашей базы данных
        conn.execute('DELETE FROM contacts WHERE name = ?', (contact_name,))
        conn.commit()

    return jsonify({'success': True})


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




@socketio.on('send_message')
def handle_send_message(data):
    print('Received message:', data)  # Для дебага
    sender = data.get('sender')
    receiver = data.get('receiver')
    message = data.get('message')

    if not all([sender, receiver, message]):
        print("Ошибка: недостаточно данных для отправки сообщения.")
        return

    database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
    with closing(create_connection(database_path)) as conn:
        try:
            # Предполагаем, что sender и receiver - это идентификаторы пользователей
            insert_message(conn, sender, receiver, message)
            emit('new_message', data, broadcast=True)  # Отправляем сообщение всем подключенным клиентам
        except Exception as e:
            print(f"Ошибка при вставке сообщения: {e}")


@app.route('/get_messages/<int:sender_id>/<int:receiver_id>', methods=['GET'])
def fetch_messages(sender_id, receiver_id):
    database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
    with closing(create_connection(database_path)) as conn:
        messages = get_messages(conn, sender_id, receiver_id)
        decrypted_messages = [{'sender_id': msg['sender_id'], 'receiver_id': msg['receiver_id'], 'message': decrypt_message(msg['message_text']), 'timestamp': msg['timestamp']} for msg in messages]

    return jsonify(decrypted_messages)

@app.route('/get_chat_history/<contact_name>')
def get_chat_history(contact_name):
    if 'username' not in session:
        # Если пользователя нет в сессии, возвращаем ошибку 401
        return jsonify({'error': 'Unauthorized'}), 401

    database_path = os.path.join(BASE_DIR, 'db', 'baza.db')  # Добавьте эту строку

    # Создаем соединение с базой данных
    with closing(create_connection(database_path)) as conn:  # Измените эту строку
        # Получаем идентификаторы пользователя и контакта
        user_id = get_user_id_by_name(conn, session['username'])
        contact_id = get_user_id_by_name(conn, contact_name)

        if user_id is None or contact_id is None:
            # Если не найден пользователь или контакт, возвращаем ошибку 404
            return jsonify({'error': 'User or contact not found'}), 404

        # Извлекаем историю чата
        chat_history = fetch_messages(conn, user_id, contact_id)
        return jsonify(chat_history)

    # В случае ошибки доступа к базе данных возвращаем ошибку 500
    return jsonify({'error': 'Internal Server Error'}), 500




# Dummy function to simulate fetching chat history for a contact
# Replace this with your actual database query logic
def get_chat_history_for_contact(contact_name):
    # Dummy data - replace with actual data retrieval and decryption
    return [{
        'sender': 'example_sender',
        'receiver': contact_name,
        'message': 'Dummy encrypted message',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }]


@app.route('/fetch_chat_history/<contact_name>')
def fetch_chat_history(contact_name):
    try:
        # Fetch chat history for the contact
        chat_history = get_chat_history_for_contact(contact_name)

        # Assuming you decrypt messages here before sending them back
        decrypted_chat_history = []
        for message in chat_history:
            decrypted_message = {
                **message,
                'message': decrypt_message(message['message']).decode('utf-8')
                # Adjust according to your encryption logic
            }
            decrypted_chat_history.append(decrypted_message)

        return jsonify(decrypted_chat_history)
    except Exception as e:
        print(f"Error fetching chat history: {str(e)}")
        return jsonify({"error": "Error fetching chat history"}), 500

def check_user_credentials(secret_word, password):
    database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
    conn = create_connection(database_path)

    if conn:
        try:
            cursor = conn.cursor()
            # Предполагается, что у вас есть столбец username в таблице users,
            # а таблица authentication связана с таблицей users через user_id
            cursor.execute("""SELECT users.full_name 
                              FROM authentication 
                              JOIN users ON users.user_id = authentication.user_id 
                              WHERE authentication.secret_word=? AND authentication.password=?""",
                           (secret_word, password))
            result = cursor.fetchone()
            if result:
                return True, result[0]  # Возвращаем True и имя пользователя
            else:
                return False, None
        except Error as e:
            print(e)
        finally:
            conn.close()
    return False, None

# Функция добавления сообщения в базу данных уже должна принимать зашифрованное сообщение
def insert_message(conn, sender_id, receiver_id, encrypted_message):
    sql = '''INSERT INTO messages (sender_id, receiver_id, message_text)
             VALUES (?, ?, ?)'''
    with conn:
        conn.execute(sql, (sender_id, receiver_id, encrypted_message))
        conn.commit()

@socketio.on('send_message')
def handle_send_message(data):
    sender = data.get('sender')  # Здесь должен быть ID отправителя, а не имя
    receiver = data.get('receiver')  # И здесь должен быть ID получателя, а не имя
    message = data.get('message')

    if not all([sender, receiver, message]):
        print("Ошибка: недостаточно данных для отправки сообщения.")
        return

    try:
        # Шифрование сообщения
        encrypted_message = encrypt_message(message)
        # Сохранение в базе данных
        database_path = os.path.join(BASE_DIR, 'db', 'baza.db')
        with closing(create_connection(database_path)) as conn:
            insert_message(conn, sender, receiver, encrypted_message)

        # Отправка сообщения обратно в интерфейс
        emit('new_message', data, broadcast=True)
    except Exception as e:
        print(f"Ошибка при вставке сообщения: {e}")


if __name__ == '__main__':
    create_database()
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)

