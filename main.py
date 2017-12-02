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

# Паттерны для модуля re, используемые в проекте
pattern_poem_list_one = re.compile('[A-Z].*_.*.html')
pattern_poem_list_two = re.compile('[A-Zmin].*_[0-9]*.html')
pattern_poem_name = re.compile('[А-Яа-я].*<br/>')
pattern_show_msg = re.compile('/show_[A-Za-z].*_[0-9]*')
pattern_sub_one = re.compile(r'<.*?>')
pattern_sub_two = re.compile(r'\n *')
pattern_sub_three = re.compile('\n\n\n')


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


# Функция отправки стихов в зависимости от выбранной темы
def poem_sent(message, poem_url, fnc):
    if fnc == 'rand':
        req = requests.get(poem_url)
        soup_sent = BeautifulSoup(req.text, "lxml")
        text_soup = soup_sent.find_all('div', {'class': 'post'})
        poems_list = pattern_poem_list_one.findall(str(text_soup))
        rand_number = random.randint(0, len(poems_list) - 1)
        random_poem = poems_list[rand_number]
        other_poem_url = "http://www.easadov.ru/" + random_poem
    elif fnc == 'notrand':
        other_poem_url = poem_url
    else:
        None
    r = requests.get(other_poem_url)
    soup_sent = BeautifulSoup(r.text, "lxml")
    text_soup = soup_sent.find_all('div', {'class': 'post'})
    for i in text_soup:
        poem_name = i.find('h2')
        poem_body = i.find('pre')
    poem_name = pattern_sub_one.sub('', str(poem_name)).replace('</.*>', '')
    poem_body = pattern_sub_one.sub('', str(poem_body)).replace('</.*>', '')
    poem_body = poem_body.strip()
    poem_body = pattern_sub_two.sub('\n', str(poem_body))
    poem_body = pattern_sub_three.sub('\n\n', str(poem_body))
    answer = poem_name
    log(message, answer)
    bot.send_message(message.chat.id, poem_name + '\n\n' + poem_body)


def search_text(text):
    s = re.sub('[,.:;]', '', text).replace(' ', '+')
    req = requests.get('https://yandex.ru/sitesearch?text=' + s + '&searchid=85177')
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
        link = link.replace('http://www.easadov.ru/', '/show_').replace('.html', '')
        splited_link = link.split('_')
        if splited_link[1] == 'mini':
            if int(splited_link[2]) > 100:
                number = int(splited_link[2]) - 100
                letter = 'mini_II'
                if number > 100:
                    number -= 100
                    letter = 'mini_III'
                splited_link[1] = letter
                splited_link[2] = str(number)
            link = '_'.join(splited_link)
        name = name.split(', ')
        msg = '<b>Название:</b> ' + name[len(name)-1] + '\n' + '<b>Отрывок:</b>\n' + text + '\n' + \
              '<b>Прочитать полностью:</b> ' + link
        return msg


def get_links_and_names(letter):
    req = requests.get('http://www.easadov.ru/' + letter + '.html')
    soup = BeautifulSoup(req.text, "lxml")
    text = soup.find_all('div', {'class': 'post'})
    list_of_poems = pattern_poem_list_two.findall(str(text))
    poem_name = pattern_poem_name.findall(str(text))
    poem_name = pattern_sub_one.sub('', str(poem_name)).replace('</.*>', '')
    poem_name = poem_name.replace('[', '').replace(']', '').replace('\', \'', '==').replace('\'', '')
    list_of_poem_names = poem_name.split('==')
    x = 0
    names = ''
    for items in list_of_poem_names:
        x += 1
        show_cmd = '/show_' + list_of_poems[x-1].replace('.html', '')
        names = names + str(x) + '.' + items + ' ' + show_cmd + '\n'
    return names


def search(message):
    s = search_text(message.text)
    if s == 'Искомая комбинация слов нигде не встречается':
        bot.send_message(message.chat.id, s)
    else:
        bot.send_message(message.chat.id, '<b>Вот, что я нашел:</b>\n' + s, parse_mode='HTML')
    answer = s
    log(message, answer)


# Считываем комманду /start и выводим на нее меню бота
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
    user_markup.row('Случайные', 'По Алфавиту')
    user_markup.row('По Теме', 'По Фразе')
    bot.send_message(message.from_user.id, "Привет", reply_markup=user_markup)
    answer = "Отправил главное меню"
    log(message, answer)


# Считываем текст отправленный, пользователем и выдаем на него ответ
@bot.message_handler(content_types=['text'])
def handle_command(message):
    list_of_letters_ru = ['А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'К', 'Л', 'М', 'Н', 'О', 'П',
                          'Р', 'С', 'Т', 'У', 'Х', 'Ц', 'Ч', 'Ш', 'Э', 'Ю', 'Я']
    list_of_letters_en = ['A', 'B', 'V', 'G', 'D', 'E', 'ZH', 'Z', 'I', 'K', 'L', 'M', 'N', 'O',
                          'P', 'R', 'S', 'T', 'U', 'H', 'TZ', 'TCH', 'SH', 'AE', 'YU', 'YA']
    list_of_themes = ['Любовь', 'Война', 'Животные', 'Общая', 'Миниатюра 1', 'Миниатюра 2', 'Миниатюра 3']

    if message.text == "Миниатюры":
        rand = str(random.randint(1, 260))
        url = "http://www.easadov.ru/mini_" + rand + ".html"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.find_all('div', {'class': 'post'})
        for items in text:
            name = items.find('h2')
            body = items.find('pre')
        name = pattern_sub_one.sub('', str(name)).replace('</.*>', '')
        body = pattern_sub_one.sub('', str(body)).replace('</.*>', '')
        body = body.strip()
        body = pattern_sub_two.sub('\n', str(body))
        answer = name
        log(message, answer)
        bot.send_message(message.chat.id, name + '\n\n' + body)

    elif message.text == "Стихи":
        rand_letter_number = random.randint(1, 26)
        rand_letter = list_of_letters_en[rand_letter_number - 1]
        url = "http://www.easadov.ru/" + rand_letter + ".html"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.find_all('div', {'class': 'post'})
        list_of_links = re.findall(rand_letter + '_.*.html', str(text))
        count_items = len(list_of_links)
        rand_poem_number = random.randint(0, count_items - 1)
        rand_poem = list_of_links[rand_poem_number]
        poem_url = "http://www.easadov.ru/" + rand_poem
        r = requests.get(poem_url)
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.find_all('div', {'class': 'post'})
        for items in text:
            name = items.find('h2')
            body = items.find('pre')
        name = pattern_sub_one.sub('', str(name)).replace('</.*>', '')
        body = pattern_sub_one.sub('', str(body)).replace('</.*>', '')
        body = body.strip()
        body = pattern_sub_two.sub('\n', str(body))
        answer = name
        log(message, answer)
        bot.send_message(message.chat.id, name + '\n\n' + body)

    elif message.text == "О Любви":
        poem_sent(message, "http://www.easadov.ru/love.html", 'rand')

    elif message.text == "О Войне":
        poem_sent(message, "http://www.easadov.ru/war.html", 'rand')

    elif message.text == "О Животных":
        poem_sent(message, "http://www.easadov.ru/animal.html", 'rand')

    elif message.text == "На Общую Тему":
        poem_sent(message, "http://www.easadov.ru/other.html", 'rand')
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
            poem_link = "http://www.easadov.ru/" + command + '.html'
            poem_sent(message, poem_link, 'notrand')
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
