# -*- coding: utf-8 -*-
import telebot
import logging
import time
import requests
from bs4 import BeautifulSoup
import random
import re
from MyToken import token
from datetime import datetime

bot = telebot.TeleBot(token)

# Получаем инфо о боте. Таким образом мы видим, что скрипт запустился и связался с Ботом
print(bot.get_me())

# Паттерны для модуля re, используемые в коде
pattern_poem_list_one = re.compile('[A-Z].*_.*.html')
pattern_poem_list_two = re.compile('[A-Zmin].*_[0-9]*.html')
pattern_poem_name = re.compile('[А-Яа-я].*<br/>')
pattern_show_msg = re.compile('/show_[A-Za-z].*_[0-9]*')
pattern_sub_one = re.compile('<[/A-Za-z0-9]*>')
pattern_sub_two = re.compile(r'\n *')
pattern_sub_three = re.compile('\n\n\n')

# Ссылка на сайт, откуда грузятся стихи
site_url = "http://www.easadov.ru/"

list_of_letters_ru = ['А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'К', 'Л', 'М', 'Н', 'О', 'П',
                      'Р', 'С', 'Т', 'У', 'Х', 'Ц', 'Ч', 'Ш', 'Э', 'Ю', 'Я']
list_of_letters_en = ['A', 'B', 'V', 'G', 'D', 'E', 'ZH', 'Z', 'I', 'K', 'L', 'M', 'N', 'O',
                      'P', 'R', 'S', 'T', 'U', 'H', 'TZ', 'TCH', 'SH', 'AE', 'YU', 'YA']
list_of_themes = ['Любовь', 'Война', 'Животные', 'Общая', 'Миниатюра 1', 'Миниатюра 2', 'Миниатюра 3']


# Функция для записи в лог обращений пользователей
def log(message, answer):
    print("\n--------")
    print(datetime.now())
    print("Сообщение от {0} (@{1}). (id = {2}) \nТекст - {3}".format(message.from_user.first_name,
                                                                     message.from_user.username,
                                                                     str(message.from_user.id),
                                                                     message.text))
    print("Ответ - " + answer)
    print("--------")


# Выгружаем структуру страницы по тегу
def get_text_from_url(url):
    req = requests.get(url)
    soup = BeautifulSoup(req.text, "lxml")
    text = soup.find_all('div', {'class': 'post'})
    return text


# Получаем рандомную ссылку на стих со всех страниц раздела "Миниатюры"
def get_random_mini_url():
    rand = str(random.randint(1, 260))
    url = site_url + "mini_" + rand + ".html"
    return url


# Получаем рандомную ссылку на стих раздела указанного в переменной
def get_random_theme_url(theme_url):
    text = get_text_from_url(theme_url)
    poems_list = pattern_poem_list_one.findall(str(text))
    rand_number = random.randint(0, len(poems_list) - 1)
    random_poem = poems_list[rand_number]
    random_theme_url = site_url + random_poem
    return random_theme_url


# Получаем рандомную ссылку на стих из всех разделов и страниц
def get_random_all_url():
    rand_letter_number = random.randint(1, 26)
    rand_letter = list_of_letters_en[rand_letter_number - 1]
    url = site_url + rand_letter + ".html"
    text = get_text_from_url(url)
    list_of_links = re.findall(rand_letter + '_.*.html', str(text))
    count_items = len(list_of_links)
    rand_poem_number = random.randint(0, count_items - 1)
    rand_poem = list_of_links[rand_poem_number]
    poem_url = site_url + rand_poem
    return poem_url


# Функция отправки стихов в зависимости от выбранной темы
def send_poem(message, url):
    text = get_text_from_url(url)
    for i in text:
        poem_name = i.find('h2')
        poem_body = i.find('pre')
    poem_name = pattern_sub_one.sub('', str(poem_name))
    poem_body = pattern_sub_one.sub('', str(poem_body))
    poem_body = poem_body.strip()
    poem_body = pattern_sub_two.sub('\n', str(poem_body))
    poem_body = pattern_sub_three.sub('\n\n', str(poem_body))
    answer = poem_name
    log(message, answer)
    bot.send_message(message.chat.id, poem_name + '\n\n' + poem_body)


