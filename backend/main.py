from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import asyncio
import threading
import time
from typing import Dict, List, Optional
import logging
from datetime import datetime

# Importações do seu bot original
from binance.client import Client
from binance.exceptions import BinanceAPIException
from requests.exceptions import ConnectionError
from dotenv import load_dotenv

app = FastAPI(title="Binance Trading Bot API", version="1.0.0")

# CORS para permitir frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carrega variáveis de ambiente
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Cliente Binance global
client = None

# Estado global do bot
bot_state = {
    "running": False,
    "thread": None,
    "start_time": None,
    "positions": {},
    "logs": []
}

# Modelos Pydantic
class BotConfig(BaseModel):
    limit: int = 100
    leverage: int = 15
    risk_per_trade_percent: float = 0.5
    max_risk_usdt_per_trade: float = 1.0
    test_mode: bool = True
    kline_interval_minutes: int = 5
    kline_trend_period: int = 50
    kline_pullback_period: int = 10
    kline_atr_period: int = 14
    min_atr_multiplier_for_entry: float = 1.5
    max_symbols_to_monitor: int = 5
    risk_reward_ratio: float = 2.0

class APICredentials(BaseModel):
    api_key: str
    api_secret: str

class BotStatus(BaseModel):
    running: bool
    start_time: Optional[str]
    uptime: Optional[str]
    positions_count: int
    test_mode: bool

# Função para inicializar o cliente Binance (do seu código original)
def initialize_binance_client():
    global client
    if not API_KEY or not API_SECRET:
        print("[ERRO] Variáveis de ambiente BINANCE_API_KEY ou BINANCE_API_SECRET não encontradas.")
        return False

    try:
        temp_client = Client(API_KEY, API_SECRET)
        temp_client.futures_ping()  # Testa a conexão
        client = temp_client
        print("[INFO] Cliente Binance Futures inicializado com sucesso.")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao inicializar cliente Binance: {e}")
        client = None
        return False

# Função para obter saldo (baseada na sua função mostrar_saldo())
def get_binance_balance():
    global client
    if client is None:
        if not initialize_binance_client():
            return None
    
    try:
        # Obter saldo da conta Futures
        account_info = client.futures_account()
        balance_info = client.futures_account_balance()
        
        # Encontrar saldo USDT
        usdt_balance = None
        for asset in balance_info:
            if asset["asset"] == "USDT":
                usdt_balance = asset
                break
        
        if not usdt_balance:
            return None
        
        # Obter informações da conta
        total_wallet_balance = float(account_info['totalWalletBalance'])
        total_unrealized_pnl = float(account_info['totalUnrealizedProfit'])
        total_margin_balance = float(account_info['totalMarginBalance'])
        available_balance = float(account_info['availableBalance'])
        
        # Calcular saldo em uso (margem utilizada)
        used_balance = total_margin_balance - available_balance
        
        return {
            "total_balance": total_margin_balance,
            "available_balance": available_balance,
            "used_balance": max(0, used_balance),  # Garantir que não seja negativo
            "unrealized_pnl": total_unrealized_pnl,
            "total_wallet_balance": total_wallet_balance,
            "currency": "USDT",
            "margin_ratio": float(account_info.get('totalMaintMargin', 0)) / total_margin_balance * 100 if total_margin_balance > 0 else 0
        }
        
    except Exception as e:
        print(f"[ERRO] Falha ao obter saldo: {e}")
        return None

# Função para obter posições abertas
def get_open_positions():
    global client
    if client is None:
        if not initialize_binance_client():
            return []
    
    try:
        positions = client.futures_position_information()
        open_positions = []
        
        for position in positions:
            position_amt = float(position['positionAmt'])
            if position_amt != 0:  # Apenas posições abertas
                entry_price = float(position['entryPrice'])
                mark_price = float(position['markPrice'])
                unrealized_pnl = float(position['unRealizedProfit'])
                
                # Calcular PnL percentual
                pnl_percent = 0
                if entry_price > 0:
                    pnl_percent = ((mark_price - entry_price) / entry_price) * 100
                    if position_amt < 0:  # Posição short
                        pnl_percent = -pnl_percent
                
                open_positions.append({
                    "symbol": position['symbol'],
                    "side": "LONG" if position_amt > 0 else "SHORT",
                    "size": abs(position_amt),
                    "entry_price": entry_price,
                    "current_price": mark_price,
                    "pnl": unrealized_pnl,
                    "pnl_percent": pnl_percent,
                    "status": "OPEN",
                    "leverage": float(position['leverage']),
                    "margin": float(position['initialMargin'])
                })
        
        return open_positions
        
    except Exception as e:
        print(f"[ERRO] Falha ao obter posições: {e}")
        return []

