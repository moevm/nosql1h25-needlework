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
        date_from: str = Query(None),
        date_to: str = Query(None),
        time_from: str = Query(None),
        time_to: str = Query(None),
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

    # Базовый запрос
    query = {}
    if date_from_dt or date_to_dt:
        query["created_at"] = {}
        if date_from_dt:
            query["created_at"]["$gte"] = date_from_dt
        if date_to_dt:
            query["created_at"]["$lte"] = date_to_dt

    # Получаем и обрабатываем посты
    sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
    cursor = db.posts.find(query).sort(sort_by, sort_direction)

    processed_posts = []
    async for post in cursor:
        # Применяем фильтры
        if author_ids and post["author_id"] not in author_ids:
            continue

        post["author"] = await get_user(post["author_id"])
        processed_posts.append(post)

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
                "time_from": time_from,
                "time_to": time_to,
                "date_from": date_from,
                "date_to": date_to,
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
            "min": min  # Функция min для шаблона
        }
    )

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
                comment["_id"] = comment_id
                comment["author"] = await get_user(comment["author_id"])
                # Форматируем дату комментария
                comment["formatted_date"] = comment.get("created_at", datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M')
                comments.append(comment)
        
        # Сортируем комментарии по дате (новые сначала)
        post["comments"] = sorted(comments, key=lambda x: x["created_at"], reverse=True)

        return templates.TemplateResponse("post_detail.html", {
            "request": request,
            "post": post,
            "current_user": current_user,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/comment/{comment_id}")
async def view_comment(request: Request, comment_id: str):
    try:
        comment = await db.comments.find_one({"_id": ObjectId(comment_id)})
        if not comment:
            return HTMLResponse("Comment not found", status_code=404)
        comment["author"] = await get_user(comment["author_id"])
        comment["formatted_date"] = comment.get("created_at", datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M')
        comment["likes_count"] = len(comment.get("likes", []))

        return templates.TemplateResponse("comment_detail.html", {
            "request": request,
            "comment": comment,
            "current_user": current_user,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/post/{post_id}/{comment_id}/like")
async def like_post(request: Request, post_id: str, comment_id: str):
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        user_id = ObjectId(current_user["_id"])
        comment = await db.comments.find_one({"_id": ObjectId(comment_id)})

        if not comment:
            raise HTTPException(status_code=404, detail="Комментарий не найден")

        updates = {"$addToSet": {"likes": user_id}}

        await db.comments.update_one({"_id": ObjectId(comment_id)}, updates)
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
            "created_at": datetime.now(timezone.utc),
            "likes": [],
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
        time_from: str = Query(None),
        date_to: str = Query(None),
        time_to: str = Query(None),
        min_posts: str = Query(None),
        max_posts: str = Query(None),
        sort_by: str = Query("registration_at"),
        sort_order: str = Query("desc")
):
    
    min_posts = int(min_posts) if min_posts and min_posts.isdigit() else None
    max_posts = int(max_posts) if max_posts and max_posts.isdigit() else None
    date_from_dt = None
    date_to_dt = None
    date_format = r'^\d{4}-\d{2}-\d{2}$'
    time_format = r'^\d{2}:\d{2}$'

    if date_from:
        if not re.match(date_format, date_from):
            raise HTTPException(status_code=400, detail="Неверный формат даты (используйте YYYY-MM-DD)")
        
        time_part = "00:00"
        if time_from and re.match(time_format, time_from):
            time_part = time_from
        
        date_from_dt = datetime.strptime(f"{date_from} {time_part}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

    if date_to:
        if not re.match(date_format, date_to):
            raise HTTPException(status_code=400, detail="Неверный формат даты (используйте YYYY-MM-DD)")
        
        time_part = "23:59"
        if time_to and re.match(time_format, time_to):
            time_part = time_to
        
        date_to_dt = datetime.strptime(f"{date_to} {time_part}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

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

    if date_from_dt or date_to_dt:
        query["registration_at"] = {}
        if date_from_dt:
            query["registration_at"]["$gte"] = date_from_dt
        if date_to_dt:
            query["registration_at"]["$lte"] = date_to_dt

    post_count_query = {}
    if min_posts is not None:
        post_count_query["$gte"] = min_posts
    if max_posts is not None:
        post_count_query["$lte"] = max_posts

    # Определяем сортировку
    sort_field = sort_by if sort_by in ["registration_at", "username", "name", "surname", 
                                      "post_count"] else "registration_at"
    sort_direction = -1 if sort_order == "desc" else 1

    # Собираем агрегационный пайплайн
    pipeline = [
        {"$match": query},
        {"$lookup": {
            "from": "posts",
            "localField": "_id",
            "foreignField": "author_id",
            "as": "posts"
        }},
        {"$addFields": {
            "post_count": {"$size": "$posts"}
        }}
    ]

    if post_count_query:
        pipeline.append({"$match": {"post_count": post_count_query}})

    # Добавляем сортировку
    pipeline.append({"$sort": {sort_field: sort_direction}})

    # Выполняем запрос
    users = []
    async for user in db.users.aggregate(pipeline):
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
            "time_from": time_from,
            "date_to": date_to,
            "time_to": time_to,
            "min_posts": min_posts,
            "max_posts": max_posts,
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

    return templates.TemplateResponse("create_post.html", {
        "request": request,
        "current_user": current_user,
    })


@app.post("/create-post")
async def create_post(
        request: Request,
        preview_image: UploadFile = File(...),
        scheme_name: str = Form(...),
        description: str = Form(default=""),
        comment: str = Form(default=""),
):
    # Проверка авторизации
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        # Проверка типа изображения
        if not preview_image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")

        # Сохраняем изображение
        preview_id = await fs.upload_from_stream(
            f"preview_{scheme_name}_{datetime.now().timestamp()}.jpg",
            await preview_image.read(),
            metadata={"contentType": preview_image.content_type}
        )

        # Создание поста
        post = {
            "preview_image_id": preview_id,
            "scheme_name": scheme_name,
            "description": description,
            "comment": comment,
            "author_id": ObjectId(current_user["_id"]),
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


@app.get("/comments", response_class=HTMLResponse)
async def view_all_comments(
        request: Request,
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
            processed_comments = []

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

    # Базовый запрос
    query = {}
    if date_from_dt or date_to_dt:
        query["created_at"] = {}
        if date_from_dt:
            query["created_at"]["$gte"] = date_from_dt
        if date_to_dt:
            query["created_at"]["$lte"] = date_to_dt

    # Получаем и обрабатываем посты
    sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
    cursor = db.comments.find(query).sort(sort_by, sort_direction)

    processed_comments = []
    async for comment in cursor:
        # Применяем фильтры
        likes_count = len(comment.get("likes", []))
        if min_likes_int is not None and likes_count < min_likes_int:
            continue
        if max_likes_int is not None and likes_count > max_likes_int:
            continue
        if author_ids and comment["author_id"] not in author_ids:
            continue

        comment["author"] = await get_user(comment["author_id"])
        comment["formatted_date"] = comment.get("created_at", datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M')
        comment["likes_count"] = likes_count
        processed_comments.append(comment)

    # Сортировка
    if sort_by == "likes":
        reverse = sort_order == "desc"
        sort_field = "likes_count"
        processed_comments.sort(key=lambda x: x[sort_field], reverse=reverse)

    # Пагинация
    total_comments = len(processed_comments)
    total_pages = ceil(total_comments / per_page_int) if total_comments > 0 else 1
    page_int = max(1, min(page_int, total_pages))
    start_idx = (page_int - 1) * per_page_int
    end_idx = start_idx + per_page_int
    paginated_comments = processed_comments[start_idx:end_idx]

    return templates.TemplateResponse(
        "comments.html",
        {
            "request": request,
            "current_user": current_user,
            "comments": paginated_comments,
            "filters": {
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
                "total_comments": total_comments,
                "total_pages": total_pages
            },
            "min": min  # Функция min для шаблона
        }
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
