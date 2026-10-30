from fastapi import FastAPI, Form
from fastapi import Request,Depends
#To handle file upload, pip install python-multipart first
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

#宣告一個fastAPI應用
app = FastAPI()

from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
	max_age=None, #86400,  # 1 day
    same_site="lax",  # Options: 'lax', 'strict', 'none'
    https_only=False,  # Set to True in production with HTTPS,
)

#example of using dependency function for login check
def chkLogin():
	def checker(request: Request): #fastAPI will auto-inject request to dependency function
		loginUser = request.session.get("user") #get identity from session
		if loginUser:
			return loginUser #return whatever you need
		else:
			#raise HTTPException(status_code=403, detail="Forbidden")
			return None
	return checker

@app.get("/")
async def home(request: Request, user=Depends(chkLogin())):
	print(user)
	if user is None:
		return RedirectResponse(url="/w/login.html", status_code=302)
	else:
		return HTMLResponse(f"Welcome {user}! <a href='/logout'>logout</a>")

@app.get("/logout")
async def logout(request: Request):
	#clear all session variables
	request.session.clear()
	return RedirectResponse(url="/")

@app.post("/login") #receive login data from form post
async def login(
	request: Request,
	username: str = Form(...),
	password: str = Form(...),
):
	#you can replace this with a DB SQL query
	if username=='user' and password == 'pass':
		#save the login status in session variable
		request.session["user"] = username
		#redirect to the home page URL
		return RedirectResponse(url="/", status_code=302)
	return HTMLResponse("Invalid credentials", status_code=401)

#定義靜態網頁的目錄
app.mount("/w", StaticFiles(directory="www"))