# Inicializar cliente na inicialização do app
@app.on_event("startup")
async def startup_event():
    initialize_binance_client()

# Endpoints
@app.get("/")
async def root():
    return {"message": "Binance Trading Bot API", "status": "online"}

@app.get("/status", response_model=BotStatus)
async def get_bot_status():
    uptime = None
    if bot_state["running"] and bot_state["start_time"]:
        uptime_seconds = time.time() - bot_state["start_time"]
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime = f"{hours}h {minutes}m"
    
    # Obter configuração atual para test_mode
    test_mode = True
    try:
        with open("config/settings.json", "r") as f:
            config = json.load(f)
            test_mode = config.get("test_mode", True)
    except:
        pass
    
    return BotStatus(
        running=bot_state["running"],
        start_time=bot_state.get("start_time"),
        uptime=uptime,
        positions_count=len(get_open_positions()),
        test_mode=test_mode
    )

@app.get("/config")
async def get_config():
    try:
        with open("config/settings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return BotConfig().dict()

@app.post("/config")
async def update_config(config: BotConfig):
    try:
        os.makedirs("config", exist_ok=True)
        with open("config/settings.json", "w") as f:
            json.dump(config.dict(), f, indent=2)
        return {"message": "Configuração atualizada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/credentials")
async def update_credentials(credentials: APICredentials):
    global API_KEY, API_SECRET, client
    try:
        with open(".env", "w") as f:
            f.write(f"BINANCE_API_KEY={credentials.api_key}\n")
            f.write(f"BINANCE_API_SECRET={credentials.api_secret}\n")
        
        # Atualizar variáveis globais
        API_KEY = credentials.api_key
        API_SECRET = credentials.api_secret
        
        # Reinicializar cliente
        client = None
        initialize_binance_client()
        
        return {"message": "Credenciais atualizadas com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start")
async def start_bot(background_tasks: BackgroundTasks):
    if bot_state["running"]:
        raise HTTPException(status_code=400, detail="Bot já está rodando")
    
    bot_state["running"] = True
    bot_state["start_time"] = time.time()
    
    return {"message": "Bot iniciado com sucesso"}

@app.post("/stop")
async def stop_bot():
    if not bot_state["running"]:
        raise HTTPException(status_code=400, detail="Bot não está rodando")
    
    bot_state["running"] = False
    bot_state["start_time"] = None
    
    return {"message": "Bot parado com sucesso"}

@app.get("/logs")
async def get_logs():
    try:
        logs = []
        if os.path.exists("logs/bot_activity.log"):
            with open("logs/bot_activity.log", "r", encoding="utf-8") as f:
                lines = f.readlines()
                logs = [line.strip() for line in lines[-100:]]
        return {"logs": logs}
    except Exception as e:
        return {"logs": [], "error": str(e)}

@app.get("/positions")
async def get_positions():
    try:
        positions = get_open_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/balance")
async def get_balance():
    try:
        balance_data = get_binance_balance()
        if balance_data is None:
            raise HTTPException(status_code=500, detail="Não foi possível obter saldo da Binance")
        
        return balance_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter saldo: {str(e)}")

@app.post("/positions/{symbol}/close")
async def close_position(symbol: str):
    global client
    if client is None:
        raise HTTPException(status_code=500, detail="Cliente Binance não inicializado")
    
    try:
        # Obter informação da posição
        positions = client.futures_position_information(symbol=symbol)
        position = None
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                position = pos
                break
        
        if not position:
            raise HTTPException(status_code=404, detail="Posição não encontrada")
        
        position_amt = float(position['positionAmt'])
        
        # Determinar lado da ordem para fechar
        side = Client.SIDE_SELL if position_amt > 0 else Client.SIDE_BUY
        quantity = abs(position_amt)
        
        # Enviar ordem de mercado para fechar
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity,
            reduceOnly=True
        )
        
        return {"message": f"Posição {symbol} fechada com sucesso", "order_id": order['orderId']}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fechar posição: {str(e)}")

@app.post("/test-connection")
async def test_connection():
    try:
        if initialize_binance_client():
            balance = get_binance_balance()
            if balance:
                return {
                    "status": "success",
                    "message": "Conexão com Binance estabelecida com sucesso",
                    "balance": balance
                }
            else:
                return {
                    "status": "error",
                    "message": "Conexão estabelecida mas falha ao obter saldo"
                }
        else:
            return {
                "status": "error",
                "message": "Falha ao conectar com Binance"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro na conexão: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
