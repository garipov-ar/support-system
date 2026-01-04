import pickle
import redis
from typing import Any, Dict, Optional, Tuple, cast
from telegram.ext import BasePersistence, PersistenceInput

class RedisPersistence(BasePersistence):
    def __init__(
        self,
        url: str,
        store_data: Optional[PersistenceInput] = None,
    ):
        super().__init__(store_data=store_data)
        self.redis = redis.from_url(url)

    async def get_user_data(self) -> Dict[int, Any]:
        data = self.redis.get("user_data")
        return pickle.loads(data) if data else {}

    async def get_chat_data(self) -> Dict[int, Any]:
        data = self.redis.get("chat_data")
        return pickle.loads(data) if data else {}

    async def get_bot_data(self) -> Dict[Any, Any]:
        data = self.redis.get("bot_data")
        return pickle.loads(data) if data else {}

    async def get_conversations(self, name: str) -> Dict[Tuple[Any, ...], Any]:
        data = self.redis.get(f"conv:{name}")
        return pickle.loads(data) if data else {}

    async def update_user_data(self, user_id: int, data: Any) -> None:
        full_data = await self.get_user_data()
        full_data[user_id] = data
        self.redis.set("user_data", pickle.dumps(full_data))

    async def update_chat_data(self, chat_id: int, data: Any) -> None:
        full_data = await self.get_chat_data()
        full_data[chat_id] = data
        self.redis.set("chat_data", pickle.dumps(full_data))

    async def update_bot_data(self, data: Any) -> None:
        self.redis.set("bot_data", pickle.dumps(data))

    async def update_conversation(self, name: str, key: Tuple[Any, ...], new_state: Optional[Any]) -> None:
        full_data = await self.get_conversations(name)
        if new_state is None:
            full_data.pop(key, None)
        else:
            full_data[key] = new_state
        self.redis.set(f"conv:{name}", pickle.dumps(full_data))

    async def flush(self) -> None:
        pass # We update in real-time in this implementation

    async def drop_chat_data(self, chat_id: int) -> None:
        pass

    async def drop_user_data(self, user_id: int) -> None:
        pass

    async def refresh_bot_data(self, bot_data: Any) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: Any) -> None:
        pass

    async def refresh_user_data(self, user_id: int, user_data: Any) -> None:
        pass

    # Added for compatibility with PTB 20.x
    async def get_callback_data(self) -> Optional[cast(Any, Tuple[Any, ...])]:
        data = self.redis.get("callback_data")
        return pickle.loads(data) if data else None

    async def update_callback_data(self, data: cast(Any, Tuple[Any, ...])) -> None:
        self.redis.set("callback_data", pickle.dumps(data))
