import pytest
from unittest.mock import Mock, MagicMock
from urllib.parse import urlparse


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None
    return session


@pytest.fixture
def mock_requests():
    mock = MagicMock()
    mock.get.return_value.status_code = 200
    mock.get.return_value.content = b'<html><a href="/link1">Link</a></html>'
    return mock


@pytest.fixture
def mock_robots():
    mock = MagicMock()
    mock.can_fetch.return_value = True
    return mock
