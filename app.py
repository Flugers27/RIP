from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'home'

# Модель пользователя
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)  # Полное имя
    death_certificate = db.Column(db.String(50), unique=True, nullable=False)  # Логин
    password = db.Column(db.String(150), nullable=False)  # Пароль


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Маршруты
@app.route('/')
def home():
    return render_template('home.html', show_login_form=not current_user.is_authenticated)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        death_certificate = request.form.get('death_certificate')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not full_name or not death_certificate or not password or not confirm_password:
            flash('Все поля обязательны для заполнения.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Пароли не совпадают.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(death_certificate=death_certificate).first():
            flash('Пользователь с таким номером свидетельства о смерти уже зарегистрирован.', 'danger')
            return redirect(url_for('register'))

        # Используем pbkdf2:sha256 для хэширования
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        new_user = User(full_name=full_name, death_certificate=death_certificate, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Авторизация нового пользователя
        login_user(new_user)
        flash('Вы успешно зарегистрировались.', 'success')
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['POST'])
def login():
    death_certificate = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(death_certificate=death_certificate).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        flash('Вы успешно вошли в систему.', 'success')
        return redirect(url_for('home'))

    flash('Неправильный номер свидетельства о смерти или пароль.', 'danger')
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():  # Создание контекста приложения
        db.create_all()      # Создаем таблицы в базе данных
    app.run(debug=True)
