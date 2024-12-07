import os
from datetime import datetime
import io
import sqlite3

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from openai import OpenAI


DATA_DIR = 'disk/data'
TEMP_DIR = 'disk/temp'
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


def optimize_prompt(page, prompt, is_description=False):
    # System prompt for the optimizer model
    system_prompt = f"""You are a model that optimizes {'system prompt of user bot' if is_description else 'user prompts'} to ensure the most relevant and effective response. 
Your task is to transform the input {'system promt' if is_description else 'prompt'} into a clearly structured format using this structure:

---
{'#### Оптимизированный промпт:' if page == 'chats' else ''}\n
<TASK>\n
*Clearly describe the user's main task or request. This is the core of what the user wants to achieve or learn*\n
\n
<CONTEXT>\n
*Provide any additional context that helps clarify the task. This can include background information or relevant details that inform the task*\n
\n
<REQUIREMENTS>\n
*List specific requirements, constraints, or preferences, if any. These are conditions that must be met for the task to be considered complete*\n
\n
<OUTPUT_FORMAT>\n
*Specify the desired format of the response (e.g., list, text, table, etc.). This helps tailor the response to the user's needs*\n
\n
<AUDIENCE>\n
*Define the target audience for the task or request. Knowing the audience can help customize the response to suit the needs of a specific group*\n
\n
<EXAMPLES>\n
*Indicate examples the user would like to receive in the response, if applicable. This can help clarify expectations*\n
\n
<LANGUAGE>\n
*Specify if the response should be in a particular language different from the request language*\n
\n
<RESOURCES>\n
*Indicate any specific resources or links that should be used in completing the task. This can guide the response to include certain references*\n
\n
<TONE>\n
*Define the desired tone of the response, such as formal, informal, friendly, etc. This helps in setting the right mood or style for the response*\n
\n

---
Make sure you put "\\n" paragraph marks everywhere.
Specify that the response must be in the same language as the request, unless otherwise specified.
Always return the result in this format.
If any section is missing in the user's request, leave it empty but retain the structure.
"""

    with st.spinner("Оптимизирую промпт..."):
        # Sending the request to OpenAI API
        response = st.session_state.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

    # Extracting and returning the optimized prompt
    optimized_prompt = response.choices[0].message.content
    return optimized_prompt


def get_account_info(user_token):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE user_token = ?", (user_token,))
        user = cur.fetchone()
        return user
    except sqlite3.Error as e:
        print(f"Error while getting account info: {e}")
    finally:
        cur.close()
        conn.close()


def get_user_id(user_token):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM users WHERE user_token = ?", (user_token,))
        user_id = cur.fetchone()[0]
        return user_id
    except sqlite3.Error as e:
        print(f"Error while getting account info: {e}")
    finally:
        cur.close()
        conn.close()


def get_api_key(user_id):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute("SELECT openai_api_key FROM users WHERE user_id = ?", (user_id,))
        api_key = cur.fetchone()[0]
        return api_key
    except sqlite3.Error as e:
        print(f"Error while getting API key: {e}")
    finally:
        cur.close()
        conn.close()


