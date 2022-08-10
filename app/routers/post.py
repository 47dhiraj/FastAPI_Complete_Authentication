import uuid
from .. import schemas, models
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, APIRouter, Response
from ..database import get_db
from app.oauth2 import require_user


# APIRouter object/instance create gareko
router = APIRouter()


@router.get('/', response_model=schemas.ListPostResponse)
def get_posts(db: Session = Depends(get_db), limit: int = 10, page: int = 1, search: str = '', user_id: str = Depends(require_user)):
    skip = (page - 1) * limit

    posts = db.query(models.Post).group_by(models.Post.id).filter(models.Post.title.contains(search)).limit(limit).offset(skip).all()

    return {'status': 'success', 'results': len(posts), 'posts': posts}



@router.post('/', status_code=status.HTTP_201_CREATED, response_model=schemas.PostResponse)
def create_post(post: schemas.CreatePostSchema, db: Session = Depends(get_db), owner_id: str = Depends(require_user)):
    post.user_id = uuid.UUID(owner_id)                      # jwt batw aayeko owner_id or user_id chai uuid hudaina, so database ma save garne bela ma chai uuid format ma convert gareko, becuase, hamile database ko table ma UUID format ma id lai rakhi rako chau

    new_post = models.Post(**post.dict())                   # new post object create gareko

    db.add(new_post)
    db.commit()                                             # database ma save gareko
    db.refresh(new_post)

    return new_post                                         # newly create gareko post lai return gareko



@router.put('/{id}', response_model=schemas.PostResponse)
def update_post(id: str, post: schemas.UpdatePostSchema, db: Session = Depends(get_db), user_id: str = Depends(require_user)):

    post_query = db.query(models.Post).filter(models.Post.id == id)
    post_to_update = post_query.first()

    if not post_to_update:
        raise HTTPException(status_code=status.HTTP_200_OK, detail=f'Post with this id: {id}, not found')

    # checking if the user is owner of the post
    if post_to_update.user_id != uuid.UUID(user_id):            # uuid.UUID(user_id) kina gareko vanda, jwt batw access gareko user_id lai ORM query ma user garna ko lagi UUID ma convert garna parcha, becuase, hamile database ko table ma UUID format ma id lai rakhi rako chau
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Unauthorized action')

    post_query.update(post.dict(), synchronize_session=False)
    db.commit()                                                 # saving the update/changes to the database
    db.refresh(post_to_update)

    return post_to_update                                       # update gareko post lai return gareko



@router.get('/{id}', response_model=schemas.PostResponse)
def get_post(id: str, db: Session = Depends(get_db), user_id: str = Depends(require_user)):

    post = db.query(models.Post).filter(models.Post.id == id).first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with this id: {id}, not found")

    return post                         # single post lai as response return gareko



@router.delete('/{id}')
def delete_post(id: str, db: Session = Depends(get_db), user_id: str = Depends(require_user)):

    post_query = db.query(models.Post).filter(models.Post.id == id)
    post = post_query.first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Post with this id: {id}, not found')

    if post.owner_id != user_id:                                # for checking if the user is owner of the post
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Unauthorized action')

    post_query.delete(synchronize_session=False)
    db.commit()                                                 # saving the update/changes to the database

    return Response(status_code=status.HTTP_204_NO_CONTENT)     # object delete gari sake pachi, just 204 No Content status code matra as a response ko rup ma pathaincha

