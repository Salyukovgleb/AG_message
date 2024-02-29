document.addEventListener('DOMContentLoaded', function () {
    startInactivityTimer();
    updateContactList(); // Предполагается, что вы хотите загрузить и отобразить контакты при загрузке страницы
});

// SocketIO connection
const socketio = io();

// Function to add a new contact
function add_contact() {
    const uniqueNumberInput = document.getElementById('unique_number');
    const personNameInput = document.getElementById('person_name');

    const uniqueNumber = uniqueNumberInput.value.trim();
    const personName = personNameInput.value.trim();

    // Check for empty fields
    if (!uniqueNumber || !personName) {
        alert('Fill in all required fields.');
        return;
    }

    console.log('Adding contact:', { unique_number: uniqueNumber, person_name: personName });

    // Send a request to add the contact
    axios.post('/add_contact', {
        unique_number: uniqueNumber,
        person_name: personName
    })
    .then(response => {
        console.log('Server response:', response.data);

        if (response.data.message) {
            alert('Contact added successfully!');
            uniqueNumberInput.value = '';
            personNameInput.value = '';
            // Update the contact list
            updateContactList();

            // Emit a SocketIO event to inform clients about the new contact
            socketio.emit('new_contact', { name: personName });
        } else if (response.data.error) {
            alert('Error adding contact: ' + response.data.error);
        }
    })
    .catch(error => {
        console.error('Error sending request:', error);
        alert('Error sending request to the server.');
    });
}

// SocketIO event listener for a new contact
socketio.on('new_contact', function(data) {
    const contactsList = document.getElementById('contacts');
    const li = document.createElement('li');
    li.textContent = data.name;
    contactsList.appendChild(li);
});


function updateContactList() {
    const contactsList = document.getElementById('contacts');

    axios.get('/get_contacts')
        .then(response => {
            contactsList.innerHTML = ''; // Очистка текущего списка

            response.data.contacts.forEach(contact => {
                const li = document.createElement('li');
                li.textContent = contact.name; // Отображение имени контакта
                li.classList.add('contact-item'); // Добавление класса для стилизации
                li.addEventListener('click', () => {
                    console.log('Клик по контакту:', contact.name); // Добавьте это для проверки
                    openChatWithContact(contact.name);
                });
                contactsList.appendChild(li);
            });
        })
        .catch(error => console.error('Ошибка при получении списка контактов:', error));
}




// Event listener for the button click
document.addEventListener('DOMContentLoaded', function () {
    const addContactButton = document.getElementById('add_contact_button');
    if (addContactButton) {
        addContactButton.addEventListener('click', function () {
            try {
                add_contact();
            } catch (error) {
                console.error('Error in add_contact:', error);
            }
        });
    }
});

// Event listener for the Logout button
document.addEventListener('DOMContentLoaded', function () {
    const logoutButton = document.getElementById('logoutButton');

    if (logoutButton) {
        logoutButton.addEventListener('click', function () {
            logout();
        });
    }
});

