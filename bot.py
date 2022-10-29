from libraries.sql import *

# from libraries.utils import *
from libraries.ssau_parser import *
import datetime
import re
from time import sleep
from itertools import groupby
import telegram
import logging

logger = logging.getLogger('bot')

first_week = 34


class Bot:

    group_num_format = re.compile('\d{4}')

    def __init__(self, token: str, db: L9LK, shedule: Shedule_DB):
        self.l9lk = db
        self.users_id = {}
        self.users_db = {}
        self.shedule = shedule
        self.tg = telegram.Bot(token)
        self.udpate_id = None

    def confirmKeyboard(self) -> telegram.InlineKeyboardMarkup:
        """Yes/no keyboard"""
        buttons = [
            [
                telegram.InlineKeyboardButton("Да", callback_data="yes"),
                telegram.InlineKeyboardButton("Нет", callback_data="no"),
            ]
        ]
        return telegram.InlineKeyboardMarkup(buttons)

    def cancelKeyboard(self) -> telegram.InlineKeyboardMarkup:
        """Cancel keyboard"""
        buttons = [
            [telegram.InlineKeyboardButton("Отмена", callback_data="cancel")]
        ]
        return telegram.InlineKeyboardMarkup(buttons)

    def classicKeyboard(self, now=None) -> telegram.InlineKeyboardMarkup:
        """Create a main bot keyboard

        Args:
            :now: :class:`str` key to hide
        """
        keys = {
            "near": "Ближайшая пара",
            "next": "Следующая пара",
            "tday": "Расписание на сегодня",
        }

        if now == None:
            buttons = [
                [
                    telegram.InlineKeyboardButton(
                        "Ближайшая пара", callback_data="near"
                    ),
                    telegram.InlineKeyboardButton(
                        "Следующая пара", callback_data="next"
                    ),
                ],
                [
                    telegram.InlineKeyboardButton(
                        "Расписание на сегодня", callback_data="tday"
                    ),
                ],
            ]

        else:
            keys.pop(now)
            buttons = [
                [
                    telegram.InlineKeyboardButton(keys[i], callback_data=i)
                    for i in keys
                ]
            ]

        return telegram.InlineKeyboardMarkup(buttons)

    def mainMenu(self, query: telegram.CallbackQuery) -> None:
        """Main menu handle (near, next and day lessons)"""
        _, l9Id = self.getTag(query)
        key = self.classicKeyboard(query.data)
        if query.data == 'near':
            answer = self.nearLesson(l9Id)

        elif query.data == 'next':
            answer = self.nextLesson(l9Id)

        elif query.data == 'tday':
            answer = self.dayShedule(l9Id)
            
        query.edit_message_text(answer, reply_markup=key)

        query.answer()

    def start(self, query: telegram.Message):
        """New users handle"""
        count = len(self.l9lk.db.get(L9LK.users_table, None, ['l9Id']))
        uid = query.from_user.id

        if count >= config['limit']:
            self.tg.sendMessage(
                uid,
                (
                    'Бот работает в тестовом режиме, поэтому количество пользователей временно ограничено.\n'
                    'К сожалению, в данный момент лимит превышен, поэтому доступ для вас закрыт 😢'
                    'Попробуйте зайти на следующей неделе, когда лимит будет повышен'
                ),
            )

        else:
            self.changeTag(uid, 'started')
            self.tg.sendMessage(
                uid,
                (
                    'Привет! Я твой новый помощник, который подскажет тебе, какая сейчас пара, '
                    'и будет напоминать о занятиях, чтобы ты ничего не упустил 🤗\n'
                    'Давай знакомиться! Введи свой номер группы (первые четыре цифры)'
                ),
            )

    def addGroup(self, l9Id: int, query: telegram.Message):
        """Appending group handle"""
        groupName = query.text
        uid = query.from_user.id

        if Bot.group_num_format.match(groupName) is None:
            self.tg.sendMessage(
                uid,
                '❗️Группа введена неверно',
                reply_markup=self.cancelKeyboard(),
            )

        else:
            result = self.l9lk.db.get(
                Shedule_DB.groups_table,
                f'groupNumber = {groupName}',
                ['groupId', 'specName'],
            )

            if result != []:
                result = result[0]
                exists = self.l9lk.db.get(
                    Shedule_DB.gu_table,
                    f'l9Id = {l9Id} AND groupId = {result[0]}',
                )
                if exists == []:
                    self.l9lk.db.insert(
                        Shedule_DB.gu_table,
                        {'l9Id': l9Id, 'groupId': result[0]},
                    )
                    self.changeTag(uid, 'ready')
                    self.tg.sendMessage(
                        uid,
                        f'Поздравляем, твоя группа {groupName}, направление "{result[1]}", подключена!',
                    )

                else:
                    self.tg.sendMessage(
                        uid,
                        '❗️Эта группа у тебя уже подключена',
                        reply_markup=self.cancelKeyboard(),
                    )

            else:
                group = findInRasp(groupName)
                if group != None:
                    group_url = f'ssau.ru/{group["url"][2:]}'
                    gr_num = group["text"]
                    groupId = group["id"]

                    self.changeTag(uid, f'conf_{groupName}_{groupId}')
                    self.tg.sendMessage(
                        uid,
                        (
                            'Такой группы у меня пока нет в базе, но она есть на сайте\n'
                            f'{group_url}\n'
                            'Проверь, пожалуйста, что это твоя группа и нажми кнопку\n'
                        ),
                        reply_markup=self.confirmKeyboard(),
                    )

                else:
                    self.tg.sendMessage(
                        uid,
                        'К сожалению, такой группы нет ни в моей базе, ни на сайте университета :(',
                        reply_markup=self.cancelKeyboard(),
                    )

    def checkMessages(self):
        """Check and handle new messages and action"""
        for update in self.tg.get_updates(offset=self.udpate_id, timeout=10):
            self.udpate_id = update.update_id + 1

            if update.callback_query:
                query = update.callback_query
                tag, l9Id = self.getTag(query)
                if query.data == 'cancel':
                    groups = self.l9lk.db.get(
                        Shedule_DB.gu_table,
                        f'l9Id = {l9Id}',
                    )
                    had_groups = len(groups) != 0
                    self.changeTag(
                        query.from_user.id,
                        'ready' if had_groups else 'started',
                    )
                    query.answer(
                        'Действие отменено'
                        if had_groups
                        else 'Внимание, требуется ввести хотя бы одну группу!',
                        not had_groups,
                    )
                    query.delete_message()
                elif tag.find('conf') != -1:
                    query.answer()
                    if query.data == 'yes':
                        query.edit_message_text('Загружаю расписание...')

                        _, groupName, groupId = tag.split('_')
                        now_week = datetime.datetime.now()
                        self.loadShedule(groupId, now_week)

                        self.l9lk.db.insert(
                            Shedule_DB.gu_table,
                            {'l9Id': l9Id, 'groupId': groupId},
                        )

                        self.changeTag(query.from_user.id, 'ready')
                        query.edit_message_text(
                            'Поздравляю, твоя группа загружена в мою базу данных! Теперь ты можешь пользоваться всем функционалом бота, подробнее в справке /help'
                        )

                    else:
                        query.edit_message_text(
                            'Возможно, ты написал не ту группу, попробуй снова'
                        )
                        query.edit_message_reply_markup(
                            self.cancelKeyboard()
                        )
                        self.changeTag(query.from_user.id, 'started')
                else:
                    self.mainMenu(query)

            if update.message:
                query = update.message
                tag, l9Id = self.getTag(query)
                uid = query.from_user.id
                if tag == 'not_started':
                    self.start(query)

                elif tag == 'started':
                    self.addGroup(l9Id, query)

                else:
                    self.tg.sendMessage(
                        uid,
                        "Нажми на кнопку - получишь результат!",
                        reply_markup=self.classicKeyboard(),
                    )
        # Yay, it's bad, but comment this is worse
        if True:
            return None

        elif tag == 'ready':
            if text == 'Ближайшая пара':
                return [self.nearLesson(l9Id)]
            elif text == 'Следующая пара':
                return [self.nextLesson(l9Id)]
            elif text == 'Расписание на сегодня':
                return [self.dayShedule(l9Id)]
            elif text[0] == '/':
                text = text.split(" ")
                cmd = text[0]
                arg = text[1:] if len(text) > 1 else None
                if cmd == '/help':
                    return [
                        open('libraries/help.txt', encoding='utf-8').read()
                    ]
                if cmd == '/first_time':
                    if arg == None:
                        self.changeTag(uid, 'first_time')
                        return [
                            "Введи время в минутах, за которое тебе нужно сообщать о начале первой пары (от 20 до 240)"
                        ]
                    else:
                        return [self.changeFirstTime(l9Id, arg[0])]
                if cmd == '/add':
                    groups_count = len(
                        self.l9lk.db.get(
                            Shedule_DB.gu_table, f'l9Id = {l9Id}'
                        )
                    )
                    if groups_count >= 2:
                        return [
                            "Ты уже подключен к двум группам, больше нельзя. Введи команду /del, чтобы удалить ненужную группу"
                        ]
                    else:
                        if arg == None:
                            self.changeTag(uid, 'add')
                            return [
                                "Введи номер новой группы в краткой форме (например, 2305)"
                            ]
                        else:
                            return self.addGroup(l9Id, arg[0])

                if cmd == '/del':
                    groups_count = len(
                        self.l9lk.db.get(
                            Shedule_DB.gu_table, f'l9Id = {l9Id}'
                        )
                    )
                    if groups_count == 0:
                        return [
                            "Ты пока не подключен ни к одной группе. Введи команду /add, чтобы подключить новую группу"
                        ]
                    else:
                        if arg == None:
                            self.changeTag(uid, 'del')
                            return [
                                "Введи номер группы, которую хочешь удалить, в краткой форме (например, 2305)"
                            ]
                        else:
                            return [self.delGroup(l9Id, arg[0])]

                if str(uid) == config["tg"]["admin"]:
                    if cmd == "/mail":
                        self.groupMailing(tg_bot, arg[0], " ".join(arg[1:]))
                        return [f"Сообщения отправлены {arg[0]}"]

                    if cmd == "/scream":
                        users = self.l9lk.db.get(
                            TG_DB.users_table, 'tgId != 0', ['tgId']
                        )
                        for user in users:
                            tg_bot.sendMessage(user[0], " ".join(arg))
                        return ["Сообщения отправлены"]

            return ['Aй!']
        # Commands
        elif text == '/cancel':
            self.changeTag(uid, 'ready')
            return ['Возврат в главное меню']

        elif tag == 'first_time':
            ans = self.changeFirstTime(l9Id, text)
            if ans.find("!") != -1:
                self.changeTag(uid, 'ready')
            return [ans]

        elif tag == 'add':
            ans = self.addGroup(l9Id, text)
            if ans[0].find("!") != -1:
                self.changeTag(uid, 'ready')
            elif ans[0].find("ssau") != -1:
                self.changeTag(uid, f'conf_{text}')
            return ans

        elif tag == 'del':
            ans = self.delGroup(l9Id, text)
            if ans.find("!") != -1:
                self.changeTag(uid, 'ready')
            return [ans]

        else:
            return ['Ой!']

    def loadShedule(self, groupId, date):
        week = date.isocalendar()[1] - first_week

        self.l9lk.db.execute(
            f'DELETE FROM {Shedule_DB.lessons_table} WHERE WEEK(`begin`, 1) = {date.isocalendar()[1]} AND groupId = {groupId};'
        )

        t_info = self.l9lk.db.get(
            Shedule_DB.teachers_table, 'teacherId!=0', teacher_columns
        )
        t_info = [dict(zip(teacher_columns, i)) for i in t_info]
        lessons, teachers = parseWeek(groupId, week, t_info)

        g = getGroupInfo(groupId)
        self.l9lk.db.insert(Shedule_DB.groups_table, g)

        for t in teachers:
            self.l9lk.db.insert(Shedule_DB.teachers_table, t)

        for l in lessons:
            self.l9lk.db.insert(Shedule_DB.lessons_table, l)

    def getTag(self, query):
        uid = query.from_user.id
        name = f'{query.from_user.first_name} {query.from_user.last_name}'

        if uid not in self.users_id:
            l9Id = tg_db.initUser(uid, name)
            self.users_id[uid] = l9Id
        else:
            l9Id = self.users_id[uid]

        tag = self.l9lk.db.get(
            TG_DB.users_table,
            f"tgId = {uid}",
            ["pos_tag"],
        )

        return tag[0][0], l9Id

    def changeFirstTime(self, l9Id, time):
        try:
            time = int(time)
            if time > 240:
                return "Ой, а не слишком ли заранее тебе надо напоминать о парах?)\nНапиши другое время, пожалуйста"
            elif time < 20:
                return "Мне кажется, что я тебе буду слишком поздно напоминать о начале пар, ты просто не успеешь собраться и добежать до универа (ну или проснуться и подключится онлайн)\nНапиши другое время, пожалуйста"
            else:
                self.l9lk.db.update(
                    L9LK.users_table,
                    f"l9Id = {l9Id}",
                    f"first_time = {time}",
                )
                return "Время установлено!"
        except ValueError:
            return "Ой, это не похоже на число ):\nНапоминаю, что тебе нужно ввести время сообщения о начале пар"

    def delGroup(self, l9Id, groupName):
        if Bot.group_num_format.match(groupName) is None:
            return '❗️Группа введена неверно'
        else:
            groupId = self.l9lk.db.get(
                Shedule_DB.groups_table,
                f'groupNumber = {groupName}',
                ['groupId'],
            )

            if groupId != []:
                self.l9lk.db.execute(
                    f"""DELETE FROM l9_lk_test.groups_users WHERE groupId = {groupId[0][0]} AND l9Id = {l9Id};"""
                )
                return "Группа успешно удалена! (если вообще была подключена (;)"
            else:
                return "❗Ошибка: группа не найдена"

    def nearLesson(self, l9Id, retry=0):
        now = datetime.datetime.now()
        groupIds = self.shedule.getGroup(l9Id)
        if groupIds != None:
            for groupId in groupIds:
                lessonIds, _ = self.shedule.nearLesson(l9Id, now, [groupId])
                if groupId[0] > 1000 and (
                    lessonIds == None or lessonIds == []
                ):
                    self.loadShedule(
                        groupId[0], now + datetime.timedelta(days=7)
                    )

        lessonId, date = self.shedule.nearLesson(l9Id, now)
        if lessonId != None:
            lessons = [self.shedule.getLesson(i) for i in lessonId]

            if date.date() > now.date():
                text = f'❗️Сегодня пар нет\nБлижайшая пара '
                if date.date() - now.date() == datetime.timedelta(days=1):
                    text += 'завтра:\n'
                else:
                    text += f'{date.day} {month[date.month-1]}:\n'

            elif date.time() > now.time():
                text = 'Ближайшая пара сегодня:\n'
            else:
                text = 'Текущая пара:\n'

            text += self.strLesson(lessons)

        elif retry < 2:

            if groupIds != None:
                for groupId in groupIds:
                    if groupId[0] > 1000:
                        now += datetime.timedelta(days=7 * retry)
                        self.loadShedule(groupId[0], now)
            return self.nearLesson(l9Id, retry + 1)
        else:
            text = 'Ой! Занятий не обнаружено!\nВозможно, ты не подключен ни к одной группе. Напиши /add, чтобы подключить новую'

        return text

    def nextLesson(self, l9Id):
        now = datetime.datetime.now()
        lessonIds, date = self.shedule.nextLesson(l9Id, now)
        if lessonIds != None:
            lessons = [self.shedule.getLesson(i) for i in lessonIds]

            text = 'Следующая пара после ближайшей или текущей:\n'
            text += self.strLesson(lessons)

        else:
            text = f'Сегодня пар больше не будет'

        return text

    def sortDayShedule(self, lessonIds):
        lessons = [self.shedule.getLesson(lid) for lid in lessonIds]

        l = [
            list(day)
            for date, day in groupby(lessons, key=lambda d: d['numInDay'])
        ]
        text = ''
        for lesson in l:
            text += self.strLesson(lesson) + "-" * 32
        return text

    def dayShedule(self, l9Id, retry=0):
        now = datetime.datetime.now()

        groupIds = self.shedule.getGroup(l9Id)

        if groupIds != None:
            for groupId in groupIds:
                lessonIds, _ = self.shedule.getDay(l9Id, now, [groupId])
                if groupId[0] > 1000 and (
                    lessonIds == None or lessonIds == []
                ):
                    self.loadShedule(
                        groupId[0], now + datetime.timedelta(days=7)
                    )

        lessonIds, date = self.shedule.getDay(l9Id, now)

        if lessonIds != None:
            if now.date() < date.date():
                text = '❗️Сегодня пар нет\nБлижайшие занятия '
                if date.date() - now.date() == datetime.timedelta(days=1):
                    text += 'завтра:\n\n'
                else:
                    text += f'{date.day} {month[date.month-1]}:\n'
            elif now.date() == date.date():
                text = '🗓Расписание на сегодня:\n'

            text += self.sortDayShedule(lessonIds)

        elif retry < 2:
            groupIds = self.shedule.getGroup(l9Id)
            if groupIds != None:
                for groupId in groupIds:
                    if groupId[0] > 1000:
                        now += datetime.timedelta(days=7 * retry)
                        self.loadShedule(groupId[0], now)
            return self.dayShedule(l9Id, retry + 1)
        else:
            text = 'Ой! Занятий не обнаружено!\nВозможно, ты не подключен ни к одной группе. Напиши /add, чтобы подключить новую'

        return text

    def strLesson(self, lesson):
        begin = lesson[0]['begin']
        end = lesson[0]['end']
        text = "\n📆 %02i:%02i - %02i:%02i" % (
            begin.hour,
            begin.minute,
            end.hour,
            end.minute,
        )

        for l in lesson:
            add_info = "" if l['add_info'] == None else "\n" + l['add_info']
            teacher = "" if l['teacher'] == None else "\n👤 " + l['teacher']
            place = "" if l['place'] == None else f"\n🧭 {l['place']}"
            text += f"\n{l['type']} {l['name']}{place}{teacher}{add_info}\n"
        return text

    def changeTag(self, uid: int, tag: str) -> None:
        self.l9lk.db.update(
            TG_DB.users_table, f"tgId = {uid}", f"pos_tag = '{tag}'"
        )

    def checkLesson(self, time):
        groupIds = self.l9lk.db.get(
            Shedule_DB.groups_table, 'groupId > 1000', ['groupId']
        )
        if groupIds != None:
            for groupId in groupIds:
                lessonIds, _ = self.shedule.nearLesson(None, now, [groupId])
                if lessonIds == None or lessonIds == []:
                    self.loadShedule(
                        groupId[0], now + datetime.timedelta(days=7)
                    )

        lessons, first_lessons = self.shedule.checkLesson(time)
        last_lessons = self.shedule.lastLesson(time)

        mailing = {}
        next_day = {}

        for groupId, lesson in lessons:
            text = "❗️ Следующая пара: \n"
            text += self.strLesson(lesson)
            mailing[groupId] = text

        for groupId, lesson in first_lessons:
            text = "❗️ Первая пара: \n"
            text += self.strLesson(lesson)
            mailing[groupId] = text

        for groupId in last_lessons:
            text = "❗️ Сегодня пар больше нет\n"
            next_day[groupId] = text

        next_lessons = self.shedule.checkNextDay(time)
        if next_lessons != []:
            for groupId, day in next_lessons:
                if groupId in next_day:
                    text = 'Следующие занятия завтра:\n'
                    text += self.sortDayShedule([i[0] for i in day])
                    next_day[groupId] += text

        mailing.update(next_day)

        return mailing

    def groupMailing(self, bot, groupId, msg):
        group = self.l9lk.db.get(
            Shedule_DB.gu_table, f'groupId = {groupId}', ['l9Id']
        )
        if group != []:
            for user in group:
                tg_id = self.l9lk.db.get(
                    TG_DB.users_table, f'l9Id = {user[0]}', ['tgId']
                )
                if tg_id != []:
                    bot.sendMessage(tg_id[0][0], msg, tg_bot.keyboard())

    def indMailing(self, bot, tgId):
        pass

    def firstMailing(self, bot, time):
        self.shedule.firstTimeCheck(time)
        str_time = time.isoformat(sep=' ')

        mail = self.l9lk.db.execute(
            f"""
							SELECT tgId, lessonId, u.first_time FROM first_mail AS fm 
							JOIN l9_users AS u ON fm.l9Id = u.l9Id
							JOIN tg_bot AS t ON t.l9Id = fm.l9Id
							WHERE fm.mailTime = '{str_time}';"""
        ).fetchall()
        if time.hour < 11:
            head = "Доброе утро 🌅\n"
        elif time.hour >= 11 and time.hour < 16:
            head = "Добрый день ☀️\n"
        else:
            head = "Добрый вечер 🌃\n"
        if mail != []:
            mail = [
                list(day) for date, day in groupby(mail, key=lambda d: d[0])
            ]
            for user in mail:
                mn = user[0][2] % 10
                end = ""
                if mn == 1:
                    end = "у"
                elif mn > 1 and mn < 5:
                    end = "ы"
                text = f"{head}Через {user[0][2]} минут{end} начнутся занятия\n\nПервая пара:\n"
                text += self.strLesson(
                    [self.shedule.getLesson(a[1]) for a in user]
                )
                bot.sendMessage(user[0][0], text, tg_bot.keyboard())

    def nextDay(self, bot, time):
        lessons = self.shedule.checkNextDay(time)

        if lessons != []:
            for group, day in lessons:
                text = "❗️ Внимание!\nЗавтра будут занятия:\n\n"
                for lid in day:
                    lesson = self.shedule.getLesson(lid[0])
                    text += self.strLesson(lesson) + "\n\n"
                self.groupMailing(bot, group, text)


