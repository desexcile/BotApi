# -*- coding: utf-8 -*-
import telebot
import psycopg2
import time
from telebot import util
import re
import os

token = os.environ.get('TOKEN')
bot = telebot.TeleBot(token)
print(bot.get_me())

host = os.environ.get('db_host')
db_name = os.environ.get('db_name')
user = os.environ.get('db_user')
password = os.environ.get('db_password')

cross_smile = u'\U0000274C'
star_smile = u'\U00002B50'
plus_smile = u'\U00002795'
minus_smile = u'\U00002796'
magnifying_smile = u'\U0001F50D'

PATTERN_SHOW_MSG = re.compile('/show_[A-Za-z].*_[0-9]*')
PATTERN_PLUS_FAV = re.compile('add::.*')
PATTERN_MINUS_FAV = re.compile('remove::.*')

# Словари для корректного определения ссылок
dict_of_letters = {'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ж': 'ZH', 'З': 'Z',
                   'И': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R',
                   'С': 'S', 'Т': 'T', 'У': 'U', 'Х': 'H', 'Ц': 'TZ', 'Ч': 'TCH', 'Ш': 'SH',
                   'Э': 'AE', 'Ю': 'YU', 'Я': 'YA'}

dict_of_themes = {'О Любви': 'love',
                  'О Войне': 'war',
                  'О Животных': 'animal',
                  'На Общую Тему': 'other',
                  'Миниатюры': 'mini',
                  'Стихи': '%'}

dict_of_theme_links = {'Любовь': 'love',
                       'Война': 'war',
                       'Животные': 'animal',
                       'Общая': 'other',
                       'Миниатюра 1': 'mini',
                       'Миниатюра 2': 'mini_II',
                       'Миниатюра 3': 'mini_III'}


def sql_cmd(sql_param):
    with psycopg2.connect(host=host, dbname=db_name, user=user, password=password) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_param)
            sql_param_cmd = sql_param.split(' ')[0]
            if sql_param_cmd == 'UPDATE' or sql_param_cmd == 'INSERT':
                result = []
            else:
                result = cur.fetchall()
    conn.close()
    return result


def update_db(data, poem_link):
    new_data = ','.join(data)
    sql = "UPDATE asadov SET favorites = '{}' where link = '{}'".format(new_data, poem_link)
    sql_cmd(sql)


def select_favorites_from_db(poem_link):
    sql = "SELECT favorites FROM asadov WHERE link = '{}'".format(poem_link)
    result = sql_cmd(sql)[0][0].split(',')
    return result


def add_to_fav_db(user_id, poem_link):
    data = select_favorites_from_db(poem_link)
    if data:
        if data.count(user_id) >= 1:
            result = 'Этот стих уже добавлен'
        else:
            data.insert(1, user_id)
            update_db(data, poem_link)
            result = 'Добавил в избранное: '
    else:
        result = "Не нашел такой стих"
    return result


def remove_from_fav_db(user_id, poem_link):
    data = select_favorites_from_db(poem_link)
    if data.count(user_id) > 0:
        data.remove(user_id)
        update_db(data, poem_link)
        result = 'Удалил из избранного: '
    else:
        result = 'Нечего удалять'
    return result


def make_search_str_for_sql_q(user_id):
    data = ['%', '%']
    data.insert(1, user_id)
    new_data = ','.join(data)
    return new_data


def clear_fav_list(user_id):
    search_str = make_search_str_for_sql_q(user_id)
    sql = "SELECT link FROM asadov WHERE favorites LIKE '{}'".format(search_str)
    fav_links = sql_cmd(sql)
    if fav_links:
        for link in fav_links:
            remove_from_fav_db(user_id, link[0])
        result = 'Все стихи удалены из избранного'
    else:
        result = 'В избранных стихах пусто'
    return result


