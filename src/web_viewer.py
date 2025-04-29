from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from bson import ObjectId
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional, List
import re
from fastapi import File, UploadFile
from fastapi.responses import RedirectResponse

templates = Jinja2Templates(directory="templates")

client = None
db = None
fs = None

current_user = None


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
    try:
        color = await db.colors.find_one({"_id": ObjectId(color_id)})
        return color['name'] if color else "Неизвестный цвет"
    except:
        return str(color_id)


# Маршруты авторизации
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    global current_user
    if current_user:
        return RedirectResponse("/")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    global current_user
    user = await db.users.find_one({"username": username, "password": password})
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=401
        )
    current_user = user
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
async def logout():
    global current_user
    current_user = None
    return RedirectResponse("/")


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        name: str = Form(...),
        surname: str = Form(...)
):
    if await db.users.find_one({"username": username}):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пользователь уже существует"},
            status_code=400
        )

    await db.users.insert_one({
        "username": username,
        "password": password,
        "name": name,
        "surname": surname,
        "registration_at": datetime.now(timezone.utc),
        "status": "user"
    })
    return RedirectResponse("/login?success=1", status_code=303)


# Основные маршруты
@app.get("/", response_class=HTMLResponse)
async def view_all_posts(
        request: Request,
        type: str = Query(None),
        color_ids: str = Query(None),
        min_length: str = Query(None),
        max_length: str = Query(None),
        min_colors: str = Query(None),
        max_colors: str = Query(None),
        date_from: str = Query(None),
        date_to: str = Query(None),
        sort_by: str = Query("created_at"),
        sort_order: str = Query("desc")
):
    # Обработка числовых параметров
    try:
        min_length_int = int(min_length) if min_length and min_length.strip() else None
        max_length_int = int(max_length) if max_length and max_length.strip() else None
        min_colors_int = int(min_colors) if min_colors and min_colors.strip() else None
        max_colors_int = int(max_colors) if max_colors and max_colors.strip() else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Числовые параметры должны быть целыми числами")

    # Обработка дат
    date_from_dt = None
    date_to_dt = None
    date_format = r'^\d{4}-\d{2}-\d{2}$'

    if date_from:
        if not re.match(date_format, date_from):
            raise HTTPException(status_code=400, detail="Неверный формат даты (используйте YYYY-MM-DD)")
        date_from_dt = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    if date_to:
        if not re.match(date_format, date_to):
            raise HTTPException(status_code=400, detail="Неверный формат даты (используйте YYYY-MM-DD)")
        date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59)

    # Обработка цветов
    selected_color_ids = []
    if color_ids:
        try:
            selected_color_ids = [ObjectId(cid.strip()) for cid in color_ids.split(',') if cid.strip()]
        except:
            raise HTTPException(status_code=400, detail="Неверный формат ID цветов")

    # Создаем базовый запрос
    query = {}

    # Добавляем фильтры
    if type:
        query["type"] = type

    # Фильтр по длине
    if min_length_int is not None or max_length_int is not None:
        query["length"] = {}
        if min_length_int is not None:
            query["length"]["$gte"] = min_length_int
        if max_length_int is not None:
            query["length"]["$lte"] = max_length_int

    # Фильтр по количеству цветов
    if min_colors_int is not None or max_colors_int is not None:
        query["color_count"] = {}
        if min_colors_int is not None:
            query["color_count"]["$gte"] = min_colors_int
        if max_colors_int is not None:
            query["color_count"]["$lte"] = max_colors_int

    # Фильтр по дате
    if date_from_dt or date_to_dt:
        query["created_at"] = {}
        if date_from_dt:
            query["created_at"]["$gte"] = date_from_dt
        if date_to_dt:
            query["created_at"]["$lte"] = date_to_dt

    # Определяем сортировку
    sort_field = sort_by if sort_by in ["created_at", "likes", "color_count", "length"] else "created_at"
    sort_direction = -1 if sort_order == "desc" else 1

    # Получаем все цвета из базы
    all_colors = await db.colors.find().to_list(None)

    # Обработка для сортировки по лайкам (используем агрегацию)
    if sort_field == "likes":
        pipeline = [
            {"$match": query},
            {"$addFields": {
                "likes_count": {"$size": {"$ifNull": ["$likes", []]}}
            }},
            {"$sort": {"likes_count": sort_direction}}
        ]

        posts = []
        async for post in db.posts.aggregate(pipeline):
            scheme_colors = set()
            for row in post['scheme']:
                for cell in row:
                    if isinstance(cell, (list, tuple)) and len(cell) == 2:
                        scheme_colors.add(ObjectId(cell[0]))

            if selected_color_ids and not all(cid in scheme_colors for cid in selected_color_ids):
                continue

            post["author"] = await get_user(post["author_id"])
            post["scheme_colors"] = list(scheme_colors)
            post["likes_count"] = len(post.get("likes", []))
            posts.append(post)
    else:
        # Обычная сортировка для других полей
        posts = []
        async for post in db.posts.find(query).sort(sort_field, sort_direction):
            post["author"] = await get_user(post["author_id"])

            # Извлекаем все color_id из схемы
            scheme_colors = set()
            for row in post['scheme']:
                for cell in row:
                    if isinstance(cell, (list, tuple)) and len(cell) == 2:
                        color_id = ObjectId(cell[0])
                        scheme_colors.add(color_id)

            # Фильтрация по цветам
            if selected_color_ids and not all(cid in scheme_colors for cid in selected_color_ids):
                continue

            post["scheme_colors"] = list(scheme_colors)
            post["likes_count"] = len(post.get("likes", []))
            posts.append(post)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user,
        "posts": posts,
        "filters": {
            "type": type,
            "color_ids": color_ids,
            "min_length": min_length,
            "max_length": max_length,
            "min_colors": min_colors,
            "max_colors": max_colors,
            "date_from": date_from,
            "date_to": date_to,
            "sort_by": sort_by,
            "sort_order": sort_order
        },
        "available_types": await db.posts.distinct("type"),
        "available_colors": all_colors
    })


