#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import smtplib
import logging
from email.message import EmailMessage
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from config import BOT_TOKEN, YOUR_TELEGRAM_ID, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, SMTP_SERVER, SMTP_PORT

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

QUESTIONS_BASE = [
    (1, "1️⃣ Тип объекта:\n\n▪️ Частный жилой дом / коттедж\n▪️ Многоквартирный жилой дом\n▪️ Административное / офисное здание\n▪️ Торговый центр / магазин\n▪️ Складское здание / логистический комплекс\n▪️ Производственное здание / цех\n▪️ Медицинское учреждение / стационар\n▪️ Образовательное учреждение / детский сад / школа\n▪️ Гостиница / хостел / апартаменты\n▪️ Подземный паркинг / автостоянка\n▪️ Культурно-зрелищное учреждение\n▪️ Другое:", 'single'),
    (2, "2️⃣ Общая площадь: _____ м²", 'free'),
    (3, "3️⃣ Этажность (в том числе подземных):", 'free'),
    (4, "4️⃣ Высота здания (от уровня проезда до пола последнего этажа) ___ м:", 'free'),
    (5, "5️⃣ Степень огнестойкости (если определена):\n\n▪️ I\n▪️ II\n▪️ III\n▪️ IV\n▪️ V", 'single'),
    (6, "6️⃣ Класс функциональной пожарной опасности (Ф1.1, Ф1.2, Ф2.1, Ф3.1, Ф4.1, Ф5.1 и т.д.):", 'free'),
    (7, "7️⃣ Категория по взрывопожарной и пожарной опасности для помещений / здания:\n\n▪️ А\n▪️ Б\n▪️ В1-В4\n▪️ Г\n▪️ Д", 'single'),
    (8, "8️⃣ Какие исходные документы есть? (можно выбрать несколько)\n\n▪️ Архитектурные планы (поэтажные, с экспликацией и площадями)\n▪️ Технологическое задание (расстановка оборудования, стеллажей, зон)\n▪️ Технические условия на подключение к электроснабжению\n▪️ Специальные технические условия (СТУ) или расчёт пожарного риска (если есть)\n▪️ Отчёт о категорировании помещений по взрывопожарной опасности\n▪️ Задание на проектирование от заказчика с перечнем систем\n▪️ Ничего нет", 'multi'),
    (9, "9️⃣ Особые условия (можно выбрать несколько):\n\n▪️ Наличие взрывоопасных зон\n▪️ Агрессивные среды (химия, влажность > 75%, температура ниже +5°C или выше +40°C)\n▪️ Помещения с круглосуточным пребыванием людей (стационары, интернаты)\n▪️ Объект культурного наследия (ограничения по монтажу)\n▪️ Высотное здание (> 28/50/75 м)\n▪️ Никаких особенностей", 'multi'),
    (10, "🔟 Нужна ли АПС (по СП 484.1311500, СП 5.13130)?\n\n▪️ Да, требуется в полном объёме\n▪️ Только в отдельных помещениях (указать)\n▪️ Нет (объект не подлежит защите по нормам)", 'single'),
    (11, "1️⃣1️⃣ Тип системы АПС:\n\n▪️ Неадресная (пороговая)\n▪️ Адресно-пороговая\n▪️ Адресно-аналоговая (рекомендуется для большинства объектов)", 'single'),
    (12, "1️⃣2️⃣ Типы пожарных извещателей, которые нужно применить (можно выбрать несколько):\n\n▪️ Дымовые (оптико-электронные)\n▪️ Тепловые (максимальные, дифференциальные)\n▪️ Ручные пожарные извещатели\n▪️ Аспирационные извещатели\n▪️ Линейные дымовые\n▪️ Извещатели пламени (УФ/ИК)\n▪️ Извещатели взрывозащищённого исполнения", 'multi'),
    (13, "1️⃣3️⃣ Особые требования к АПС (можно выбрать несколько):\n\n▪️ Контроль задвижек, насосов, вентиляции\n▪️ Интеграция с СКУД (разблокировка дверей при пожаре)\n▪️ Управление лифтами (спуск на 1-й этаж)\n▪️ Передача сигнала «Пожар» на пульт пожарной охраны\n▪️ Дублирование сигналов на пост охраны с круглосуточным дежурантом\n▪️ Нет дополнительных требований", 'multi'),
    (14, "1️⃣4️⃣ Требуется ли СОУЭ и какого типа?\n\n▪️ Не требуется (только АПС)\n▪️ Тип 1 – звуковое оповещение (сирены)\n▪️ Тип 2 – звуковое + светоуказатели «Выход»\n▪️ Тип 3 – речевое оповещение + светоуказатели\n▪️ Тип 4 – речевое с разделением на зоны, обратная связь\n▪️ Тип 5 – комплексная с управлением движением, противодымной защитой и т.д.\n▪️ Пока не определились, нужен расчёт по нормам", 'single'),
    (15, "1️⃣5️⃣ Зоны оповещения:\n\n▪️ Одна зона на всё здание\n▪️ Поэтажное / посекционное оповещение\n▪️ Разделение на зоны в зависимости от сценариев эвакуации", 'single'),
    (16, "1️⃣6️⃣ Дополнительные элементы СОУЭ (можно выбрать несколько):\n\n▪️ Световые оповещатели «Выход»\n▪️ Табло с подсветкой по путям эвакуации\n▪️ Фотолюминесцентные эвакуационные знаки\n▪️ Система эвакуационного освещения (управление)\n▪️ Речевое оповещение с записанными сообщениями\n▪️ Микрофонная консоль для ручного объявления", 'multi'),
    (17, "1️⃣7️⃣ Требуется ли система автоматического пожаротушения?\n\n▪️ Да, водяное спринклерное\n▪️ Да, водяное дренчерное\n▪️ Да, тонкораспылённая вода (ТРВ)\n▪️ Да, газовое пожаротушение (углекислота, хладоны, инертные газы)\n▪️ Да, порошковое / аэрозольное\n▪️ Да, система пожаротушения пеной\n▪️ Нет, не требуется", 'single'),
]