def show_fav_list_to_user(user_id):
    search_str = make_search_str_for_sql_q(user_id)
    sql = "SELECT name, link FROM asadov WHERE favorites LIKE '{}' ORDER BY link".format(search_str)
    result = sql_cmd(sql)
    fav_list = ''
    keyboard = telebot.types.InlineKeyboardMarkup()
    clear_button = telebot.types.InlineKeyboardButton(text=cross_smile + 'Очистить' + cross_smile,
                                                      callback_data="clear")
    keyboard.add(clear_button)
    for index, i in enumerate(result):
        fav_list = fav_list + str(index + 1) + '.' + ' '.join(i) + '\n'
    if fav_list:
        bot.send_message(user_id, 'Спиоск избранных стихов:\n' + fav_list, reply_markup=keyboard)
    else:
        bot.send_message(user_id, 'Нет сохраненных стихов.')
    return fav_list


def search_fn_one(phrase, sql):
    # Попытка поиска по целым словам
    find_string = re.sub('[,.:;-]', '%', phrase.lower()).replace(' ', '%')
    new_str = '%' + find_string + '%'
    result = sql_cmd(sql.format(new_str))
    return result, new_str


def search_fn_two(phrase, sql):
    # Попытка поиска по неполной фразе(удаляется одно слово, если не нашлось совпадений слово восстанавливается)
    find_string = re.sub('[,.:;-]', '%', phrase.lower()).replace(' ', '%')
    find_string = find_string.split('%')
    new_str = ''
    result = []
    for index, word in enumerate(find_string[:]):
        find_string.pop(index)
        new_str = '%' + '%'.join(find_string) + '%'
        result = sql_cmd(sql.format(new_str))
        if result:
            find_string.insert(index, '++')
            new_str = '%' + '%'.join(find_string) + '%'
            break
        else:
            find_string.insert(index, word)
    return result, find_string, new_str


def search_fn_three(sql, find_string):
    # Попытка поиска по фразе без гласных букв(заменяются на "_"(случайный символ))
    find_string = '%'.join(find_string)
    find_string = re.sub('[аоиеёэыуюя]', '_', find_string)
    new_str = '%' + find_string + '%'
    result = sql_cmd(sql.format(new_str))
    return result, find_string, new_str


def search_by_phrase(message):
    phrase = message.text
    sql = "SELECT name, link, body FROM asadov WHERE body ILIKE '{}'"
    result, new_str = search_fn_one(phrase, sql)
    if result:
        if len(result) > 10:
            result = 'Слишком много совпадений, попробуйте другую фразу.'
    else:
        result, find_string, new_str = search_fn_two(phrase, sql)
        if result:
            if len(result) > 10:
                result = 'Слишком много совпадений, попробуйте другую фразу..'
        else:
            result, find_string, new_str = search_fn_three(sql, find_string)
            if result:
                if len(result) > 10:
                    result = 'Слишком много совпадений, попробуйте другую фразу...'
            else:
                result = 'Искомая комбинация слов нигде не встречается.'

    # cut_search_phrase_from_found_text(result, new_str)
    if isinstance(result, list):
        found_poems = ''
        for idx, items in enumerate(result):
            name = result[idx][0]
            link = result[idx][1]
            found_poems = found_poems + "{}.{} {}\n".format(str(idx + 1), name, link)
        bot.send_message(message.chat.id, "Вот, что я нашел:\n{}".format(found_poems))
    else:
        bot.send_message(message.chat.id, result)
    return result


