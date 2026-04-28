import aiohttp
from src.config import settings

class MarzbanAPI:
    def __init__(self):
        self.host = settings.MARZBAN_HOST
        self.username = settings.MARZBAN_USERNAME
        self.password = settings.MARZBAN_PASSWORD

    async def _get_token(self) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.host}/api/admin/token",
                data={"username": self.username, "password": self.password}
            ) as resp:
                data = await resp.json()
                return data["access_token"]

    async def _headers(self):
        token = await self._get_token()
        return {"Authorization": f"Bearer {token}"}

    async def create_key(self, username: str, expire_timestamp: int = 0, data_limit_gb: int = 0) -> tuple:
        """
        创建或获取用户
        expire_timestamp: Unix时间戳，0=永不过期
        data_limit_gb: 流量限制GB，0=不限制
        """
        headers = await self._headers()
        data_limit_bytes = data_limit_gb * 1024**3 if data_limit_gb > 0 else 0

        payload = {
            "username": username,
            "proxies": {
                "vless": {"flow": "xtls-rprx-vision"},
                "vmess": {},
                "trojan": {},
                "shadowsocks": {"method": "chacha20-ietf-poly1305"}
            },
            "inbounds": {
                "vless": ["VLESS_REALITY","VLESS_WS_TLS","VLESS_GRPC_TLS","VLESS_HTTPUPGRADE_TLS"],
                "vmess": ["VMESS_WS_TLS","VMESS_GRPC_TLS","VMESS_HTTPUPGRADE_TLS"],
                "trojan": ["TROJAN_TCP_TLS","TROJAN_WS_TLS","TROJAN_GRPC_TLS"],
                "shadowsocks": ["SHADOWSOCKS_TCP"]
            },
            "expire": expire_timestamp,
            "data_limit": data_limit_bytes,
            "data_limit_reset_strategy": "month" if data_limit_gb > 0 else "no_reset",
            "status": "active"
        }

        async with aiohttp.ClientSession() as session:
            # 先尝试获取已有用户
            async with session.get(
                f"{self.host}/api/user/{username}",
                headers=headers
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    # 更新到期时间和流量
                    update_payload = {
                        "expire": expire_timestamp,
                        "data_limit": data_limit_bytes,
                        "data_limit_reset_strategy": "month" if data_limit_gb > 0 else "no_reset",
                        "status": "active"
                    }
                    async with session.put(
                        f"{self.host}/api/user/{username}",
                        json=update_payload,
                        headers=headers
                    ) as ur:
                        if ur.status == 200:
                            data = await ur.json()
                else:
                    # 用户不存在，创建
                    async with session.post(
                        f"{self.host}/api/user",
                        json=payload,
                        headers=headers
                    ) as resp:
                        data = await resp.json()

        vless_key = ""
        links = data.get("links", [])
        for link in links:
            if link.startswith("vless://"):
                vless_key = link
                break
        if not vless_key and links:
            vless_key = links[0]

        sub_url = data.get("subscription_url", "")
        if sub_url and not sub_url.startswith("http"):
            sub_url = self.host + sub_url

        return vless_key, sub_url

    async def update_user_expire(self, username: str, expire_timestamp: int, data_limit_gb: int = 0):
        """单独更新用户到期时间和流量"""
        headers = await self._headers()
        data_limit_bytes = data_limit_gb * 1024**3 if data_limit_gb > 0 else 0
        payload = {
            "expire": expire_timestamp,
            "data_limit": data_limit_bytes,
            "data_limit_reset_strategy": "month" if data_limit_gb > 0 else "no_reset",
            "status": "active"
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.host}/api/user/{username}",
                json=payload,
                headers=headers
            ) as r:
                return await r.json()

    async def get_subscription_url(self, username: str) -> str:
        """获取最新订阅链接"""
        try:
            headers = await self._headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/api/user/{username}",
                    headers=headers
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        sub_url = data.get("subscription_url", "")
                        if sub_url and not sub_url.startswith("http"):
                            sub_url = self.host + sub_url
                        return sub_url
        except Exception:
            pass
        return ""

    async def get_user_status(self, username: str) -> dict:
        try:
            headers = await self._headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/api/user/{username}",
                    headers=headers
                ) as resp:
                    data = await resp.json()
                    return {"online": 1 if data.get("online_at") else 0}
        except Exception:
            return {"online": 0}

    async def get_user_usage(self, username: str) -> int:
        try:
            headers = await self._headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/api/user/{username}",
                    headers=headers
                ) as resp:
                    data = await resp.json()
                    return data.get("used_traffic", 0)
        except Exception:
            return 0

    async def list_users_by_prefix(self, prefix: str = "trial_") -> list:
        """列出所有用户名以 prefix 开头的用户"""
        try:
            headers = await self._headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/api/users?username={prefix}&limit=500",
                    headers=headers,
                ) as r:
                    data = await r.json()
                    return data.get("users", [])
        except Exception:
            return []

    async def delete_user(self, username: str) -> bool:
        """删除用户"""
        try:
            headers = await self._headers()
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.host}/api/user/{username}",
                    headers=headers,
                ) as r:
                    return r.status in (200, 204)
        except Exception:
            return False

    async def cleanup_expired_trials(self, prefix: str = "trial_") -> int:
        """删除所有已过期的 trial 账号,返回删除的数量"""
        import time as _time
        users = await self.list_users_by_prefix(prefix)
        now = int(_time.time())
        deleted = 0
        for u in users:
            username = u.get("username", "")
            if not username.startswith(prefix):
                continue
            expire = u.get("expire")
            # 把 ISO 字符串转回时间戳判断
            is_expired = False
            if isinstance(expire, str):
                try:
                    from datetime import datetime
                    e = datetime.fromisoformat(expire.replace("Z", "+00:00"))
                    is_expired = e.timestamp() <= now
                except Exception:
                    is_expired = False
            elif isinstance(expire, (int, float)):
                is_expired = expire and expire <= now
            # 如果状态已是 expired/limited 也算
            if u.get("status") in ("expired", "limited", "disabled"):
                is_expired = True
            if is_expired:
                ok = await self.delete_user(username)
                if ok:
                    deleted += 1
        return deleted




api = MarzbanAPI()