@app.get("/post/{post_id}", response_class=HTMLResponse)
async def view_post(request: Request, post_id: str):
    try:
        post = await db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return HTMLResponse("Post not found", status_code=404)

        # Получаем автора
        post["author"] = await get_user(post["author_id"])

        # Форматируем дату поста
        post["formatted_date"] = post.get("created_at", datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M')

        # Получаем и форматируем комментарии
        post["comments"] = []
        async for comment in db.comments.find({"post_id": ObjectId(post_id)}):
            comment["author"] = await get_user(comment["author_id"])
            comment["formatted_date"] = comment.get("created_at", datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M')
            post["comments"].append(comment)

        # Обработка легенды
        color_legend = []
        for item in post.get('legend', []):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                code, color_ref = item
                color_name = await get_color_name(color_ref)
                color_legend.append((code, color_name))
            elif isinstance(item, dict):
                for code, color_ref in item.items():
                    color_name = await get_color_name(color_ref)
                    color_legend.append((code, color_name))

        post["color_legend"] = color_legend

        # Проверяем лайки/дизлайки
        post["user_liked"] = False
        post["user_disliked"] = False
        if current_user:
            user_id = ObjectId(current_user["_id"])
            post["user_liked"] = user_id in post.get("likes", [])
            post["user_disliked"] = user_id in post.get("dislikes", [])

        return templates.TemplateResponse("post_detail.html", {
            "request": request,
            "post": post,
            "current_user": current_user
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post/{post_id}/like")
async def like_post(request: Request, post_id: str):
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        user_id = ObjectId(current_user["_id"])
        post = await db.posts.find_one({"_id": ObjectId(post_id)})

        if not post:
            raise HTTPException(status_code=404, detail="Пост не найден")

        updates = {"$addToSet": {"likes": user_id}}
        if user_id in post.get("dislikes", []):
            updates["$pull"] = {"dislikes": user_id}

        await db.posts.update_one({"_id": ObjectId(post_id)}, updates)
        return RedirectResponse(f"/post/{post_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/post/{post_id}/dislike")
async def dislike_post(request: Request, post_id: str):
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        user_id = ObjectId(current_user["_id"])
        post = await db.posts.find_one({"_id": ObjectId(post_id)})

        if not post:
            raise HTTPException(status_code=404, detail="Пост не найден")

        updates = {"$addToSet": {"dislikes": user_id}}
        if user_id in post.get("likes", []):
            updates["$pull"] = {"likes": user_id}

        await db.posts.update_one({"_id": ObjectId(post_id)}, updates)
        return RedirectResponse(f"/post/{post_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/post/{post_id}/comment")
async def add_comment(request: Request, post_id: str, comment_text: str = Form(...)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        # Создаем комментарий
        comment = {
            "post_id": ObjectId(post_id),
            "author_id": ObjectId(current_user["_id"]),
            "text": comment_text[:512],  # Ограничиваем длину
            "created_at": datetime.now(timezone.utc)
        }

        # Сохраняем в базу
        result = await db.comments.insert_one(comment)

        # Обновляем пост (добавляем ID комментария)
        await db.posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$push": {"comments": result.inserted_id}}
        )

        return RedirectResponse(f"/post/{post_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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


@app.get("/users", response_class=HTMLResponse)
async def search_users(
        request: Request,
        username: str = Query(None),
        name: str = Query(None),
        surname: str = Query(None),
        status: str = Query(None),
        date_from: str = Query(None),
        date_to: str = Query(None),
        sort_by: str = Query("registration_at"),
        sort_order: str = Query("desc")
):
    # Обработка дат
    date_from_dt = None
    date_to_dt = None
    date_format = r'^\d{4}-\d{2}-\d{2}$'

    if date_from:
        if not re.match(date_format, date_from):
            raise HTTPException(status_code=400, detail="Неверный формат даты (используйте YYYY-MM-DD)")
        date_from_dt = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    if date_to:
        if not re.match(date_format, date_to):
            raise HTTPException(status_code=400, detail="Неверный формат даты (используйте YYYY-MM-DD)")
        date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59)

    # Создаем базовый запрос
    query = {}

    # Добавляем фильтры
    if username:
        query["username"] = {"$regex": f".*{username}.*", "$options": "i"}

    if name:
        query["name"] = {"$regex": f".*{name}.*", "$options": "i"}

    if surname:
        query["surname"] = {"$regex": f".*{surname}.*", "$options": "i"}

    if status:
        query["status"] = status

    # Фильтр по дате
    if date_from_dt or date_to_dt:
        query["registration_at"] = {}
        if date_from_dt:
            query["registration_at"]["$gte"] = date_from_dt
        if date_to_dt:
            query["registration_at"]["$lte"] = date_to_dt

    # Определяем сортировку
    sort_field = sort_by if sort_by in ["registration_at", "username", "name", "surname",
                                        "post_count"] else "registration_at"
    sort_direction = -1 if sort_order == "desc" else 1

    # Для сортировки по количеству постов используем агрегацию
    if sort_by == "post_count":
        pipeline = [
            {"$match": query},
            {"$lookup": {
                "from": "posts",
                "localField": "_id",
                "foreignField": "author_id",
                "as": "user_posts"
            }},
            {"$addFields": {
                "post_count": {"$size": "$user_posts"}
            }},
            {"$sort": {"post_count": sort_direction}}
        ]

        users = []
        async for user in db.users.aggregate(pipeline):
            # Форматируем дату для отображения
            if "registration_at" in user and isinstance(user["registration_at"], datetime):
                user["formatted_date"] = user["registration_at"].strftime('%Y-%m-%d %H:%M')
            else:
                user["formatted_date"] = "Неизвестно"
            users.append(user)
    else:
        # Обычная сортировка для других полей
        users = []
        async for user in db.users.find(query).sort(sort_field, sort_direction):
            # Добавляем количество постов для каждого пользователя
            post_count = await db.posts.count_documents({"author_id": user["_id"]})
            user["post_count"] = post_count

            # Форматируем дату для отображения
            if "registration_at" in user and isinstance(user["registration_at"], datetime):
                user["formatted_date"] = user["registration_at"].strftime('%Y-%m-%d %H:%M')
            else:
                user["formatted_date"] = "Неизвестно"

            users.append(user)

    return templates.TemplateResponse("users.html", {
        "request": request,
        "current_user": current_user,
        "users": users,
        "filters": {
            "username": username,
            "name": name,
            "surname": surname,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
            "sort_by": sort_by,
            "sort_order": sort_order
        },
        "available_statuses": ["user", "admin"]
    })


@app.get("/user/{user_id}", response_class=HTMLResponse)
async def view_user_profile(request: Request, user_id: str):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Форматируем дату регистрации
        if "registration_at" in user and isinstance(user["registration_at"], datetime):
            user["formatted_date"] = user["registration_at"].strftime('%Y-%m-%d')
        else:
            user["formatted_date"] = "Неизвестно"

        # Получаем посты пользователя
        posts = await db.posts.find({"author_id": ObjectId(user_id)}).sort("created_at", -1).to_list(None)

        # Добавляем количество лайков для каждого поста
        for post in posts:
            post["likes_count"] = len(post.get("likes", []))
            # Форматируем дату поста
            if "created_at" in post and isinstance(post["created_at"], datetime):
                post["formatted_date"] = post["created_at"].strftime('%Y-%m-%d')

        return templates.TemplateResponse("user_profile.html", {
            "request": request,
            "current_user": current_user,
            "profile_user": user,
            "posts": posts,
            "post_count": len(posts)
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/create-post", response_class=HTMLResponse)
async def create_post_page(request: Request):
    # Проверка авторизации
    if not current_user:
        return RedirectResponse("/login")

    # Получаем доступные цвета и действия для формы
    colors = await db.colors.find().to_list(None)
    actions = await db.actions.find().to_list(None)

    return templates.TemplateResponse("create_post.html", {
        "request": request,
        "current_user": current_user,
        "colors": colors,
        "actions": actions,
        "available_types": ["вязание", "вышивка"]
    })


@app.post("/create-post")
async def create_post(
        request: Request,
        preview_image: UploadFile = File(...),
        scheme_name: str = Form(...),
        type: str = Form(...),
        description: str = Form(default=""),
        comment: str = Form(default=""),
        scheme: str = Form(...)
):
    # Проверка авторизации
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        try:
            import ast
            scheme_data = ast.literal_eval(scheme)
            if not isinstance(scheme_data, list):
                raise ValueError("Схема должна быть списком")
            for row in scheme_data:
                if not isinstance(row, list):
                    raise ValueError("Каждый элемент схемы должен быть списком")
                for cell in row:
                    if not (isinstance(cell, tuple) and len(cell) == 2):
                        raise ValueError("Каждый элемент должен быть кортежем из 2 элементов")
        except (ValueError, SyntaxError) as e:
            raise HTTPException(status_code=400, detail=f"Неверный формат схемы: {str(e)}")

        # Проверка типа изображения
        if not preview_image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")

        # Сохраняем изображение
        preview_id = await fs.upload_from_stream(
            f"preview_{scheme_name}_{datetime.now().timestamp()}.jpg",
            await preview_image.read(),
            metadata={"contentType": preview_image.content_type}
        )

        # Подсчет метрик
        unique_colors = set()
        total_length = 0

        for row in scheme_data:
            for color_id, action_id in row:
                try:
                    # Проверяем существование цвета и действия
                    color_exists = await db.colors.count_documents({"_id": ObjectId(color_id)}) > 0
                    action_exists = await db.actions.count_documents({"_id": ObjectId(action_id)}) > 0

                    if not color_exists or not action_exists:
                        raise HTTPException(status_code=400, detail="Неверный ID цвета или действия")

                    unique_colors.add(color_id)
                    action = await db.actions.find_one({"_id": ObjectId(action_id)})
                    total_length += action["length"]
                except:
                    raise HTTPException(status_code=400, detail="Неверный формат ID цвета или действия")

        # Создание поста
        post = {
            "preview_image_id": preview_id,
            "scheme": [[(str(color_id), str(action_id)) for color_id, action_id in row] for row in scheme_data],
            "type": type,
            "scheme_name": scheme_name,
            "description": description,
            "comment": comment,
            "author_id": ObjectId(current_user["_id"]),
            "color_count": len(unique_colors),
            "length": total_length,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "likes": [],
            "dislikes": []
        }

        result = await db.posts.insert_one(post)
        await db.users.update_one(
            {"_id": ObjectId(current_user["_id"])},
            {"$push": {"posts": result.inserted_id}}
        )

        return RedirectResponse(f"/post/{result.inserted_id}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании поста: {str(e)}")


@app.get("/create-action", response_class=HTMLResponse)
async def create_action_page(request: Request):
    # Проверка авторизации
    if not current_user:
        return RedirectResponse("/login")

    return templates.TemplateResponse("create_action.html", {
        "request": request,
        "current_user": current_user
    })


@app.post("/create-action")
async def create_action(
        request: Request,
        description: str = Form(...),
        length: int = Form(...)
):
    # Проверка авторизации
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        # Создаем новое действие
        action = {
            "description": description[:64],
            "length": length,
            "created_at": datetime.now(timezone.utc),
            "created_by": ObjectId(current_user["_id"])
        }

        # Сохраняем в базу
        await db.actions.insert_one(action)

        return RedirectResponse("/", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)