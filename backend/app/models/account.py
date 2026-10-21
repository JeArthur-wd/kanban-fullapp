"""Request models for sign-in, sign-up and account settings."""

from pydantic import BaseModel, Field

from app.config import PASSWORD_MIN_CHARS


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=200)
    password: str = Field(..., max_length=200)


class RegisterRequest(BaseModel):
    # The username pattern is checked in the route, after it is lower-cased.
    username: str = Field(..., max_length=200)
    password: str = Field(..., min_length=PASSWORD_MIN_CHARS, max_length=200)
    display_name: str = Field(default="", max_length=80)


class ProfileUpdate(BaseModel):
    display_name: str = Field(..., max_length=80)


class PasswordChange(BaseModel):
    current_password: str = Field(..., max_length=200)
    new_password: str = Field(..., min_length=PASSWORD_MIN_CHARS, max_length=200)


class AccountDelete(BaseModel):
    password: str = Field(..., max_length=200)
