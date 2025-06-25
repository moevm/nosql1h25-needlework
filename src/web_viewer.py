from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from io import BytesIO
from fastapi import File, UploadFile
from fastapi.responses import RedirectResponse
from math import ceil
from datetime import datetime, timezone
import re
from bson import ObjectId
from fastapi import HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from pymongo import ASCENDING, DESCENDING
import json
from bson import json_util
import tempfile
import os
from datetime import datetime
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks

templates = Jinja2Templates(directory="/app/templates")

client = None
db = None
fs = None


current_user = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db, fs
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://db:27017")
    client = AsyncIOMotorClient(mongodb_url)
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
        time_from: str = Query(None),
        time_to: str = Query(None),
        min_likes: str = Query(None),
        max_likes: str = Query(None),
        author_name: str = Query(None),
        author_surname: str = Query(None), 
        sort_by: str = Query("created_at"),
        sort_order: str = Query("desc"),
        page: str = Query("1"),
        per_page: str = Query("5")
):
    """Обработчик главной страницы с пагинацией и фильтрацией"""

    # Обработка параметров пагинации
    try:
        page_int = max(1, int(page)) if page and page != "None" else 1
        per_page_int = max(1, min(50, int(per_page))) if per_page and per_page != "None" else 5
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Параметры пагинации должны быть целыми числами"
        )

    # Функция для безопасного преобразования параметров
    def safe_int_convert(param):
        if not param or param == "None":
            return None
        try:
            return int(param)
        except ValueError:
            return None

    # Обработка числовых фильтров
    min_length_int = safe_int_convert(min_length)
    max_length_int = safe_int_convert(max_length)
    min_colors_int = safe_int_convert(min_colors)
    max_colors_int = safe_int_convert(max_colors)
    min_likes_int = safe_int_convert(min_likes)
    max_likes_int = safe_int_convert(max_likes)

    # Обработка фильтра по автору
    author_query = {}
    if author_name and author_name != "None":
        author_query["name"] = {"$regex": f".*{author_name}.*", "$options": "i"}
    if author_surname and author_surname != "None":
        author_query["surname"] = {"$regex": f".*{author_surname}.*", "$options": "i"}

    author_ids = []
    if author_query:
        authors = db.users.find(author_query)
        async for author in authors:
            author_ids.append(author["_id"])
        
        if not author_ids:
            processed_posts = []

    # Обработка дат и времени
    date_from_dt = None
    date_to_dt = None
    
    if date_from and date_from != "None":
        try:
            if time_from and time_from != "None":
                datetime_str = f"{date_from} {time_from}"
                date_from_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            else:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат даты/времени (используйте YYYY-MM-DD и HH:MM)"
            )

    if date_to and date_to != "None":
        try:
            if time_to and time_to != "None":
                datetime_str = f"{date_to} {time_to}"
                date_to_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            else:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат даты/времени (используйте YYYY-MM-DD и HH:MM)"
            )

    # Обработка цветов
    selected_color_ids = []
    if color_ids and color_ids != "None":
        try:
            selected_color_ids = [
                ObjectId(cid.strip())
                for cid in color_ids.split(',')
                if cid.strip()
            ]
        except:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат ID цветов"
            )

    # Базовый запрос
    query = {}
    if type and type != "None":
        query["type"] = type
    if date_from_dt or date_to_dt:
        query["created_at"] = {}
        if date_from_dt:
            query["created_at"]["$gte"] = date_from_dt
        if date_to_dt:
            query["created_at"]["$lte"] = date_to_dt

    # Получаем данные из БД
    all_colors = await db.colors.find().to_list(None)
    actions = {
        action["_id"]: action.get("length", 0)
        async for action in db.actions.find({})
    }

    # Получаем и обрабатываем посты
    if sort_by in ["color_count", "length"]:
        cursor = db.posts.find(query)
    else:
        sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
        cursor = db.posts.find(query).sort(sort_by, sort_direction)

    processed_posts = []
    async for post in cursor:
        unique_colors = set()
        total_length = 0

        for row in post['scheme']:
            for cell in row:
                if isinstance(cell, (list, tuple)) and len(cell) == 2:
                    try:
                        color_id = ObjectId(cell[0])
                        action_id = ObjectId(cell[1])
                        unique_colors.add(color_id)
                        total_length += actions.get(action_id, 0)
                    except:
                        continue

        # Применяем фильтры
        if min_length_int is not None and total_length < min_length_int:
            continue
        if max_length_int is not None and total_length > max_length_int:
            continue
        if min_colors_int is not None and len(unique_colors) < min_colors_int:
            continue
        if max_colors_int is not None and len(unique_colors) > max_colors_int:
            continue
        if selected_color_ids and not all(cid in unique_colors for cid in selected_color_ids):
            continue
        likes_count = len(post.get("likes", []))
        if min_likes_int is not None and likes_count < min_likes_int:
            continue
        if max_likes_int is not None and likes_count > max_likes_int:
            continue
        if author_ids and post["author_id"] not in author_ids:
            continue

        post["color_count"] = len(unique_colors)
        post["length"] = total_length
        post["author"] = await get_user(post["author_id"])
        post["likes_count"] = len(post.get("likes", []))
        processed_posts.append(post)

    # Сортировка
    if sort_by in ["color_count", "length", "likes"]:
        reverse = sort_order == "desc"
        sort_field = "likes_count" if sort_by == "likes" else sort_by
        processed_posts.sort(key=lambda x: x[sort_field], reverse=reverse)

    # Пагинация
    total_posts = len(processed_posts)
    total_pages = ceil(total_posts / per_page_int) if total_posts > 0 else 1
    page_int = max(1, min(page_int, total_pages))
    start_idx = (page_int - 1) * per_page_int
    end_idx = start_idx + per_page_int
    paginated_posts = processed_posts[start_idx:end_idx]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": current_user,
            "posts": paginated_posts,
            "filters": {
                "type": type,
                "color_ids": color_ids,
                "min_length": min_length,
                "max_length": max_length,
                "min_colors": min_colors,
                "max_colors": max_colors,
                "time_from": time_from,
                "time_to": time_to,
                "date_from": date_from,
                "date_to": date_to,
                "min_likes": min_likes,
                "max_likes": max_likes,
                "author_name": author_name,
                "author_surname": author_surname,
                "sort_by": sort_by,
                "sort_order": sort_order
            },
            "pagination": {
                "page": page_int,
                "per_page": per_page_int,
                "total_posts": total_posts,
                "total_pages": total_pages
            },
            "available_types": await db.posts.distinct("type"),
            "available_colors": all_colors,
            "min": min  # Функция min для шаблона
        }
    )


