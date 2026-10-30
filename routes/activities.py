from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TAIPEI = ZoneInfo("Asia/Taipei")

#jinja filter: {{ a.start_time | tw }} -> 台灣時間
def to_taipei(dt):
	return dt.astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M") if dt else ""
templates.env.filters["tw"] = to_taipei

#routes starts here
@router.get("/")
async def activityList(request: Request):
	activities = await db.get_activities()
	return templates.TemplateResponse(name="activities.html", request=request, context={"activities": activities})

#必須寫在 /activities/{activity_id} 前面，否則 "new" 會被當成 activity_id
@router.get("/activities/new")
async def activityNewPage(request: Request):
	return templates.TemplateResponse(name="activity_new.html", request=request, context={"form": {}})

@router.post("/activities")
async def activityCreate(request: Request, title: str = Form(""), description: str = Form(""), location: str = Form(""),
		start_time: str = Form(""), end_time: str = Form(""), deadline: str = Form(""), capacity: str = Form("")):
	form = {"title": title, "description": description, "location": location,
		"start_time": start_time, "end_time": end_time, "deadline": deadline, "capacity": capacity}
	try:
		activity_id = await db.create_activity(**form)
	except db.InvalidInput as e:
		#re-render the form with the error and what the user typed
		return templates.TemplateResponse(
			name="activity_new.html", request=request, status_code=400,
			context={"form": form, "error": e.message})
	return RedirectResponse(url=f"/activities/{activity_id}", status_code=303) #use 303 to switch to GET

@router.get("/activities/{activity_id}")
async def activityDetail(activity_id: int, request: Request):
	activity = await db.get_activity(activity_id)
	if activity is None:
		raise HTTPException(status_code=404, detail="查無此活動")
	return templates.TemplateResponse(name="activity_detail.html", request=request, context={"activity": activity})

@router.post("/activities/{activity_id}/register")
async def register(activity_id: int, request: Request, name: str = Form(""), phone: str = Form(""), email: str = Form("")):
	try:
		registration_id = await db.register_participant(activity_id, name, phone, email)
	except db.ActivityNotFound:
		raise HTTPException(status_code=404, detail="查無此活動")
	except db.RegistrationError as e:
		#re-render the detail page with the error and what the user typed
		status = 400 if isinstance(e, db.InvalidInput) else 409
		activity = await db.get_activity(activity_id)
		return templates.TemplateResponse(
			name="activity_detail.html", request=request, status_code=status,
			context={"activity": activity, "error": e.message, "name": name, "phone": phone, "email": email})
	return RedirectResponse(url=f"/registrations/{registration_id}/success", status_code=303) #use 303 to switch to GET

@router.post("/activities/{activity_id}/close")
async def activityClose(activity_id: int):
	try:
		await db.close_registration(activity_id)
	except db.ActivityNotFound:
		raise HTTPException(status_code=404, detail="查無此活動")
	return RedirectResponse(url=f"/activities/{activity_id}", status_code=303)

@router.get("/registrations/{registration_id}/success")
async def registrationSuccess(registration_id: int, request: Request):
	registration = await db.get_registration(registration_id)
	if registration is None:
		raise HTTPException(status_code=404, detail="查無此報名紀錄")
	return templates.TemplateResponse(name="registration_success.html", request=request, context={"r": registration})

@router.get("/activities/{activity_id}/registrations")
async def registrationList(activity_id: int, request: Request):
	activity = await db.get_activity(activity_id)
	if activity is None:
		raise HTTPException(status_code=404, detail="查無此活動")
	registrations = await db.get_activity_registrations(activity_id)
	return templates.TemplateResponse(
		name="registrations.html", request=request,
		context={"activity": activity, "registrations": registrations})
