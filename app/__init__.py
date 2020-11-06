from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
import flask_excel as excel
from telebot import TeleBot


app = Flask(__name__, static_folder='static')
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
bootstrap = Bootstrap(app)
excel.init_excel(app)

telegram_bot = TeleBot(Config.BOT_TOKEN)

from app import routes, models, telegram_bot
