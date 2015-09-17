from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Unicode, Float, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from config import config
import art
import datetime
import urllib

DATABASE_URL = config.get('Database', 'url')

engine = create_engine(DATABASE_URL, max_overflow=-1)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Song(Base):
    __tablename__ = 'songs'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    title = Column(Unicode(200))
    artist = Column(Unicode(200))
    album = Column(Unicode(200))
    length = Column(Float)
    path = Column(Unicode(1000))
    tracknumber = Column(Integer)

    # MD5 checksum to verify file integrity
    checksum = Column(String(32))

    packet = relationship('Packet', uselist=False, cascade='all,delete-orphan',
                          passive_deletes=True, backref='songs')
    history = relationship('PlayHistory', cascade='all,delete-orphan',
                           passive_deletes=True, backref='songs')

    def mrl(self):
        return 'file://' + urllib.quote(self.path.encode('utf-8'))

    def dictify(self):
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'length': self.length,
            'path': self.path,
            'tracknumber': self.tracknumber,
            'play_count': self.play_count(),
            'art_uri': art.get_art(self.artist, self.album),
        }

    def play_count(self):
        session = Session()
        count = session.query(PlayHistory).filter_by(song_id=self.id).count()
        session.commit()
        return count

    def last_played(self):
        session = Session()
        history_item = (session.query(PlayHistory).filter_by(song_id=self.id)
                        .order_by(PlayHistory.id.desc()).first())
        session.commit()
        if history_item:
            return history_item.played_at


class PlayHistory(Base):
    __tablename__ = 'play_history'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey('songs.id', ondelete='CASCADE'))
    user = Column(String(8))
    played_at = Column(DateTime, default=datetime.datetime.utcnow)
    player_name = Column(String(16))


class Packet(Base):
    __tablename__ = 'packets'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey('songs.id', ondelete='CASCADE'),
                     unique=True)
    stream_url = Column(String(100))  # renamed from video_url
    stream_title = Column(Unicode(100))  # renamed from video_title
    stream_length = Column(Float)  # renamed from video_length
    stream_id = Column(String(32))  # compatibility with soundcloud & youtube
    art_uri = Column(String(100))  # compatibility with soundcloud & youtube
    artist = Column(Unicode(100))  # compatibility with soundcloud
    user = Column(String(8))
    arrival_time = Column(Float)
    finish_time = Column(Float)
    additional_votes = relationship('Vote', cascade='all,delete-orphan',
                                    passive_deletes=True, backref='packets')
    player_name = Column(String(16))

    def num_votes(self):
        return 1 + len(self.additional_votes)

    def weight(self):
        # The 1 denotes the user weight
        return 1 * 2 ** (self.num_votes() - 1)

    def has_voted(self, user):
        return (self.user == user or
                any(vote.user == user for vote in self.additional_votes))


class Vote(Base):
    __tablename__ = 'votes'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    packet_id = Column(Integer, ForeignKey('packets.id', ondelete='CASCADE'),
                       primary_key=True)
    user = Column(String(8), primary_key=True)


class AuditLogMessage(Base):
    __tablename__ = 'audit_log'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    user = Column(String(8))
    message = Column(String(200))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    player_name = Column(String(16))


class BannedUser(Base):
    __tablename__ = 'banned_users'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    username = Column(String(8), primary_key=True)
    reason = Column(String(200))

def init_db():
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    init_db()
