# main.py
# 啟動： fastapi dev main.py  或  uv run fastapi dev main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from db import lifespan

app = FastAPI(lifespan=lifespan)

# Include the router
from routes.activities import router as activityRoute
app.include_router(activityRoute) #mount every thing from ./routes/activities.py to url root

#定義靜態檔案（CSS）的目錄
app.mount("/static", StaticFiles(directory="static"), name="static")
