import time
from typing import Optional, Set, Tuple

try:
    import redis.asyncio as aioredis  # pip install redis
except Exception:
    aioredis = None  # optional


class RolePermsCache:
    """Cache role permissions keyed by (role_id, rv) with TTL.
       Uses Redis if provided, otherwise in-memory map.
    """

    def __init__(self, ttl_seconds: int = 300, redis_client: Optional["aioredis.Redis"] = None):
        self.ttl = ttl_seconds
        self.redis = redis_client
        self._mem: dict[Tuple[int, int], Tuple[float, Set[str]]] = {}

    def _mem_get(self, key: Tuple[int, int]) -> Optional[Set[str]]:
        v = self._mem.get(key)
        if not v:
            return None
        exp, perms = v
        if time.time() > exp:
            self._mem.pop(key, None)
            return None
        return perms

    def _mem_set(self, key: Tuple[int, int], perms: Set[str]):
        self._mem[key] = (time.time() + self.ttl, perms)

    async def get(self, role_id: int, rv: int) -> Optional[Set[str]]:
        key = f"role:{role_id}:rv:{rv}"
        if self.redis:
            data = await self.redis.smembers(key)
            return set(map(lambda b: b.decode() if isinstance(b, (bytes, bytearray)) else b, data)) if data else None
        else:
            return self._mem_get((role_id, rv))

    async def set(self, role_id: int, rv: int, perms: Set[str]):
        key = f"role:{role_id}:rv:{rv}"
        if self.redis:
            if perms:
                await self.redis.delete(key)
                await self.redis.sadd(key, *perms)
                await self.redis.expire(key, self.ttl)
            else:
                await self.redis.delete(key)
        else:
            self._mem_set((role_id, rv), perms)
