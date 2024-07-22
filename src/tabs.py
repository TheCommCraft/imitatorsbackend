from __future__ import annotations
from typing import Any
from mysql.connector.cursor import MySQLCursor

def get_new_tab(*, cursor : MySQLCursor, username : str) -> list[list[Any]]:
    cursor.execute("SELECT uid, title, author, likers, views FROM drawings ORDER BY score DESC LIMIT 27;")
    data = cursor.fetchall()
    return [[row[0], row[1], row[2], len(row[3]), row[4], username in row[3], "", ""] for row in data]

def get_pop_tab(*, cursor : MySQLCursor, username : str) -> list[list[Any]]:
    cursor.execute("SELECT uid, title, author, likers, views FROM drawings ORDER BY time_created DESC LIMIT 27;")
    data = cursor.fetchall()
    return [[row[0], row[1], row[2], len(row[3]), row[4], username in row[3], "", ""] for row in data]