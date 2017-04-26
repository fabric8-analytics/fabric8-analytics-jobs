import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Sequence, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from cucoslib.conf import get_postgres_connection_string
import bayesian_jobs.configuration as configuration
from bayesian_jobs.error import TokenExpired
from sqlalchemy.orm.exc import NoResultFound

_Base = declarative_base()

logger = logging.getLogger(__name__)


def create_models():
    engine = create_engine(get_postgres_connection_string())
    _Base.metadata.create_all(engine)


def get_session():
    engine = create_engine(get_postgres_connection_string())
    return sessionmaker(bind=engine)()


class JobToken(_Base):
    """ Model for token storing """
    __tablename__ = 'jobs_tokens'

    id = Column(Integer, Sequence('token_id'), primary_key=True)
    login = Column(String(256))
    token = Column(String(256), unique=True)
    created_at = Column(DateTime)
    valid_until = Column(DateTime)
    revoked = Column(Boolean, default=False)

    def to_dict(self):
        return {
            'token': self.token,
            'valid_until': self.valid_until,
            'created_at': self.created_at,
            'login': self.login,
            'revoked': self.revoked,
            'expired': self.valid_until < datetime.now()
        }

    @staticmethod
    def verify(token):
        """ Verify that the given token exists and is valid

        :param token: token to be verified
        :return: True if token is valid, False otherwise
        :raises TokenExpired: if the given token has expired
        """
        logger.info("Verifying token '%s'", token)

        if not token:
            logger.info("Invalid token '%s'", token)
            return False

        session = get_session()

        try:
            entry = session.query(JobToken).filter(JobToken.token == token).one()
        except NoResultFound:
            logger.info("No token '%s' was found", token)
            return False

        if entry.valid_until < datetime.now() or entry.revoked:
            logger.info("Token '%s' (revoked: %s) for user '%s' with validity until '%s' is no longer applicable",
                        entry.token, entry.revoked, entry.login, entry.valid_until)
            raise TokenExpired()

        logger.info("Verified user '%s' using token '%s' (valid till: %s)",
                    entry.login, entry.token, str(entry.valid_until))
        return True

    @staticmethod
    def _invalidate_tokens(session, login):
        try:
            entries = session.query(JobToken).\
                filter(JobToken.login == login).\
                filter(JobToken.revoked.is_(False)).\
                all()
        except NoResultFound:
            return

        for entry in entries:
            entry.revoked = True
        session.commit()

    @classmethod
    def store_token(cls, login, token):
        """ Store given token and invalidate old ones

        :param login: login for which token should be stored
        :param token: token to be stored
        :return: dict, describing token information
        """
        session = get_session()
        cls._invalidate_tokens(session, login)

        now = datetime.now()
        entry = JobToken(
            login=login,
            token=token,
            valid_until=now + configuration.TOKEN_VALID_TIME,
            created_at=now
        )
        session.add(entry)
        session.commit()

        return cls.get_info(token)

    @classmethod
    def get_info(cls, token):
        """ Get information about token

        :param token: token to get information about
        :return: token information
        """
        if not token:
            return {'error': 'No token assigned'}

        session = get_session()
        session.query()

        try:
            entry = session.query(JobToken).filter(JobToken.token == token).one()
        except NoResultFound:
            logger.info("No info for token '%s' was found", token)
            return {'error': 'Unknown token'}

        return entry.to_dict()


