from motor.motor_asyncio import AsyncIOMotorClient


async def clear_database():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://db:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.embroidery_db

    # Удаление всех коллекций
    collections = await db.list_collection_names()
    for collection_name in collections:
        await db[collection_name].delete_many({})

    print("Все коллекции очищены")


# Запуск
if __name__ == "__main__":
    import asyncio

    asyncio.run(clear_database())
