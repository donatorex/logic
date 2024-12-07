from streamlit_cookies_controller import CookieController
import time


controller = CookieController()


def set_cookie(key, value):
    controller = CookieController()
    controller.set(key, value)
    time.sleep(0.5)


def get_all_cookies():
    controller = CookieController()
    return controller.getAll()


def get_cookie(key):
    # controller = CookieController()
    return controller.get(key)


def remove_user_cookies():
    controller = CookieController()
    controller.remove('logic_user_token')
