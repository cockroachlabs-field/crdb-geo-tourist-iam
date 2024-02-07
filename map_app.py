#!/usr/bin/env python3

#
# Set the following environment variables:
#
#  export DB_URL="postgres://user:passwd@localhost:26257/defaultdb"
#  export FLASK_PORT=18080
#  export USE_GEOHASH=true
#

import logging
import re, os, sys, time, random, json, uuid
from psycopg2.errors import SerializationFailure
import psycopg2
import Geohash

# SQLAlchemy imports
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy import create_engine, text, event
from sqlalchemy import Table, MetaData
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import warnings

# The Flask and related imports
from flask import Flask, request, Response, render_template, flash, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, current_user, login_user, login_required, logout_user

db_url = os.getenv("DB_URL")
if db_url is None:
  print("Environment DB_URL must be set. Quitting.")
  sys.exit(1)

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
  level=log_level
  , format="[%(asctime)s] %(message)s"
  , datefmt="%m/%d/%Y %I:%M:%S %p"
)
print("Log level: {} (export LOG_LEVEL=[DEBUG|INFO|WARN|ERROR] to change this)".format(log_level))

db_url = re.sub(r"^postgres(ql)?", "cockroachdb", db_url)
# For using follower reads:
eng_read = create_engine(db_url, pool_size=10, pool_pre_ping=True,
  connect_args = { "application_name": "CRDB Geo Tourist READ" })

# For any other queries, or for writes:
eng_write = create_engine(db_url, pool_size=10, pool_pre_ping=True,
  connect_args = { "application_name": "CRDB Geo Tourist READ/WRITE" })

@event.listens_for(eng_read, "connect")
def connect(dbapi_connection, connection_record):
  cursor_obj = dbapi_connection.cursor()
  cursor_obj.execute("SET default_transaction_use_follower_reads = on;")
  cursor_obj.close()

# Returns list of tuples: [(x11, x12), (x21, x22), ...]
def run_stmt(engine, stmt, max_retries=3):
  rv = []
  for retry in range(0, max_retries):
    if retry > 0:
      logging.warning("Retry number {}".format(retry))
    try:
      with engine.connect() as conn:
        rs = conn.execute(stmt)
        for row in rs:
          rv.append(row)
        conn.commit() # Didn't realize I had to explicitly commit here
      return rv
    except SerializationFailure as e:
      logging.warning("Error: %s", e)
      logging.warning("EXECUTE SERIALIZATION_FAILURE BRANCH")
      sleep_s = (2**retry) * 0.1 * (random.random() + 0.5)
      logging.warning("Sleeping %s s", sleep_s)
      time.sleep(sleep_s)
    except (sa.exc.OperationalError, psycopg2.OperationalError) as e:
      # Get a new connection and try again
      logging.warning("Error: %s", e)
      logging.warning("EXECUTE CONNECTION FAILURE BRANCH")
      sleep_s = 0.12 + random.random() * 0.25
      logging.warning("Sleeping %s s", sleep_s)
      time.sleep(sleep_s)
    except psycopg2.Error as e:
      logging.warning("Error: %s", e)
      logging.warning("EXECUTE DEFAULT BRANCH")
      raise e
  raise ValueError(f"Transaction did not succeed after {max_retries} retries")

# Initialize the app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
# For next line: https://flask-sqlalchemy.palletsprojects.com/en/2.x/api/
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = { "pool_size": 10, "pool_pre_ping": True }
login_manager = LoginManager(app)
login_manager.init_app(app)

# Suppress SQLAlchemy warnings
osm_table = None
with warnings.catch_warnings():
  warnings.simplefilter("ignore", category=sa.exc.SAWarning)
  osm_table = Table("osm", MetaData(), autoload_with=eng_write)

# SQLAlchemy (https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/quickstart/)
class Base(DeclarativeBase):
  pass
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Models / Classes
class Tourist(UserMixin, db.Model):
  id: so.Mapped[uuid.UUID] = so.mapped_column(
    sa.types.Uuid,
    primary_key=True,
    server_default=sa.text("gen_random_uuid()")
  )
  username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
  email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
  password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

  def __repr__(self):
    return "[Tourist: username = {}]".format(self.username)

  def set_password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)

# https://community.plotly.com/t/how-to-tell-if-user-is-mobile-or-desktop-in-backend/47270/3
def is_mobile():
  user_agent = request.headers.get("User-Agent")
  user_agent = user_agent.lower()
  phones = ["android", "iphone"]
  if any(x in user_agent for x in phones):
    return True
  return False

# Inherit from this case class for Login, Signup
class LatLonForm(FlaskForm):
  lat = HiddenField("lat")
  lon = HiddenField("lon")

