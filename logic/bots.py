import os

import streamlit as st
from streamlit_lottie import st_lottie

from logic import get_account_info, get_chatbot_list, get_description, new_chat, ChatbotCanvas


TEMP_DIR = '/disk/temp'
os.makedirs(TEMP_DIR, exist_ok=True)


user_info = get_account_info(st.context.cookies.get('ajs_anonymous_id', None))


@st.cache_data
def animation():
    st_lottie("https://lottie.host/0fba30a0-5a7e-4e3d-b741-f9e3b888a380/mh9GuBuzlD.json", height=200)


if user_info:
    if user_info[6] is None:
        animation()
        st.info(f"""
            Видимо, вы забыли ввести свой OpenAI API-ключ.
    
            Если у вас уже есть ключ, то перейдите в раздел "Аккаунт" и укажите его там.
    
            Если у вас нет ключа, выполните следующие шаги для его получения:        
            > 1. Перейдите на сайт [OpenAI](https://platform.openai.com/settings/organization/general);
            > 2. Зарегистрируйтесь или войдите в свою учетную запись;
            > 3. Перейдите в раздел API Keys;
            > 4. Нажмите "Create new secret key" для создания нового ключа;
            > 5. Скопируйте сгенерированный ключ и вставьте его в разделе "Аккаунт".
        """
                )
        st.stop()

    bot_list = get_chatbot_list('bots')

    if len(bot_list) == 0:
        st.write('У тебя ещё нет ни одного бота? Пора создать - нажми "Новый бот"')

    context = st.sidebar.selectbox(
        'Выбери бот',
        (_name for _name in bot_list.keys()),
        index=len(bot_list) - 1
    )

    if st.sidebar.button('Новый бот'):
        new_chat('bots')

    if 'model' not in st.session_state:
        st.session_state.model = 'gpt-4o'
    if 'hd_speech' not in st.session_state:
        st.session_state.hd_speech = False

    if context:
        bot_canvas = ChatbotCanvas(context, bot_list[context], page='bots')

        with st.sidebar:
            st.divider()
            st.write('Управление текущим ботом:\n')

            available_models = [
                'gpt-4.1',
                'gpt-4.1-mini',
                'gpt-4.1-nano',
                'gpt-4o',
                'chatgpt-4o-latest',
                'gpt-4-turbo',
            ]

            if model := st.pills('Модель:', available_models, selection_mode='single', default=st.session_state.model):
                st.session_state.model = model

            st.toggle('Сохранять историю', help="""
                GPT модель будет помнить всю историю сообщений данного бота (при этом стоимость
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

            if st.button('Изменить имя/описание бота'):
                bot_canvas.change_info()

            if st.button('Очистить историю'):
                bot_canvas.clear()
                st.rerun()

            if st.button('Удалить бот', type='primary'):
                bot_canvas.delete()
                st.rerun()

        for filename in os.listdir(TEMP_DIR):
            if filename.startswith(f'voice_message_{st.session_state.user_id}'):
                os.remove(os.path.join(TEMP_DIR, filename))

        if 'repeat_message' in st.session_state:
            bot_canvas.send_message(st.session_state.repeat_message)
            del st.session_state['repeat_message']
            st.rerun()

        if prompt := st.chat_input("Введи своё сообщение..."):
            bot_canvas.send_message(prompt)
            st.rerun()
