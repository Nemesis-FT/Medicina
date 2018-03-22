from flask import Flask, session, url_for, redirect, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import bcrypt
from datetime import datetime, date, timedelta
import os
import random
import string
import threading
import socket

app = Flask(__name__)
app.secret_key = "sgozzolicaione"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
token = "MODNAO"
indirizzo_nao = '172.18.191.144'


class User(db.Model):
    __tablename__ = 'user'
    uid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    passwd = db.Column(db.LargeBinary, nullable=True)
    level = db.Column(db.Integer, nullable=False)

    def __init__(self, username, passwd, livello):
        self.username = username
        self.passwd = passwd
        self.level = livello

    def __repr__(self):
        return "{}-{}-{}".format(self.uid, self.username, self.passwd)


class Medicina(db.Model):
    __tablename__ = 'medicina'
    mid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    dimensione_scatola = db.Column(db.Integer, nullable=False)
    slot = db.Column(db.Integer)

    def __init__(self, nome, dimensione, slot):
        self.nome = nome
        self.dimensione_scatola = dimensione
        self.slot = slot

    def __repr__(self):
        return "{}-{}-{}".format(self.mid, self.nome, self.slot)


class Prescrizione(db.Model):
    __tablename__ = 'prescrizione'
    pid = db.Column(db.Integer, primary_key=True)
    nonno_id = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    medicina_id = db.Column(db.Integer, db.ForeignKey('medicina.mid'), nullable=False)
    ora = db.Column(db.Time, nullable=False)

    def __init__(self, nonno, medicina, ora):
        self.nonno_id = nonno
        self.medicina_id = medicina
        self.ora = ora

    def __repr__(self):
        return "{}-{}-{}".format(self.nonno_id, self.medicina_id, self.ora)


def login(username, password):
    user = User.query.filter_by(username=username).first()
    try:
        return bcrypt.checkpw(bytes(password, encoding="utf-8"), user.passwd)
    except AttributeError:
        # Se non esiste l'Utente
        return False


def find_user(username):
    return User.query.filter_by(username=username).first()


def controllore():
    conteggiate = []
    while True:
        prescrizioni = Prescrizione.query.join(Medicina).join(User).all()
        for prescrizione in prescrizioni:
            ora = datetime.now()
            if prescrizione.ora.hour == ora.hour and prescrizione.ora.minute == ora.minute and prescrizione not in conteggiate:
                conteggiate.append(prescrizione)
                utente = User.query.get_or_404(prescrizione.nonno_id)
                medicina = Medicina.query.get_or_404(prescrizione.medicina_id)
                if medicina > 0:
                    medicina.dimensione_scatola = medicina.dimensione_scatola-1
                    if indirizzo_nao != "nessuno":
                        addr = (indirizzo_nao, 5000)
                        s = socket.socket()
                        s.connect(addr)
                        stringa = "{};{}".format(utente.username, medicina.slot)
                        stringa = stringa.encode('utf-8')
                        s.send(stringa)
                        s.close()
                        interact_with_gpio(medicina.slot)
            if ora.hour == 0:
                conteggiate = []


def interact_with_gpio(scomparto):
    pass
    #put down here that goddamn code that makes this shit work


@app.route("/")
def page_home():
    if 'username' not in session:
        return redirect(url_for('page_login'))
    else:
        session.pop('username')
        return redirect(url_for('page_login'))


@app.route("/login", methods=['GET', 'POST'])
def page_login():
    if request.method == "GET":
        return render_template("login.htm")
    else:
        if login(request.form['username'], request.form['password']):
            session['username'] = request.form['username']
            return redirect(url_for('page_dashboard'))
        else:
            abort(403)


@app.route("/dashboard", methods=['GET'])
def page_dashboard():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        medicine = Medicina.query.all()
        utente = find_user(session['username'])
        query1 = text(
            "SELECT * FROM prescrizione, medicina, user WHERE prescrizione.nonno_id = user.uid AND prescrizione.medicina_id=medicina.mid")
        prescrizioni = db.session.execute(query1).fetchall()
        return render_template("dashboard.htm", utente=utente, medicine=medicine, prescrizioni=prescrizioni)


@app.route("/utente_list", methods=['GET'])
def page_utente_list():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        entita = User.query.filter_by(level=0).all()
        utente = find_user(session['username'])
        return render_template("user/list.htm", utente=utente, entita=entita)


