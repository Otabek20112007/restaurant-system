"""
Фейковый принтер. Слушает порт 9100 и выводит полученные данные в консоль.
Запуск: python fake_printer.py
"""
import socket

HOST = '0.0.0.0'
PORT = 9100


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"🖨  Фейковый принтер слушает {HOST}:{PORT}...")
        print("Нажмите Ctrl+C для остановки.\n")
        
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(65536)
                print(f"--- Получено от {addr} ({len(data)} байт) ---")
                # Декодируем CP866 (кириллица для ESC/POS)
                text = data.decode('cp866', errors='replace')
                # Убираем непечатаемые ESC/POS команды для читаемости
                clean = ''.join(
                    c if c.isprintable() or c in '\n' else ''
                    for c in text
                )
                print(clean)
                print("--- Конец тикета ---\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Остановлено.")