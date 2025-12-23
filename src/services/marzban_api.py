import asyncio
import uuid
import random 

class MarzbanAPI:
    """
    Класс для работы с API Marzban.
    """

    async def create_key(self, username: str) -> str:
        await asyncio.sleep(1)

        fake_uuid = str(uuid.uuid4())

        key = f"vless://{fake_uuid}@1.1.1.1:443?security=reality&sni=google.com&fp=chrome&type=tcp&headerType=none#{username}_TEST"

        return key

    async def get_user_usage(self, username: str) -> int:
        """
        Возвращает текущий использованный трафик пользователя (в байтах).
        """
        # TODO: Здесь должен быть реальный запрос к API Marzban: GET /api/user/{username}
        # resp = await client.get(f"/api/user/{username}")
        # return resp.json().get('used_traffic', 0)
        
        await asyncio.sleep(0.1)
        return random.randint(100, 50000000)  # Mock: возвращает случайное число для теста

    async def get_user_status(self, username: str) -> dict:
        """
        Возвращает статус пользователя (онлайн и т.д.)
        """
        await asyncio.sleep(0.1)
        return {"online": random.randint(0, 2)}
    
api = MarzbanAPI()