from fastapi import FastAPI


# Creating FastAPI instance/object
app = FastAPI()


@app.get('/api/v1/')
def root():
    return {'message': 'FastAPI Complete Authentication'}
