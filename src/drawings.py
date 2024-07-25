from __future__ import annotations
from mysql.connector.cursor import MySQLCursor
from datetime import datetime
import json, secrets

def find_drawing_screen_data(*, cursor : MySQLCursor, uid : int, user : str) -> dict:
    cursor.execute("SELECT content, likers, highscore_content, highscore_score, highscore_user FROM drawings WHERE uid=%s;", (uid, ))
    data = cursor.fetchall()
    return {"content": data[0][0], "liked": user in json.loads(data[0][1]), "highscore": {"score": data[0][3], "content": data[0][2], "user": data[0][4]}}

def find_content(*, cursor : MySQLCursor, uid : int) -> str:
    cursor.execute("SELECT content FROM drawings WHERE uid=%s;", (uid, ))
    data = cursor.fetchall()
    return data[0][0]

def find_highscore(*, cursor : MySQLCursor, uid : int) -> tuple[str, float, str]:
    cursor.execute("SELECT highscore_content, highscore_score, highscore_user FROM drawings WHERE uid=%s;", (uid, ))
    data = cursor.fetchall()
    return data[0]

def update_highscore(*, cursor : MySQLCursor, uid : int, highscore_content : str, highscore_score : float, highscore_user : str) -> bool:
    _, last_highscore_score = find_highscore(cursor=cursor, uid=uid)
    if last_highscore_score < highscore_score:
        return False
    cursor.execute("UPDATE drawings SET highscore_content=%s, highscore_score=%s, highscore_user=%s WHERE uid=%s;", (highscore_content, highscore_score, highscore_user, uid))
    cursor.fetchall()
    return True

def create_drawing(*, cursor : MySQLCursor, title : str, author : str, content : str) -> None:
    uid = secrets.randbits(24)
    time_created = datetime.now()
    time_modified = datetime.now()
    views = 0
    likers = "[]"
    highscore_content = ""
    highscore_score = 0
    highscore_user = ""
    score = 0
    last_score_time = datetime.now()
    cursor.execute("INSERT INTO drawings \
        (uid, title, time_created, time_modified, author, views, likers, content, highscore_content, highscore_score, highscore_user, score, last_score_time) \
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
        (uid, title, time_created, time_modified, author, views, likers, content, highscore_content, highscore_score, highscore_user, score, last_score_time)
    )
    cursor.fetchall()
    
def add_liker(*, cursor : MySQLCursor, uid : int, liker : str) -> bool:
    cursor.execute("SELECT likers, score, last_score_time FROM drawings WHERE uid=%s;", (uid, ))
    data = cursor.fetchall()
    score = data[0][1]
    last_score_time = data[0][2]
    likers = json.loads(data[0][0])
    if liker in likers and not liker is None:
        return False
    likers.append(liker)
    time_difference = (datetime.now() - last_score_time).total_seconds()
    score = score * (0.8 ** (time_difference / 86400)) + 500
    cursor.execute("UPDATE drawings SET likers=%s, score=%s, last_score_time=%s WHERE uid=%s;", (json.dumps(likers), score, datetime.now(), uid))
    cursor.fetchall()
    return True
    
def remove_liker(*, cursor : MySQLCursor, uid : int, liker : str) -> bool:
    cursor.execute("SELECT likers, score, last_score_time FROM drawings WHERE uid=%s;", (uid, ))
    data = cursor.fetchall()
    score = data[0][1]
    last_score_time = data[0][2]
    likers = json.loads(data[0][0])
    if not liker in likers:
        return False
    likers.remove(liker)
    time_difference = (datetime.now() - last_score_time).total_seconds()
    score = score * (0.8 ** (time_difference / 86400)) - 500
    cursor.execute("UPDATE drawings SET likers=%s, score=%s, last_score_time=%s WHERE uid=%s;", (json.dumps(likers), score, datetime.now(), uid))
    cursor.fetchall()
    return True
    
def has_liked(*, cursor : MySQLCursor, uid : int, liker : str) -> bool:
    cursor.execute("SELECT likers FROM drawings WHERE uid=%s;", (uid, ))
    data = cursor.fetchall()
    likers = json.loads(data[0][0])
    return liker in likers

def add_view(*, cursor : MySQLCursor, uid : int) -> None:
    cursor.execute("SELECT views, score, last_score_time FROM drawings WHERE uid=%s;", (uid, ))
    data = cursor.fetchall()
    score = data[0][1]
    last_score_time = data[0][2]
    views = data[0][0]
    views += 1
    time_difference = (datetime.now() - last_score_time).total_seconds()
    score = score * (0.8 ** (time_difference / 86400)) + 50
    cursor.execute("UPDATE drawings SET views=%s, score=%s, last_score_time=%s WHERE uid=%s;", (views, score, datetime.now(), uid))
    cursor.fetchall()