QUESTIONS_WATER = [
    (18, "Площадь, защищаемая спринклерами _____ м² (или все помещения):", 'free'),
    (19, "Количество спринклерных секций (ориентировочно):", 'free'),
    (20, "Нужна ли насосная станция пожаротушения?\n\n▪️ да, подобрать\n▪️ нет, сеть обеспечивает", 'single'),
    (21, "Требуется ли резервуар для воды (пожарный запас)? Объём по расчёту", 'free'),
    (22, "Нужен ли пожарный водопровод (ВПВ) совмещённый с АУПТ?", 'free'),
    (23, "Категория помещений по влажности, температуре (для выбора типа оросителей)", 'free'),
]

QUESTIONS_GAS = [
    (18, "Перечень помещений, подлежащих защите (серверная, архив, склад ЛВЖ):", 'free'),
    (19, "Требуется ли модульное или централизованное исполнение?", 'free'),
    (20, "Нужно ли выдерживать герметичность помещений (расчёт по утечкам)?", 'free'),
    (21, "Должен ли газ быть безопасным для персонала (3М Novec 1230, хладон 227ea)?", 'free'),
]

COMMON_QUESTIONS = [
    (24, "Требуется ли система противодымной защиты (по СП 7.13130)? (можно выбрать несколько)\n\n▪️ Дымоудаление из коридоров, холлов\n▪️ Дымоудаление из торговых залов, атриумов\n▪️ Дымоудаление из помещений без естественного проветривания\n▪️ Подпор воздуха в лифтовые шахты\n▪️ Подпор в незадымляемые лестничные клетки (Н2, Н3)\n▪️ Подпор в тамбур-шлюзы\n▪️ Компенсационная подача наружного воздуха\n▪️ Нет, не требуется", 'multi'),
    (25, "Особые требования к ПДВ (можно выбрать несколько):\n\n▪️ Автоматическое включение от сигнала АПС\n▪️ Диспетчеризация и контроль параметров\n▪️ Огнестойкость воздуховодов и вентиляторов (EIS 60, 90, 120)\n▪️ Резервирование вентиляторов\n▪️ Нет особых требований", 'multi'),
    (26, "Требуется ли внутренний пожарный водопровод?\n\n▪️ Да, пожарные краны (ПК) с рукавами и стволами\n▪️ Да, совмещённый с хозяйственно-питьевым или отдельный\n▪️ Нет, не требуется", 'single'),
    (27, "Количество одновременно действующих струй:", 'free'),
    (28, "Требуемый расход на пожаротушение (если известен): _____ л/с", 'free'),
    (29, "Наружное пожаротушение:\n\n▪️ Подключение к городским гидрантам\n▪️ Нужны собственные пожарные резервуары или водоём\n▪️ Нужна сухотрубная система для подачи воды пожарными машинами\n▪️ Не требуется", 'single'),
    (30, "Требования к интеграции и автоматике (можно выбрать несколько):\n\n▪️ Единый прибор управления пожарной автоматикой (ППУ)\n▪️ Интеграция со СКУД: разблокировка дверей эвакуационных выходов\n▪️ Управление лифтами при пожаре (спуск, блокировка)\n▪️ Отключение общеобменной вентиляции и кондиционирования\n▪️ Управление противодымными клапанами и вентиляторами\n▪️ Автоматическое включение пожарных насосов\n▪️ Передача сигналов в диспетчерскую (пост охраны)\n▪️ Никакой интеграции не требуется", 'multi'),
    (31, "Электроснабжение пожарных систем:\n\n▪️ Требуется 1 категория надёжности (АВР, дизель-генератор, ИБП)\n▪️ Достаточно 2 категории (АВР, но без автономного генератора)\n▪️ Электропитание только от общей сети (с резервом от аккумуляторов ППК)", 'single'),
    (32, "Дополнительные системы безопасности (можно выбрать несколько):\n\n▪️ Система пожарного мониторинга (передача в МЧС)\n▪️ Система газового контроля (утечка газа, СО)\n▪️ Система оповещения о ЧС на объекте\n▪️ Огнезадерживающие клапаны в воздуховодах\n▪️ Противопожарные двери и шторы с автоматическим закрытием\n▪️ Ничего дополнительно", 'multi'),
    (33, "Какую стадию проектирования нужно выполнить?\n\n▪️ Эскизный проект (принципиальные схемы, расстановка оборудования)\n▪️ Проектная документация (стадия «П»)\n▪️ Рабочая документация (стадия «РД»)\n▪️ Полный пакет: расчёты + П + РД + смета", 'single'),
    (34, "Ориентировочный бюджет на оборудование и монтаж (только противопожарные системы):\n\n▪️ до 500 000 ₽\n▪️ 500 000 – 2 000 000 ₽\n▪️ 2 000 000 – 5 000 000 ₽\n▪️ свыше 5 000 000 ₽\n▪️ Бюджет открытый, нужна смета", 'single'),
    (35, "Сроки:\n\n▪️ Начало проектирования:\n▪️ Начало монтажа:", 'free'),
    (36, "Контактная информация:\n\n▪️ Город:\n▪️ Имя:\n▪️ Телефон:\n▪️ Телеграмм:\n▪️ Email:", 'free'),
    (37, "Какие материалы и документы вы можете предоставить? (можно выбрать несколько)\n\n▪️ Архитектурные планы (формат PDF/DWG)\n▪️ Технологическое задание / экспликация помещений\n▪️ Специальные технические условия (СТУ)\n▪️ Отчёт о категорировании по взрывопожарной опасности\n▪️ Технические условия на электроснабжение\n▪️ Существующие проекты смежных систем (вентиляция, водопровод)\n▪️ Ничего нет, нужен выезд и предпроектное обследование", 'multi'),
]

