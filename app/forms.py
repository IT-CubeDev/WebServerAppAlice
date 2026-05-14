from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

from app.models import User


class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")


class RegisterForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6, max=128)])
    password2 = PasswordField(
        "Повтор пароля",
        validators=[DataRequired(), EqualTo("password", message="Пароли должны совпадать")],
    )
    submit = SubmitField("Зарегистрироваться")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError("Такой логин уже занят.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Этот email уже используется.")


class NoteForm(FlaskForm):
    title = StringField("Заголовок", validators=[DataRequired(), Length(min=1, max=140)])
    body = TextAreaField("Текст", validators=[DataRequired(), Length(max=20000)])
    tags = StringField(
        "Теги (через запятую)",
        validators=[Optional(), Length(max=200)],
        description="Например: учёба, идеи",
    )
    image = FileField(
        "Картинка (необязательно)",
        validators=[
            Optional(),
            FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Допустимы только изображения."),
            FileSize(max_size=4 * 1024 * 1024, message="Файл не больше 4 МБ."),
        ],
    )
    submit = SubmitField("Сохранить")