# Константы для типов стежков
STITCH_TYPES = {
    "крестик": {"symbol": "X", "length": 10},
    "полукрест": {"symbol": "/", "length": 5},
    "гобеленовый": {"symbol": "=", "length": 15},
    "стебельчатый": {"symbol": "|", "length": 8},
    "левый стежок": {"symbol": "}", "length": 18},
    "полуторный": {"symbol": "*", "length": 17},
    "тамбурный": {"symbol": "^", "length": 16},
    "расколотый": {"symbol": ";", "length": 14},
    "французский": {"symbol": "@", "length": 13},
    "гладью": {"symbol": "$", "length": 12},
    "назад вперед": {"symbol": "%", "length": 11}
}

COLOR_HEX_MAP = {
    "red": "#ff0000",
    "blue": "#0000ff",
    "green": "#00ff00",
    "black": "#000000",
    "white": "#ffffff"
}


def color_name_to_hex(color_name: str) -> str:
    return COLOR_HEX_MAP.get(color_name.lower(), "#cccccc")


async def get_color_name(color_ref: str) -> str:
    try:
        color = await db.colors.find_one({"_id": ObjectId(color_ref)})
        return color["name"] if color else "Unknown"
    except:
        return "Unknown"


@app.get("/post/{post_id}", response_class=HTMLResponse)
async def view_post(request: Request, post_id: str):
    try:
        post = await db.posts.find_one({"_id": ObjectId(post_id)})
        if not post:
            return HTMLResponse("Post not found", status_code=404)

        # Получаем информацию об авторе поста
        post["author"] = await get_user(post["author_id"])

        # Форматируем дату
        post["formatted_date"] = post.get("created_at", datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M')

        # Получаем и обрабатываем комментарии
        comments = []
        for comment_id in post.get("comments", []):
            comment = await db.comments.find_one({"_id": comment_id})
            if comment:
                # Получаем данные автора комментария
                comment["author"] = await get_user(comment["author_id"])
                # Форматируем дату комментария
                comment["formatted_date"] = comment.get("created_at", datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M')
                comments.append(comment)
        
        # Сортируем комментарии по дате (новые сначала)
        post["comments"] = sorted(comments, key=lambda x: x["created_at"], reverse=True)

        # Обработка легенды цветов
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

        # Получаем информацию о всех действиях из STITCH_TYPES
        valid_actions = list(STITCH_TYPES.keys())
        actions_dict = {}
        async for action in db.actions.find({"description": {"$in": valid_actions}}):
            action_desc = action['description'].lower()
            if action_desc in STITCH_TYPES:
                actions_dict[str(action['_id'])] = {
                    "description": action_desc,
                    "symbol": STITCH_TYPES[action_desc]["symbol"]
                }

        # Строим схему для отображения
        grid_scheme = []
        for row in post["scheme"]:
            grid_row = []
            for color_id, action_id in row:
                color_name = await get_color_name(color_id)
                action_info = actions_dict.get(str(action_id), {})

                grid_row.append({
                    "color_hex": color_name_to_hex(color_name),
                    "symbol": action_info.get("symbol", "?"),
                    "title": f"{action_info.get('description', 'Unknown')}, {color_name}"
                })
            grid_scheme.append(grid_row)

        stitch_legend = [{
            "description": name,
            "symbol": info["symbol"]
        } for name, info in STITCH_TYPES.items()]

        # Проверяем, лайкал/дизлайкал ли текущий пользователь пост
        if current_user:
            post["user_liked"] = ObjectId(current_user["_id"]) in post.get("likes", [])
            post["user_disliked"] = ObjectId(current_user["_id"]) in post.get("dislikes", [])
        else:
            post["user_liked"] = False
            post["user_disliked"] = False

        return templates.TemplateResponse("post_detail.html", {
            "request": request,
            "post": post,
            "current_user": current_user,
            "grid_scheme": grid_scheme,
            "stitch_legend": stitch_legend,
            "color_name_to_hex": color_name_to_hex
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
            "text": comment_text[:512],
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
        # Безопасный парсинг схемы вместо eval
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
            "description": description[:64],  # Ограничиваем длину
            "length": length,
            "created_at": datetime.now(timezone.utc),
            "created_by": ObjectId(current_user["_id"])
        }

        # Сохраняем в базу
        await db.actions.insert_one(action)

        return RedirectResponse("/", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/database-tools", response_class=HTMLResponse)
async def database_tools_page(request: Request):
    """Страница управления импортом/экспортом БД без авторизации"""
    return templates.TemplateResponse("database_tools.html", {
        "request": request,
        "current_user": None  # Убираем проверку пользователя
    })


@app.get("/export-database")
async def export_entire_database(background_tasks: BackgroundTasks):
    """Экспорт всей базы данных в один JSON файл"""
    try:
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp_file:
            collections = await db.list_collection_names()
            db_data = {}

            for collection_name in collections:
                if collection_name.startswith('system.'):
                    continue  # Пропускаем системные коллекции

                cursor = db[collection_name].find()
                db_data[collection_name] = await cursor.to_list(length=None)

            # Сериализуем с использованием bson.json_util
            json.dump(
                db_data,
                tmp_file,
                default=json_util.default,
                ensure_ascii=False,
                indent=2
            )
            tmp_file_path = tmp_file.name

        # Создаем удобное имя файла
        filename = f"embroidery_db_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Добавляем задачу удаления временного файла
        background_tasks.add_task(lambda: os.unlink(tmp_file_path))

        # Возвращаем файл для скачивания
        return FileResponse(
            tmp_file_path,
            media_type='application/json',
            filename=filename
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при экспорте базы данных: {str(e)}"
        )


@app.post("/import-database")
async def import_entire_database(
        file: UploadFile = File(...),
        clear_existing: bool = Form(False)
):
    """Импорт всей базы данных без проверки прав"""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Требуется JSON файл")

    try:
        contents = await file.read()
        db_data = json_util.loads(contents.decode('utf-8'))

        results = {}
        for collection_name, documents in db_data.items():
            if collection_name.startswith('system.'):
                continue

            collection = db[collection_name]

            if clear_existing:
                await collection.delete_many({})

            if documents and len(documents) > 0:
                result = await collection.insert_many(documents)
                results[collection_name] = len(result.inserted_ids)
            else:
                results[collection_name] = 0

        return {
            "message": "Импорт базы данных завершен",
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка импорта: {str(e)}")


@app.post("/delete-database")
async def delete_entire_database():
    """Удаление всех данных из базы (кроме системных коллекций)"""
    try:
        collections = await db.list_collection_names()
        results = {}

        for collection_name in collections:
            if collection_name.startswith('system.'):
                continue

            result = await db[collection_name].delete_many({})
            results[collection_name] = result.deleted_count

        return {
            "message": "База данных успешно очищена",
            "results": results,
            "total_deleted": sum(results.values())
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при очистке базы данных: {str(e)}"
        )


@app.get("/actions", response_class=HTMLResponse)
async def view_actions(
        request: Request,
        search: str = Query(None),
        min_length: str = Query(None),
        max_length: str = Query(None),
        sort_by: str = Query("length"),  # Сортировка по длине по умолчанию
        sort_order: str = Query("desc"),  # По убыванию по умолчанию
        page: str = Query("1"),
        per_page: str = Query("10")
):
    """Страница просмотра стежков"""

    # Обработка параметров
    try:
        page_int = max(1, int(page)) if page and page != "None" else 1
        per_page_int = max(1, min(50, int(per_page))) if per_page and per_page != "None" else 10
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверные параметры")

    # Поиск по описанию и длине
    query = {}
    if search and search != "None":
        query["description"] = {"$regex": f".*{search}.*", "$options": "i"}
    
    # Фильтрация по длине
    length_query = {}
    if min_length and min_length != "None":
        try:
            length_query["$gte"] = float(min_length)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверное значение минимальной длины")
    
    if max_length and max_length != "None":
        try:
            length_query["$lte"] = float(max_length)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверное значение максимальной длины")
    
    if length_query:
        query["length"] = length_query

    # Сортировка по длине
    sort_field = "length"
    sort_direction = DESCENDING if sort_order == "desc" else ASCENDING

    # Получаем данные
    total_actions = await db.actions.count_documents(query)
    total_pages = ceil(total_actions / per_page_int) if total_actions > 0 else 1
    page_int = min(page_int, total_pages)
    skip = (page_int - 1) * per_page_int

    actions = await db.actions.find(query) \
        .sort(sort_field, sort_direction) \
        .skip(skip) \
        .limit(per_page_int) \
        .to_list(None)

    return templates.TemplateResponse(
        "actions.html",
        {
            "request": request,
            "actions": actions,
            "search": search if search != "None" else "",
            "min_length": min_length if min_length != "None" else "",
            "max_length": max_length if max_length != "None" else "",
            "sort_order": sort_order,
            "pagination": {
                "page": page_int,
                "per_page": per_page_int,
                "total_actions": total_actions,
                "total_pages": total_pages
            }
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