def make_single_keyboard(options_text):
    lines = options_text.strip().split('\n')
    options = []
    for line in lines:
        line = line.strip()
        if line and (line.startswith('▪️') or line.startswith('-') or (line and line[0].isdigit())):
            clean = line.lstrip('▪️- ').strip()
            if clean:
                options.append(clean)
    if not options:
        options = [l.strip() for l in lines if l.strip()]
    keyboard = [options[i:i+2] for i in range(0, len(options), 2)]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def extract_options(question_text):
    lines = question_text.split('\n')
    opts = []
    for line in lines:
        line = line.strip()
        if line.startswith('▪️'):
            opts.append(line[2:].strip())
    return opts

async def send_email_report(user_data):
    text = "📋 Анкета по противопожарным системам\n\n"
    for step, answer in user_data.items():
        if step == 0:
            continue
        q_text = "Вопрос"
        for q in QUESTIONS_BASE + QUESTIONS_WATER + QUESTIONS_GAS + COMMON_QUESTIONS:
            if q[0] == step:
                q_text = q[1].split('\n')[0][:80]
                break
        text += f"{q_text}: {answer}\n\n"
    msg = EmailMessage()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = "Новая анкета противопожарной безопасности"
    msg.set_content(text)
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info("Письмо отправлено")
    except Exception as e:
        logging.error(f"Ошибка почты: {e}")

