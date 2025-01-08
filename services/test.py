import asyncio
import sys
import os
import httpx
import jwt

encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
