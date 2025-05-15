import os

import streamlit as st
from openai import OpenAI
from streamlit_lottie import st_lottie

from logic import get_account_info, get_chatbot_list, new_chat, ChatbotCanvas


TEMP_DIR = '/disk/temp'
os.makedirs(TEMP_DIR, exist_ok=True)


user_info = get_account_info(st.context.cookies.get('ajs_anonymous_id', None))


@st.cache_data
def animation():
    st_lottie("https://lottie.host/0fba30a0-5a7e-4e3d-b741-f9e3b888a380/mh9GuBuzlD.json", height=200)

def reset_selection(cm_pills: bool):
    if cm_pills:
        st.session_state.cm_pills_reset_key += 1
    else:
        st.session_state.rm_pills_reset_key += 1


if user_info:
    if user_info[6] is None:
        animation()
        st.info("""
            Видимо, вы забыли ввести свой OpenAI API-ключ.

            Если у вас уже есть ключ, то перейдите в раздел "Аккаунт" и укажите его там.

            Если у вас нет ключа, выполните следующие шаги для его получения:
            > 1. Перейдите на сайт [OpenAI](https://platform.openai.com/settings/organization/general);
            > 2. Зарегистрируйтесь или войдите в свою учетную запись;
            > 3. Перейдите в раздел API Keys;
            > 4. Нажмите "Create new secret key" для создания нового ключа;
            > 5. Скопируйте сгенерированный ключ и вставьте его в разделе "Аккаунт".

            Также можете указать DeepSeek API-ключ для доступа к моделям DeepSeek.
        """
                )
        st.stop()

    chat_list = get_chatbot_list('chats')

    if len(chat_list) == 0:
        st.write('У тебя ещё нет ни одного чата? Пора создать - нажми "Новый чат"')

    context = st.sidebar.selectbox(
        'Выбери чат',
        (_name for _name in chat_list.keys()),
        index=len(chat_list) - 1
    )

    if st.sidebar.button('Новый чат'):
        new_chat('chats')

    if 'model' not in st.session_state:
        st.session_state.model = None
    #     st.session_state.model = 'gpt-4.1-mini'
        # st.session_state.openai_client = OpenAI(api_key=user_info[6])
    if 'cm_pills_reset_key' not in st.session_state:
        st.session_state.cm_pills_reset_key = 0
    if 'rm_pills_reset_key' not in st.session_state:
        st.session_state.rm_pills_reset_key = 0
    if 'hd_speech' not in st.session_state:
        st.session_state.hd_speech = False

    if context:
        chat_canvas = ChatbotCanvas(context, chat_list[context], page='chats')

        with st.sidebar:
            st.divider()
            st.write('Управление текущим чатом:\n')

            available_classic_models = [
                'gpt-4.1',
                'gpt-4.1-mini',
                'gpt-4.1-nano',
                'gpt-4o',
                'chatgpt-4o-latest',
                'gpt-4-turbo'
            ]
            available_reasoning_models = [
                'o3-mini',
                'o4-mini'
            ]

            if user_info[7]:
                available_classic_models.append('deepseek-chat')
                available_reasoning_models.append('deepseek-reasoner')

            tab1, tab2 = st.tabs(['💬 Обычные модели', '🧠 Reasoning-модели'])

            classic_models_pills = tab1.empty()
            reasoning_models_pills = tab2.empty()

            classic_models_pills.pills(
                'classic',
                available_classic_models,
                label_visibility='collapsed',
                default=None,
                key=f'cm_pills_{st.session_state.cm_pills_reset_key}',
                on_change=reset_selection,
                args=(False,)
            )
            reasoning_models_pills.pills(
                'reasoning',
                available_reasoning_models,
                label_visibility='collapsed',
                default=None,
                key=f'rm_pills_{st.session_state.rm_pills_reset_key}',
                on_change=reset_selection,
                args=(True,)
            )

            cm_pills_value = st.session_state[f'cm_pills_{st.session_state.cm_pills_reset_key}']
            rm_pills_value = st.session_state[f'rm_pills_{st.session_state.rm_pills_reset_key}']

            st.session_state.model = cm_pills_value if cm_pills_value else rm_pills_value

            if st.session_state.model and 'deepseek' in st.session_state.model:
                st.session_state.openai_client = OpenAI(
                    api_key=user_info[7], base_url="https://api.deepseek.com")
            else:
                st.session_state.openai_client = OpenAI(api_key=user_info[6])

            st.toggle('Сохранять историю', help="""
                GPT модель будет помнить всю историю сообщений данного чата (при этом стоимость
                использования API сильно увеличивается).

                Если историю не сохранять, то модель будет помнить только
                текущий запрос (история на экране при этом все равно будет
                отображаться).
                """,
                      key='save_history')

            st.toggle('Оптимизировать промпт', help="""
                При включении данного параметра, ваш запрос будет оптимизирован и структурирован
                для получения наиболее релевантного ответа.

                Недоступно при включенном параметре "Сохранять историю".
            """,
                      key='optimize_prompt', disabled=True if st.session_state.save_history else False)

            st.toggle('HD озвучка сообщений', help=""" 
                При включении этого варианта, озвучка сообщений будет производиться с помощью Text-to-Speech модели
                OpenAI  (tts-1), которая обеспечивает высокое качество звучания и естественность голоса.

                Обратите внимание, что использование модели tts-1 является платным.

                Если вы отключите этот вариант, озвучка будет производиться с помощью gTTS (Google Text-to-Speech), 
                который является бесплатным, но может иметь менее качественное звучание по сравнению с HD вариантом.

            """,
                      key='hd_speech')

            if st.button('Изменить имя/описание чата'):
                chat_canvas.change_info()

            if st.button('Очистить историю'):
                chat_canvas.clear()
                st.rerun()

            if st.button('Удалить чат', type='primary'):
                chat_canvas.delete()
                st.rerun()

            st.write(st.session_state)

        for filename in os.listdir(TEMP_DIR):
            if filename.startswith(f'voice_message_{st.session_state.user_id}'):
                os.remove(os.path.join(TEMP_DIR, filename))

        if 'repeat_message' in st.session_state:
            st.rerun()
            del st.session_state['repeat_message']

            if st.session_state.model is None:
                st.toast('Сначала выберите модель')
            else:
                chat_canvas.send_message(st.session_state.repeat_message)
                st.rerun()

        if prompt := st.chat_input("Введи своё сообщение...", disabled=st.session_state.model is None):
            chat_canvas.send_message(prompt)
            st.rerun()
