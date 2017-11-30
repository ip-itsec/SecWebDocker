import random
import string

from flask import Flask, request, session, url_for, redirect, render_template
from db_handler import DB_Handler
from flaskext.mysql import MySQL
import json
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["MYSQL_DATABASE_USER"] = "db_admin_tralala"
app.config["MYSQL_DATABASE_PASSWORD"] = "tr4l4l4_mysql_db."
app.config["MYSQL_DATABASE_DB"] = "tralala"
app.config["MYSQL_DATABASE_HOST"] = "localhost"

mysql = MySQL()
mysql.init_app(app)


@app.route("/")
def index():
    """
    Startseite
    Hier muss ebenfalls die Darstellung aller Posts aus der DB behandelt werden
    """

    db_handler = DB_Handler()
    (code, data) = db_handler.get_all_posts(mysql)

    if code == -1:
        return render_template("index.html", error_message="Keine Posts gefunden!")

    colors = ["red", "blue", "green", "yellow"]

    post_list = []

    for row in data:
        color_key = random.randint(0, 3)
        upvotes = int(row[5])
        downvotes = -int(row[6])  # Vorzeichenwechsel
        total_votes = upvotes + downvotes

        html_trans = ""
        html_trans += "<div class=\"" + colors[color_key] + "\">"
        html_trans += "<div id=\"usr\">" + str(row[1]) + " | " + str(
            row[2]) + " | <b>Votes: " + str(total_votes) + "</b></div>"
        html_trans += "<p>" + row[3] + "<p>"
        html_trans += "</br></br>"
        html_trans += "<div><b>" + row[4] + "</b>&nbsp;&nbsp;&nbsp;"
        html_trans += "<a class=\"post_vote_up\" href=\"" + url_for("vote") + "?method=upvote&post_id=" + str(
            row[0]) + "\">+</a>&nbsp;&nbsp;&nbsp;"
        html_trans += "<a class=\"post_vote_down\" href=\"" + url_for("vote") + "?method=downvote&post_id=" + str(
            row[0]) + "\">-</a>&nbsp;&nbsp;&nbsp;</div>"
        html_trans += "</div>"
        post_list.append(html_trans)

    return render_template("index.html", post_list=post_list)


@app.route("/login", methods=["POST", "GET"])
def login():
    """
    tbd
    """
    # Falls bereits eingeloggt
    try:
        session["logged_in"]
        return render_template("Du bist bereits eingeloggt!")
    except:
        pass

    # Hole Daten aus Loginform
    if request.method == "GET":
        return_info = {}
        return_info["invalid_method"] = "GET"

        return prepare_info_json(url_for("post_user"), "GET ist unzulässig für den Login", return_info)

    login_email = request.form["login_email"]
    login_password = request.form["login_password"]

    if login_email == "" or login_password == "":
        return prepare_info_json(url_for("post_user"), "Es wurden Felder beim Login leergelassen")

    # Hashe Passwort
    login_password_hashed = generate_password_hash(login_password)

    # Suche nach User in DB
    db_handler = DB_Handler()
    (code, data) = db_handler.check_for_existence(mysql, login_email)
    if code == -1:
        return render_template("quick_info.html", info_text="Passwort und/oder Benutzername sind inkorrekt!")
    app.logger.debug("user found=" + data["email"] + ":" + data["password"])

    # Überprüfe gehashte Passwörter
    if not check_password_hash(data["password"], login_password):
        return render_template("quick_info.html", info_text="Benutzername und/oder Passwort sind inkorrekt!")
    else:
        # Setze Sessionvariable
        session["logged_in"] = True
        session["user"] = login_email
        session["uid"] = data["uid"]
        session["role_id"] = data["role_id"]
        return render_template("quick_info.html",
                               info_text="Du wurdest eingeloggt. Willkommen zurück, " + login_email)


