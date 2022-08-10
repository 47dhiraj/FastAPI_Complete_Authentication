from datetime import timedelta
import hashlib
from random import randbytes
from fastapi import APIRouter, Request, Response, status, Depends, HTTPException
from pydantic import EmailStr

from app import oauth2
from .. import schemas, models, utils
from sqlalchemy.orm import Session
from ..database import get_db
from app.oauth2 import AuthJWT
from ..config import settings
from ..email import Email


router = APIRouter()        # creating router object

ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN



@router.post('/register', status_code=status.HTTP_201_CREATED)
async def create_user(payload: schemas.CreateUserSchema, request: Request, db: Session = Depends(get_db)):

    # Check if user already exist
    user_query = db.query(models.User).filter(models.User.email == EmailStr(payload.email.lower()))
    user = user_query.first()
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Account already exist')

    # Compare password and passwordConfirm
    if payload.password != payload.passwordConfirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Passwords do not match')

    #  Hash the password
    payload.password = utils.hash_password(payload.password)
    del payload.passwordConfirm

    payload.role = 'user'
    payload.verified = False
    payload.email = EmailStr(payload.email.lower())

    new_user = models.User(**payload.dict())                    # yo line le new user object create garcha
    db.add(new_user)
    db.commit()
    db.refresh(new_user)                                        # latest create vayeko user object lai database batw fetch garera dincha

    try:
        # Send Verification Email
        token = randbytes(10)
        hashedCode = hashlib.sha256()
        hashedCode.update(token)
        verification_code = hashedCode.hexdigest()
        user_query.update({'verification_code': verification_code}, synchronize_session=False)
        db.commit()                                             # email send garna vanda pahila, user ko email verification code lai database ma save gareko

        url = f"{request.url.scheme}://{request.client.host}:{request.url.port}/api/v1/auth/verifyemail/{token.hex()}"

        await Email(new_user, url, [payload.email]).sendVerificationCode()      # yo line le email.py ko Email class ko constructor lai call garcha & then only, sendVerificationCode() vanni function lai call garcha

    except Exception as error:
        print('Error', error)

        user_query.update({'verification_code': None}, synchronize_session=False)
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='There was an error sending email')


    return {'status': 'success', 'message': 'Verification token successfully sent to your email'}




@router.post('/login')
def login(payload: schemas.LoginUserSchema, response: Response, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    # Check if the user exist
    user = db.query(models.User).filter(models.User.email == EmailStr(payload.email.lower())).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid Credentials')

    # Check if user verified his email
    if not user.verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Please verify your account')

    # Check if the password is valid
    if not utils.verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid Credentials')

    # Creating/Generating access token
    access_token = Authorize.create_access_token(subject=str(user.id), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))

    # Creating/Generating refresh token
    refresh_token = Authorize.create_refresh_token(subject=str(user.id), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))

    # Store refresh token in cookie
    response.set_cookie('refresh_token', refresh_token, REFRESH_TOKEN_EXPIRES_IN * 60, REFRESH_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')

    response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60, ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')

    # sending access_token as json response to the frontend
    return {'status': 'success', 'access_token': access_token}



@router.get('/refresh')
def refresh_token(response: Response, request: Request, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    try:
        Authorize.jwt_refresh_token_required()              # surumai valid refresh token cha ki nai vanera check garcha
        user_id = Authorize.get_jwt_subject()               # refresh token batw user_id lai grab garcha

        if not user_id:                                     # yedi user_id vetena vani
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized/Invalid token')

        user = db.query(models.User).filter(models.User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token or token expired')

        # Creating/Generating new access token
        access_token = Authorize.create_access_token(subject=str(user.id), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))

        # Creating/Generating new Refresh token
        refresh_token = Authorize.create_refresh_token(subject=str(user.id), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))

    except Exception as e:
        error = e.__class__.__name__
        if error == 'MissingTokenError':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Please provide refresh token')

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Store refresh_token in cookie
    response.set_cookie('refresh_token', refresh_token, REFRESH_TOKEN_EXPIRES_IN * 60, REFRESH_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')

    response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60, ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')

    # Sending access_token as json response
    return {'access_token': access_token}



@router.get('/logout', status_code=status.HTTP_200_OK)
def logout(response: Response, Authorize: AuthJWT = Depends(), user_id: str = Depends(oauth2.require_user)):

    Authorize.unset_jwt_cookies()                           # removing the cookies(i.e refresh_token) from the frontend

    response.set_cookie('logged_in', '', -1)

    return {'status': 'success'}



@router.get('/verifyemail/{token}')                         # route for verifying the email address for newly registered user
def verify_me(token: str, db: Session = Depends(get_db)):

    hashedCode = hashlib.sha256()
    hashedCode.update(bytes.fromhex(token))                 # token ko help batw verification feri regenerate garcha
    verification_code = hashedCode.hexdigest()

    user_query = db.query(models.User).filter(models.User.verification_code == verification_code)   # user ko database ma vayeko verification code ra uta email ko url ma click garera re-generate vayeko verification code match huna parcha
    # db.commit()

    user = user_query.first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Email can only be verified once')

    user_query.update({'verified': True, 'verification_code': None}, synchronize_session=False)     # yo line le user lai verify garcha & verfication_code lai database ma null set garcha

    db.commit()                 # saving the changes to the database

    return {
        "status": "success",
        "message": "Account verified successfully"
    }


