import os
import sqlite3
import random
from sqlite3 import Error
from contextlib import closing
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'baza.db')
KEY_FILE = os.path.join(BASE_DIR, 'secret.key')


# Ensure this runs only once to generate the key
def generate_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)

def load_key():
    try:
        return open(KEY_FILE, "rb").read()
    except FileNotFoundError:
        print("Encryption key file not found. Generating a new one.")
        generate_key()
        return open(KEY_FILE, "rb").read()

# Use the load_key function to read the encryption key
def encrypt_message(message):
    key = load_key()
    f = Fernet(key)
    encrypted_message = f.encrypt(message.encode())
    return encrypted_message

def decrypt_message(encrypted_message):
    key = load_key()
    f = Fernet(key)
    decrypted_message = f.decrypt(encrypted_message).decode()
    return decrypted_message



def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Это важно
        print(sqlite3.version)
    except Error as e:
        print(e)
    return conn





def create_users_table(conn):
    sql = '''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                unique_number TEXT
            );'''
    execute_query(conn, sql)



def create_authentication_table(conn):
    sql = '''CREATE TABLE IF NOT EXISTS authentication (
                user_id INTEGER PRIMARY KEY,
                password TEXT,
                secret_word TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );'''
    execute_query(conn, sql)



def create_device_info_table(conn):
    sql = '''CREATE TABLE IF NOT EXISTS device_info (
                user_id INTEGER PRIMARY KEY,
                ip_address TEXT,
                mac_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );'''
    execute_query(conn, sql)

def create_contacts_table(conn):
    sql = '''CREATE TABLE IF NOT EXISTS contacts (
                contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                unique_number TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );'''
    execute_query(conn, sql)

def create_messages_table(conn):
    sql = '''CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                receiver_id INTEGER,
                message_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(user_id),
                FOREIGN KEY (receiver_id) REFERENCES users(user_id)
            );'''
    execute_query(conn, sql)


def execute_query(conn, sql):
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
    except Error as e:
        print(e)


def create_database():
    conn = create_connection()
    if conn:
        create_users_table(conn)
        create_authentication_table(conn)
        create_device_info_table(conn)
        conn.close()

def create_database():
    conn = create_connection()
    if conn:
        create_users_table(conn)
        create_authentication_table(conn)
        create_device_info_table(conn)
        create_contacts_table(conn)  # Add this line to create the contacts table
        conn.close()

def create_database():
    conn = create_connection()
    if conn:
        create_users_table(conn)
        create_authentication_table(conn)
        create_device_info_table(conn)
        create_contacts_table(conn)
        create_messages_table(conn)  # Ensure this is the only call
        conn.close()

def generate_unique_key():
    # Генерируем уникальный ключ из 12 цифр
    unique_key = ''.join([str(random.randint(0, 9)) for _ in range(12)])
    return unique_key

def insert_contact_data(conn, user_id, name, unique_number):
    try:
        with conn:
            conn.execute("INSERT INTO contacts (user_id, name, unique_number) VALUES (?, ?, ?)", (user_id, name, unique_number))

        print(f"Contact added successfully: name={name}, unique_number={unique_number}")
    except sqlite3.ProgrammingError as pe:
        if "Cannot operate on a closed database" in str(pe):
            print("Error in insert_contact_data: Database connection is closed.")
        else:
            print(f"Error in insert_contact_data: {str(pe)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in insert_contact_data: {str(e)}")

def get_user_id_by_name(conn, full_name):
    """Возвращает идентификатор пользователя по его полному имени."""
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE full_name = ?", (full_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None



def fetch_messages(conn, user_id, contact_id):
    """Извлекает сообщения между двумя пользователями."""
    cursor = conn.cursor()
    cursor.execute("""SELECT message, timestamp FROM messages
                      WHERE (sender_id = ? AND receiver_id = ?)
                      OR (sender_id = ? AND receiver_id = ?)
                      ORDER BY timestamp ASC""",
                   (user_id, contact_id, contact_id, user_id))
    messages = cursor.fetchall()
    return [{'message': message[0], 'timestamp': message[1]} for message in messages]


def insert_user_data(conn, full_name, password, secret_word, ip_address, mac_address):
    user_sql = "INSERT INTO users (full_name, unique_number) VALUES (?, ?)"

    # Генерируем уникальный ключ из 12 цифр
    unique_number = generate_unique_key()

    cursor = conn.cursor()
    cursor.execute(user_sql, (full_name, unique_number))
    conn.commit()

    user_id = cursor.lastrowid

    auth_sql = "INSERT INTO authentication (user_id, password, secret_word) VALUES (?, ?, ?)"
    cursor.execute(auth_sql, (user_id, password, secret_word))
    conn.commit()

    device_info_sql = "INSERT INTO device_info (user_id, ip_address, mac_address) VALUES (?, ?, ?)"
    cursor.execute(device_info_sql, (user_id, ip_address, mac_address))
    conn.commit()


def user_exists(conn, unique_number):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE unique_number=?", (unique_number,))
        user = cursor.fetchone()
        return user is not None
    except Exception as e:
        print(f"Error in user_exists: {str(e)}")
        return False
    # finally:
    #     conn.close()



def get_contacts_list(db_file):
    """
    Функция для получения списка имен контактов из базы данных.

    Параметры:
    db_file (str): Путь к файлу базы данных SQLite.

    Возвращает:
    list: Список имен контактов.
    """
    contacts_list = []

    # Создание соединения с базой данных с использованием контекстного менеджера
    with closing(sqlite3.connect(db_file)) as conn:
        # Создание курсора
        cursor = conn.cursor()

        # Выполнение SQL-запроса
        cursor.execute('SELECT name FROM contacts')

        # Получение всех результатов выполнения запроса
        contacts = cursor.fetchall()

        # Преобразование результатов в список имен
        contacts_list = [contact[0] for contact in contacts]

    return contacts_list


def insert_message(conn, sender_id, receiver_id, message_text):
    try:
        encrypted_message = encrypt_message(message_text)
        sql = '''INSERT INTO messages (sender_id, receiver_id, message_text)
                 VALUES (?, ?, ?)'''
        with conn:
            conn.execute(sql, (sender_id, receiver_id, encrypted_message))
    except Error as e:
        print(f"Error inserting message: {e}")



def get_messages(conn, sender_id, receiver_id):
    sql = '''SELECT * FROM messages
             WHERE sender_id = ? AND receiver_id = ?
             OR sender_id = ? AND receiver_id = ?
             ORDER BY timestamp'''
    cursor = conn.cursor()
    cursor.execute(sql, (sender_id, receiver_id, receiver_id, sender_id))
    encrypted_messages = cursor.fetchall()
    decrypted_messages = []
    for msg in encrypted_messages:
        decrypted_text = decrypt_message(msg["message_text"])
        decrypted_messages.append({**msg, "message_text": decrypted_text})
    return decrypted_messages





def get_mac_address(environ):
    # This is a simplified way to get the MAC address in a development environment
    return environ.get('HTTP_X_REAL_IP', 'get_this_value_from_request')


if __name__ == '__main__':
    db_path = 'db/baza.db'  # Укажите здесь путь к вашей базе данных
    contacts = get_contacts_list(db_path)
    print("Список контактов:")
    for name in contacts:
        print(name)
