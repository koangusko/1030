# db.py
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from psycopg import errors
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

load_dotenv() #read DATABASE_URL from .env
DATABASE_URL = os.environ["DATABASE_URL"]
TAIPEI = ZoneInfo("Asia/Taipei")

pool: AsyncConnectionPool | None = None #shared by getDB() and the data access functions below

# Lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
	global pool
	pool = AsyncConnectionPool(
		conninfo = DATABASE_URL,
		kwargs={"row_factory": dict_row},
		open=False,
		#min_size=1,
		#max_size=10,
		#timeout=10,
		)
	await pool.open()
	app.state.pool = pool
	print("Connected to DB")

	yield  # App runs here

	# Shutdown logic
	await pool.close()
	print("Disconnected from DB")

#a wrapper for fastAPI's Depends Injection
async def getDB(request: Request):
	async with request.app.state.pool.connection() as conn:
		#set cuurent login user from session
		yield conn


# ---- 失敗的例外類型（routes 依類型決定顯示的訊息） ----
class RegistrationError(Exception):
	message = "報名失敗"

class InvalidInput(RegistrationError):
	def __init__(self, message):
		super().__init__(message)
		self.message = message

class ActivityNotFound(RegistrationError):
	message = "查無此活動"

class AlreadyRegistered(RegistrationError):
	message = "您已報名此活動"

class ActivityFull(RegistrationError):
	message = "活動名額已滿"

class RegistrationClosed(RegistrationError):
	message = "報名已截止"


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?\d{8,15}$")

def normalize_phone(phone):
	#0912-345-678 / 0912 345 678 / +886912345678 -> 0912345678
	phone = re.sub(r"[\s\-()]", "", phone or "")
	if phone.startswith("+886"):
		phone = "0" + phone[4:]
	return phone

def validate_input(name, phone, email):
	name = " ".join((name or "").split()) #trim and collapse inner spaces, so "王  小明" == "王 小明"
	phone = normalize_phone(phone)
	email = (email or "").strip().lower()
	if not name:
		raise InvalidInput("請填寫姓名")
	if len(name) > 100:
		raise InvalidInput("姓名不可超過 100 字元")
	if not phone:
		raise InvalidInput("請填寫電話")
	if not PHONE_RE.match(phone):
		raise InvalidInput("電話格式不正確")
	if not email:
		raise InvalidInput("請填寫 Email")
	if len(email) > 254 or not EMAIL_RE.match(email):
		raise InvalidInput("Email 格式不正確")
	return name, phone, email


# 剩餘名額 = capacity - 報名數；closed 以資料庫時間判斷是否已截止
ACTIVITY_SQL = """
	SELECT a.activity_id, a.title, a.description, a.location,
		a.start_time, a.end_time, a.deadline, a.capacity,
		COUNT(r.registration_id) AS registered,
		a.capacity - COUNT(r.registration_id) AS remaining,
		a.deadline < now() AS closed
	FROM activities a
	LEFT JOIN registrations r ON r.activity_id = a.activity_id
"""

async def get_activities():
	async with pool.connection() as conn:
		cur = await conn.execute(ACTIVITY_SQL + " GROUP BY a.activity_id ORDER BY a.start_time, a.activity_id")
		return await cur.fetchall()

async def get_activity(activity_id):
	async with pool.connection() as conn:
		cur = await conn.execute(ACTIVITY_SQL + " WHERE a.activity_id = %s GROUP BY a.activity_id", (activity_id,))
		return await cur.fetchone()

