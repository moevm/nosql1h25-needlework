import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
from pprint import pprint


async def print_all_data(db):
    """Вывод всей информации из базы данных"""
    print("\n=== ЦВЕТА ===")
    colors = await db.colors.find().to_list(length=None)
    for color in colors:
        print(f"ID: {color['_id']} - {color['name']}")

    print("\n=== ДЕЙСТВИЯ ===")
    actions = await db.actions.find().to_list(length=None)
    for action in actions:
        print(f"ID: {action['_id']} - {action['description']} (длина: {action['length']})")

    print("\n=== ПОЛЬЗОВАТЕЛИ ===")
    users = await db.users.find().to_list(length=None)
    for user in users:
        print(f"\nID: {user['_id']}")
        print(f"Имя: {user['name']} {user['surname']}")
        print(f"Логин: {user['username']}")
        print(f"Статус: {user['status']}")
        print(f"Дата регистрации: {user['registration_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"Количество постов: {len(user['posts'])}")

    print("\n=== ПОСТЫ ===")
    posts = await db.posts.find().to_list(length=None)
    for post in posts:
        author = await db.users.find_one({"_id": post["author_id"]})
        print(f"\nID: {post['_id']}")
        print(f"Название: {post['scheme_name']}")
        print(f"Тип: {post['type']}")
        print(f"Автор: {author['name']} {author['surname']}")
        print(f"Описание: {post['description']}")
        print(f"Комментарий автора: {post['comment']}")
        print(f"Лайков: {len(post['likes'])}")
        print(f"Дизлайков: {len(post['dislikes'])}")
        print(f"Дата создания: {post['created_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"Есть превью: {'Да' if 'preview_image_id' in post else 'Нет'}")

        # Вывод комментариев к посту
        comments = await db.comments.find({"post_id": post["_id"]}).to_list(length=None)
        if comments:
            print("\nКомментарии:")
            for comment in comments:
                comment_author = await db.users.find_one({"_id": comment["author_id"]})
                print(f"- {comment_author['name']}: {comment['text']}")


async def main():
    # Инициализация подключения
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.embroidery_db

    try:
        # Выводим всю информацию
        await print_all_data(db)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())