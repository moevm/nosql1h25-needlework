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


async def insert_test_data():
    """Вставка тестовых данных с реальными изображениями"""
    # Подключение к MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.embroidery_db
    fs = AsyncIOMotorGridFSBucket(db)

    try:
        # 1. Создаем тестовые цвета
        colors = ["Красный", "Синий", "Зеленый", "Черный", "Белый"]
        color_ids = [(await db.colors.insert_one({"name": color})).inserted_id for color in colors]
        print(f"Добавлено {len(color_ids)} цветов")

        # 2. Создаем тестовые действия
        actions = [
            {"description": "Крестик", "length": 10},
            {"description": "Полукрест", "length": 5},
            {"description": "Гобеленовый", "length": 15},
            {"description": "Стебельчатый", "length": 8}
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
                "registration_at": datetime.now(timezone.utc)
            },
            {
                "username": "user2",
                "status": "admin",
                "name": "Иван",
                "surname": "Петров",
                "password": "pass456",
                "posts": [],
                "registration_at": datetime.now(timezone.utc)
            }
        ]
        user_ids = [(await db.users.insert_one(user)).inserted_id for user in users]
        print(f"Добавлено {len(user_ids)} пользователей")

        images_dir = Path("images")
        images_dir.mkdir(exist_ok=True)

        # 4. Создаем тестовые посты с реальными изображениями
        posts = [
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo1.jpg",
                    "цветочный_узор.jpg"
                ),
                "scheme": [[(1, 10), (2, 15)], [(3, 20), (4, 25)]],
                "legend": [("1", "красный"), ("2", "синий")],
                "type": "вышивка",
                "scheme_name": "Цветочный узор",
                "description": "Схема для вышивки цветов",
                "comment": "Используйте нитки DMC",
                "author_id": user_ids[0],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "likes": [user_ids[1]],
                "dislikes": []
            },
            {
                "preview_image_id": await upload_image_from_file(
                    fs,
                    images_dir / "photo2.jpg",
                    "животные.jpg"
                ),
                "scheme": [[(4, 30), (5, 10)], [(1, 15), (5, 20)]],
                "legend": [("4", "черный"), ("5", "белый")],
                "type": "вышивка",
                "scheme_name": "Животные",
                "description": "Схема с животными",
                "comment": "Рекомендую канву Aida 16",
                "author_id": user_ids[1],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "likes": [user_ids[0]],
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