class SignUpForm(LatLonForm):
  username = StringField("Username", validators=[DataRequired()])
  email = StringField("Email", validators=[DataRequired(), Email()])
  password = PasswordField("Password", validators=[DataRequired()])
  password2 = PasswordField("Repeat Password", validators=[DataRequired(), EqualTo("password")])
  submit = SubmitField("Sign Up")

  def validate_username(self, username):
    user = db.session.scalar(sa.select(Tourist).where(Tourist.username == username.data))
    if user is not None:
      raise ValidationError("Please use a different username.")

  def validate_email(self, email):
    user = db.session.scalar(sa.select(Tourist).where(Tourist.email == email.data))
    if user is not None:
      raise ValidationError("Please use a different email address.")

class LoginForm(LatLonForm):
  username = StringField("Username", validators=[DataRequired()])
  password = PasswordField("Password", validators=[DataRequired()])
  remember_me = BooleanField("Remember Me")
  submit = SubmitField("Log In")

class AmenityForm(FlaskForm):
  name = StringField("Name", validators=[DataRequired()])
  lat = StringField("Lat", render_kw={'readonly': True})
  lon = StringField("Lon", render_kw={'readonly': True})
  rating = StringField("Rating")
  amenity = StringField("Amenity", render_kw={'readonly': True})
  geohash4 = HiddenField("geohash4")
  id = HiddenField("id")
  submit = SubmitField("Save Changes")

# Create tables based on objects in models.py
with app.app_context():
  db.create_all()

@login_manager.user_loader
def load_user(id):
    return db.session.get(Tourist, id)

# Return a JSON list of the sites where the tourist may be located
@app.route("/sites", methods = ["GET"])
def sites():
  sql = """
  SELECT lat, lon
  FROM tourist_locations
  WHERE enabled = TRUE
  ORDER BY RANDOM()
  LIMIT 1;
  """
  stmt = text(sql)
  rv = { "lat": 51.506712, "lon": -0.127235 } # Default tourist location, if none are enabled
  for row in run_stmt(eng_read, stmt):
    (rv["lat"], rv["lng"]) = row # Returns a single row
  return Response(json.dumps(rv), status=200, mimetype="application/json")

useGeohash = False
# Return a JSON list of the top 10 nearest features of type <amenity>
# TODO: parameterize max. dist., limit; handle mutiple features
@app.route("/features", methods = ["POST"])
def features():
  obj = request.get_json(force=True)
  lat = float(obj["lat"])
  lon = float(obj["lon"])
  amenity = obj["amenity"]
  geohash = Geohash.encode(lat, lon)
  obj["geohash"] = geohash
  logging.info("Tourist: %s", json.dumps(obj))
  sql = """
  WITH q1 AS
  (
    SELECT
      name,
      ST_Distance(ST_MakePoint(:lon_val, :lat_val)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,
      ST_Y(ref_point::GEOMETRY) lat,
      ST_X(ref_point::GEOMETRY) lon,
      rating,
      geohash4,
      id
    FROM osm
    WHERE
  """
  if useGeohash:
    sql += "geohash4 = SUBSTRING(:geohash FOR 4) AND amenity = :amenity"
  else:
    sql += "ST_DWithin(ST_MakePoint(:lon_val, :lat_val)::GEOGRAPHY, ref_point, 5.0E+03, TRUE)"
    sql += " AND key_value && ARRAY[:amenity]"
  sql += """
  )
  SELECT * FROM q1
  """
  if useGeohash:
    sql += "WHERE dist_m < 5.0E+03"
  sql += """
  ORDER BY dist_m ASC
  LIMIT 10;
  """
  rv = []
  logging.debug("SQL: %s", sql)
  stmt = None
  if useGeohash:
    stmt = text(sql).bindparams(lon_val=lon, lat_val=lat, geohash=geohash, amenity=amenity)
  else:
    stmt = text(sql).bindparams(lon_val=lon, lat_val=lat, amenity="amenity=" + amenity)
  for row in run_stmt(eng_read, stmt):
    (name, dist_m, lat, lon, rating, geohash4, id) = row
    d = {}
    d["name"] = name
    if current_user.is_authenticated: # Logged in => editable
      d["name"] = '<a href="/amenity/edit/{}/{}/{}">{}</a>'.format(geohash4, amenity, id, name)
    d["amenity"] = amenity
    d["dist_m"] = str(dist_m)
    d["lat"] = lat
    d["lon"] = lon
    d["rating"] = "Rating: " + (str(rating) + " out of 5" if rating is not None else "(not rated)")
    logging.debug("Feature: %s", json.dumps(d))
    rv.append(d)
  return Response(json.dumps(rv), status=200, mimetype="application/json")