# Поиск стиха по тексту используя Яндекс поиск по сайту
def search_text(text):
    string = re.sub('[,.:;]', '', text).replace(' ', '+')
    req = requests.get('https://yandex.ru/sitesearch?text=' + string + '&searchid=85177')
    soup = BeautifulSoup(req.text, "lxml")
    try:
        find_check = soup.find('div', {'class': 'b-gap g-gap-vertical g-gap-horizontal'}).text
    except AttributeError:
        find_check = 'Ошибка'
    if find_check == 'Искомая комбинация слов нигде не встречается':
        return find_check
    else:
        link = soup.find('a', {'class': 'b-serp-item__title-link'}).get('href')
        name = soup.find('a', {'class': 'b-serp-item__title-link'}).find('span').text
        text = soup.find('div', {'class': 'b-serp-item__text'}).text
        link = link.replace(site_url, '/show_').replace('.html', '')
        name = name.split(', ')
        msg = '<b>Вот, что я нашел:</b>\n' + '<b>Название:</b> ' + name[len(name)-1] + '\n' + '<b>Отрывок:</b>\n' + text + '\n' + \
              '<b>Прочитать полностью:</b> ' + link
        return msg


# Получаем список стихов и ссылки на них по букве
def get_links_and_names(letter):
    url = site_url + letter + '.html'
    text = get_text_from_url(url)
    list_of_poems = pattern_poem_list_two.findall(str(text))
    poem_name = pattern_poem_name.findall(str(text))
    poem_name = pattern_sub_one.sub('', str(poem_name))
    poem_name = poem_name.replace('[', '').replace(']', '').replace('\', \'', '==').replace('\'', '')
    list_of_poem_names = poem_name.split('==')
    x = 0
    names = ''
    for items in list_of_poem_names:
        x += 1
        show_cmd = '/show_' + list_of_poems[x-1].replace('.html', '')
        names = names + str(x) + '.' + items + ' ' + show_cmd + '\n'
    return names


# Функция для вызова поиска по фразе
def search(message):
    found_text = search_text(message.text)
    bot.send_message(message.chat.id, found_text, parse_mode='HTML')
    log(message, found_text)


# Считываем комманду /start и выводим на нее меню бота
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
    user_markup.row('Случайные', 'По Алфавиту')
    user_markup.row('По Теме', 'По Фразе')
    bot.send_message(message.from_user.id, "Привет", reply_markup=user_markup)
    answer = "Отправил главное меню"
    log(message, answer)


