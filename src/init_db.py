import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorGridFSBucket
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Tuple, Optional, BinaryIO
from io import BytesIO
from pprint import pprint

# Глобальные переменные для подключения
client = None
db = None
fs = None


class User:
    def __init__(self, db: AsyncIOMotorCollection):
        self.collection = db.users

    async def create_user(self, username: str, status: str, name: str, surname: str, password: str) -> ObjectId:
        user = {
            "username": username[:20],
            "registration_at": datetime.now(timezone.utc),
            "status": status[:10],
            "name": name[:50],
            "surname": surname[:50],
            "password": password[:100],
            "posts": []
        }
        result = await self.collection.insert_one(user)
        return result.inserted_id

    async def get_user_info(self, user_id: ObjectId) -> Optional[dict]:
        return await self.collection.find_one({"_id": user_id})

    async def get_all_users(self) -> List[dict]:
        return await self.collection.find().to_list(None)


class Post:
    def __init__(self, db: AsyncIOMotorCollection):
        self.collection = db.posts

    async def create_post(self, preview_image: BinaryIO, scheme: List[List[Tuple[ObjectId, ObjectId]]],
                          legend: List[Tuple[str, str]], type: str, scheme_name: str,
                          description: str, comment: str, author_id: ObjectId) -> ObjectId:
        # Сохраняем изображение в GridFS
        preview_id = await fs.upload_from_stream(
            f"preview_{scheme_name}.jpg",
            preview_image,
            metadata={"contentType": "image/jpeg"}
        )

        # Получаем все действия для быстрого доступа к длинам
        actions = {action['_id']: action['length'] for action in await db.actions.find().to_list(None)}

        # Подсчет общей длины и уникальных цветов
        unique_colors = set()
        total_length = 0

        for row in scheme:
            for color_id, action_id in row:
                unique_colors.add(color_id)
                action_length = actions.get(action_id, 0)
                total_length += action_length

        post = {
            "preview_image_id": preview_id,
            "scheme": [[(str(color_id), str(action_id)) for color_id, action_id in row] for row in scheme],
            "legend": legend,
            "type": type[:10],
            "scheme_name": scheme_name[:50],
            "description": description[:512],
            "comment": comment[:512],
            "author_id": author_id,
            "color_count": len(unique_colors),
            "length": total_length,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "likes": [],
            "dislikes": []
        }
        result = await self.collection.insert_one(post)
        await db.users.update_one(
            {"_id": author_id},
            {"$push": {"posts": result.inserted_id}}
        )
        return result.inserted_id

    async def get_post_preview(self, post_id: ObjectId) -> Optional[bytes]:
        post = await self.get_post_info(post_id)
        if not post or "preview_image_id" not in post:
            return None

        grid_out = await fs.open_download_stream(post["preview_image_id"])
        return await grid_out.read()

    async def add_like(self, post_id: ObjectId, user_id: ObjectId) -> bool:
        post = await self.get_post_info(post_id)
        if not post or user_id in post['likes']:
            return False

        updates = {"$addToSet": {"likes": user_id}}
        if user_id in post['dislikes']:
            updates["$pull"] = {"dislikes": user_id}

        result = await self.collection.update_one(
            {"_id": post_id},
            updates
        )
        return result.modified_count > 0

    async def add_dislike(self, post_id: ObjectId, user_id: ObjectId) -> bool:
        post = await self.get_post_info(post_id)
        if not post or user_id in post['dislikes']:
            return False

        updates = {"$addToSet": {"dislikes": user_id}}
        if user_id in post['likes']:
            updates["$pull"] = {"likes": user_id}

        result = await self.collection.update_one(
            {"_id": post_id},
            updates
        )
        return result.modified_count > 0

    async def get_post_info(self, post_id: ObjectId) -> Optional[dict]:
        return await self.collection.find_one({"_id": post_id})

    async def get_all_posts(self) -> List[dict]:
        return await self.collection.find().to_list(None)


class Comment:
    def __init__(self, db: AsyncIOMotorCollection):
        self.collection = db.comments

    async def create_comment(self, post_id: ObjectId, author_id: ObjectId, text: str) -> ObjectId:
        comment = {
            "post_id": post_id,
            "author_id": author_id,
            "text": text[:512]
        }
        result = await self.collection.insert_one(comment)
        return result.inserted_id

    async def get_comments_for_post(self, post_id: ObjectId) -> List[dict]:
        return await self.collection.find({"post_id": post_id}).to_list(None)


class Action:
    def __init__(self, db: AsyncIOMotorCollection):
        self.collection = db.actions

    async def create_action(self, description: str, length: int) -> ObjectId:
        action = {
            "description": description[:64],
            "length": length
        }
        result = await self.collection.insert_one(action)
        return result.inserted_id

    async def get_all_actions(self) -> List[dict]:
        return await self.collection.find().to_list(None)


class Color:
    def __init__(self, db: AsyncIOMotorCollection):
        self.collection = db.colors

    async def create_color(self, name: str) -> ObjectId:
        color = {
            "name": name[:10]
        }
        result = await self.collection.insert_one(color)
        return result.inserted_id

    async def get_all_colors(self) -> List[dict]:
        return await self.collection.find().to_list(None)


async def init_collections():
    """Инициализация индексов"""
    await db.users.create_index("username", unique=True)
    await db.posts.create_index("author_id")
    await db.comments.create_index("post_id")
    await db.actions.create_index("description")
    await db.colors.create_index("name")

async def list_collections():
    """Выводит список всех коллекций в базе данных"""
    collections = await db.list_collection_names()
    print("Доступные коллекции в базе данных:")
    for collection in collections:
        print(f"- {collection}")



async def main():
    global client, db, fs

    # Инициализация подключения
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.embroidery_db
    fs = AsyncIOMotorGridFSBucket(db)

    await init_collections()
    await list_collections()


if __name__ == "__main__":
    asyncio.run(main())