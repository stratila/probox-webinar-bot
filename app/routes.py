from flask import render_template, flash, redirect, url_for, request, send_from_directory
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app import app, db, telegram_bot, excel
from app.forms import LoginForm, RegistrationForm, SendForm
from app.models import User, TelegramUser
from app.bot_state import BotSate, Course
from app.bot_messages import start_message, request_phone_number_text, phone_decline_button_text, phone_button_text,\
    registration_start_message, course_choice_message, smart_house_message, python_message, javascript_message, \
    smart_house_link, javascript_link, python_link
from sqlalchemy import func
from telebot import types
import threading
import time
import json


@app.route('/' + app.config['BOT_TOKEN'], methods=['POST'])
def getMessage():
    telegram_bot.process_new_updates([types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@app.route("/set_webhook")
def webhook():
    telegram_bot.remove_webhook()
    telegram_bot.set_webhook(url='https://probox-webinar-bot.herokuapp.com/' + app.config['BOT_TOKEN'])
    return "!", 200

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = SendForm()
    users_count = db.session.query(func.count(TelegramUser.id)).scalar()
    # рассылка сообщений пользователям, которые вошли в Telegram-бот
    if form.validate_on_submit():

        telegram_users = TelegramUser.query.all()

        # запускаем рассылку в свободном потоке, чтобы получить ответ от сервера быстро
        t = threading.Thread(target=send_message_to_all_telegram_users,
                             args=(telegram_users, form.message.data,),
                             daemon=True)
        t.start()

        flash('Сообщение отправлено')
        return render_template('index.html', title='Home Page', form=form, users_count=users_count)
    return render_template('index.html', title='Home Page', form=form, users_count=users_count)


# скачивание excel файла (все поля, кроме state)
@app.route("/webinar-data", methods=["GET"])
@login_required
def get_tg_users_excel():
    query_sets = TelegramUser.query.all()
    column_names = ['id', 'first_name', 'last_name', 'username', 'language_code', 'phone_number', 'course']
    return excel.make_response_from_query_sets(
        query_sets, column_names, "xlsx", dest_sheet_name="webinar-participants"
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('{} just have been registered!'.format(user.username))
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('register.html', title='Register', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


def send_message_to_all_telegram_users(users, message):
    # start = time.time()
    # при рассылке использовать try-except, так как пользватель может заблокировать бота
    for user in users:
        try:
            telegram_bot.send_message(user.id, message)
        except Exception as e:
            pass
    # end = time.time()






def request_start(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Старт', callback_data=json.dumps({'strt': True})))
    telegram_bot.send_message(chat_id=chat_id,
                              text=start_message,
                              reply_markup=markup,
                              parse_mode='Markdown')


def request_phone_number(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)
    markup.add(types.KeyboardButton(text=phone_button_text, request_contact=True))
    markup.add(types.KeyboardButton(text=phone_decline_button_text))
    telegram_bot.send_message(text=request_phone_number_text, chat_id=chat_id,
                              reply_markup=markup, parse_mode='Markdown')


def request_registration_start(chat_id):
    telegram_bot.send_message(text=registration_start_message, chat_id=chat_id,
                              parse_mode='Markdown')


def send_or_update_course_option(chat_id, message_id=None, update=False):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Умный дом на Arduino С++',
                                          callback_data=json.dumps({'crs': Course.SMART_HOUSE})))
    markup.add(types.InlineKeyboardButton(text='Python Джедай', callback_data=json.dumps({'crs': Course.PYTHON})))
    markup.add(types.InlineKeyboardButton(text='JavaScript', callback_data=json.dumps({'crs': Course.JAVASCRIPT})))
    if update:
        telegram_bot.edit_message_text(chat_id=chat_id, text=course_choice_message,
                                       reply_markup=markup, parse_mode='Markdown', message_id=message_id)
    else:
        telegram_bot.send_message(chat_id=chat_id, text=course_choice_message,
                                  reply_markup=markup, parse_mode='Markdown')


def request_course_option(chat_id, wait=False):
    if wait:
        time.sleep(7) #ждать 7 секунд

    user = TelegramUser.query.get(chat_id)
    user.state = BotSate.COURSE_CHOICE
    db.session.commit()

    send_or_update_course_option(chat_id)


def request_course(course, chat_id, message_id=None, update=False,):
    if not (course in [Course.SMART_HOUSE, Course.PYTHON, Course.JAVASCRIPT]):
        raise Exception('Invalid Course was given.')

    markup = types.InlineKeyboardMarkup()

    markup.add(types.InlineKeyboardButton(text='Хочешь записаться на пробный урок?',
                                          callback_data=json.dumps({'prb': course})))
    markup.add(types.InlineKeyboardButton(text='Скачать топ языков программирования',
                                          callback_data=json.dumps({'dwnl': True})))
    markup.add(types.InlineKeyboardButton(text='🔙',
                                          callback_data=json.dumps({'prb': 'back'})))


    if course == Course.SMART_HOUSE:
        message_text = smart_house_message
    elif course == Course.PYTHON:
        message_text = python_message
    elif course == Course.JAVASCRIPT:
        message_text = javascript_message

    if update:
        telegram_bot.edit_message_text(text=message_text, chat_id=chat_id, reply_markup=markup,
                                       message_id=message_id, disable_web_page_preview=True, parse_mode='Markdown')
    else:
        telegram_bot.send_message(text=message_text, chat_id=chat_id, disable_web_page_preview=True,
                                  parse_mode='Markdown', reply_markup=markup)


@telegram_bot.message_handler(commands=['start'])
def auth_telegram_user(message):
    if TelegramUser.query.filter_by(id=message.from_user.id).first():
        check_state(message)
    else:
        user = TelegramUser(id=message.from_user.id,
                            first_name=message.from_user.first_name,
                            last_name=message.from_user.last_name,
                            username=message.from_user.username,
                            language_code=message.from_user.language_code,
                            state=BotSate.START)

        db.session.add(user)
        db.session.commit()
        request_start(user.id)


@telegram_bot.message_handler(content_types=['text', 'contact'])
def check_state(message):
    user = TelegramUser.query.get(message.chat.id)
    if user.state == BotSate.START:
        request_start(user.id)
    elif user.state == BotSate.PHONE:
        if message.contact is not None:
            user.phone_number = message.contact.phone_number
            user.state = BotSate.REGISTRATION_START
            db.session.commit()
            request_registration_start(user.id)
            t = threading.Thread(target=request_course_option,
                                 args=(user.id, True,),
                                 daemon=True)
            t.start()
        elif message.text == phone_decline_button_text:
            user.state = BotSate.REGISTRATION_START
            db.session.commit()
            request_registration_start(user.id)
            t = threading.Thread(target=request_course_option,
                                 args=(user.id, True,),
                                 daemon=True)
            t.start()
        else:
            request_phone_number(user.id)
    elif user.state == BotSate.COURSE_CHOICE:
        request_course_option(user.id)
    elif user.state == BotSate.SMART_HOUSE_CHOICE:
        request_course(Course.SMART_HOUSE, user.id)
    elif user.state == BotSate.PYTHON_CHOICE:
        request_course(Course.PYTHON, user.id)
    elif user.state == BotSate.JAVASCRIPT_CHOICE:
        request_course(Course.JAVASCRIPT, user.id)


@telegram_bot.callback_query_handler(func=lambda query: json.loads(query.data).get('strt') == True)
def begin_registration(query):
    user = TelegramUser.query.get(query.message.chat.id)
    if user.state == BotSate.START:
        user.state = BotSate.PHONE
        db.session.commit()
        check_state(query.message)


@telegram_bot.callback_query_handler(func=lambda query: json.loads(query.data).get('crs') is not None)
def course_choice(query):
    user = TelegramUser.query.get(query.message.chat.id)
    course = json.loads(query.data).get('crs')
    if course == Course.SMART_HOUSE:
        user.course = Course.SMART_HOUSE.name
        user.state = BotSate.SMART_HOUSE_CHOICE
        db.session.commit()
        request_course(course, user.id, query.message.message_id, update=True)
    elif course == Course.PYTHON:
        user.course = Course.PYTHON.name
        user.state = BotSate.PYTHON_CHOICE
        db.session.commit()
        request_course(course, user.id, query.message.message_id, update=True)
    elif course == Course.JAVASCRIPT:
        user.course = Course.JAVASCRIPT.name
        user.state = BotSate.JAVASCRIPT_CHOICE
        db.session.commit()
        request_course(course, user.id, query.message.message_id, update=True)


@telegram_bot.callback_query_handler(func=lambda query: json.loads(query.data).get('prb') is not None)
def course_link(query):
    user = TelegramUser.query.get(query.message.chat.id)
    course = json.loads(query.data).get('prb')

    # вернуться к выбору языков
    if course == 'back':
        user.state = BotSate.COURSE_CHOICE
        db.session.commit()
        send_or_update_course_option(user.id, query.message.message_id, update=True)
        return
    # ccылки на курсы
    if course == Course.SMART_HOUSE:
        telegram_bot.send_message(user.id, text=smart_house_link, disable_web_page_preview=True,
                                  parse_mode='Markdown')
    elif course == Course.PYTHON:
        telegram_bot.send_message(user.id, text=python_link, disable_web_page_preview=True,
                                  parse_mode='Markdown')
    elif course == Course.JAVASCRIPT:
        telegram_bot.send_message(user.id, text=javascript_link, disable_web_page_preview=True,
                                  parse_mode='Markdown')


@telegram_bot.callback_query_handler(func=lambda query: json.loads(query.data).get('dwnl') is not None)
def send_useful_file(query):
    user = TelegramUser.query.get(query.message.chat.id)
    doc = open('app/static/top_programming_languages.pdf', 'rb')
    telegram_bot.send_document(user.id, doc)