@app.route("/logout", methods=["POST", "GET"])
def logout():
    """
    tbd
    """
    try:
        # Zugriff auf die Session Variable wirft einen KeyError. Durch den Catch wird das Template gerendert
        session["logged_in"]
    except:
        return render_template("quick_info.html", info_text="Du bist nicht eingeloggt!")

    session.pop("logged_in", None)
    session.pop("user", None)
    return render_template("quick_info.html", info_text="Du wurdest erfolgreich ausgeloggt!")


@app.route("/signup/post_user", methods=["POST", "GET"])
def post_user():
    """
    Überprüfe die Eingaben des Benutzers unabhängig von der clientseitigen Überprüfung.
    Sollten alle Eingaben korrekt sein, persistiere das neue Benutzerkonto in der Datenbank und schicke
    eine Bestätigungsemail an die angegebene Email.
    :return:
    """
    try:
        session["logged_in"]  # Falls der User bereits eingeloggt ist, soll er auf die Startseite weitergeleitet werden
        return redirect(url_for("index"))
    except:
        pass

    if request.method == "GET":
        return_info = {}
        return_info["invalid_method"] = "GET"

        return prepare_info_json(url_for("post_user"), "GET ist unzulässig für die Registration", return_info)

    else:
        reg_email = request.form["reg_email"]
        reg_password = request.form["reg_password"]
        reg_password_repeat = request.form["reg_password_repeat"]

        if reg_email == "" or reg_password == "" or reg_password_repeat == "":  # Reicht es, das allein durch JavaScript zu überprüfen?
            return prepare_info_json(url_for("post_user"), "Es wurden Fehler bei der Registrierung leer gelassen")

        # Hier überprüfen und ggf. sanitizen

        # Überprüfe, ob Password und Passwordwiederholung übereinstimmen
        if not reg_password == reg_password_repeat:
            app.logger.error("Passwort wurde nicht korrekt wiederholt")
            return render_template("registration_no_success.html", code=2)

        # Überprüfe, ob User schon existiert
        success = register_new_account(mysql, reg_email, generate_password_hash(reg_password),
                                       generate_verification_token(50))
        if success == -1:
            app.logger.error("Neuer Benutzer konnte nicht in die Datenbank geschrieben werden. Versuche es erneut")
            return render_template("registration_no_success.html", code=-1)
        elif success == 0:
            app.logger.error("Benutzer existiert bereits")
            return render_template("registration_no_success.html", code=0, reg_email=reg_email)

        app.logger.debug("Registrierung war erfolgreich. Benutzer wurde in die DB geschrieben (und Verification Token)")
        success = send_verification_email(reg_email)

        if success == -1:
            return render_template("registration_no_success.html", code=3, reg_email=reg_email)

        return render_template("registration_success.html", reg_email=reg_email)


@app.route("/admin/dashboard")
def admin_dashboard():
    """
    tbd
    """
    # Benutzerdaten holen
    db_handler = DB_Handler()
    (code, data) = db_handler.get_all_users(mysql)

    if not code == 1:
        return render_template("admin.html",
                               error="Admin Dashboard konnte nicht geladen werden. Versuche es später noch einmal.")

    admin_table = ""
    admin_table += "<table>"
    admin_table += "<tr>" \
                   "<th>ID</th>" \
                   "<th>E-Mail</th>" \
                   "<th>Benutzer löschen</th>" \
                   "<th>Rolle ändern</th>" \
                   "</tr>"

    for row in data:
        admin_table += "<tr>"
        admin_table += "<td>" + str(row[1]) + "</td>"
        admin_table += "<td>" + str(row[0]) + "</td>"
        admin_table += "<td>" + "Benutzer löschen" + "</td>"
        admin_table += "<td>" + "Rolle ändern" + "</td>"
        admin_table += "</tr>"

    admin_table += "</table>"

    return render_template("admin.html", dashboard=admin_table)

    # In Dashboard eintragen


    return render_template("admin.html")


"""
    
    <tr>
        <th>ID</th>
        <th>E-Mail</th>
        <th>Benutzer löschen</th>
        <th>Rolle ändern</th>
    </tr>
    
    <tr>
        <th>ID</th>
        <th>Username</th>
        <th>E-Mail</th>
        <th>PWD Reset</th>
        <th>User L&ouml;schen</th>
        <th>Make Admin</th>
    </tr>

"""


