import os
import pytest
from pathlib import Path

from project.app import app, db

from project.models import Post
import json

TEST_DB = "test.db"


@pytest.fixture
def client():
    BASE_DIR = Path(__file__).resolve().parent.parent
    app.config["TESTING"] = True
    app.config["DATABASE"] = BASE_DIR.joinpath(TEST_DB)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR.joinpath(TEST_DB)}"

    with app.app_context():
        db.create_all()  # setup
        yield app.test_client()  # tests run here
        db.drop_all()  # teardown


def login(client, username, password):
    """Login helper function"""
    return client.post(
        "/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def logout(client):
    """Logout helper function"""
    return client.get("/logout", follow_redirects=True)


def test_index(client):
    response = client.get("/", content_type="html/text")
    assert response.status_code == 200


def test_database(client):
    """initial test. ensure that the database exists"""
    tester = Path("test.db").is_file()
    assert tester


def test_empty_db(client):
    """Ensure database is blank"""
    rv = client.get("/")
    assert b"No entries yet. Add some!" in rv.data


def test_login_logout(client):
    """Test login and logout using helper functions"""
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"])
    assert b"You were logged in" in rv.data
    rv = logout(client)
    assert b"You were logged out" in rv.data
    rv = login(client, app.config["USERNAME"] + "x", app.config["PASSWORD"])
    assert b"Invalid username" in rv.data
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"] + "x")
    assert b"Invalid password" in rv.data


def test_messages(client):
    """Ensure that user can post messages"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.post(
        "/add",
        data=dict(title="<Hello>", text="<strong>HTML</strong> allowed here"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv.data
    assert b"&lt;Hello&gt;" in rv.data
    assert b"<strong>HTML</strong> allowed here" in rv.data


# "Be sure to write a test for this on your own!"
def test_search(client):
    # degbugging the 1 failue testcase: adding "hello" to the html. needa make the post exist before the page renders
    with client.application.app_context():
        post = Post(title="hello", text="This is a test")
        db.session.add(post)
        db.session.commit()

    # hit /search/ without a query
    response = client.get("/search/")
    assert response.status_code == 200
    # hit /search/ with a query
    response = client.get("/search/?query=hello")
    assert response.status_code == 200
    assert b"hello" in response.data or b"Search results" in response.data
    

# "Be sure to write a test for this on your own!"


def test_delete_requires_login(client):
    # First, create a post in the test database
    with client.application.app_context():
        post = Post(title="Test Post", text="This is a test")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # Try deleting without logging in
    response = client.get(f"/delete/{post_id}")
    assert response.status_code == 401  # should be unauthorized
    data = response.get_json()
    assert data["status"] == 0
    assert "Please log in" in data["message"]

    # Log in first
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Now deletion should succeed
    response = client.get(f"/delete/{post_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == 1
    assert "Post Deleted" in data["message"]

    # Check that the post is actually removed from the database
    with client.application.app_context():
        post_in_db = db.session.query(Post).filter_by(id=post_id).first()
        assert post_in_db is None


def test_delete_message(client):
    """Ensure the messages are being deleted"""
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 0
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 1
