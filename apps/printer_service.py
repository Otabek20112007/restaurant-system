"""
Сервис печати на IP-принтеры (Xprinter ESC/POS).
Отправляет тикеты на принтеры по сети (TCP порт 9100).
"""
import socket
import logging

logger = logging.getLogger(__name__)


# --- ESC/POS команды ---
ESC_INIT = b'\x1b\x40'                      # Инициализация
ESC_ALIGN_LEFT = b'\x1b\x61\x00'            # Выравнивание влево
ESC_ALIGN_CENTER = b'\x1b\x61\x01'          # Выравнивание по центру
ESC_BOLD_ON = b'\x1b\x45\x01'               # Жирный вкл
ESC_BOLD_OFF = b'\x1b\x45\x00'              # Жирный выкл
ESC_DOUBLE_ON = b'\x1b\x21\x30'             # Двойной размер вкл
ESC_DOUBLE_OFF = b'\x1b\x21\x00'            # Двойной размер выкл
ESC_FEED = b'\n\n\n'                        # Подача бумаги
ESC_CUT = b'\x1d\x56\x00'                   # Обрезка
ESC_CODEPAGE_CYRILLIC = b'\x1b\x74\x11'     # Кириллица CP866


def send_to_printer(ip: str, port: int, data: bytes, timeout: int = 5) -> bool:
    """
    Отправляет байты на принтер по сети (RAW-печать).
    Возвращает True при успехе.
    """
    if not ip:
        logger.warning("IP принтера не задан — печать пропущена")
        return False
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((ip, port))
            sock.sendall(data)
        logger.info(f"✅ Данные отправлены на {ip}:{port}")
        return True
    except socket.timeout:
        logger.error(f"❌ Таймаут при подключении к {ip}:{port}")
        return False
    except ConnectionRefusedError:
        logger.error(f"❌ Принтер {ip}:{port} отклонил соединение")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка печати на {ip}:{port} — {e}")
        return False


def build_ticket(order, target: str, fallback: bool = False) -> bytes:
    """
    Формирует тикет для конкретного цеха.
    В тикет попадают только блюда этого цеха.
    """
    ticket = ESC_INIT + ESC_CODEPAGE_CYRILLIC
    ticket += ESC_ALIGN_CENTER + ESC_DOUBLE_ON
    
    if fallback:
        ticket += b"*** FALLBACK ***\n"
        target_label = {
            'kitchen': 'ДЛЯ КУХНИ',
            'bar': 'ДЛЯ БАРА',
            'cold': 'ДЛЯ ХОЛОДНОГО ЦЕХА',
            'cashier': 'ДЛЯ КАССЫ',
        }.get(target, target.upper())
        ticket += f"[{target_label}]\n".encode('cp866')
    
    ticket += f"ЗАКАЗ #{order.id}\n".encode('cp866')
    ticket += ESC_DOUBLE_OFF
    
    table_num = order.table.number if order.table else '?'
    ticket += f"Стол: {table_num}\n".encode('cp866')
    ticket += b"================================\n"
    
    # Позиции заказа, отфильтрованные по цеху
    for item in order.items.all():
        if item.menu_item.category.printer_target != target:
            continue
        
        ticket += ESC_ALIGN_LEFT + ESC_BOLD_ON
        line = f"{item.quantity}x {item.menu_item.name}\n"
        ticket += line.encode('cp866')
        ticket += ESC_BOLD_OFF
        
        if order.comment:
            ticket += f"   ({order.comment})\n".encode('cp866')
    
    ticket += b"================================\n"
    ticket += f"Время: {order.created_at.strftime('%H:%M')}\n".encode('cp866')
    
    if fallback:
        ticket += "!!! ПЕРЕДАТЬ В ЦЕХ !!!\n".encode('cp866')
    
    ticket += ESC_FEED + ESC_CUT
    return ticket


def _has_items_for_target(order, target: str) -> bool:
    """Проверяет, есть ли в заказе блюда для этого цеха"""
    return any(
        item.menu_item.category.printer_target == target
        for item in order.items.all()
    )


def print_order_to_target(order, target: str) -> dict:
    """
    Печатает заказ на принтер цеха.
    Если принтера нет — отправляет на fallback (касса).
    
    Возвращает:
    {
        'target': 'kitchen',
        'printed': True/False,
        'fallback_used': True/False,
        'reason': 'причина'
    }
    """
    from .models import Printer, FailedPrintJob
    
    # Если для этого цеха нет блюд — ничего не делаем
    if not _has_items_for_target(order, target):
        return {
            'target': target,
            'printed': False,
            'fallback_used': False,
            'reason': 'no_items_for_target'
        }
    
    # Ищем принтер цеха с настроенным IP
    printer = Printer.objects.filter(
        target=target,
        is_active=True,
        ip_address__isnull=False
    ).exclude(ip_address='').first()
    
    # Если нашли — печатаем
    if printer:
        ticket = build_ticket(order, target, fallback=False)
        if send_to_printer(printer.ip_address, printer.port, ticket):
            return {
                'target': target,
                'printed': True,
                'fallback_used': False,
                'printer': printer.name,
                'reason': 'ok'
            }
        logger.warning(f"Принтер {printer.name} недоступен")
        reason = 'printer_unreachable'
    else:
        logger.info(f"Нет принтера для цеха '{target}' — используем fallback")
        reason = 'no_printer'
    
    # Fallback: ищем принтер по умолчанию
    fallback_printer = Printer.get_fallback()
    
    if fallback_printer and fallback_printer.ip_address:
        ticket = build_ticket(order, target, fallback=True)
        if send_to_printer(fallback_printer.ip_address, fallback_printer.port, ticket):
            return {
                'target': target,
                'printed': True,
                'fallback_used': True,
                'printer': fallback_printer.name,
                'reason': reason
            }
        else:
            logger.error(f"Fallback-принтер {fallback_printer.name} недоступен")
            reason = 'fallback_unreachable'
    else:
        logger.warning("Fallback-принтер не настроен")
        reason = 'no_fallback'
    
    # Совсем некуда печатать — сохраняем для кассы
    FailedPrintJob.objects.create(
        order=order,
        target=target,
        reason=reason
    )
    
    return {
        'target': target,
        'printed': False,
        'fallback_used': False,
        'reason': reason
    }


def print_order_to_all_targets(order) -> dict:
    """
    Печатает заказ по всем цехам, представленным в заказе.
    Возвращает словарь {цех: результат}.
    """
    targets = set(
        item.menu_item.category.printer_target
        for item in order.items.all()
    )
    
    results = {}
    for target in targets:
        results[target] = print_order_to_target(order, target)
    
    return results