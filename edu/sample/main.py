from fastapi import FastAPI
import uvicorn


app = FastAPI()

@app.get("/")
def hello():
    return {"message": "안녕하세요"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8100, reload=True)