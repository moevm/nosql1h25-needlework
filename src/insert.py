# insert_test_data.py
import asyncio
import os
from io import BytesIO
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from bson import ObjectId
from datetime import datetime, timezone


async def upload_image_from_file(fs, file_path, filename=None):
    """Загружает изображение из файла в GridFS"""
    if not filename:
        filename = os.path.basename(file_path)

    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден, используется заглушка")
        return await fs.upload_from_stream(filename, BytesIO(b"fake_image_data"))

    with open(file_path, 'rb') as f:
        return await fs.upload_from_stream(filename, f)


async def is_database_empty(db):
    """Проверяет, пустая ли база данных"""
    collections = await db.list_collection_names()
    
    for collection_name in collections:
        if collection_name in ['users', 'posts', 'colors', 'actions', 'comments']:
            count = await db[collection_name].count_documents({})
            if count > 0:
                return False
    return True


async def insert_test_data():
    """Вставка тестовых данных с реальными изображениями"""
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://db:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.embroidery_db
    fs = AsyncIOMotorGridFSBucket(db)

    try:
        # Проверяем, есть ли данные в базе
        if not await is_database_empty(db):
            print("База данных уже содержит данные. Заполнение тестовыми данными пропущено.")
            return {
                "status": "skipped",
                "message": "Database already contains data"
            }

        print("База данных пустая, начинаем заполнение тестовыми данными...")
        # 1. Создаем тестовые цвета
        colors = ["red", "blue", "green", "black", "white"]
        color_ids = [(await db.colors.insert_one({"name": color})).inserted_id for color in colors]
        print(f"Добавлено {len(color_ids)} цветов")

        # 2. Создаем тестовые действия
        actions = [
            {"description": "крестик", "length": 10},
            {"description": "полукрест", "length": 5},
            {"description": "гобеленовый", "length": 15},
            {"description": "левый стежок", "length": 18},
            {"description": "полуторный", "length": 17},
            {"description": "тамбурный", "length": 16},
            {"description": "расколотый", "length": 14},
            {"description": "французский", "length": 13},
            {"description": "гладью", "length": 12},
            {"description": "назад вперед", "length": 11},
            {"description": "стебельчатый", "length": 8}
        ]
        action_ids = [(await db.actions.insert_one(action)).inserted_id for action in actions]
        print(f"Добавлено {len(action_ids)} действий")

        # 3. Создаем тестовых пользователей
        users = [
            {
                "username": "user1",
                "status": "user",
                "name": "Анна",
                "surname": "Иванова",
                "password": "pass123",
                "posts": [],
                "registration_at": datetime(2023, 5, 15, 14, 30, 0, tzinfo=timezone.utc)
            },
            {
                "username": "user2",
                "status": "admin",
                "name": "Иван",
                "surname": "Петров",
                "password": "pass456",
                "posts": [],
                "registration_at": datetime(2024, 5, 15, 14, 30, 0, tzinfo=timezone.utc)
            }
        ]
        user_ids = [(await db.users.insert_one(user)).inserted_id for user in users]
        print(f"Добавлено {len(user_ids)} пользователей")

        images_dir = Path("src/images")
        images_dir.mkdir(exist_ok=True)

        # 4. Создаем тестовые посты с реальными изображениями
        # Схема: каждая клетка - (color_id, action_id)
        posts = [
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo2.jpg",
                    "животные.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])],
                    [(color_ids[1], action_ids[0]), (color_ids[2], action_ids[1]), (color_ids[3], action_ids[2]), (color_ids[4], action_ids[3])],
                    [(color_ids[2], action_ids[0]), (color_ids[3], action_ids[1]), (color_ids[4], action_ids[2]), (color_ids[0], action_ids[3])],
                    [(color_ids[3], action_ids[0]), (color_ids[4], action_ids[1]), (color_ids[0], action_ids[2]), (color_ids[1], action_ids[3])]
                ],
                "legend": [
                    ("4", str(color_ids[3])),  # 4: Черный
                    ("5", str(color_ids[4]))   # 5: Белый
                ],
                "type": "вышивка",
                "scheme_name": "Цветы",
                "description": "Схема для вышивки цветов",
                "comment": "Рекомендую канву Aida 16",
                "author_id": user_ids[1],
                "created_at": datetime(2023, 8, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 9, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo3.jpg",
                    "животные.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]), (color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[1], action_ids[0]), (color_ids[2], action_ids[1]), (color_ids[3], action_ids[2]), (color_ids[4], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[2], action_ids[0]), (color_ids[3], action_ids[1]), (color_ids[4], action_ids[2]), (color_ids[0], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[3], action_ids[0]), (color_ids[4], action_ids[1]), (color_ids[0], action_ids[2]), (color_ids[1], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[4], action_ids[0]), (color_ids[0], action_ids[1]), (color_ids[1], action_ids[2]), (color_ids[2], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]), (color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[1], action_ids[0]), (color_ids[2], action_ids[1]), (color_ids[3], action_ids[2]), (color_ids[4], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[2], action_ids[0]), (color_ids[3], action_ids[1]), (color_ids[4], action_ids[2]), (color_ids[0], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])]
                ],
                "legend": [
                    ("4", str(color_ids[3])),  # 4: Черный
                    ("5", str(color_ids[4]))  # 5: Белый
                ],
                "type": "вязание",
                "scheme_name": "подложка",
                "description": "чай поставьте",
                "comment": "Рекомендую канву Aida 16",
                "author_id": user_ids[1],
                "created_at": datetime(2024, 8, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2024, 9, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Животные",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[3]), (color_ids[3], action_ids[4]),(color_ids[3], action_ids[5]),(color_ids[3], action_ids[6]),(color_ids[3], action_ids[7]),(color_ids[1], action_ids[8]), (color_ids[2], action_ids[9]),(color_ids[1], action_ids[10]), (color_ids[2], action_ids[2])],
                    [(color_ids[1], action_ids[0]), (color_ids[2], action_ids[1]), (color_ids[3], action_ids[2]), (color_ids[4], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[2], action_ids[0]), (color_ids[3], action_ids[1]), (color_ids[4], action_ids[2]), (color_ids[0], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[3], action_ids[0]), (color_ids[4], action_ids[1]), (color_ids[0], action_ids[2]), (color_ids[1], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[4], action_ids[0]), (color_ids[0], action_ids[1]), (color_ids[1], action_ids[2]), (color_ids[2], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]), (color_ids[3], action_ids[3]),
                     (color_ids[3], action_ids[3]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),
                     (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]), (color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[1], action_ids[0]), (color_ids[2], action_ids[1]), (color_ids[3], action_ids[2]), (color_ids[4], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])],
                    [(color_ids[2], action_ids[0]), (color_ids[3], action_ids[1]), (color_ids[4], action_ids[2]), (color_ids[0], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[3], action_ids[3]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2]),(color_ids[1], action_ids[1]), (color_ids[2], action_ids[2])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Тест",
                "description": "Тест на все виды действий",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [
                    [(color_ids[0], action_ids[0]), (color_ids[1], action_ids[1])],
                    [(color_ids[2], action_ids[2]), (color_ids[3], action_ids[3])]
                ],
                "legend": [
                    ("1", str(color_ids[0])),
                    ("2", str(color_ids[1]))
                ],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
                "updated_at": datetime(2023, 7, 15, 14, 30, 0, tzinfo=timezone.utc),
                "likes": [user_ids[1], user_ids[0]],
                "dislikes": []
            }
        ]
        post_ids = [(await db.posts.insert_one(post)).inserted_id for post in posts]

        # Обновляем посты у пользователей
        await db.users.update_one(
            {"_id": user_ids[0]},
            {"$push": {"posts": post_ids[0]}}
        )
        await db.users.update_one(
            {"_id": user_ids[1]},
            {"$push": {"posts": post_ids[1]}}
        )
        print(f"Добавлено {len(post_ids)} постов")

        # 5. Создаем тестовые комментарии
        comments = [
            {"post_id": post_ids[0], "author_id": user_ids[1], "text": "Отличная схема!"},
            {"post_id": post_ids[0], "author_id": user_ids[0], "text": "Спасибо!"},
            {"post_id": post_ids[1], "author_id": user_ids[0], "text": "Красивые животные"}
        ]
        await db.comments.insert_many(comments)
        print(f"Добавлено {len(comments)} комментариев")

        print("\nТестовые данные успешно добавлены!")
        return {
            "user_ids": user_ids,
            "post_ids": post_ids,
            "color_ids": color_ids,
            "action_ids": action_ids
        }
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(insert_test_data())
