import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorGridFSBucket
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Tuple, Optional, BinaryIO
from io import BytesIO
from pprint import pprint
import os

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

    async def create_post(self, preview_image: BinaryIO, scheme_name: str,
                          description: str, comment: str, author_id: ObjectId) -> ObjectId:
        # Сохраняем изображение в GridFS
        preview_id = await fs.upload_from_stream(
            f"preview_{scheme_name}.jpg",
            preview_image,
            metadata={"contentType": "image/jpeg"}
        )

        post = {
            "preview_image_id": preview_id,
            "scheme_name": scheme_name[:50],
            "description": description[:512],
            "comment": comment[:512],
            "author_id": author_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
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
            "text": text[:512],
            "likes": []
        }
        result = await self.collection.insert_one(comment)
        return result.inserted_id

    async def get_comments_for_post(self, post_id: ObjectId) -> List[dict]:
        return await self.collection.find({"post_id": post_id}).to_list(None)


async def init_collections():
    """Инициализация индексов"""
    await db.users.create_index("username", unique=True)
    await db.posts.create_index("author_id")
    await db.comments.create_index("post_id")

async def list_collections():
    """Выводит список всех коллекций в базе данных"""
    collections = await db.list_collection_names()
    print("Доступные коллекции в базе данных:")
    for collection in collections:
        print(f"- {collection}")



async def main():
    global client, db, fs

    # Инициализация подключения
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://db:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.embroidery_db
    fs = AsyncIOMotorGridFSBucket(db)

    await init_collections()
    await list_collections()


if __name__ == "__main__":
    asyncio.run(main())