@app.route("/confirm")
def confirm():
    """
    tbd
    """
    # Suche nach Email basierend auf Token
    token = request.args.get("token")

    db_handler = DB_Handler()
    (success, email) = db_handler.get_user_for_token(mysql, token)
    if success == -1:
        app.logger.error("Es konnte kein User for das Token '" + token + "' zurückgeliefert werden (ungültiges Token)")
        return render_template("quick_info.html", info_text="Der Benutzer konnte nicht bestätigt werden!")
    if success == 2:
        app.logger.debug("Benutzer ist bereits bestätigt!")
        return render_template("quick_info.html", info_text="Der Benutzer wurde bereits bestätigt!")
    if success == 1:
        app.logger.debug("Account bestätigt für Benutzer '" + email + "' für Token '" + token + "'")

    # Setze Token auf Defaultwert und setze verified auf 1
    success = db_handler.user_successful_verify(mysql, email)

    if success == -1:
        app.logger.error("User konnte nicht bestätigt werden (Benutzer konnte in der DB nicht bestätigt werden)")
        return render_template("quick_info.html", info_text="Der Benutzer konnte nicht bestätigt werden!")
    if success == 1:
        app.logger.debug("User wurde bestätigt")
        return render_template("quick_info.html",
                               info_text="Der Benutzer wurde erfolgreich bestätigt. Du kannst dich nun einloggen.")


@app.route("/post_message", methods=["POST", "GET"])
def post_message():
    try:
        session["logged_in"]  # Nur eingeloggte Benutzer dürfen Nachrichten posten
    except:
        return render_template("quick_info.html", info_text="Du musst eingeloggt sein, um eine Nachricht zu posten!")

    # Post sanitizen
    message = request.form["post_message"]
    hashtags = request.form["post_hashtags"]

    if message == "":
        return render_template("quick_info.html",
                               info_text="Leider konnte deine Nachricht nicht gepostet werden, da du keine Nachricht angegeben hast. Versuche es bitte erneut!")

    # Post in DB schreiben
    db_handler = DB_Handler()
    success = db_handler.post_message_to_db(mysql, session["uid"], None, message[:279], hashtags)

    if success == -1:
        return render_template("quick_info.html",
                               info_text="Deine Nachricht konnte nicht geposted werden. Versuche es erneut!")
    elif success == 1:
        return render_template("quick_info.html",
                               info_text="Deine Nachricht wurde geposted. Du kannst sie auf der Postseite nun sehen!")

    return "post message uid=" + str(session["uid"]) + " message=" + message + " hashtags=" + hashtags


@app.route("/vote")
def vote():
    """

    /vote_up?post_id=123
    """
    # Lese GET-Parameter
    method = request.args.get("method")
    post_id = request.args.get("post_id")

    if post_id == "" or method == "":
        return render_template("quick_info.html", info_text="Ungültige Post ID oder Zugriffsmethode!")

    # Hole Post aus DB
    db_handler = DB_Handler()
    (code, data) = db_handler.get_post_by_pid(mysql, post_id)

    if code == -1:
        return render_template("quick_info.html",
                               info_text="Wir konnten leider keinen Post mit der ID " + str(post_id) + " finden!")

    method_labels = {"upvote": "Upvote", "downvote": "Downvote"}
    csrf_seq = generate_verification_token(8)

    # Gebe Seite mit vollständigem Post zurück
    # Präsentiere zufällige Zeichenfolge, die eingegeben werden muss, um CSRF-Attacken zu unterbinden
    return render_template("vote.html", post=data, csrf_seq=csrf_seq, method=method,
                           method_label=method_labels[method])


