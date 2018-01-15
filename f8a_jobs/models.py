"""Module with functions to handle database sessions and job API tokens."""

import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Sequence, String, DateTime, Boolean
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from f8a_worker.defaults import configuration as worker_configuration
import f8a_jobs.defaults as configuration
from f8a_jobs.error import TokenExpired
from sqlalchemy.orm.exc import NoResultFound

_Base = declarative_base()

logger = logging.getLogger(__name__)


def create_models():
    """Create the engine to manage many individual database connections."""
    engine = create_engine(worker_configuration.POSTGRES_CONNECTION)
    _Base.metadata.create_all(engine)


def get_session():
    """Retrieve the database connection session."""
    engine = create_engine(worker_configuration.POSTGRES_CONNECTION)
    return sessionmaker(bind=engine)()


class JobToken(_Base):
    """Model for token storing."""

    __tablename__ = 'jobs_tokens'

    id = Column(Integer, Sequence('token_id'), primary_key=True)
    login = Column(String(256))
    token = Column(String(256), unique=True)
    created_at = Column(DateTime)
    valid_until = Column(DateTime)
    revoked = Column(Boolean, default=False)

    def to_dict(self):
        """Convert the object of type JobToken into a dictionary."""
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
        """Verify that the given token exists and is valid.

        :param token: token to be verified
        :return: True if token is valid, False otherwise
        :raises TokenExpired: if the given token has expired
        """
        if not token:
            logger.info("Invalid token '%s'", token)
            return False

        logger.info("Verifying token '%s***'", token[:4])
        session = get_session()

        try:
            entry = session.query(JobToken).filter(JobToken.token == token).one()
        except NoResultFound:
            logger.info("No token '%s' was found", token)
            return False
        except SQLAlchemyError:
            session.rollback()
            raise

        if entry.valid_until < datetime.now() or entry.revoked:
            logger.info("Token '%s' (revoked: %s) for user '%s' with validity until '%s' "
                        "is no longer applicable",
                        entry.token, entry.revoked, entry.login, entry.valid_until)
            raise TokenExpired()

        logger.info("Verified user '%s' using token '%s***' (valid till: %s)",
                    entry.login, entry.token[:4], str(entry.valid_until))
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
        except SQLAlchemyError:
            session.rollback()
            raise

        for entry in entries:
            entry.revoked = True
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

    @classmethod
    def store_token(cls, login, token):
        """Store given token and invalidate old ones.

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
        try:
            logger.info("Storing token '%s'", str(entry.to_dict()))
            session.add(entry)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

        return cls.get_info(token)

    @classmethod
    def get_info(cls, token):
        """Get information about token.

        :param token: token to get information about
        :return: token information
        """
        if not token:
            return {'error': 'No token assigned'}

        session = get_session()

        try:
            entry = session.query(JobToken).filter(JobToken.token == token).one()
        except NoResultFound:
            logger.info("No info for token '%s' was found", token)
            return {'error': 'Unknown token'}
        except SQLAlchemyError:
            session.rollback()
            raise

        return entry.to_dict()
