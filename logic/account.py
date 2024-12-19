import datetime
import os
import time

import streamlit as st
import sqlite3
from openai import OpenAI

from logic import get_account_info


DATA_DIR = '/disk/data'
os.makedirs(DATA_DIR, exist_ok=True)


@st.dialog("Изменить API-ключ")
def change_api_key():
    new_api_key = st.text_input("Введите новый API-ключ", type="password")
    checkbox = st.checkbox("Подтвердите, что вы ввели правильный ключ")

    button_visible = new_api_key != '' and new_api_key is not None and checkbox

    if st.button("Сохранить", disabled=not button_visible):

        conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
        cur = conn.cursor()
        try:
            cur.execute("UPDATE users SET openai_api_key = ? WHERE user_id = ?", (new_api_key, st.session_state.user_id))
            conn.commit()
            st.session_state.openai_client = OpenAI(api_key=new_api_key)
        except sqlite3.Error as e:
            print(f"Error while updating API key: {e}")
        finally:
            cur.close()
            conn.close()
            st.rerun()


def get_statistics():
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        user_id = st.session_state.user_id
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM chats WHERE user_id = ?) AS chat_count,
                (SELECT COUNT(*) FROM bots WHERE user_id = ?) AS bot_count,
                (SELECT COUNT(*) FROM chat_messages WHERE chat_id IN (SELECT chat_id FROM chats WHERE user_id = ?)) +
                (SELECT COUNT(*) FROM bot_messages WHERE bot_id IN (SELECT bot_id FROM bots WHERE user_id = ?)) AS total_messages;
        """, (user_id, user_id, user_id, user_id))
        result = cur.fetchone()
        return result
    except sqlite3.Error as e:
        print(f"Error while getting statistics: {e}")
    finally:
        cur.close()
        conn.close()
    pass


# @st.dialog("Изменить аватар")
def change_avatar():
    st.toast('Функция изменения аватара находится в разработке и будет представлена в следующих версиях!', icon="🛠️")
    pass


def change_password():
    st.toast('Функция изменения пароля находится в разработке и будет представлена в следующих версиях! Если Вы '
             'забыли пароль - выйдите из аккаунта и нажмите "Забыли пароль" в окне авторизации.', icon="🛠️")
    pass


@st.dialog("Удаление аккаунта")
def delete_account():
    st.text("""
        Вы собираетесь удалить свой аккаунт - это действие нельзя отменить. Для подтверждения, заполните чекбоксы снизу:
    """)
    st.checkbox(
        "Я хочу удалить свой аккаунт Logic, включая все личные данные, чаты и боты", key="delete_account_checkbox_1"
    )
    st.checkbox("Я осознаю, что удаленный аккаунт невозможно будет восстановить", key="delete_account_checkbox_2")

    button_visible = st.session_state.delete_account_checkbox_1 and st.session_state.delete_account_checkbox_2

    if st.button("Удалить аккаунт", type="primary", disabled=not button_visible):
        # remove_user_cookies()
        with st.spinner("Удаляем Ваш аккаунт..."):
            time.sleep(1)
            conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM chat_messages WHERE chat_id IN (SELECT chat_id FROM chats WHERE user_id = ?)", (st.session_state.user_id,))
                cur.execute("DELETE FROM bot_messages WHERE bot_id IN (SELECT bot_id FROM bots WHERE user_id = ?)", (st.session_state.user_id,))
                cur.execute("DELETE FROM chats WHERE user_id = ?", (st.session_state.user_id,))
                cur.execute("DELETE FROM bots WHERE user_id = ?", (st.session_state.user_id,))
                cur.execute("DELETE FROM users WHERE user_id = ?", (st.session_state.user_id,))
                conn.commit()

                st.session_state.user_id = None
                st.session_state.success_account_deleting = True
                st.rerun()
            except sqlite3.Error as e:
                print(f"Error while deleting user: {e}")
            finally:
                cur.close()
                conn.close()


col1, col2 = st.columns([1, 2], vertical_alignment='center')
avatar = col1.image('assets/user_avatar.png', width=250)
col2.button('', icon=":material/inbox_customize:", on_click=change_avatar)

title = st.empty()
st.divider()

user_info = get_account_info(st.context.cookies.get('ajs_anonymous_id', None))

if user_info:

    user_id, user_token, username, email, password, register_date_str, api_key = user_info
    register_date = datetime.datetime.strptime(register_date_str, '%Y-%m-%d %H:%M:%S.%f')

    title.title(f":gray[Аккаунт:] {username}")

    chat_count, bot_count, total_messages = get_statistics()

    col1, col2, col3, col4 = st.columns([5, 2, 2, 2])

    col1.metric("Дата регистрации", register_date.strftime('%d.%m.%Y'))
    col2.metric("Чатов", chat_count)
    col3.metric("Ботов", bot_count)
    col4.metric("Сообщений", total_messages)

    st.caption('Email:')
    with st.container():
        st.text_input(label='Email', value=email, disabled=True, label_visibility='collapsed')

    st.caption('Пароль:')
    with st.container():
        col1, col2 = st.columns([8, 1])
        col1.text_input(label='API_KEY', value=password, type="password", disabled=True, label_visibility='collapsed')
        col2.button("", icon=':material/edit:', key='change_password', on_click=change_password)

    st.caption('OpenAI API key:')
    with st.container():
        col1, col2 = st.columns([8, 1])
        col1.text_input(label='API_KEY', value=api_key, disabled=True, label_visibility='collapsed')
        col2.button("", icon=':material/edit:', key='change_api_key', on_click=change_api_key)

    st.write("")

    if st.button("Выйти из аккаунта", icon=":material/logout:", key='logout'):
        # remove_user_cookies()
        with st.spinner("Выход..."):
            conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
            cur = conn.cursor()
            try:
                cur.execute("UPDATE users SET user_token = NULL WHERE user_id = ?", (st.session_state.user_id,))
                conn.commit()
                st.session_state.user_id = None
                st.session_state.success_logout = True
            except sqlite3.Error as e:
                print(f"Error while logout: {e}")
            finally:
                cur.close()
                conn.close()
                st.rerun()

    if st.button("Удалить аккаунт", type='primary', icon=":material/delete:", key='acc_delete'):
        delete_account()