@app.route("/finish_vote", methods=["GET", "POST"])
def finish_vote():
    """
    tbd
    """
    # Hole GET-Parameter
    csrf_token = request.args.get("csrf_token")
    post_id = request.args.get("post_id")
    method = request.args.get("method")
    input_csrf = request.form["vote_code"]

    try:
        post_id_int = int(post_id)
    except:
        return render_template("quick_info.html", info_text="Deine Anfrage war ungültig. Bitte versuche es erneut!")

    if input_csrf == "" or csrf_token == "" or post_id == "" or post_id_int < 0 or not method in ["upvote", "downvote"]:
        return render_template("quick_info.html", info_text="Deine Anfrage war ungültig. Bitte versuche es erneut!")
    # Überprüfe csrf_seq
    if not csrf_token == input_csrf:
        return render_template("quick_info.html",
                               info_text="Der eingegebene Code war leider falsch. Bitte versuche es erneut!")

    # Persistiere Vote
    db_handler = DB_Handler()

    if method == "upvote":
        success = db_handler.do_upvote(mysql, post_id)
        if success == -1:
            return render_template("quick_info.html", info_text="Etwas ist schiefgelaufen! Versuche es erneut!")
        return render_template("quick_info.html", info_text="Upvote erfolgreich!")

    elif method == "downvote":
        success = db_handler.do_downvote(mysql, post_id)
        if success == -1:
            return render_template("quick_info.html", info_text="Etwas ist schiefgelaufen! Versuche es erneut!")
        return render_template("quick_info.html", info_text="Downvote erfolgreich!")


"""
Hilfsfunktionen, die keine HTTP Requests bearbeiten
"""


def generate_verification_token(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def send_verification_email(reg_email):
    """
        Sende Bestätigungsmail mit Verification Token.
    """

    app.logger.debug("Sende Bestätigungsmail.")

    # Hole Verification Token aus der DB
    db_handler = DB_Handler()
    (success, token) = db_handler.get_token_for_user(mysql, reg_email)

    if success == -1:
        return -1

    # Sende Bestätigungsemail mit Token
    sender = "verification_tralala@gmx.de"
    password = "sichwebapp_2017"

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = reg_email
    msg["Subject"] = "Bestätige deinen Account bei Tralala!"

    msg.attach(MIMEText(u"Hallo " + reg_email + "!</br>" \
                                                "Benutze den folgenden Link, um deinen Account zu bestaetigen. Du musst diesen in die Adresszeile deines Browsers kopieren.</br></br>" \
                                                "<a href=\"localhost:5000" + url_for(
        "confirm") + "?token=" + token + "\">" + "localhost:5000" + url_for(
        "confirm") + "?token=" + token + "</a>",
                        "html"))

    try:
        server = smtplib.SMTP("mail.gmx.net", 587)
        server.starttls()
        server.login(sender, password)

        server.sendmail(sender, reg_email, msg.as_string())
        server.quit()
    except Exception as e:
        app.logger.error("Fehler beim Senden der Bestätigungsmail...\n" + str(e))
        return -1

    app.logger.debug("Bestätigungsemail gesendet an '" + reg_email + "' ...")
    return 1


def prepare_info_json(affected_url, info_text, additions):
    """
        Gebe eine Info- bzw. Fehlermeldung im JSON-Format zurück.
        Dictionary akzeptiert keine additions, falls folgende Keys in den additions existieren:
            1. called_url
            2. timestamp
            3. info_text
        Durch eine Exception wird der dict merge abgebrochen
    """

    return_info = {}
    return_info["info_text"] = info_text
    return_info["called_url"] = str(affected_url)
    return_info["timestamp"] = str(time.ctime())

    copy = return_info.copy()

    try:
        return_info.update(additions)
    except:
        return json.dumps(copy, indent=4)

    return json.dumps(return_info, indent=4)


"""
    Zugriff auf die DB mit der DB_Handler Klasse
"""


def register_new_account(mysql, email, pw_hash, verification_token):
    db_handler = DB_Handler()
    success = db_handler.add_new_user(mysql, email, pw_hash, verification_token)

    return success


if __name__ == '__main__':
    app.secret_key = "e5ac358c-f0bf-11e5-9e39-d3b532c10a28"  # Wichtig für Sessions, da Cookies durch diesen Key signiert sind!
    app.run(debug=True)
