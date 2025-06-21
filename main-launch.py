# inside launch.py (alternative version)
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main-serve:app", reload=True, port=8000)
