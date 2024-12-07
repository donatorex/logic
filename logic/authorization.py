import re
import secrets
import sqlite3
import smtplib
import os
import time
from datetime import datetime
from email.mime.text import MIMEText

import streamlit as st

from logic import get_cookie, set_cookie


SMTP_SERVER = os.environ.get('SMTP_SERVER')
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

DATA_DIR = 'disk/data'
os.makedirs(DATA_DIR, exist_ok=True)


def username_is_valid(username):
    return re.match(r'^[a-zA-Z0-9_]{3,20}$', username) or username == ""


def username_is_unique(username):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        return user is None
    except sqlite3.Error as e:
        print(f"Error while checking username uniqueness: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def username_input():
    st.text_input('Логин', key='username_input')
    if st.session_state.username_input:
        if not username_is_valid(st.session_state.username_input):
            st.error(f"""
                    Некорректное имя пользователя.

                    Придерживайтесь следующих правил:
                    - Длина логина от 3 до 20 символов;
                    - Логин должен состоять из латинских букв, цифр (также допускается знак подчеркивания '_');
                    - Пробел не допускается.
                """)
            st.stop()
        if not username_is_unique(st.session_state.username_input):
            st.error('Пользователь с таким именем уже существует')
            st.stop()

        st.session_state.registration_username = st.session_state.username_input
        del st.session_state.username_input
        return True


def email_is_valid(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) or email == ""


def email_is_unique(email):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        return user is None
    except sqlite3.Error as e:
        print(f"Error while checking email uniqueness: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def email_input(tab):
    # if st.session_state.registration_username :
    st.text_input('Email', key='email_input')
    if st.session_state.email_input:
        if not email_is_valid(st.session_state.email_input):
            st.error('Некорректный email. Введите email в формате example@example.com')
            st.stop()
        email_uniqueness = email_is_unique(st.session_state.email_input)
        if tab == 'registration' and not email_uniqueness:
            st.error('Пользователь с таким email уже существует')
            st.stop()
        if tab == 'forgot_password' and email_uniqueness:
            st.error('Пользователь с таким email не зарегистрирован')
            st.stop()

        st.session_state[f"{tab}_email"] = st.session_state.email_input
        del st.session_state.email_input
        return True


def get_username_from_email(email):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT username FROM users WHERE email = ?", (email,))
        username = cur.fetchone()
        if username:
            return username[0]
        else:
            st.error("Пользователь с таким email не зарегистрирован")
            st.stop()
    except sqlite3.Error as e:
        print(f"Error while checking email: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def password_is_valid(password):
    return not len(password) in range(1, 6)


def password_input(tab):
    with st.container(border=True):
        if tab == 'forgot_password':
            st.write('Введите новый пароль:')
        st.text_input('Пароль', type='password', key=f'{tab}_password_1')
        if not password_is_valid(st.session_state[f'{tab}_password_1']):
            st.error('Пароль должен содержать не менее 6 символов')
            st.stop()
        if st.session_state[f'{tab}_password_1'] != '':
            st.text_input('Повторите пароль', type='password', key=f'{tab}_password_2')
            if st.session_state[f'{tab}_password_2'] != '' and st.session_state[f'{tab}_password_1'] != \
                    st.session_state[f'{tab}_password_2']:
                st.error('Пароли не совпадают')
                st.stop()
        dis = st.session_state[f'{tab}_password_1'] == '' or st.session_state[f'{tab}_password_1'] != \
            st.session_state[f'{tab}_password_2']
        if st.button('Зарегистрироваться' if tab == 'registration' else 'Сохранить пароль', disabled=dis):
            if tab == 'registration':
                add_new_user(
                    st.session_state.registration_username,
                    st.session_state.registration_email,
                    st.session_state.registration_password_1
                )
            else:
                reset_password(st.session_state.forgot_password_email, st.session_state.forgot_password_password_1)


def reset_password(email, password):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET password = ? WHERE email = ?", (password, email))
        conn.commit()

        del st.session_state['reset_password']
        del st.session_state[f'forgot_password_username']
        del st.session_state[f'forgot_password_email']
        del st.session_state[f'forgot_password_verified']
        st.success('Пароль успешно изменен!')
        time.sleep(1)
        st.rerun(scope='fragment')
    except sqlite3.Error as e:
        print(f"Error while resetting password: {e}")
    finally:
        cur.close()
        conn.close()


def login(login_input, password):
    if '@' in login_input:
        if not email_is_valid(login_input):
            st.error('Некорректный email. Введите email в формате example@example.com')
            st.stop()
        username = get_username_from_email(login_input)
    else:
        username = login_input

    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cur.fetchone()
        if user:
            # set_cookie("logic_user_token", secrets.token_urlsafe(16))
            cur.execute("UPDATE users SET user_token = ? WHERE username = ?", (
                st.context.cookies.get('ajs_anonymous_id', None),
                username
            )
                        )
            conn.commit()
            st.rerun()
        else:
            st.error("Неправильное имя пользователя или пароль")
    except sqlite3.Error as e:
        print(f"Error while logging in: {e}")
    finally:
        cur.close()
        conn.close()


@st.fragment
def login_tab():
    if 'reset_password' not in st.session_state:
        st.session_state['reset_password'] = False

    if not st.session_state.reset_password:
        st.markdown("""
            <style>
            .element-container:has(#reset-password) + div button {
                background-color: transparent; /* Убираем фон */
                border: none; /* Убираем рамку */
                color: gray; /* Устанавливаем серый цвет иконки */
                font-size: 12px; /* Размер иконки */
                padding: 0; /* Убираем отступы */
                min-height: 0;
                line-height: 0.5;
                transition: none; /* Убираем эффект перехода */

            }
            .element-container:has(#reset-password) + div button:hover {
                color: #FF4B4B; /* Цвет иконки при наведении */
            }
            .element-container:has(#reset-password) + div button:active {
                transform: scale(0.97); /* Эффект нажатия */
            }
            </style>
            """, unsafe_allow_html=True)

        st.text_input('Логин / email', key='login')
        st.text_input('Пароль', type='password', key='password')

        col1, col2, col3 = st.columns([3, 1, 2], vertical_alignment='center')

        dis = st.session_state.login == '' or st.session_state.password == ''
        if col1.button('Войти', disabled=dis):
            login(st.session_state.login, st.session_state.password)

        col3.markdown('<span id="reset-password"></span>', unsafe_allow_html=True)
        if col3.button('Забыли пароль?'):
            st.session_state.reset_password = True
            st.session_state.forgot_password_verified = False
            st.session_state.forgot_password_email = None
            st.rerun(scope='fragment')
    else:
        st.subheader("Сброс пароля:")

        if not st.session_state.forgot_password_email:
            if email_input(tab='forgot_password'):
                st.rerun(scope='fragment')
        else:
            st.write(f"Email: {st.session_state.forgot_password_email} ✅")
            st.session_state.forgot_password_username = get_username_from_email(
                st.session_state.forgot_password_email
            )

            if not st.session_state.forgot_password_verified:
                code_sent(
                    st.session_state.forgot_password_email,
                    st.session_state.forgot_password_username,
                    code_type="forgot_password"
                )
            else:
                password_input(tab='forgot_password')


@st.fragment
def singup_tab():
    if not st.session_state.registration_username:
        if username_input():
            st.rerun(scope='fragment')
    else:
        st.write(f"Логин: {st.session_state.registration_username} ✅")

        if not st.session_state.registration_email:
            if email_input(tab='registration'):
                st.rerun(scope='fragment')
        else:
            st.write(f"Email: {st.session_state.registration_email} ✅")

            if not st.session_state.registration_verified:
                code_sent(
                    st.session_state.registration_email,
                    st.session_state.registration_username,
                    code_type="registration")
            else:
                password_input(tab='registration')


def add_new_user(username, email, password):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO users (username, email, password, register_date) VALUES (?, ?, ?, ?)
        """, (username, email, password, datetime.now())
        )
        conn.commit()

        del st.session_state[f'registration_username']
        del st.session_state[f'registration_email']
        del st.session_state[f'registration_verified']
        st.session_state.success_register = True
        st.rerun()
    except sqlite3.Error as e:
        print(f"Error while signing up: {e}")
    finally:
        cur.close()
        conn.close()


def load_template(template_type, username, verification_code):
    with open(f"assets/{template_type}_email_template.html", "r", encoding="utf-8") as file:
        template = file.read()
    return template.replace('{USERNAME}', username).replace('{CODE}', verification_code)


def email_confirmation(email_type, email_receiver, body):
    server = smtplib.SMTP(SMTP_SERVER, 587)
    try:
        msg = MIMEText(body, 'html')
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email_receiver
        msg['Subject'] = "Подтверждение регистрации аккаунта Logic" \
            if email_type == "registration" else "Сброс пароля аккаунта Logic"

        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, email_receiver, msg.as_string())
    except Exception as e:
        print(f"Error while sending email: {e}")
    finally:
        server.quit()


def code_sent(email, username, code_type):
    if f'{code_type}_code' not in st.session_state:
        st.session_state[f'{code_type}_code'] = secrets.token_hex(3)
    if f'{code_type}_code_sent' not in st.session_state:
        st.session_state[f'{code_type}_code_sent'] = False

    with st.container(border=True):
        st.write('**Подтвердите email:**')
        if not st.session_state[f'{code_type}_code_sent']:
            st.text('На Ваш email-адрес будет направлен код подтверждения - введите его ниже.')
            if st.button('Отправить код'):
                with st.spinner('Отправляем код...'):
                    body = load_template(template_type=code_type, username=username,
                                         verification_code=st.session_state[f'{code_type}_code'])
                    email_confirmation(code_type, email, body)
                    st.session_state[f'{code_type}_code_sent'] = True
                    st.rerun(scope='fragment')
        elif st.session_state[f'{code_type}_code_sent'] and not st.session_state[f'{code_type}_verified']:
            col1, col2 = st.columns([1, 1], vertical_alignment='bottom')
            code = col1.text_input('Код подтверждения')
            if col2.button('Подтвердить'):
                if code == st.session_state[f'{code_type}_code']:
                    st.write('✅ Почта подтверждена!')
                    time.sleep(1)
                    st.session_state[f'{code_type}_verified'] = True
                    del st.session_state[f'{code_type}_code']
                    del st.session_state[f'{code_type}_code_sent']
                    st.rerun(scope='fragment')
                else:
                    st.write('❌ Неверный код подтверждения')


@st.dialog("Привет!")
def authorization():
    tab1, tab2 = st.tabs(["Авторизация", "Регистрация"])
    with tab1:
        login_tab()

    with tab2:
        if 'registration_username' not in st.session_state:
            st.session_state['registration_username'] = None
        if 'registration_email' not in st.session_state:
            st.session_state['registration_email'] = None
        if 'registration_verified' not in st.session_state:
            st.session_state['registration_verified'] = False

        singup_tab()