async def send_telegram_copy(update, context, user_data):
    report_lines = ["✅ Ваши ответы на анкету:"]
    for step, answer in user_data.items():
        if step == 0:
            continue
        q_text = "Вопрос"
        for q in QUESTIONS_BASE + QUESTIONS_WATER + QUESTIONS_GAS + COMMON_QUESTIONS:
            if q[0] == step:
                q_text = q[1].split('\n')[0][:60]
                break
        report_lines.append(f"{q_text}: {answer}")
    report = "\n\n".join(report_lines)
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=report)
    if YOUR_TELEGRAM_ID:
        await context.bot.send_message(
            chat_id=YOUR_TELEGRAM_ID,
            text=f"📬 Новая анкета от @{update.effective_user.username or 'Пользователь'}\n\n{report}"
        )

async def show_multi_question(update, context, step, q_text, options):
    if 'multi_selected' not in context.user_data:
        context.user_data['multi_selected'] = {}
    if step not in context.user_data['multi_selected']:
        context.user_data['multi_selected'][step] = [False] * len(options)
    selected = context.user_data['multi_selected'][step]
    keyboard = []
    for i, opt in enumerate(options):
        status = "✅" if selected[i] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{status} {opt}", callback_data=f"multi_{step}_{i}")])
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data=f"multi_done_{step}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=q_text, reply_markup=reply_markup)

async def start(update, context):
    await update.message.reply_text("Привет! Я задам вопросы для проектирования противопожарных систем. Для отмены /cancel.")
    context.user_data.clear()
    context.user_data['current_step'] = 1
    context.user_data['branch'] = None
    await ask_current_question(update, context)

async def ask_current_question(update, context):
    step = context.user_data.get('current_step')
    if not step:
        await finish_survey(update, context)
        return
    if step <= 17:
        for q in QUESTIONS_BASE:
            if q[0] == step:
                num, text, q_type = q
                break
        else:
            await finish_survey(update, context)
            return
    elif step >= 18 and step <= 23:
        branch = context.user_data.get('branch')
        if branch == 'water':
            for q in QUESTIONS_WATER:
                if q[0] == step:
                    num, text, q_type = q
                    break
            else:
                await finish_survey(update, context)
                return
        elif branch == 'gas':
            for q in QUESTIONS_GAS:
                if q[0] == step:
                    num, text, q_type = q
                    break
            else:
                await finish_survey(update, context)
                return
        else:
            await finish_survey(update, context)
            return
    else:
        for q in COMMON_QUESTIONS:
            if q[0] == step:
                num, text, q_type = q
                break
        else:
            await finish_survey(update, context)
            return
    context.user_data['current_question_num'] = num
    context.user_data['current_question_text'] = text
    context.user_data['current_question_type'] = q_type
    if q_type == 'single':
        parts = text.split('\n\n', 1)
        options_part = parts[1] if len(parts) > 1 else text
        reply_markup = make_single_keyboard(options_part)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
    elif q_type == 'multi':
        options = extract_options(text)
        context.user_data['multi_options'] = options
        await context.bot.send_message(chat_id=update.effective_chat.id, text="(Выберите несколько вариантов, затем нажмите 'Готово')")
        await show_multi_question(update, context, step, text, options)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text + "\n(Введите ваш ответ текстом)", reply_markup=ReplyKeyboardRemove())