# Считываем текст, отправленный пользователем, и выдаем на него ответ
@bot.message_handler(content_types=['text'])
def handle_command(message):
    if message.text == "Миниатюры":
        send_poem(message, get_random_mini_url())
    elif message.text == "Стихи":
        send_poem(message, get_random_all_url())
    elif message.text == "О Любви":
        send_poem(message, get_random_theme_url(site_url + 'love.html'))
    elif message.text == "О Войне":
        send_poem(message, get_random_theme_url(site_url + 'war.html'))
    elif message.text == "О Животных":
        send_poem(message, get_random_theme_url(site_url + 'animal.html'))
    elif message.text == "На Общую Тему":
        send_poem(message, get_random_theme_url(site_url + 'other.html'))
    elif message.text == "Случайные":
        user_markup_rand = telebot.types.ReplyKeyboardMarkup(True, True)
        user_markup_rand.row('Миниатюры', 'Стихи')
        user_markup_rand.row('О Любви', 'О Войне')
        user_markup_rand.row('О Животных', 'На Общую Тему')
        user_markup_rand.row('Назад')
        bot.send_message(message.from_user.id, "Выбирайте...", reply_markup=user_markup_rand)
        answer = "Отправил меню:Случайные"
        log(message, answer)
    elif message.text == "По Алфавиту":
        user_markup_alpha = telebot.types.ReplyKeyboardMarkup(True, True)
        user_markup_alpha.row('А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И')
        user_markup_alpha.row('К', 'Л', 'М', 'Н', 'О', 'П', 'Р', 'С', 'Т')
        user_markup_alpha.row('У', 'Х', 'Ц', 'Ч', 'Ш', 'Э', 'Ю', 'Я')
        user_markup_alpha.row('Назад')
        bot.send_message(message.from_user.id, "Выбирайте букву", reply_markup=user_markup_alpha)
        answer = "Отправил меню:По Алфавиту"
        log(message, answer)
    elif message.text == "По Теме":
        user_markup_theme = telebot.types.ReplyKeyboardMarkup(True, True)
        user_markup_theme.row('Любовь', 'Война')
        user_markup_theme.row('Животные', 'Общая')
        user_markup_theme.row('Миниатюра 1', 'Миниатюра 2')
        user_markup_theme.row('Миниатюра 3', 'Назад')
        bot.send_message(message.from_user.id, "Выбирайте тему", reply_markup=user_markup_theme)
        answer = "Отправил меню:По Теме"
        log(message, answer)
    elif message.text == "Назад":
        user_markup_back = telebot.types.ReplyKeyboardMarkup(True, True)
        user_markup_back.row('Случайные', 'По Алфавиту')
        user_markup_back.row('По Теме', 'По Фразе')
        bot.send_message(message.from_user.id, "Возвращаемся...", reply_markup=user_markup_back)
        answer = "Отправил меню:Назад(Главное)"
        log(message, answer)
    elif message.text in list_of_letters_ru:
        dict_of_letters = {'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ж': 'ZH', 'З': 'Z',
                           'И': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R',
                           'С': 'S', 'Т': 'T', 'У': 'U', 'Х': 'H', 'Ц': 'TZ', 'Ч': 'TCH', 'Ш': 'SH',
                           'Э': 'AE', 'Ю': 'YU', 'Я': 'YA'}
        names = get_links_and_names(dict_of_letters[message.text])
        bot.send_message(message.chat.id, 'Выберите стих\n' + names)
        answer = "Отправил список стихов"
        log(message, answer)
    elif pattern_show_msg.match(message.text) is not None:
        command = message.text.replace('/show_', '')
        try:
            poem_link = site_url + command + '.html'
            send_poem(message, poem_link)
        except IndexError:
            bot.send_message(message.chat.id, 'Ошибочная ссылка')
    elif message.text in list_of_themes:
        dict_of_theme_links = {'Любовь': 'love',
                               'Война': 'war',
                               'Животные': 'animal',
                               'Общая': 'other',
                               'Миниатюра 1': 'mini',
                               'Миниатюра 2': 'mini_II',
                               'Миниатюра 3': 'mini_III'}
        names = get_links_and_names(dict_of_theme_links[message.text])
        z = names.split('\n')
        y = len(z)
        if y > 40:
            bot.send_message(message.chat.id, 'Выберите стих')
            count = 0
            start = 0
            stop = 40
            while y > 40:
                count = count + 1
                y = y - 40
                bot.send_message(message.chat.id, '\n'.join(z[start:stop]))
                start = stop
                stop += 40
            bot.send_message(message.chat.id, '\n'.join(z[start:]))
        else:
            bot.send_message(message.chat.id, 'Выберите стих\n' + names)
        answer = "Отправил список стихов"
        log(message, answer)
    elif message.text == 'По Фразе':
        msg = bot.send_message(message.chat.id, 'Введите фразу для поиска')
        bot.register_next_step_handler(msg, search)
    else:
        bot.send_message(message.chat.id, 'Выберите из меню')


# Бесконечный цикл для бота
if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as err:
            logging.error(err)
            time.sleep(5)
