from backend import *
from flask import Flask, request, render_template, url_for, redirect
from flask_admin.contrib import sqla
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, ForeignKey
import os.path
from flask_admin import Admin
from flask_login import LoginManager, UserMixin, current_user, login_user, login_required, logout_user
from flask_admin.contrib.sqla import ModelView

db.create_all()
db.session.commit()