function logout() {
    axios.get('/logout')
        .then(response => {
            if (response.data && response.data.success) {
                // Clear session and redirect to the signin page
                session.clear();
                window.location.replace('/signin');
            } else {
                console.error('Logout failed:', response.data ? response.data.error : 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Error during logout:', error);
        });
}


// Function to start the inactivity timer
function startInactivityTimer() {
    let inactivityTime = 300000; // 5 minutes in milliseconds
    let timeoutId;
    let countdownElement = document.getElementById('countdown');

    function resetTimer() {
        clearTimeout(timeoutId);
        let remainingTime = inactivityTime;

        function updateCountdown() {
            const minutes = Math.floor(remainingTime / 60000);
            const seconds = Math.floor((remainingTime % 60000) / 1000);

            countdownElement.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
        }

        timeoutId = setInterval(() => {
            updateCountdown();
            remainingTime -= 1000;

            if (remainingTime < 0) {
                clearInterval(timeoutId);
                logout();
            }
        }, 1000);

        updateCountdown();
    }

    function logout() {
        axios.get('/logout')
            .then(response => {
                window.location.href = '/signin';
            })
            .catch(error => {
                console.error('Error during logout:', error);
            });
    }

    document.addEventListener('mousemove', resetTimer);
    document.addEventListener('keypress', resetTimer);

    resetTimer();
}




// Предположим, что у вас есть функция для получения контактов
document.addEventListener('DOMContentLoaded', function() {
    axios.get('/get_contacts')
        .then(function(response) {
            const contacts = response.data.contacts;
            const contactsListElement = document.getElementById('contacts-list'); // Предполагается, что у вас есть элемент с id="contacts-list"

            // Очистка списка перед добавлением новых элементов
            contactsListElement.innerHTML = '';

            contacts.forEach(contact => {
                const li = document.createElement('li');
                li.textContent = contact.name; // Теперь здесь только имя контакта
                contactsListElement.appendChild(li);
            });
        })
        .catch(function(error) {
            console.log('Ошибка при загрузке контактов:', error);
        });
});

// Вызовите эту функцию где-то в вашем коде, чтобы загрузить контакты
loadContacts();

li.addEventListener('click', function() {
    // Здесь логика для открытия чата с выбранным контактом
    // Например, можно изменить содержимое какого-то элемента для отображения чата
    console.log('Чат с', li.textContent, 'открыт');
    // Допустим, у вас есть элемент с id="person_chat" для отображения чата
    document.getElementById('person_chat').innerHTML = 'Чат с ' + li.textContent;
});

function openChatWithContact(contactName) {
    // Очищаем предыдущие сообщения
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = '';

    // Устанавливаем имя выбранного пользователя в качестве заголовка чата
    document.getElementById('person_chat').innerHTML = `<h3>${contactName}</h3>
                                                        <div id="chat-messages" class="chat-messages"></div>
                                                        <div class="chat-input">
                                                            <input type="text" id="message-input" placeholder="Введите сообщение...">
                                                            <button id="send-message" onclick="sendChatMessage('${contactName}')">Отправить</button>
                                                        </div>`;

    // Загружаем историю чата для выбранного контакта
    axios.get(`/get_chat_history/${contactName}`)
        .then(response => {
            response.data.forEach(msg => {
                const messageElement = document.createElement('div');
                messageElement.textContent = `${msg.sender}: ${msg.message}`;
                document.getElementById('chat-messages').appendChild(messageElement);
            });
        })
        .catch(error => console.error('Ошибка при загрузке истории чата:', error));
}




// Отправка сообщения на сервер
document.getElementById('send-message').addEventListener('click', function() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    if (message) {
        // Предположим, что sender и receiver установлены где-то в вашем коде
        socket.emit('send_message', {sender: 'Имя отправителя', receiver: 'Имя получателя', message: message});
        messageInput.value = ''; // Очистка поля ввода

        // Добавляем сообщение в чат
        const chatMessages = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.textContent = `Вы: ${message}`;
        chatMessages.appendChild(messageElement);
    }
});


// Прослушивание новых сообщений от сервера
socket.on('new_message', function(data) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    messageElement.textContent = `${data.sender}: ${data.message}`;
    chatMessages.appendChild(messageElement);
});






function sendChatMessage(contactName) {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    if (message) {
        console.log(`Отправка сообщения "${message}" пользователю ${contactName}`);
        // Здесь код для отправки сообщения на сервер...

        // Добавляем сообщение в чат сразу после отправки
        const chatMessages = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.textContent = message; // Ваше сообщение
        chatMessages.appendChild(messageElement);

        messageInput.value = ''; // Очищаем поле ввода после отправки
    }
}


// Должно быть внутри функции updateContactList после успешного получения списка контактов
response.data.contacts.forEach(contact => {
    const li = document.createElement('li');
    li.textContent = contact.name;
    li.classList.add('contact-item');
    li.addEventListener('click', () => openChatWithContact(contact.name)); // Убедитесь, что это работает
    contactsList.appendChild(li);
});

contacts.forEach(contact => {
    const li = document.createElement('li');
    li.textContent = contact.name;
    li.addEventListener('click', () => {
        openChatWithContact(contact.name);
    });
    contactsList.appendChild(li);
});





// Подключение к Socket.IO
var socket = io.connect('http://' + document.domain + ':' + location.port);

// Отправка сообщения на сервер
socket.emit('send_message', {sender: 'Артем', receiver: 'Ботыр', message: 'Привет!'});

// Прослушивание новых сообщений от сервера
socket.on('new_message', function(data) {
    console.log(data);
    // Здесь код для добавления сообщения в чат на клиенте
});



function init() {
    updateContactList();
    // Другие необходимые инициализации
}

document.addEventListener('DOMContentLoaded', init);


// Call init function
init();