def get_chatbot_list(page):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT {page[:-1]}_name, {page[:-1]}_id, {page[:-1]}_create_date, {page[:-1]}_description
            FROM {page}
            WHERE user_id = ?
        """, (st.session_state.user_id,))
        rows = cur.fetchall()
        return {row[0]: row[1:] for row in rows}
    except sqlite3.Error as e:
        print(f"Error while getting {page[:-1]} list: {e}")
    finally:
        cur.close()
        conn.close()


def get_description(page, name):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT {page[:-1]}_description FROM {page} WHERE {page[:-1]}_name = ?", (name,))
        description = cur.fetchone()[0]
        return description
    except sqlite3.Error as e:
        print(f"Error while getting {page[:-1]} description: {e}")
    finally:
        cur.close()
        conn.close()


def get_date(page, name):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT {page[:-1]}_create_date FROM {page} WHERE {page[:-1]}_name = ?", (name,))
        date = cur.fetchone()[0]
        return date
    except sqlite3.Error as e:
        print(f"Error while getting {page[:-1]} creation date: {e}")
    finally:
        cur.close()
        conn.close()


def transcribe_audio(page, audio_b):
    with st.spinner("Расшифровываю аудио..."):
        transcriptions = st.session_state.openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_b,
            response_format="text"
        )
        return optimize_prompt(page, transcriptions, is_description=True)


@st.dialog(f"Настройки")
def new_chat(page):
    set_name = st.text_input(label='Введите имя')
    description_place = st.empty()
    st.caption('или')
    audio_place = st.empty()

    button_disabled = True if page == "chats" else False

    if audio_input := audio_place.audio_input('Надиктуйте описание в свободной форме', disabled=button_disabled):
        button_disabled = True

    set_description = description_place.text_area(
        'Введите описание',
        value=None if page == "bots" else "Ты очень полезный помощник",
        height=300,
        disabled=button_disabled
    )

    optimize = st.checkbox("Оптимизировать описание", help="""
        При включении данного параметра, описание бота будет оптимизировано и структурировано для получения наиболее
        релевантного ответа.
        
        Не доступно в чатах, а также при аудио-описании, т.к. оно оптимизируется автоматически.
    """, disabled=button_disabled)

    if st.button("Submit"):

        if check_chat_name(page, set_name):
            st.error(f'Имя \"{set_name}\" уже используется', icon="🚨")
            return

        if audio_input:
            set_description = transcribe_audio(page, audio_input)
        elif optimize:
            set_description = optimize_prompt(page, set_description, is_description=True)

        conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
        cur = conn.cursor()

        try:
            cur.execute(f"""
                INSERT INTO {page} (user_id, {page[:-1]}_name, {page[:-1]}_create_date, {page[:-1]}_description)
                VALUES (?, ?, ?, ?)
            """, (st.session_state.user_id, set_name, datetime.now(), set_description))
            conn.commit()
            st.toast(f"Чат {set_name} успешно создан!")
            st.rerun()
        except sqlite3.Error as e:
            print(f"Error while creating chat: {e}")
        finally:
            cur.close()
            conn.close()


def check_chat_name(page, chat_name, chat_id=None):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT EXISTS (
                SELECT 1 FROM {page} WHERE {page[:-1]}_name = ? AND user_id = ?{f" AND {page[:-1]}_id != {chat_id}" if chat_id else ""}
            ) AS FOUND;
        """, (chat_name, st.session_state.user_id))
        return cur.fetchone()[0]
    except sqlite3.Error as e:
        print(f"Error while checking chat name: {e}")
    finally:
        cur.close()
        conn.close()