@app.route("/utente_add", methods=['GET', 'POST'])
def page_utente_add():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            return render_template("user/add.htm", utente=utente)
        else:
            nuovoUtente = User(request.form['username'], bytes("null", encoding="utf-8"), 0)
            db.session.add(nuovoUtente)
            db.session.commit()
            return redirect(url_for('page_utente_list'))


@app.route("/utente_del/<int:uid>", methods=['GET'])
def page_utente_del(uid):
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        user = User.query.get_or_404(uid)
        prescrizioni = Prescrizione.query.filter_by(nonno_id=uid).all()
        for prescrizione in prescrizioni:
            db.session.delete(prescrizione)
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('page_utente_list'))


@app.route("/medicina_add", methods=['GET', 'POST'])
def page_medicina_add():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            return render_template("medicina/add.htm", utente=utente)
        else:
            nuovaMedicina = Medicina(request.form['nome'], request.form['numerop'], request.form['slot'])
            db.session.add(nuovaMedicina)
            db.session.commit()
            return redirect(url_for('page_dashboard'))


@app.route("/medicina_ricarica/<int:mid>", methods=['GET', 'POST'])
def page_medicina_ricarica(mid):
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            return render_template("medicina/ricarica.htm", utente=utente, mid=mid)
        else:
            medicina = Medicina.query.get_or_404(mid)
            medicina.dimensione_scatola = request.form['valore']
            db.session.commit()
            return redirect(url_for('page_dashboard'))


@app.route("/medicina_del/<int:mid>", methods=['GET'])
def page_medicina_del(mid):
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        medicina = Medicina.query.get_or_404(mid)
        prescrizioni = Prescrizione.query.filter_by(medicina_id=mid).all()
        for prescrizione in prescrizioni:
            db.session.delete(prescrizione)
        db.session.delete(medicina)
        db.session.commit()
        return redirect(url_for('page_dashboard'))


@app.route("/prescrizione_add", methods=['GET', 'POST'])
def page_prescrizione_add():
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        if request.method == "GET":
            utente = find_user(session['username'])
            pazienti = User.query.filter_by(level=0).all()
            medicine = Medicina.query.all()
            return render_template("prescrizione/add.htm", utente=utente, pazienti=pazienti, medicine=medicine)
        else:
            ora = datetime.strptime(request.form['ora'], '%H:%M').time()
            nuovaPrescrizione = Prescrizione(request.form['paziente'], request.form['medicina'], ora)
            db.session.add(nuovaPrescrizione)
            db.session.commit()
            return redirect(url_for('page_dashboard'))


@app.route("/prescrizione_del/<int:pid>", methods=['GET'])
def page_prescrizione_delete(pid):
    if 'username' not in session or 'username' is None:
        return redirect(url_for('page_login'))
    else:
        prescrizione = Prescrizione.query.get_or_404(pid)
        db.session.delete(prescrizione)
        db.session.commit()
        return redirect(url_for('page_dashboard'))


# ------------ Api functions under this line ------------

@app.route("/api/recv_pazienti", methods=['POST'])
def page_api_recv_pazienti():
    if request.form['token'] == token:
        msg = "UID;NOME;\n"
        pazienti = User.query.filter_by(level=0).all()
        for paziente in pazienti:
            msg += paziente.uid + ";" + paziente.nome + ";\n"
        return msg
    else:
        return "403 - Accesso Negato"


@app.route("/api/recv_prescrizioni", methods=['POST'])
def page_api_recv_prescrizioni():
    if request.form['token'] == token:
        msg = "PID;NID;NOME;MID;MEDICINA;ORA;\n"
        query1 = text(
            "SELECT * FROM prescrizione, medicina, user WHERE prescrizione.nonno_id = user.uid AND prescrizione.medicina_id=medicina.mid")
        prescrizioni = db.session.execute(query1).fetchall()
        for prescrizione in prescrizioni:
            msg += prescrizione[0] + ";" + prescrizione[1] + prescrizione[9] + ";" + prescrizione[2] + ";" + \
                   prescrizione[5] + ";" + prescrizione[3] + ";\n"
        return msg
    else:
        return "403 - Accesso Negato"


if __name__ == "__main__":
    # Se non esiste il database viene creato
    if not os.path.isfile("db.sqlite"):
        db.create_all()
        p = bytes("password", encoding="utf-8")
        cenere = bcrypt.hashpw(p, bcrypt.gensalt())
        valore = 1
        admin = User("admin@admin.com", cenere, valore)
        db.session.add(admin)
        db.session.commit()
    t = threading.Thread(target=controllore)
    t.start()
    app.run()
