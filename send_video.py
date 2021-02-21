from telebot import TeleBot

bot = TeleBot('token')

vlad_video = open('app/static/py.MOV', 'rb')
caption = 'Приглашение на онлайн мастер-класс. Такой проект вы сможете создать вместе с ProBox. Интересно? Ждем вас сегодня'
#bot.send_video(164898079, vlad_video, caption='Приглашение на онлайн мастер-класс. Такой проект вы сможете создать вместе с ProBox. Интересно? Ждем вас сегодня')

users = []

print('Кол-во пользователей: ', len(users))

sent = 0
failed = 0
for user in users:
    try:
        with open('app/static/py.MOV', 'rb') as vid:
            bot.send_video(user, vid, caption='')
            sent+=1
    except Exception as e:
        print(e)
        failed+=1

print('Видео отправлено кол-ву человек: {}\nУдалили бот кол-во человек: {}'.format(sent, failed))