async def register_participant(activity_id, name, phone, email):
	name, phone, email = validate_input(name, phone, email)
	async with pool.connection() as conn:
		async with conn.transaction(): #any exception inside rolls back the whole registration
			#1. lock the activity row so registrations for the same activity run one at a time
			cur = await conn.execute(
				"SELECT capacity, deadline < now() AS closed FROM activities WHERE activity_id = %s FOR UPDATE",
				(activity_id,))
			activity = await cur.fetchone()
			if activity is None:
				raise ActivityNotFound()
			if activity["closed"]:
				raise RegistrationClosed()

			#2. same name + same phone already registered for this activity?
			cur = await conn.execute("""
				SELECT 1 FROM registrations r
				JOIN participants p ON p.participant_id = r.participant_id
				WHERE r.activity_id = %s AND p.name = %s AND p.phone = %s""", (activity_id, name, phone))
			if await cur.fetchone():
				raise AlreadyRegistered()

			#3. capacity check (still under the lock)
			cur = await conn.execute("SELECT COUNT(*) AS n FROM registrations WHERE activity_id = %s", (activity_id,))
			if (await cur.fetchone())["n"] >= activity["capacity"]:
				raise ActivityFull()

			#4. find or create the participant by (name, phone); existing email is not overwritten
			cur = await conn.execute(
				"INSERT INTO participants (name, phone, email) VALUES (%s, %s, %s) ON CONFLICT (name, phone) DO NOTHING RETURNING participant_id",
				(name, phone, email))
			row = await cur.fetchone()
			if row is None:
				cur = await conn.execute("SELECT participant_id FROM participants WHERE name = %s AND phone = %s", (name, phone))
				row = await cur.fetchone()

			#5. UNIQUE(activity_id, participant_id) is the final guard against duplicates
			try:
				cur = await conn.execute(
					"INSERT INTO registrations (activity_id, participant_id) VALUES (%s, %s) RETURNING registration_id",
					(activity_id, row["participant_id"]))
			except errors.UniqueViolation:
				raise AlreadyRegistered()
			return (await cur.fetchone())["registration_id"]

async def get_registration(registration_id):
	async with pool.connection() as conn:
		cur = await conn.execute("""
			SELECT r.registration_id, r.registered_at, p.name,
				a.activity_id, a.title, a.location, a.start_time, a.end_time
			FROM registrations r
			JOIN participants p ON p.participant_id = r.participant_id
			JOIN activities a ON a.activity_id = r.activity_id
			WHERE r.registration_id = %s""", (registration_id,))
		return await cur.fetchone()

async def get_activity_registrations(activity_id):
	async with pool.connection() as conn:
		cur = await conn.execute("""
			SELECT p.name, r.registered_at
			FROM registrations r
			JOIN participants p ON p.participant_id = r.participant_id
			WHERE r.activity_id = %s
			ORDER BY r.registered_at, r.registration_id""", (activity_id,))
		return await cur.fetchall()


# ---- 活動管理：新增活動、截止報名 ----
def parse_time(value, label):
	#<input type="datetime-local"> 送來 "2026-11-06T15:00"（沒有時區），視為台灣時間
	try:
		dt = datetime.fromisoformat((value or "").strip())
	except ValueError:
		raise InvalidInput(f"請填寫正確的{label}")
	return dt if dt.tzinfo else dt.replace(tzinfo=TAIPEI)

def validate_activity(title, description, location, start_time, end_time, deadline, capacity):
	title = (title or "").strip()
	description = (description or "").strip() or None
	location = (location or "").strip()
	if not title:
		raise InvalidInput("請填寫活動名稱")
	if len(title) > 100:
		raise InvalidInput("活動名稱不可超過 100 字元")
	if not location:
		raise InvalidInput("請填寫地點")
	if len(location) > 200:
		raise InvalidInput("地點不可超過 200 字元")
	start_time = parse_time(start_time, "開始時間")
	end_time = parse_time(end_time, "結束時間")
	deadline = parse_time(deadline, "報名截止時間")
	if end_time <= start_time:
		raise InvalidInput("結束時間必須晚於開始時間")
	if deadline > start_time:
		raise InvalidInput("報名截止時間不可晚於開始時間")
	try:
		capacity = int(str(capacity).strip())
	except ValueError:
		raise InvalidInput("名額必須是整數")
	if not 1 <= capacity <= 100000:
		raise InvalidInput("名額必須介於 1 到 100000")
	return title, description, location, start_time, end_time, deadline, capacity

async def create_activity(title, description, location, start_time, end_time, deadline, capacity):
	values = validate_activity(title, description, location, start_time, end_time, deadline, capacity)
	async with pool.connection() as conn:
		cur = await conn.execute("""
			INSERT INTO activities (title, description, location, start_time, end_time, deadline, capacity)
			VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING activity_id""", values)
		return (await cur.fetchone())["activity_id"]

async def close_registration(activity_id):
	#把截止時間提前到現在；已經截止的活動維持原本的截止時間
	#UPDATE 會鎖住活動列，和 register_participant 的 FOR UPDATE 互相排隊
	async with pool.connection() as conn:
		cur = await conn.execute(
			"UPDATE activities SET deadline = LEAST(deadline, now()) WHERE activity_id = %s RETURNING activity_id",
			(activity_id,))
		if await cur.fetchone() is None:
			raise ActivityNotFound()
