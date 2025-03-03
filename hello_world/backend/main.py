from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorClient

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the database connection
    await startup_db_client(app)
    yield
    # Close the database connection
    await shutdown_db_client(app)


# method for start the MongoDb Connection
async def startup_db_client(app):
    app.mongodb_client = AsyncIOMotorClient("mongodb://mongo:27017/")
    app.mongodb = app.mongodb_client.get_database("test")
    print("MongoDB connected.")


# method to close the database connection
async def shutdown_db_client(app):
    app.mongodb_client.close()
    print("Database disconnected.")


# creating a server with python FastAPI
app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://localhost:80",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/test/{item_id}")
async def get_data(item_id: str):
    result = await app.mongodb["test_collection"].find_one({"_id": ObjectId(item_id)})
    if result:
        result['_id'] = str(result['_id'])
        return result
    else:
        raise HTTPException(status_code=404, detail=f"Unable to retrieve record")


@app.post("/test")
async def write_data(data_dict: dict):
    result = await app.mongodb["test_collection"].insert_one(data_dict)
    inserted_data = await app.mongodb["test_collection"].find_one({"_id": result.inserted_id})
    if inserted_data:
        inserted_data['_id'] = str(inserted_data['_id'])
        return inserted_data
    else:
        raise HTTPException(status_code=404, detail=f"Unable to retrieve record")


@app.get('/test')
async def get_all_data():
    result = await app.mongodb["test_collection"].find().to_list()
    for i in range(len(result)):
        result[i]['_id'] = str(result[i]['_id'])
    return result


# hello world endpoint
@app.get("/")
def read_root():  # function that is binded with the endpoint
    return {"Hello": "Aboba"}
