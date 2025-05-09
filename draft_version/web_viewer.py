from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from bson import ObjectId
from io import BytesIO

templates = Jinja2Templates(directory="templates")

client = None
db = None
fs = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db, fs
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.embroidery_db
    fs = AsyncIOMotorGridFSBucket(db)
    yield
    if client:
        client.close()


app = FastAPI(lifespan=lifespan)


async def get_user(user_id):
    return await db.users.find_one({"_id": ObjectId(user_id)})


async def get_color_name(color_id):
    if isinstance(color_id, str) and not ObjectId.is_valid(color_id):
        return color_id
    try:
        color = await db.colors.find_one({"_id": ObjectId(color_id)})
        return color['name'] if color else "Неизвестный цвет"
    except:
        return str(color_id)


@app.get("/", response_class=HTMLResponse)
async def view_all_posts(request: Request):
    posts = []
    async for post in db.posts.find():
        post["author"] = await get_user(post["author_id"])
        posts.append(post)
    return templates.TemplateResponse("index.html", {"request": request, "posts": posts})


@app.get("/post/{post_id}", response_class=HTMLResponse)
async def view_post(request: Request, post_id: str):
    try:
        post = await db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return HTMLResponse("Post not found", status_code=404)

        post["author"] = await get_user(post["author_id"])

        # Получаем комментарии с авторами
        post["comments"] = []
        async for comment in db.comments.find({"post_id": ObjectId(post_id)}):
            comment["author"] = await get_user(comment["author_id"])
            post["comments"].append(comment)

        # Обрабатываем легенду цветов
        color_legend = []
        for item in post.get('legend', []):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                code, color_ref = item
                color_name = await get_color_name(color_ref)
                color_legend.append((code, color_name))
            elif isinstance(item, dict):
                # Если легенда хранится как словарь
                for code, color_ref in item.items():
                    color_name = await get_color_name(color_ref)
                    color_legend.append((code, color_name))

        post["color_legend"] = color_legend

        return templates.TemplateResponse("post_detail.html", {
            "request": request,
            "post": post
        })
    except Exception as e:
        return HTMLResponse(f"Error: {str(e)}", status_code=500)


@app.get("/image/{image_id}")
async def get_image(image_id: str):
    try:
        grid_out = await fs.open_download_stream(ObjectId(image_id))
        image_data = await grid_out.read()
        return StreamingResponse(
            BytesIO(image_data),
            media_type="image/jpeg"
        )
    except Exception as e:
        return {"error": str(e)}, 404


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)