async def handle_message(update, context):
    step = context.user_data.get('current_step')
    if not step:
        await update.message.reply_text("Начните с /start")
        return
    q_type = context.user_data.get('current_question_type')
    if q_type == 'multi':
        await update.message.reply_text("Пожалуйста, используйте кнопки для выбора вариантов и нажмите 'Готово'.")
        return
    context.user_data[step] = update.message.text
    if step == 17:
        answer = update.message.text.lower()
        if 'водяное' in answer or 'спринклерное' in answer or 'дренчерное' in answer or 'тонкораспыл' in answer or 'пеной' in answer:
            context.user_data['branch'] = 'water'
            next_step = 18
        elif 'газовое' in answer or 'порошковое' in answer or 'аэрозольное' in answer:
            context.user_data['branch'] = 'gas'
            next_step = 18
        else:
            next_step = 24
    elif step >= 18:
        branch = context.user_data.get('branch')
        if branch == 'water':
            if step < 23:
                next_step = step + 1
            else:
                next_step = 24
        elif branch == 'gas':
            if step < 21:
                next_step = step + 1
            else:
                next_step = 24
        else:
            next_step = step + 1
    else:
        next_step = step + 1
    if next_step <= 37:
        context.user_data['current_step'] = next_step
        await ask_current_question(update, context)
    else:
        await finish_survey(update, context)

async def handle_multi_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    step = context.user_data.get('current_step')
    if not step:
        return
    q_text = context.user_data.get('current_question_text')
    options = context.user_data.get('multi_options', [])
    if data.startswith("multi_done_"):
        selected = context.user_data.get('multi_selected', {}).get(step, [])
        answer = ", ".join([opt for i, opt in enumerate(options) if i < len(selected) and selected[i]]) if any(selected) else "Ничего не выбрано"
        context.user_data[step] = answer
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Ответ сохранён!")
        context.user_data.pop('multi_selected', None)
        context.user_data.pop('multi_options', None)
        if step == 17:
            if any('водяное' in opt.lower() or 'спринклерное' in opt.lower() or 'дренчерное' in opt.lower() or 'пеной' in opt.lower() for opt in answer):
                context.user_data['branch'] = 'water'
                next_step = 18
            elif any('газовое' in opt.lower() or 'порошковое' in opt.lower() for opt in answer):
                context.user_data['branch'] = 'gas'
                next_step = 18
            else:
                next_step = 24
        elif step >= 18:
            branch = context.user_data.get('branch')
            if branch == 'water':
                if step < 23:
                    next_step = step + 1
                else:
                    next_step = 24
            elif branch == 'gas':
                if step < 21:
                    next_step = step + 1
                else:
                    next_step = 24
            else:
                next_step = step + 1
        else:
            next_step = step + 1
        if next_step <= 37:
            context.user_data['current_step'] = next_step
            await ask_current_question(update, context)
        else:
            await finish_survey(update, context)
        return
    elif data.startswith("multi_"):
        idx_option = int(data.split("_")[2])
        if 'multi_selected' not in context.user_data:
            context.user_data['multi_selected'] = {}
        if step not in context.user_data['multi_selected']:
            context.user_data['multi_selected'][step] = [False] * len(options)
        context.user_data['multi_selected'][step][idx_option] = not context.user_data['multi_selected'][step][idx_option]
        selected = context.user_data['multi_selected'][step]
        keyboard = []
        for i, opt in enumerate(options):
            status = "✅" if selected[i] else "⬜"
            keyboard.append([InlineKeyboardButton(f"{status} {opt}", callback_data=f"multi_{step}_{i}")])
        keyboard.append([InlineKeyboardButton("✅ Готово", callback_data=f"multi_done_{step}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        return

async def finish_survey(update, context):
    user_data = {k: v for k, v in context.user_data.items() if isinstance(k, int)}
    await send_email_report(user_data)
    await send_telegram_copy(update, context, user_data)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🎉 Спасибо! Анкета успешно отправлена.\nМы свяжемся с вами.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()

async def cancel(update, context):
    await update.message.reply_text("❌ Опрос отменён.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('cancel', cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_multi_callback))
    print("✅Бот для противопожарных систем запускается...")
    application.run_polling(poll_interval=1.0, timeout=30)

if __name__ == "__main__":
    main()
