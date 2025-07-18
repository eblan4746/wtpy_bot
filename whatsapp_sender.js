const { useMultiFileAuthState, makeWASocket } = require("@whiskeysockets/baileys");
const qrcode = require('qrcode-terminal');
const fs = require('fs');

const args = process.argv.slice(2);
const [sessionName, groupLink, durationHours, messagesFile] = args;

async function run() {
    // Инициализация аутентификации
    const { state, saveCreds } = await useMultiFileAuthState(`sessions/${sessionName}`);
    
    // Создание сокета WhatsApp
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        logger: { level: 'warn' }
    });

    // Генерация QR-кода
    sock.ev.on('connection.update', ({ qr }) => {
        if (qr) {
            qrcode.generate(qr, { small: true });
            fs.writeFileSync(`sessions/${sessionName}_qr.txt`, qr);
        }
    });

    // Сохранение учетных данных
    sock.ev.on('creds.update', saveCreds);

    // Ожидание подключения
    await new Promise(resolve => sock.ev.on('connection.update', (update) => {
        if (update.connection === 'open') resolve();
    }));

    console.log('✅ WhatsApp подключен!');
    
    // Извлечение ID группы из ссылки
    const groupId = groupLink.split('/').pop();
    
    // Присоединение к группе
    await sock.groupAcceptInvite(groupId);
    console.log(`✅ Присоединились к группе: ${groupId}`);
    
    // Загрузка сообщений из файла
    const messages = JSON.parse(fs.readFileSync(messagesFile, 'utf-8'));
    const totalMessages = messages.length;
    
    // Расчет интервала между сообщениями
    const totalHours = parseInt(durationHours);
    const messageInterval = (totalHours * 3600000) / totalMessages;
    
    // Отправка сообщений
    for (let i = 0; i < totalMessages; i++) {
        const randomDelay = Math.random() * messageInterval;
        const delay = i * messageInterval + randomDelay;
        
        setTimeout(async () => {
            try {
                await sock.sendMessage(`${groupId}@g.us`, { 
                    text: messages[i]
                });
                console.log(`✉️ Отправлено сообщение #${i+1}/${totalMessages}`);
            } catch (error) {
                console.error('Ошибка отправки:', error);
            }
        }, delay);
    }
    
    console.log(`⏳ Запланировано ${totalMessages} сообщений на ${totalHours} часов`);
}

run().catch(err => {
    console.error('❗ Ошибка в работе:', err);
    process.exit(1);
});