def get_messages(page, canvas_id):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT {page[:-1]}_message_id, {page[:-1]}_message_date, {page[:-1]}_role, {page[:-1]}_message
            FROM {page[:-1]}_messages
            WHERE {page[:-1]}_id = ?
            ORDER BY {page[:-1]}_message_date ASC
        """, (canvas_id,))
        rows = cur.fetchall()
        if rows is not None:
            return rows
        else:
            return []
    except sqlite3.Error as e:
        print(f"Error while getting messages: {e}")
    finally:
        cur.close()
        conn.close()


def formatted_date(date):
    if type(date) == str:
        return datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f').strftime('%d %b %Y - %H:%M')
    else:
        return date.strftime('%d %b %Y - %H:%M')


def add_message(page, canvas_id, message):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute(f"""
            INSERT INTO {page[:-1]}_messages (
                {page[:-1]}_id,
                {page[:-1]}_message_date,
                {page[:-1]}_role,
                {page[:-1]}_message
            )
            VALUES (?, ?, ?, ?)
        """, (canvas_id, message[0], message[1], message[2]))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error while adding message: {e}")
    finally:
        cur.close()
        conn.close()


def delete_message(page, message_id):
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
    cur = conn.cursor()
    try:
        cur.execute(f"DELETE FROM {page[:-1]}_messages WHERE {page[:-1]}_message_id = ?", (message_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error while deleting message: {e}")
    finally:
        cur.close()
        conn.close()


def text2speech(text, message_id, hd=False, model=None, voice=None):
    if hd:
        response = st.session_state.openai_client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
        )
        response_filepath = os.path.join(TEMP_DIR, f"voice_message_{st.session_state.user_id}_{message_id}.mp3")
        response.stream_to_file(response_filepath)
        return response_filepath
    else:
        tts = gTTS(text, lang='ru', tld='ru', slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp


def copy_to_clipboard(text):
    js_code = f"""
    <script>
    function copyToClipboard(text) {{
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
    }}
    </script>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&icon_names=content_copy" />
    <style>
        * {{
            margin: 0;
            padding: 0;
        }}
        .copy-button {{
            display: flex;
            align-items: center;
            background-color: transparent; /* Убираем фон */
            color: gray; /* Устанавливаем серый цвет иконки */
            border: none; /* Убираем рамку */
            font-size: 16px; /* Размер иконки */
            font-family: "Source Code Pro", monospace;
            margin: 0;
            padding-top: 10px; /* Устанавливаем отступы для высоты кнопки */
            min-height: 40px; /* Устанавливаем минимальную высоту кнопки */
            line-height: 1.5; /* Устанавливаем высоту строки */
        }}
        .copy-button:hover {{
            color: #FF4B4B; /* Цвет фона при наведении */
        }}
        .copy-button:active {{
            transform: scale(0.97); /* Эффект нажатия */
        }}
        .material-symbols-rounded {{
            font-size: 1.25em;
            margin-right: 10px; /* Отступ между иконкой и текстом */
            font-size: 20px; /* Размер иконки */
        }}
    </style>
    <button class="copy-button" onclick="copyToClipboard(`%s`)">
        <span class="material-symbols-rounded">
            content_copy
        </span>
        Копировать
    </button>
    """ % text.replace('"', '&quot;').replace('`', '\`')
    components.html(js_code, height=40)


class Message:
    def __init__(self, page, message, message_id=None, stream=None):
        self.type = page
        self.id = message_id
        self.date = message[0]
        self.role = message[1]
        self.message = message[2]
        self.stream = stream

        if self.role == "assistant":
            self.avatar = f"assets/{self.type}_avatar.jpg"
        else:
            self.avatar = "assets/user_avatar.png"

        st.markdown("""
            <style>
            .element-container:has(#button-after) + div button {
                background-color: transparent; /* Убираем фон */
                border: none; /* Убираем рамку */
                color: gray; /* Устанавливаем серый цвет иконки */
                font-size: 16px; /* Размер иконки */
                padding: 0; /* Убираем отступы */
                min-height: 0;
                line-height: 0.5;
                transition: none; /* Убираем эффект перехода */
                
            }
            .element-container:has(#button-after) + div button:hover {
                color: #FF4B4B; /* Цвет иконки при наведении */
            }
            .element-container:has(#button-after) + div button:active {
                transform: scale(0.97); /* Эффект нажатия */
            }
            </style>
            """, unsafe_allow_html=True)

        if self.stream:
            self.stream_message()
        else:
            self.show_message()

    def message_template(self):
        return st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="
                    flex-grow: 1;
                    color: #6d6d6d;
                    ">
                    {formatted_date(self.date)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def show_message(self):
        with st.chat_message(self.role, avatar=self.avatar):

            self.message_template()
            st.markdown(self.message)

            if self.id:
                col1, col2, col3 = st.columns([1, 1, 1])
                col2.markdown('<span id="button-after"></span>', unsafe_allow_html=True)
                col3.markdown('<span id="button-after"></span>', unsafe_allow_html=True)

                if self.role == "user":
                    with col1:
                        copy_to_clipboard(self.message)
                    if col2.button("Повторить", icon=':material/replay:', key=f"retry_message_id_{self.id}"):
                        st.session_state.repeat_message = self.message
                        st.rerun()
                    if col3.button("Удалить", icon=':material/delete:', key=f"delete_message_id_{self.id}"):
                        delete_message(self.type, self.id)
                        st.rerun()
                else:
                    with col1:
                        copy_to_clipboard(self.message)
                    hd_speech = ' (HD)' if st.session_state.hd_speech else ''
                    if col2.button(f"Озвучить{hd_speech}", icon=':material/graphic_eq:',
                                   key=f"play_message_id_{self.id}"):
                        with st.spinner("Перевожу текст в речь..."):
                            audio = text2speech(
                                self.message,
                                self.id,
                                hd=st.session_state.hd_speech,
                                model='tts-1' if st.session_state.hd_speech else None,
                                voice='nova' if st.session_state.hd_speech else None
                            )
                        st.audio(audio, format="audio/mp3")
                    if col3.button("Удалить", icon=':material/delete:', key=f"delete_message_id_{self.id}"):
                        delete_message(self.type, self.id)
                        st.rerun()

    def stream_message(self):
        with st.chat_message(self.role, avatar=self.avatar):
            self.message_template()

            message_placeholder = st.empty()

            for chunk in self.stream:
                if chunk.choices[0].delta.content is not None:
                    self.message += chunk.choices[0].delta.content
                    message_placeholder.markdown(self.message + "▌")
            message_placeholder.markdown(self.message)


class ChatbotCanvas:
    def __init__(self, name, params, page):
        self.name = name
        self.id = params[0]
        self.date = params[1]
        self.description = params[2]
        self.type = page

        self.bio()
        self.canvas()

        st.session_state.openai_client = OpenAI(api_key=get_api_key(st.session_state.user_id))

    def bio(self):
        st.title(self.name)
        st.text(f"Дата создания: {formatted_date(self.date)}")
        st.divider()

        if self.type == "bots":
            with st.container(border=True):
                st.write(f"**Описание бота**:\n\n{self.description}")

    def canvas(self):
        messages = get_messages(self.type, self.id)

        for message in messages:
            message_id = message[0]
            Message(self.type, message[1:], message_id)

    def send_message(self, message):

        if st.session_state.optimize_prompt and not st.session_state.save_history:
            message = optimize_prompt(self.type, message)

        user_message_date = datetime.now()

        Message(self.type, [user_message_date, "user", message])

        if not st.session_state.save_history:
            messages = [{"role": "system", "content": self.description}, {"role": "user", "content": message}]
        else:
            messages = [{"role": "system", "content": self.description}] + [
                {"role": _m[2], "content": _m[3]} for _m in get_messages(self.type, self.id)
            ] + [{"role": "user", "content": message}]

        try:
            stream = st.session_state.openai_client.chat.completions.create(
                model=st.session_state.model,
                messages=messages,
                temperature=0.5,
                stream=True
            )
            assistant_message_date = datetime.now()
            response = Message(self.type, [assistant_message_date, "assistant", ""], stream=stream)
            add_message(self.type, self.id, [user_message_date, "user", message])
            add_message(self.type, self.id, [assistant_message_date, "assistant", response.message])
        except Exception as e:
            st.error(f"При отправке сообщения произошла ошибка: {e}")

    def clear(self):
        conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
        cur = conn.cursor()
        try:
            cur.execute(f"DELETE FROM {self.type[:-1]}_messages WHERE {self.type[:-1]}_id = ?", (self.id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error while clearing {self.type[:-1]} history: {e}")
        finally:
            cur.close()
            conn.close()

    def delete(self):
        conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
        cur = conn.cursor()
        try:
            cur.execute(f"DELETE FROM {self.type[:-1]}_messages WHERE {self.type[:-1]}_id = ?", (self.id,))
            cur.execute(f"DELETE FROM {self.type} WHERE {self.type[:-1]}_id = ?", (self.id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error while deleting {self.type[:-1]}: {e}")
        finally:
            cur.close()
            conn.close()

    @st.dialog(f"Изменить имя/описание")
    def change_info(self):
        new_name = st.text_input("Введите новое имя", value=self.name)
        new_description = st.text_area(
            "Введите новое описание",
            value=self.description,
            height=300,
            disabled=True if self.type == "chats" else False
        )
        button_visible = new_name != '' and new_description != ''

        if st.button("Сохранить", disabled=not button_visible):

            if check_chat_name(self.type, new_name, self.id):
                st.error(f'Имя \"{new_name}\" уже используется', icon="🚨")
                return

            conn = sqlite3.connect(os.path.join(DATA_DIR, 'logic.db'))
            cur = conn.cursor()
            try:
                cur.execute(f"""
                    UPDATE {self.type}
                    SET {self.type[:-1]}_name = ?,
                        {self.type[:-1]}_description = ?
                    WHERE {self.type[:-1]}_id = ?
                """, (new_name, new_description, self.id)
                )
                conn.commit()
                self.name = new_name
                self.description = new_description
            except sqlite3.Error as e:
                print(f"Error while updating {self.type[:-1]} info: {e}")
            finally:
                cur.close()
                conn.close()
            st.rerun()

