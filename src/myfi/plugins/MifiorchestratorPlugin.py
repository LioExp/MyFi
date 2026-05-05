import httpx
from base64 import b64encode
from hashlib import sha256

async with httpx.AsyncClient() as client:
    # 1. Obter cookie inicial (qualquer página)
    await client.get("http://192.168.0.1/index.html")
    # 2. Login
    username_b64 = b64encode(b"MyFi 4G").decode()
    password_hash = sha256(b"your password").hexdigest()
    password_b64 = b64encode(password_hash.encode()).decode()
    resp = await client.post(
        "http://192.168.0.1/reqproc/proc_post",
        data={
            "isTest": "false",
            "goformId": "LOGIN",
            "username": username_b64,
            "password": password_b64,
        },
        headers={"X-Requested-With": "XMLHttpRequest"}
    )
    # A sessão fica autenticada via cookie random.
