import asyncio
import aiohttp
import os
from datetime import datetime

class KeepAlive:
    def __init__(self, url: str, interval: int = 840):  # 14 minutos
        self.url = url
        self.interval = interval
        self.running = False
        
    async def ping_self(self):
        """Faz ping na própria aplicação para mantê-la ativa"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/health") as response:
                    if response.status == 200:
                        print(f"[KEEP-ALIVE] ✅ Ping successful at {datetime.now()}")
                    else:
                        print(f"[KEEP-ALIVE] ⚠️ Ping failed with status {response.status}")
        except Exception as e:
            print(f"[KEEP-ALIVE] ❌ Ping error: {e}")
    
    async def start(self):
        """Inicia o keep-alive loop"""
        self.running = True
        print(f"[KEEP-ALIVE] 🚀 Started - pinging every {self.interval} seconds")
        
        while self.running:
            await self.ping_self()
            await asyncio.sleep(self.interval)
    
    def stop(self):
        """Para o keep-alive"""
        self.running = False
        print("[KEEP-ALIVE] 🛑 Stopped")

# Instância global
keep_alive = None