# Routes
@app.route("/")
def index():
  logging.warning("current_user: {}".format(current_user))
  return render_template("index.html")

# Generate the URL to get back to the map when using the amenity edit view
def gen_url(form):
  url = "/?amenity={}&lat={}&lon={}".format(form.amenity.data, form.lat.data, form.lon.data)
  return url

# Handle the case when the user submits the form
@app.route("/amenity/edit", methods=["POST"])
def edit_post():
  if not current_user.is_authenticated:
    return redirect(url_for("login"))
  form = AmenityForm()
  if form.validate_on_submit():
    logging.info("UPDATE for '{}': rating = {}".format(form.name.data, form.rating.data))
    # UPDATE code here
    sql = """
    UPDATE osm SET rating = :rating, name = :name
    WHERE geohash4 = :geohash4 AND amenity = :amenity AND id = :id
    RETURNING rating
    """
    stmt = text(sql).bindparams(
      rating=form.rating.data
      , name=form.name.data
      , geohash4=form.geohash4.data
      , amenity=form.amenity.data
      , id=form.id.data
    )
    rv = run_stmt(eng_write, stmt)
    return render_template("amenity_edit.html", amenity_form=form, url=gen_url(form), is_mobile=is_mobile())

# Handle the HTTP GET from the <a href...> link
# Pre-populate the form based on values in the HTTP request:
# https://stackoverflow.com/questions/35892144/pre-populate-an-edit-form-with-wtforms-and-flask
@app.route("/amenity/edit/<geohash4>/<amenity>/<id>", methods=["GET"])
def edit_get(geohash4, amenity, id):
  if not current_user.is_authenticated:
    return redirect(url_for("login"))
  sql = """
  SELECT name, lat, lon, rating
  FROM osm
  WHERE geohash4 = :geohash4 AND amenity = :amenity AND id = :id;
  """
  stmt = text(sql).bindparams(geohash4=geohash4, amenity=amenity, id=id)
  row = run_stmt(eng_write, stmt)
  (name, lat, lon, rating) = row[0]
  logging.info("geohash4 = '{}' AND amenity = '{}' AND id = {}".format(geohash4, amenity, id))
  logging.info("row: %s", row)
  form = AmenityForm()
  form.name.data = name
  form.lat.data = lat
  form.lon.data = lon
  form.rating.data = rating
  form.geohash4.data = geohash4 
  form.amenity.data = amenity 
  form.id.data = id 
  return render_template("amenity_edit.html", amenity_form=form, url=gen_url(form), is_mobile=is_mobile())

@app.route("/login", methods=["GET", "POST"])
def login():
  login_form = LoginForm()
  """
  if request.method == 'POST':
    lat = login_form.lat.data
    lon = login_form.lon.data
  else:
    lat = request.args.get("lat")
    lon = request.args.get("lon")
  url_params = "lat={}&lon={}".format(lat, lon)
  logging.info("url_params: {}".format(url_params))
  """
  if current_user.is_authenticated:
    return redirect("/")
  if login_form.validate_on_submit():
    user = db.session.scalar(sa.select(Tourist).where(Tourist.username == login_form.username.data))
    if user is None or not user.check_password(login_form.password.data):
      flash("Invalid username or password")
      return redirect("/login")
    login_user(user, remember=login_form.remember_me.data)
    return redirect("/")
  """
  login_form.lat.data = lat
  login_form.lon.data = lon
  """
  return render_template("login.html", login_form=login_form, is_mobile=is_mobile())

# Default login view for pages requiring user to be logged in
login_manager.login_view = "login"

@app.route("/logout")
@login_required
def logout():
  logout_user()
  return redirect(url_for("index"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
  if current_user.is_authenticated:
    return redirect(url_for("index"))
  signup_form = SignUpForm()
  if signup_form.validate_on_submit():
    user = Tourist(username=signup_form.username.data, email=signup_form.email.data)
    user.set_password(signup_form.password.data)
    db.session.add(user)
    db.session.commit()
    flash("Congratulations, you are now a registered user!")
    return redirect(url_for("login"))
  return render_template("signup.html", signup_form=signup_form)

if __name__ == "__main__":
  port = int(os.getenv("FLASK_PORT", 18080))
  useGeohash = (os.getenv("USE_GEOHASH", "true").lower() == "true")
  print("useGeohash = %s" % ("True" if useGeohash else "False"))
  print("Secret: {}".format(app.config["SECRET_KEY"]))
  from waitress import serve
  serve(app, host="0.0.0.0", port=port, threads=10)
  # Shut down the DB connection when app quits
  eng_read.dispose()