# Допилить разделение по /n
def send_poem(message, link):
    poem = sql_cmd("SELECT name, body FROM asadov WHERE link = '{}'".format(link))
    if poem:
        name = poem[0][0]
        body = poem[0][1]
        keyboard = telebot.types.InlineKeyboardMarkup()
        plus_fav_button = telebot.types.InlineKeyboardButton(text=plus_smile + star_smile,
                                                             callback_data="add::" + link)
        minus_fav_button = telebot.types.InlineKeyboardButton(text=minus_smile + star_smile,
                                                              callback_data="remove::" + link)
        show_fav_button = telebot.types.InlineKeyboardButton(text=magnifying_smile + star_smile,
                                                             callback_data="show")
        keyboard.add(plus_fav_button, minus_fav_button, show_fav_button)
        if len(body) > 4000:
            splited_text = util.split_string(body, 4000)
            count = len(splited_text)
            bot.send_message(message.chat.id, name + '\n')
            for large_text in splited_text:
                if large_text == splited_text[count - 1]:
                    bot.send_message(message.chat.id, large_text, reply_markup=keyboard)
                else:
                    bot.send_message(message.chat.id, large_text)
        else:
            bot.send_message(message.chat.id, name + '\n' + body, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Ошибочная ссылка")


def markup_random(message):
    user_markup_rand = telebot.types.ReplyKeyboardMarkup(True, True)
    user_markup_rand.row('Миниатюры', 'Стихи')
    user_markup_rand.row('О Любви', 'О Войне')
    user_markup_rand.row('О Животных', 'На Общую Тему')
    user_markup_rand.row('Назад')
    bot.send_message(message.from_user.id, "Выбирайте...", reply_markup=user_markup_rand)


def markup_alpha(message):
    user_markup_alpha = telebot.types.ReplyKeyboardMarkup(True, True)
    user_markup_alpha.row('А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И')
    user_markup_alpha.row('К', 'Л', 'М', 'Н', 'О', 'П', 'Р', 'С', 'Т')
    user_markup_alpha.row('У', 'Х', 'Ц', 'Ч', 'Ш', 'Э', 'Ю', 'Я')
    user_markup_alpha.row('Назад')
    bot.send_message(message.from_user.id, "Выбирайте букву", reply_markup=user_markup_alpha)


def markup_theme(message):
    user_markup_theme = telebot.types.ReplyKeyboardMarkup(True, True)
    user_markup_theme.row('Любовь', 'Война')
    user_markup_theme.row('Животные', 'Общая')
    user_markup_theme.row('Миниатюра 1', 'Миниатюра 2')
    user_markup_theme.row('Миниатюра 3', 'Назад')
    bot.send_message(message.from_user.id, "Выбирайте тему", reply_markup=user_markup_theme)


def markup_back(message):
    user_markup_back = telebot.types.ReplyKeyboardMarkup(True, True)
    user_markup_back.row('Случайные', 'По Алфавиту')
    user_markup_back.row('По Теме', 'По Фразе')
    bot.send_message(message.from_user.id, "Возвращаемся...", reply_markup=user_markup_back)


def random_poem(theme):
    sql = "SELECT link FROM asadov WHERE theme LIKE '{}%' ORDER BY random() limit 1".format(theme)
    link = sql_cmd(sql)[0][0]
    return link


markup_dict = {'Назад': markup_back, 'По Теме': markup_theme, 'По Алфавиту': markup_alpha, 'Случайные': markup_random}


def send_theme_list(message, theme):
    sql = "SELECT name, link FROM asadov WHERE theme = '{}' ORDER BY alphabet_item_num ASC".format(theme)
    result = sql_cmd(sql)
    theme_list = ''
    for idx, name in enumerate(result):
        theme_list = theme_list + "{}.{} {}\n".format(idx+1, name[0], name[1])
    splited_theme_list = theme_list.split('\n')
    splited_theme_list_count = len(splited_theme_list)
    if splited_theme_list_count > 40:
        bot.send_message(message.chat.id, 'Выберите стих:')
        count = 0
        start = 0
        stop = 40
        while splited_theme_list_count > 40:
            count += 1
            splited_theme_list_count -= 40
            bot.send_message(message.chat.id, '\n'.join(splited_theme_list[start:stop]))
            start = stop
            stop += 40
        bot.send_message(message.chat.id, '\n'.join(splited_theme_list[start:]))
    else:
        bot.send_message(message.chat.id, 'Выберите стих:\n' + theme_list)


def send_letter_list(message, letter):
    sql = r"SELECT name, link FROM asadov WHERE link LIKE '%\_{}\_%' ORDER BY alphabet_item_num ASC".format(letter)
    result = sql_cmd(sql)
    letter_list = ''
    for idx, name in enumerate(result):
        letter_list = letter_list + "{}.{} {}\n".format(idx + 1, name[0], name[1])
    bot.send_message(message.chat.id, 'Выберите стих:\n' + letter_list)


@bot.message_handler(commands=['start'])
def handle_start(message):
    sql = 'SELECT count(link) FROM asadov'
    poem_count = sql_cmd(sql)[0][0]
    user_markup = telebot.types.ReplyKeyboardMarkup(True, True)
    user_markup.row('Случайные', 'По Алфавиту')
    user_markup.row('По Теме', 'По Фразе')
    line1 = 'Привет!\nЯ умею искать и отправлять стихи Эдуарда Асадова.\n'
    line2 = 'Стихов в базе {}.\n'.format(str(poem_count))
    line3 = 'Стихи можно искать по фразе, по алфавиту, по теме или получить случайный стих.\n'
    line4 = 'Любой стих можно добавить в избранное для быстрого доступа.'
    msg = line1+line2+line3+line4
    bot.send_message(message.from_user.id, msg, reply_markup=user_markup)


@bot.message_handler(commands=['favorite'])
def handle_favorite(message):
    show_fav_list_to_user(str(message.chat.id))


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if PATTERN_PLUS_FAV.match(call.data) is not None:
        link = call.data.split('::')
        result = add_to_fav_db(str(call.message.chat.id), link[1])
        if result == 'Добавил в избранное: ':
            bot.send_message(call.message.chat.id, result + link[1])
        else:
            bot.send_message(call.message.chat.id, result)
    if PATTERN_MINUS_FAV.match(call.data) is not None:
        link = call.data.split('::')
        result = remove_from_fav_db(str(call.message.chat.id), link[1])
        if result == 'Нечего удалять':
            bot.send_message(call.message.chat.id, result)
        else:
            bot.send_message(call.message.chat.id, result + link[1])
    if call.data == 'show':
        show_fav_list_to_user(str(call.message.chat.id))
    if call.data == 'clear':
        result = clear_fav_list(str(call.message.chat.id))
        bot.send_message(call.message.chat.id, result)


@bot.message_handler(content_types=['text'])
def handle_command(message):
    if PATTERN_SHOW_MSG.match(message.text) is not None:
        send_poem(message, message.text)
    elif message.text == 'По Фразе':
        msg = bot.send_message(message.chat.id, 'Введите фразу для поиска')
        bot.register_next_step_handler(msg, search_by_phrase)
    else:
        markup = markup_dict.get(message.text)
        rand = dict_of_themes.get(message.text)
        theme = dict_of_theme_links.get(message.text)
        letter = dict_of_letters.get(message.text)
        if callable(markup):
            markup(message)
        elif rand:
            send_poem(message, random_poem(rand))
        elif theme:
            send_theme_list(message, theme)
        elif letter:
            send_letter_list(message, letter)
        else:
            bot.send_message(message.chat.id, 'Выберите из меню')
            
            
@bot.message_handler(content_types=['document'])
def handle_docs(message):
	if message.chat.id == 109964287:
		try:
			file_info = bot.get_file(message.document.file_id)
			file = bot.download_file(file_info.file_path)
			poem = file.decode('utf-8').split('\r\n')
			link = poem[0]
			item_num = int(poem[1])
			theme = poem[2]
			name = poem[3]
			poem.remove(name)
			poem.remove(link)
			poem.remove(str(item_num))
			poem.remove(theme)
			body = '\n'.join(poem)
			fav = 'x,x'
			sql = "INSERT INTO asadov values ({0}, '{1}', '{2}', '{3}', '{4}', '{5}')".format(
        item_num, link, name, body, theme, fav)
			sql_cmd(sql)
			bot.send_message(message.chat.id, 'Новый стих добавлен')
		except Exception as e:
			bot.send_message(message.chat.id, 'Ошибка в файле')
    else:
        bot.send_message(message.chat.id, 'Выберите из меню, я не принимаю файлы')


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as err:
            print(err)
            time.sleep(5)
