import os
import sqlite3
import json
import logging

import streamlit as st
from streamlit_lottie import st_lottie

from logic import get_user_id, authorization


st.set_page_config(
    page_title="Logic",
    layout="centered",
    page_icon="Logic.ico"
)


DATA_DIR = '/disk/data'
os.makedirs(DATA_DIR, exist_ok=True)

TEST_BUILD = True

# disable HTTP request logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)


def create_database():
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_token TEXT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                register_date TIMESTAMP NOT NULL,
                openai_api_key TEXT,
                deepseek_api_key TEXT,
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_name TEXT NOT NULL,
                chat_create_date TIMESTAMP NOT NULL,
                chat_description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_name TEXT NOT NULL,
                bot_create_date TIMESTAMP NOT NULL,
                bot_description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                chat_message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                chat_message_date TIMESTAMP NOT NULL,
                chat_role TEXT NOT NULL,
                chat_message TEXT,
                reasoning_output TEXT,
                model TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_messages (
                bot_message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER,
                bot_message_date TIMESTAMP NOT NULL,
                bot_role TEXT NOT NULL,
                bot_message TEXT,
                reasoning_output TEXT,
                model TEXT,
                FOREIGN KEY (bot_id) REFERENCES bots(bot_id)
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error while creating database: {e}")
    finally:
        cur.close()
        conn.close()


def is_logged_in():
    cookie_id = cookies.get("ajs_anonymous_id", None)

    if cookie_id is None:
        print("Cookie not found")
        return cookie_id, False

    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM users WHERE user_token = ? LIMIT 1", (cookie_id,))
        result = cur.fetchone()
        return cookie_id, result is not None
    except sqlite3.Error as e:
        print(f"Error while checking login status: {e}")
        return cookie_id, False
    finally:
        cur.close()
        conn.close()


@st.cache_data
def animation():
    with open('assets/logic_animation.json', 'r') as f:
        lottie_json = json.load(f)
    st.container(height=200, border=False)
    col1, col2, col3 = st.columns([1, 10, 1], vertical_alignment='center')
    with col2:
        st_lottie(lottie_json, loop=True)


def start_page():
    if st.session_state.success_register:
        st.toast('Вы успешно зарегистрировались! Для авторизации нажмите кнопку "Войти"', icon="✅")
        st.session_state.success_register = False
    if st.session_state.success_logout:
        st.toast('Вы вышли из аккаунта!', icon=":material/logout:")
        st.session_state.success_logout = False
    if st.session_state.success_account_deleting:
        st.toast('Ваш аккаунт Logic удален. Спасибо,что были с нами!', icon="😌")
        st.session_state.success_account_deleting = False

    animation()

    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            [data-testid="stSidebarCollapsedControl"] {
                display: none;
            }
        </style>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 2])
    if col2.button("Войти", use_container_width=True):
        authorization()


if not os.path.exists(os.path.join(DATA_DIR, 'logic.db')):
    create_database()

cookies = st.context.cookies
cookie, is_logged_in = is_logged_in()

if is_logged_in:
    if 'user_id' not in st.session_state:
        st.session_state.user_id = get_user_id(cookie)
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = None
    st.logo('assets/logo_icon.png')

    if TEST_BUILD:
        st.sidebar.title('TEST BUILD')

    pg = st.navigation(
        [
            st.Page("logic/account.py", title="Аккаунт", icon=":material/account_circle:", default=True),
            st.Page("logic/chats.py", title="Мои чаты", icon=":material/forum:"),
            st.Page("logic/bots.py", title="Мои боты", icon=":material/smart_toy:"),
        ]
    )
    pg.run()
else:
    if 'success_register' not in st.session_state:
        st.session_state.success_register = False
    if 'success_logout' not in st.session_state:
        st.session_state.success_logout = False
    if 'success_account_deleting' not in st.session_state:
        st.session_state.success_account_deleting = False

    start_page()