if __name__ == "__main__":
    initLogger(logger)
    logger.info("Restart bot")

    config = loadJSON("config")
    l9lk = L9LK(config['sql'])
    tg_db = TG_DB(l9lk)
    sh_db = Shedule_DB(l9lk)
    bot = Bot(config['tg']['token'], l9lk, sh_db)

    timer = datetime.datetime(2022, 1, 1)

    logger.info("Bot ready!")

    while True:
        msgs = bot.checkMessages()
        """
        if isinstance(msgs, list):
            for msg in msgs:
                logger.info("\t".join(msg.values()))
                answer = bot.checkMessage(msg)
                tag, _ = bot.getTag(msg)

                if tag == 'ready':
                    key = tg_bot.keyboard()
                elif tag.find('conf') != -1:
                    key = tg_bot.confirmKeyboard()
                else:
                    key = None
                if isinstance(answer, list):
                    for i in answer:
                        tg_bot.sendMessage(msg['uid'], i, key)

                elif isinstance(answer, Exception):
                    logger.error(answer, exc_info=True)
                else:
                    logger.warning(answer)

        else:
            if isinstance(msgs, str) and msgs == "Flood Stop":
                sleep(5)
            logger.error(msgs, exc_info=True)

        now = datetime.datetime.now()
        if now - timer > datetime.timedelta(minutes=5):
            timer = now.replace(
                minute=now.minute // 5 * 5, second=0, microsecond=0
            )
            logger.debug("check " + now.isoformat())
            # timer = datetime.datetime(2022,10,24,9,35)
            bot.firstMailing(tg_bot, timer)

            mail = bot.checkLesson(timer)
            for groupId, msg in mail.items():
                bot.groupMailing(tg_bot, groupId, msg)

            # if timer.hour == 19 and timer.minute == 00:
            # bot.nextDay(tg_bot, now)
"""
