from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from mysql.connector.cursor import MySQLCursor
from datetime import datetime
import json, secrets


def to_datetime(__time : Optional[datetime] = None) -> str:
    if __time is None:
        __time = datetime.now()
    return datetime.strftime(__time, '%Y-%m-%d %H:%M:%S')

def from_datetime(__time : Optional[str] = None) -> datetime:
    if __time is None:
        return datetime.now()
    return datetime.strptime(__time, '%Y-%m-%d %H:%M:%S')


@dataclass
class BaseDrawing:
    _cursor : MySQLCursor = field(repr=False)
    _modified : bool = field(default=False, init=False, repr=False)
    uid : int = field(default_factory=lambda : secrets.randbits(24), kw_only=True)
    title : str = field(kw_only=True)
    time_created : datetime = field(default_factory=datetime.now, kw_only=True)
    time_modified : datetime = field(default_factory=datetime.now, kw_only=True)
    author : str = field(kw_only=True)
    likers : list[str] = field(default_factory=list, kw_only=True)
    views : int = field(default=0, kw_only=True)
    content : str = field(kw_only=True)
    highscore_content : str = field(default="", kw_only=True)
    highscore_score : float = field(default=0.0, kw_only=True)
    score : float = field(default=0, kw_only=True)
    
class Drawing(BaseDrawing):
    def __init__(self, *args, **kwargs):
        kwargs["likers"] = json.loads(kwargs.get("likers", "[]"))
        kwargs["time_created"] = from_datetime(kwargs.get("time_created"))
        kwargs["time_modified"] = from_datetime(kwargs.get("time_modified"))
        super().__init__(*args, **kwargs)
        
    @property
    def _data(self):
        data = {}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if isinstance(v, list):
                v = json.dumps(v)
            data[k] = v
            
    def register_modification(self):
        self._modified = True
        self.time_modified = datetime.now()
            
    def register_highscore(self, content, score) -> bool:
        if score < self.highscore_score:
            return False
        self.register_modification()
        self.highscore_content = content
        self.highscore_score = score
        return True
    
    @classmethod
    def find(cls, *, cursor : MySQLCursor, uid : int):
        cursor.execute
    
    @classmethod
    def create(cls, *, title : str, author : str, content : str, cursor : MySQLCursor):
        new = cls(_cursor=cursor, title=title, author=author, content=content)
        rows, values = new.get_rows()
        cursor.execute(
            f"insert into drawings \
{rows} \
values ({', '.join(len(rows)*['%s'])});", values
        )
        return new
    
    def get_rows(self) -> tuple[str, str]:
        data = self._data
        rows = ("uid", "title", "time_created", "time_modified", "author", "likers", "views", "content", "highscore_content", "highscore_score", score)
        values = [data.get(row) for row in rows]
        return (
            "("+", ".join(rows)+")", 
            values
        )
    
    def save(self):
        if not self._modified:
            return
        command = "update drawings set "
        values = []
        for k, v in self._data.items():
            command += f"{k}=%s, "
            values.append(v)
        command = command.removesuffix(", ")
        command += " where uid=%s;"
        self._cursor.execute(command, (*values, self.uid))
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.save()
        