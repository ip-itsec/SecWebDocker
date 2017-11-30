from flask import Flask
from flaskext.mysql import MySQL
import time


class DB_Handler:
    db_connection_data = {}
    DB_TABLE_TRALALA_USERS = "tralala_users"
    DB_TABLE_TRALALA_POSTS = "tralala_posts"

    def __init__(self):
        self.db_connection_data = None

    # if db_connection_data == None:
    #     self.db_connection_data["MYSQL_DATABASE_USER"] = "db_admin_tralala"
    #     self.db_connection_data["MYSQL_DATABASE_PASSWORD"] = "tr4l4l4_mysql_db."
    #     self.db_connection_data["MYSQL_DATABASE_DB"] = "tralala"
    #     self.db_connection_data["MYSQL_DATABASE_HOST"] = "localhost"
    #     self.db_connection_data["DB_TABLE_TRALALA_USERS"] = "tralala_users"
    #
    # else:
    #     self.db_connection_data = db_connection_data


    def add_new_user(self, mysql, email, pw_hash, verification_token):
        """
            DB-Verbindung nach jedem Call wieder schließen

            1: User wurde angelegt
            0: User existiert bereits
            -1: User konnte nicht angelegt werden
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        pid = 1  # unverified
        role_id = 3  # unverified
        verified = 0

        record = [pid, email, pw_hash, role_id, verified, verification_token]

        # Überprüfe ob User schon existiert
        cursor.execute("select email from " + self.DB_TABLE_TRALALA_USERS + " where email=\"" + email + "\"")
        data = cursor.fetchone()

        if cursor.rowcount != 0:  # User existiert bereits
            return 0

        # Füge neuen User zur DB
        try:
            cursor.execute(
                "insert into " + self.DB_TABLE_TRALALA_USERS + " (pid, email, password, role_id, verified, verification_token) values (%s,%s,%s,%s,%s,%s)",
                record)
            conn.commit()
            conn.close()
            return 1
        except Exception as e:
            conn.close()
            return -1

    def get_token_for_user(self, mysql, email):
        """
        tbd
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        cursor.execute(
            "select verification_token from " + self.DB_TABLE_TRALALA_USERS + " where email=\"" + email + "\"")
        data = cursor.fetchone()

        if cursor.rowcount == 0:
            conn.close();

            return -1, "no_token"
        else:
            conn.close();
            return 1, data[0]

    def get_user_for_token(self, mysql, token):
        """
        tbd
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        cursor.execute(
            "select email, verified from " + self.DB_TABLE_TRALALA_USERS + " where verification_token=%s", (token,))
        data = cursor.fetchone()

        if cursor.rowcount == 0:
            conn.close();
            return -1, "no_email"
        else:
            if data[1] == 1:  # wenn der Benutzer bereits bestätigt ist (verified=1)
                conn.close();
                return 2, data[0]
            else:
                return 1, data[0]

    def user_successful_verify(self, mysql, email):
        """
        tbd
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE " + self.DB_TABLE_TRALALA_USERS + " SET verified=1, role_id=4 WHERE email=\"" + email + "\"")
            conn.commit();
            conn.close();
            return 1
        except Exception as e:
            print("Error bei user_successful_verify " + str(e))
            conn.close();
            return -1

    def check_for_existence(self, mysql, email):
        """
        tbd
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        cursor.execute(
            "select email, password, uid, role_id from " + self.DB_TABLE_TRALALA_USERS + " where email=%s", (email,))
        data = cursor.fetchone()

        if cursor.rowcount == 0:
            conn.close();
            return -1, "no_user"
        else:
            conn.close();
            return 1, {"email": data[0], "password": data[1], "uid": data[2], "role_id": data[3]}

    def post_message_to_db(self, mysql, uid, email, text, hashtags):
        """
        tbd
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        post_date = time.strftime('%Y-%m-%d %H:%M:%S')
        hashtag_list = ""
        temp = hashtags.strip().split(",")

        for hashtag in temp:
            t = "#" + hashtag
            hashtag_list += " " + t

        record = [uid, post_date, text, hashtag_list, 0, 0]

        try:
            cursor.execute(
                "INSERT INTO " + self.DB_TABLE_TRALALA_POSTS + " (uid, post_date, post_text, hashtags, upvotes, downvotes) VALUES (%s,%s,%s,%s,%s,%s)",
                record)

            conn.commit()
            conn.close()
            return 1
        except Exception as e:
            conn.close()
            return -1

    def get_all_posts(self, mysql):
        """
        tbd
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        # cursor.execute("SELECT * FROM " + self.DB_TABLE_TRALALA_POSTS + " ORDER BY post_id DESC")
        cursor.execute(
            "SELECT tralala_posts.post_id, tralala_users.email, tralala_posts.post_date, tralala_posts.post_text, tralala_posts.hashtags, tralala_posts.upvotes, tralala_posts.downvotes FROM tralala_posts INNER JOIN tralala_users ON tralala_posts.uid = tralala_users.uid ORDER BY post_id DESC")
        data = cursor.fetchall()

        if cursor.rowcount == 0:
            conn.close()
            return -1, "no_posts"
        else:
            conn.close()
            return 1, data

    def get_post_by_pid(self, mysql, post_id):
        conn = mysql.connect()
        cursor = conn.cursor()

        # cursor.execute("SELECT * FROM " + self.DB_TABLE_TRALALA_POSTS + " WHERE post_id=%s", (post_id,))
        cursor.execute(
            "SELECT tralala_posts.post_id, tralala_users.email, tralala_posts.post_date, tralala_posts.post_text, tralala_posts.hashtags, tralala_posts.upvotes, tralala_posts.downvotes FROM tralala_posts INNER JOIN tralala_users ON tralala_posts.uid = tralala_users.uid WHERE post_id=%s",
            (post_id,))
        data = cursor.fetchone()

        if cursor.rowcount == 0:
            conn.close()
            return -1, "no_post"
        else:
            conn.close()
            return 1, data

    def do_upvote(self, mysql, post_id):
        """
        tbd
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE " + self.DB_TABLE_TRALALA_POSTS + " SET upvotes = upvotes + 1 WHERE post_id=%s", (post_id,))
            conn.commit();
            conn.close();
            return 1
        except:
            conn.close();
            return -1

    def do_downvote(self, mysql, post_id):
        """
        tbd
        votes = upvotes + (neg(downvotes))
        """
        conn = mysql.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE " + self.DB_TABLE_TRALALA_POSTS + " SET downvotes = downvotes + 1 WHERE post_id=%s", (post_id,))
            conn.commit();
            conn.close();
            return 1
        except:
            conn.close();
            return -1

    def get_all_users(self, mysql):
        """
                tbd
                """
        conn = mysql.connect()
        cursor = conn.cursor()

        cursor.execute(
            "select email, uid, role_id from " + self.DB_TABLE_TRALALA_USERS)
        data = cursor.fetchall()

        if cursor.rowcount == 0:
            conn.close();
            return -1, "no_user"
        else:
            conn.close();
            return 1, data
