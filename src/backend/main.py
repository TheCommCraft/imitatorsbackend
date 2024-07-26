from os import getenv
from os.path import dirname, join
import json, secrets, sys
import mysql.connector as mc
sys.path.insert(0, r"C:\Users\simon\OneDrive\Dokumente\scratchcommunication\scratchcommunication\scratchcommunication-1")
from cachetools import TTLCache
from typing import Optional
from types import FunctionType
from scratchcommunication import Session, Sky, CloudSocket
from scratchcommunication.cloudrequests import RequestHandler, ErrorMessage
from scratchcommunication.security import Security
from scratchattach import get_project
from mysql.connector import connect as mysql_connect
from .tabs import get_new_tab, get_pop_tab, get_own_tab
from .drawings import add_view, find_content, add_liker, remove_liker, update_highscore, find_drawing_screen_data, create_drawing
from dotenv import load_dotenv

def start(duration : Optional[int] = None):
    def log(msg : str) -> None:
        print("Logging:", msg)

    load_dotenv(join(dirname(__file__), ".env"))

    log("Loading environment variables...")

    SESSION_ID = getenv("SESSION_ID")
    XTOKEN = getenv("XTOKEN")
    USERNAME = getenv("USERNAME")
    PROJECT_ID = getenv("PROJECT_ID")
    SECURITY_SECRET = getenv("SECURITY_SECRET")
    MYSQL_HOST = getenv("MYSQL_HOST")
    MYSQL_PORT = getenv("MYSQL_PORT")
    MYSQL_USER = getenv("MYSQL_USER")
    MYSQL_PASS = getenv("MYSQL_PASS")
    MYSQL_DB = getenv("MYSQL_DB")

    log("Loaded environment variables.")

    log("Creating connections...")

    session = Session(USERNAME, session_id=SESSION_ID, xtoken=XTOKEN)
    security = Security.from_string(SECURITY_SECRET)
    cloud1 = session.create_cloudconnection(PROJECT_ID, daemon_thread=True)
    cloud2 = session.create_tw_cloudconnection(PROJECT_ID, contact_info="TheCommCraft on Scratch and Github", daemon_thread=True)
    sky = Sky(cloud1, cloud2)
    cloud = CloudSocket(cloud=sky, security=security)
    client = RequestHandler(cloud_socket=cloud)
    mysql = mysql_connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS, database=MYSQL_DB)
    cursor = mysql.cursor()
    project = get_project(PROJECT_ID)

    log("Created connections.")

    def get_comments() -> list[dict]:
        return project.comments()

    def check_comment(content : Optional[str] = None, *, predicate : Optional[FunctionType] = None, user : Optional[str] = None) -> bool:
        for comment in get_comments():
            if user and comment["author"]["username"] != user:
                continue
            if content and comment["content"] != content:
                continue
            if predicate and not predicate(comment["content"]):
                continue
            return comment["author"]["username"]

    codes = TTLCache(64, 300)

    @client.request(name="load_tab", auto_convert=True, allow_python_syntax=True)
    def load_tab(tab : str) -> json.dumps:
        user = client.current_client_username
        if tab in ["popular", "pop", "0"]:
            return get_pop_tab(cursor=cursor, username=user)
        if tab in ["new", "1"]:
            return get_new_tab(cursor=cursor, username=user)
        if tab in ["own", "mine", "yours", "2"]:
            try:
                assert user
            except AssertionError:
                return []
            return get_own_tab(cursor=cursor, username=user)
        return []

    @client.request(name="load_drawing", auto_convert=True, allow_python_syntax=True)
    def load_drawing(uid : int) -> str:
        try:
            add_view(cursor=cursor, uid=uid)
            return find_content(cursor=cursor, uid=uid)
        finally:
            mysql.commit()

    @client.request(name="like_drawing", auto_convert=True, allow_python_syntax=True)
    def like_drawing(uid : int) -> bool:
        try:
            assert client.current_client.secure
            user = client.current_client_username
            return add_liker(cursor=cursor, uid=uid, liker=user)
        finally:
            mysql.commit()

    @client.request(name="unlike_drawing", auto_convert=True, allow_python_syntax=True)
    def unlike_drawing(uid : int) -> bool:
        try:
            assert client.current_client.secure
            user = client.current_client_username
            return remove_liker(cursor=cursor, uid=uid, liker=user)
        finally:
            mysql.commit()

    @client.request(name="propose_highscore", auto_convert=True, allow_python_syntax=True)
    def propose_highscore(uid : int, highscore_content : str, highscore_score : float) -> bool:
        try:
            if len(highscore_content) > 8000:
                raise ErrorMessage("Too big!")
            user = client.current_client_username or "Turbowarp user"
            return update_highscore(cursor=cursor, uid=uid, highscore_content=highscore_content, highscore_score=highscore_score, highscore_user=user)
        finally:
            mysql.commit()
            
    @client.request(name="load_drawing_screen_data", auto_convert=True, allow_python_syntax=True)
    def load_drawing_screen_data(uid : int) -> json.dumps:
        try:
            add_view(cursor=cursor, uid=uid)
            user = client.current_client_username
            return find_drawing_screen_data(cursor=cursor, uid=uid, user=user)
        finally:
            mysql.commit()
            
    @client.request(name="create_code", auto_convert=True, allow_python_syntax=True)
    def create_code() -> int:
        assert client.current_client.secure
        if not client.current_client.client_id in codes:
            codes[client.current_client.client_id] = secrets.randbits(32)
        return codes[client.current_client.client_id]
        
    @client.request(name="upload_drawing", auto_convert=True, allow_python_syntax=True)
    def upload_drawing(content : str, title : str) -> str:
        try:
            if len(content) > 8000:
                raise ErrorMessage("Too big!")
            assert client.current_client.secure
            if client.current_client_username:
                if not client.current_client_username == "TheCommCraft" and not check_comment(title):
                    raise ErrorMessage("No comment found.")
                user = client.current_client_username
                create_drawing(cursor=cursor, title=title, author=user, content=content)
                return "Success!"
            comment = f"{codes[client.current_client.client_id]}: {title}"
            if not (author := check_comment(comment)):
                raise ErrorMessage("No comment found.")
            create_drawing(cursor=cursor, title=title, author=author, content=content)
            return "Success!"
        finally:
            mysql.commit()
        
    @sky.on("invalid_syntax")
    def on_inv(event):
        log(f"Invalid syntax: {event.__dict__}")
        
    @sky.on("new_user")
    def on_user(event):
        log(f"New user: {event.client.username} @ {event.client.client_id}")
        
    @sky.on("secure_message")
    def on_msg(event):
        log(f"{event.client.client_id} ({event.client.username}) >>> {repr(event.content)}")
        
    @client.on_error
    def on_err(error : Exception, retry : FunctionType):
        nonlocal mysql
        nonlocal cursor
        if isinstance(error, mc.errors.OperationalError):
            mysql = mysql_connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS, database=MYSQL_DB)
            cursor = mysql.cursor()
            retry()
            return
        raise error
    
    log("Starting requests handler...")

    try:
        client.start(duration=duration or None)
    finally:
        cursor.close()
        mysql.close()
        log("Finished")
