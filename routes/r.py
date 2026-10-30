from fastapi import APIRouter
from fastapi.responses import HTMLResponse
router = APIRouter()

#routes starts here
@router.get("/tes")
async def route1():
	return HTMLResponse("this text comes from route-1")

@router.get("/test")
async def route2():
	return HTMLResponse("this text comes from route-2")


