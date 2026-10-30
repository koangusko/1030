# main.py
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse,RedirectResponse

app = FastAPI()

# Include the router
from routes.r import router as myRoute #取個別名避免同名變數衝突
app.include_router(myRoute, prefix="/rou") #mount every thing from ./routes/ to url under prefix

@app.get("/")
async def home():
	return HTMLResponse("this text comes from home")
