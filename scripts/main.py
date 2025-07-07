import os
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException
from requests.exceptions import ConnectionError
from dotenv import load_dotenv
import json
import sys
import decimal
import statistics 
import math 
from functools import wraps
import logging # Importa o módulo de logging

# --- Configuração de Logging ---
# Garante que o diretório de logs exista
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configura o logger raiz
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Limpa quaisquer handlers existentes para evitar duplicação ou conflitos
if logger.hasHandlers():
    logger.handlers.clear()

# Configura o FileHandler para salvar logs em um arquivo com UTF-8
file_handler = logging.FileHandler(os.path.join(log_dir, 'bot_activity.log'), mode='a', encoding='utf-8')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Configura o StreamHandler para exibir logs no console com UTF-8
# Usa sys.stdout para garantir que a saída vá para o console padrão
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
console_handler.encoding = 'utf-8' # <--- ESTA É A LINHA CRÍTICA PARA UTF-8 NO CONSOLE
logger.addHandler(console_handler)

# Define o logger específico para o módulo (se você usa o __name__)
# Isso garante que todas as mensagens do seu código usem esta configuração
logger = logging.getLogger(__name__)


# --- Carrega variáveis de ambiente ---
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# --- Variáveis globais do bot ---
client = None
CONFIG_FILE_PATH = "config/settings.json"
SYMBOL_INFO = {} 
LEVERAGE_SET_FOR_SYMBOL = {} 
OPEN_POSITIONS = {} 
TIME_OFFSET_MS = 0 

# --- Configurações para Reconexão, Monitoramento de Ordens e Retries ---
RECONNECT_INTERVAL_SECONDS = 10 # Intervalo para tentar reconectar à API
ORDER_MONITOR_INTERVAL_SECONDS = 2 # Intervalo para verificar o status de ordens
ORDER_FILL_TIMEOUT_SECONDS = 60 # Tempo máximo para uma ordem ser preenchida
MAX_RETRIES = 3 # Número máximo de tentativas para chamadas de API
RETRY_DELAY_SECONDS = 2 # Atraso inicial entre as tentativas de retry
CYCLE_SLEEP_SECONDS = 6 # Tempo de espera entre os ciclos principais do bot

# --- Decorador para adicionar lógica de retry a chamadas de API ---
def retry_api_call(max_retries=MAX_RETRIES, delay=RETRY_DELAY_SECONDS):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, BinanceAPIException) as e:
                    logger.warning(f"[RETRY] Tentativa {i+1}/{max_retries} falhou para {func.__name__}: {e}")
                    if i < max_retries - 1:
                        time.sleep(delay * (2 ** i)) # Atraso exponencial
                    else:
                        logger.error(f"[RETRY] Todas as tentativas falharam para {func.__name__}. Erro: {e}")
                        raise # Re-lança a exceção após todas as tentativas
                except Exception as e:
                    logger.error(f"[ERRO] Erro inesperado em {func.__name__}: {e}")
                    raise # Re-lança exceções inesperadas
        return wrapper
    return decorator

# --- Função para inicializar o cliente Binance de forma robusta e sincronizar o tempo ---
def initialize_binance_client():
    global client, TIME_OFFSET_MS
    if not API_KEY or not API_SECRET:
        logger.critical("[ERRO CRÍTICO] Variáveis de ambiente BINANCE_API_KEY ou BINANCE_API_SECRET não encontradas ou estão vazias.")
        logger.critical("Por favor, configure-as em seu arquivo .env.")
        client = None
        return False

    try:
        temp_client = Client(API_KEY, API_SECRET)
        temp_client.futures_ping() # Testa a conexão
        client = temp_client # Atribui o cliente globalmente
        
        # Sincroniza o tempo para evitar erros de timestamp
        server_time_ms = client.futures_time()['serverTime']
        local_time_ms = int(time.time() * 1000)
        TIME_OFFSET_MS = server_time_ms - local_time_ms
        client.timestamp_offset = TIME_OFFSET_MS # Define o offset no cliente

        logger.info("[INFO] Cliente Binance Futures inicializado e conectado com sucesso.")
        return True
    except Exception as e:
        logger.critical(f"[ERRO CRÍTICO] Falha ao inicializar ou conectar o cliente Binance Futures: {e}")
        logger.critical("Verifique suas chaves de API e sua conexão com a internet.")
        client = None
        return False

# --- Função para carregar configurações do arquivo JSON ---
def load_config_from_json():
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        logger.critical(f"[ERRO CRÍTICO] Arquivo de configuração '{CONFIG_FILE_PATH}' não encontrado.")
        logger.critical("O bot não pode operar sem as configurações. Por favor, crie a pasta 'config' e o arquivo 'settings.json' dentro dela.")
        return None
    except json.JSONDecodeError as e:
        logger.critical(f"[ERRO CRÍTICO] Erro ao decodificar JSON em '{CONFIG_FILE_PATH}': {e}")
        logger.critical("Verifique a sintaxe do seu seu arquivo 'settings.json'.")
        return None
    except Exception as e:
        logger.critical(f"[ERRO CRÍTICO] Ocorreu um erro inesperado ao carregar o arquivo de configuração: {e}")
        return None

# --- Função para obter informações de precisão dos símbolos da Binance ---
@retry_api_call()
def get_exchange_info():
    global SYMBOL_INFO
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível obter informações da exchange.")
        return
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['contractType'] == 'PERPETUAL' and s['status'] == 'TRADING':
            lot_size_filter = next((f for f in s['filters'] if f['filterType'] == 'LOT_SIZE'), None)
            price_filter = next((f for f in s['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
            min_notional_filter = next((f for f in s['filters'] if f['filterType'] == 'MIN_NOTIONAL'), None)
            market_lot_size_filter = next((f for f in s['filters'] if f['filterType'] == 'MARKET_LOT_SIZE'), None) 

            if lot_size_filter and price_filter and min_notional_filter and market_lot_size_filter:
                quantity_precision = -decimal.Decimal(lot_size_filter['stepSize']).normalize().as_tuple().exponent
                if quantity_precision < 0: quantity_precision = 0
                price_precision = -decimal.Decimal(price_filter['tickSize']).normalize().as_tuple().exponent
                if price_precision < 0: price_precision = 0

                SYMBOL_INFO[s['symbol']] = {
                    'quantity_precision': quantity_precision,
                    'price_precision': price_precision,
                    'min_qty': float(lot_size_filter['minQty']),
                    'max_qty': float(lot_size_filter['maxQty']),
                    'min_price': float(price_filter['minPrice']),
                    'max_price': float(price_filter['maxPrice']), 
                    'step_size': float(lot_size_filter['stepSize']),
                    'min_notional': float(min_notional_filter['notional']),
                    'market_max_qty': float(market_lot_size_filter['maxQty']) 
                }
    logger.info("[INFO] Informações de precisão dos símbolos carregadas com sucesso da Binance.")

# --- Função para mostrar o saldo de USDT na conta Futures ---
@retry_api_call()
def mostrar_saldo():
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível obter saldo.")
        return 0.0
    info = client.futures_account_balance()
    available_balance = 0.0
    for ativo in info:
        if ativo["asset"] == "USDT":
            available_balance = float(ativo['availableBalance'])
            logger.info(f"💰 Saldo Futures USDT: Total = {ativo['balance']} | Disponível = {available_balance}")
            return available_balance
    logger.warning("[AVISO] Saldo USDT não encontrado na conta Futures.")
    return 0.0

# --- Função robusta para obter o preço de mercado atual ---
def get_current_market_price(symbol_name, max_retries=MAX_RETRIES, delay=RETRY_DELAY_SECONDS):
    global client
    for i in range(max_retries):
        try:
            if not isinstance(client, Client) or not hasattr(client, 'futures_ticker_price'):
                logger.warning(f"[RECUPERAÇÃO] Cliente Binance não está pronto para obter preço. Tentando re-inicializar ({i+1}/{max_retries})...")
                if not initialize_binance_client():
                    logger.error(f"[ERRO] Falha ao re-inicializar cliente para obter preço para {symbol_name}.")
                    if i < max_retries - 1:
                        time.sleep(delay)
                    continue
                else:
                    logger.info(f"[INFO] Cliente Binance re-inicializado com sucesso para obter preço.")
                    time.sleep(1) 

            ticker_price = client.futures_ticker_price(symbol=symbol_name)
            return float(ticker_price['price'])
        except Exception as e:
            logger.warning(f"[AVISO] Falha ao obter preço de mercado para {symbol_name} (tentativa {i+1}/{max_retries}): {e}. Tentando novamente.")
            if i < max_retries - 1:
                time.sleep(delay)
    logger.error(f"[ERRO] Não foi possível obter o preço de mercado para {symbol_name} após {max_retries} tentativas.")
    return None

# --- Funções de Indicadores Técnicos ---
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    ema = [0.0] * len(prices)
    ema[period - 1] = sum(prices[:period]) / period
    multiplier = 2 / (period + 1)
    for i in range(period, len(prices)):
        ema[i] = ((prices[i] - ema[i-1]) * multiplier) + ema[i-1]
    return ema[-1] 

def calculate_atr(klines, period):
    if len(klines) < period:
        return None
    
    true_ranges = []
    for i in range(1, len(klines)):
        high = float(klines[i][2])
        low = float(klines[i][3])
        prev_close = float(klines[i-1][4])
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_ranges.append(max(tr1, tr2, tr3))
    
    if len(true_ranges) < period:
        return None

    atr_values = [0.0] * len(true_ranges)
    atr_values[period - 1] = sum(true_ranges[:period]) / period 
    
    multiplier = 2 / (period + 1)
    for i in range(period, len(true_ranges)):
        atr_values[i] = ((true_ranges[i] - atr_values[i-1]) * multiplier) + atr_values[i-1]
        
    return atr_values[-1] 

# --- Função para obter todos os símbolos de Futuros USDT ---
@retry_api_call()
def get_all_usdt_futures_symbols():
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível obter a lista de símbolos.")
        return []
    
    try:
        exchange_info = client.futures_exchange_info()
        usdt_symbols = []
        for s in exchange_info['symbols']:
            if s['symbol'].endswith('USDT') and s['contractType'] == 'PERPETUAL' and s['status'] == 'TRADING':
                usdt_symbols.append(s['symbol'])
        logger.info(f"[INFO] Encontrados {len(usdt_symbols)} pares USDT perpétuos negociáveis.")
        return usdt_symbols
    except Exception as e:
        logger.error(f"[ERRO] Falha ao obter todos os símbolos de Futuros USDT: {e}")
        return []

# --- Função para varrer e selecionar os melhores símbolos ---
@retry_api_call()
def scan_and_select_best_symbols(kline_interval_minutes, kline_trend_period, kline_pullback_period, kline_atr_period, min_atr_multiplier_for_entry, max_symbols_to_monitor): 
    global client
    all_usdt_symbols = get_all_usdt_futures_symbols()
    if not all_usdt_symbols:
        logger.warning("[AVISO] Nenhuma lista de símbolos USDT disponível para varredura. Retornando lista vazia.")
        return []

    selected_symbols_data = [] 
    
    kline_interval_map = {
        1: Client.KLINE_INTERVAL_1MINUTE,
        5: Client.KLINE_INTERVAL_5MINUTE,
        15: Client.KLINE_INTERVAL_15MINUTE,
        30: Client.KLINE_INTERVAL_30MINUTE,
        60: Client.KLINE_INTERVAL_1HOUR,
        240: Client.KLINE_INTERVAL_4HOUR,
        1440: Client.KLINE_INTERVAL_1DAY
    }
    kline_interval_str = kline_interval_map.get(kline_interval_minutes)
    
    required_klines_count = max(kline_trend_period, kline_pullback_period, kline_atr_period) + 2 
    
    logger.info(f"\n--- Iniciando Varredura de Mercado para os Melhores Pares ({kline_interval_minutes}m Klines) ---")
    logger.info(f"Critérios: Tendência de Alta, Volatilidade Suficiente (ATR).") 

    for symbol in all_usdt_symbols:
        try:
            if symbol not in SYMBOL_INFO:
                get_exchange_info() 
                if symbol not in SYMBOL_INFO:
                    logger.info(f"[SCAN] {symbol}: Informações de precisão não disponíveis. Pulando.")
                    continue

            klines = client.futures_klines(symbol=symbol, interval=kline_interval_str, limit=required_klines_count)
            if not klines or len(klines) < required_klines_count:
                continue
            
            close_prices = [float(kline[4]) for kline in klines]
            
            ema_trend = calculate_ema(close_prices, kline_trend_period)
            if ema_trend is None:
                continue

            current_price = float(klines[-1][4]) 

            is_uptrend = current_price > ema_trend
            
            atr = calculate_atr(klines, kline_atr_period)
            if atr is None:
                continue
            
            min_atr_threshold = SYMBOL_INFO[symbol]['step_size'] * 5 * min_atr_multiplier_for_entry
            if atr < min_atr_threshold:
                logger.info(f"[SCAN] {symbol}: Volatilidade (ATR {atr:.{SYMBOL_INFO[symbol]['price_precision']}f}) abaixo do mínimo ({min_atr_threshold:.{SYMBOL_INFO[symbol]['price_precision']}f}). Sem sinal.")
                continue

            if is_uptrend:
                selected_symbols_data.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'ema_trend': ema_trend,
                    'atr': atr
                })
                logger.info(f"[SCAN] ✅ {symbol}: Selecionado! Preço: {current_price:.{SYMBOL_INFO[symbol]['price_precision']}f}, EMA Tendência: {ema_trend:.{SYMBOL_INFO[symbol]['price_precision']}f}, ATR: {atr:.{SYMBOL_INFO[symbol]['price_precision']}f}")

        except Exception as e:
            logger.error(f"[ERRO SCAN] Falha ao analisar {symbol}: {e}")

    selected_symbols_data.sort(key=lambda x: x['atr'], reverse=False) # Ordena por ATR, menos volátil primeiro
    
    final_selected_symbols = [s['symbol'] for s in selected_symbols_data[:max_symbols_to_monitor]]

    logger.info(f"\n--- Varredura Concluída. {len(final_selected_symbols)} Pares Selecionados para Monitoramento ---")
    logger.info(f"Pares Selecionados: {final_selected_symbols}")
    return final_selected_symbols

# --- Função para calcular SL/TP baseado no ATR ---
def calculate_atr_based_sl_tp(current_price, atr_value, side, risk_reward_ratio, price_precision):
    sl_multiplier = 2.0 
    tp_multiplier = sl_multiplier * risk_reward_ratio

    sl_price = None
    tp_price = None

    if side == Client.SIDE_BUY: 
        sl_price = current_price - (atr_value * sl_multiplier)
        tp_price = current_price + (atr_value * tp_multiplier)
    elif side == Client.SIDE_SELL: 
        sl_price = current_price + (atr_value * sl_multiplier)
        tp_price = current_price - (atr_value * tp_multiplier)
    
    if sl_price is not None:
        sl_price = round(sl_price, price_precision)
    if tp_price is not None:
        tp_price = round(tp_price, price_precision)
        
    if side == Client.SIDE_BUY and sl_price >= current_price:
        sl_price = current_price * 0.99 
        logger.warning(f"[AVISO] SL para {side} ajustado para {sl_price:.{price_precision}f} (fallback).")
    elif side == Client.SIDE_SELL and sl_price <= current_price:
        sl_price = current_price * 1.01 
        logger.warning(f"[AVISO] SL para {side} ajustado para {sl_price:.{price_precision}f} (fallback).")

    if side == Client.SIDE_BUY and tp_price <= current_price:
        tp_price = current_price * 1.01 
        logger.warning(f"[AVISO] TP para {side} ajustado para {tp_price:.{price_precision}f} (fallback).")
    elif side == Client.SIDE_SELL and tp_price >= current_price:
        tp_price = current_price * 0.99 
        logger.warning(f"[AVISO] TP para {side} ajustado para {tp_price:.{price_precision}f} (fallback).")

    return sl_price, tp_price

# --- Função para calcular a quantidade da ordem a ser negociada (com gerenciamento de risco e min_notional) ---
def calcular_quantidade_ordem(entrada_preco, available_balance, stop_loss_price,
                              leverage_val, risk_per_trade_percent, max_risk_usdt_per_trade, symbol_name):
    if symbol_name not in SYMBOL_INFO:
        logger.error(f"[ERRO] Informações de símbolo para {symbol_name} não encontradas. Não é possível calcular a quantidade.")
        return None

    info = SYMBOL_INFO[symbol_name]
    
    if entrada_preco <= 0:
        logger.error("[ERRO] Preço de entrada inválido para cálculo de quantidade.")
        return None

    price_diff = abs(entrada_preco - stop_loss_price)
    if stop_loss_price is None or price_diff < info['step_size'] * 2: 
        logger.error("[ERRO] Preço de Stop Loss inválido ou muito próximo do preço de entrada para cálculo de quantidade.")
        return None
    
    sl_value_per_unit = price_diff 
    
    risk_usdt_from_percent = available_balance * (risk_per_trade_percent / 100)
    risk_usdt = min(risk_usdt_from_percent, max_risk_usdt_per_trade)
    
    if risk_usdt <= 0:
        logger.warning("[AVISO] Risco calculado é zero ou negativo. Não é possível calcular a quantidade da ordem.")
        return None

    # 1. Calcula a quantidade baseada no risco
    quantidade_base_risco = risk_usdt / sl_value_per_unit
    
    step_size = info['step_size']
    quantity_precision = info['quantity_precision']
    min_qty = info['min_qty']
    max_qty = info['max_qty']
    min_notional = info.get('min_notional', 5.0) # Obtém o min_notional do SYMBOL_INFO, com fallback
    market_max_qty = info.get('market_max_qty', max_qty) 

    # 2. Calcula a quantidade mínima para atender ao valor nocional
    # Arredonda para cima para garantir que o mínimo nocional seja atendido
    quantidade_min_notional_raw = min_notional / entrada_preco
    quantidade_min_notional = math.ceil(quantidade_min_notional_raw / step_size) * step_size
    quantidade_min_notional = round(quantidade_min_notional, quantity_precision)

    # 3. A quantidade final deve ser a MAIOR entre a calculada pelo risco e a mínima pelo nocional
    # Isso garante que o requisito de min_notional seja sempre atendido primeiro
    quantidade_final = max(quantidade_base_risco, quantidade_min_notional)
    
    # Arredonda para baixo para o step_size mais próximo para garantir que não exceda o saldo
    quantidade_final = math.floor(quantidade_final / step_size) * step_size 
    quantidade_final = round(quantidade_final, quantity_precision)

    # Log para informar ajuste de nocional
    # Se a quantidade final calculada (que já atende ao min_notional) for maior que a base de risco
    if quantidade_final > quantidade_base_risco and quantidade_base_risco > 0:
        logger.warning(f"[AVISO] Quantidade ajustada de {quantidade_base_risco:.{quantity_precision}f} para {quantidade_final:.{quantity_precision}f} para atender ao valor nocional mínimo ({min_notional:.2f} USDT).")
    elif quantidade_final < min_notional / entrada_preco and quantidade_final > 0: # Se por algum arredondamento ficou abaixo do nocional
        logger.warning(f"[AVISO] Quantidade calculada ({quantidade_final:.{quantity_precision}f}) é menor que a necessária para o valor nocional mínimo ({min_notional:.2f} USDT). Forçando ajuste.")
        quantidade_final = quantidade_min_notional
        logger.info(f"[INFO] Quantidade ajustada para {quantidade_final} para atender ao valor nocional mínimo.")


    # 4. Verifica limites de quantidade da exchange (min_qty, max_qty, market_max_qty)
    if quantidade_final < min_qty:
        logger.warning(f"[AVISO] Quantidade calculada ({quantidade_final}) menor que a mínima ({min_qty}) para {symbol_name}. Não é possível abrir posição.")
        return None 
    elif quantidade_final > max_qty:
        logger.warning(f"[AVISO] Quantidade calculada ({quantidade_final}) maior que a máxima ({max_qty}) para {symbol_name}. Ajustando para max_qty.")
        quantidade_final = max_qty
    
    if quantidade_final > market_max_qty:
        logger.warning(f"[AVISO] Quantidade calculada ({quantidade_final}) maior que a máxima permitida para ordem de mercado ({market_max_qty}) para {symbol_name}. Ajustando para market_max_qty.")
        quantidade_final = market_max_qty
        
    # Arredonda novamente após todos os ajustes de limites
    quantidade_final = round(quantidade_final / step_size) * step_size
    quantidade_final = round(quantidade_final, quantity_precision)
    
    # 5. Verifica se há margem suficiente para a quantidade final (que já atende ao min_notional e outros filtros)
    initial_margin_needed = (entrada_preco * quantidade_final) / leverage_val
    if initial_margin_needed > available_balance:
        logger.error(f"[ERRO] Saldo insuficiente para a margem inicial calculada ({initial_margin_needed:.2f} USDT) para {symbol_name}. Disponível: {available_balance:.2f} USDT. Não é possível abrir esta posição com o valor nocional mínimo exigido.")
        return None 

    return quantidade_final

# --- Função para enviar ordens (TESTE ou REAL) ---
def enviar_ordem(symbol, quantity, price, side, order_type, test_mode, time_in_force=None, stop_price=None, reduce_only=False):
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível enviar ordem.")
        return None
    params = {
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'quantity': quantity,
    }
    if price is not None: 
        params['price'] = price
    if time_in_force:
        params['timeInForce'] = time_in_force
    if stop_price:
        params['stopPrice'] = stop_price
    
    if reduce_only:
        params['reduceOnly'] = True
        
    if order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET'] and 'price' in params:
         del params['price']

    if test_mode: 
        logger.info(f"--- SIMULANDO ORDEM (TESTE) para {symbol} ---")
        # Em modo de teste, simula um preenchimento completo para ordens de mercado,
        # e um status 'FILLED' para ordens limit/stop.
        simulated_status = 'FILLED' if order_type == 'MARKET' and reduce_only is not True else 'NEW' 
        simulated_avg_price = price if price else get_current_market_price(symbol)
        if simulated_avg_price is None: simulated_avg_price = 0.0 # Valor de fallback
        
        logger.info(f"✅ Ordem de TESTE {order_type} {side} para {symbol} simulada com sucesso. Status: {simulated_status}, Preço Médio: {simulated_avg_price}")
        return {'orderId': f'TEST_ORDER_{int(time.time())}_{symbol}_{order_type}', 'status': simulated_status, 'executedQty': quantity if simulated_status == 'FILLED' else 0.0, 'avgPrice': simulated_avg_price} 
    else:
        logger.info(f"--- ENVIANDO ORDEM REAL para {symbol} ---")
        try:
            response = client.futures_create_order(**params)
            
            # Se for uma ordem de mercado, monitore até que seja FILLED
            if order_type == 'MARKET':
                order_id = response.get('orderId')
                if order_id:
                    start_time = time.time()
                    while time.time() - start_time < ORDER_FILL_TIMEOUT_SECONDS:
                        order_info = client.futures_get_order(symbol=symbol, orderId=order_id)
                        current_status = order_info['status']
                        executed_qty = float(order_info['executedQty'])
                        avg_price = float(order_info['avgPrice'])

                        if current_status == 'FILLED' and executed_qty >= quantity: # Garante que foi preenchida totalmente
                            logger.info(f"✅ Ordem REAL MARKET {side} para {symbol} preenchida com sucesso! ID: {order_id}, Quantidade: {executed_qty}, Preço Médio: {avg_price}")
                            return order_info # Retorna a informação completa da ordem preenchida
                        elif current_status in ['CANCELED', 'EXPIRED', 'REJECTED', 'PARTIALLY_FILLED']:
                            # Se a ordem foi cancelada, expirou, rejeitada ou preenchida parcialmente (e não totalmente)
                            logger.warning(f"[AVISO] Ordem REAL MARKET {side} para {symbol} não foi totalmente preenchida. Status: {current_status}, Executado: {executed_qty}/{quantity}.")
                            return order_info # Retorna o status atual para que a lógica de erro possa lidar
                        
                        logger.info(f"⏳ Aguardando preenchimento da ordem MARKET {order_id} para {symbol}. Status atual: {current_status}, Executado: {executed_qty}/{quantity}")
                        time.sleep(ORDER_MONITOR_INTERVAL_SECONDS)
                    
                    logger.warning(f"[AVISO] Tempo limite excedido para preenchimento da ordem MARKET {order_id} para {symbol}. Status final: {current_status}, Executado: {executed_qty}/{quantity}")
                    return order_info # Retorna o último status conhecido
                else:
                    logger.error(f"[ERRO] Ordem MARKET {side} para {symbol} não retornou um orderId. Falha no envio inicial.")
                    return {'orderId': None, 'status': 'FAILED', 'executedQty': 0.0, 'avgPrice': 0.0}
            else: # Para ordens que não são MARKET (STOP_MARKET, TAKE_PROFIT_MARKET, etc.)
                clean_message = f"✅ Ordem REAL {order_type} {side} para {symbol} enviada com sucesso."
                clean_message += f" ID: {response.get('orderId')}"
                clean_message += f", Quantidade Solicitada: {response.get('origQty')}"
                clean_message += f", Quantidade Preenchida: {response.get('executedQty')}"
                clean_message += f", Status: {response.get('status')}"
                
                if response.get('avgPrice') and float(response.get('avgPrice', 0.0)) > 0:
                    clean_message += f", Preço Médio: {response.get('avgPrice')}"
                if response.get('stopPrice') and order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                    clean_message += f", Preço de Gatilho: {response.get('stopPrice')}"
                
                logger.info(clean_message)
                return response
        except Exception as e:
            logger.error(f"Falha ao enviar ordem REAL para {symbol}: {e}")
            return {'orderId': None, 'status': 'FAILED', 'executedQty': 0.0, 'avgPrice': 0.0}


# --- Função para monitorar o status de uma ordem LIMIT (mantida para referência, mas não usada para entrada MARKET) ---
@retry_api_call()
def monitor_limit_order_status(symbol_name, order_id, timeout_seconds, test_mode, tp_price_target):
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível monitorar ordem.")
        return 'ERROR'
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if test_mode: 
            logger.info(f"[SIMULAÇÃO] Ordem de teste {order_id} para {symbol_name} assumida como FILLED.")
            return 'FILLED' 
        
        order_info = client.futures_get_order(symbol=symbol_name, orderId=order_id)
        status = order_info['status']

        current_market_price = get_current_market_price(symbol_name) 

        if current_market_price is None:
            logger.warning(f"[AVISO] Não foi possível obter preço de mercado durante monitoramento da ordem {order_id}. Continuando...")
            time.sleep(ORDER_MONITOR_INTERVAL_SECONDS)
            continue

        if tp_price_target is not None and current_market_price >= tp_price_target:
            logger.info(f"[OPORTUNIDADE PERDIDA] Preço de mercado ({current_market_price:.{SYMBOL_INFO[symbol_name]['price_precision']}f}) atingiu ou ultrapassou o TP teórico ({tp_price_target:.{SYMBOL_INFO[symbol_name]['price_precision']}f}) antes da ordem de entrada {order_id} ser preenchida. Cancelando ordem.")
            cancel_all_open_orders_for_symbol(symbol_name, test_mode)
            return 'MISSED_OPPORTUNITY'

        logger.info(f"[MONITOR] Status da ordem {order_id} para {symbol_name}: {status}")

        if status == 'FILLED':
            return 'FILLED'
        elif status in ['CANCELED', 'EXPIRED', 'REJECTED']:
            return 'CANCELED' 
        
        time.sleep(ORDER_MONITOR_INTERVAL_SECONDS) 
            
    logger.warning(f"[MONITOR] Tempo limite ({timeout_seconds}s) excedido para ordem {order_id} de {symbol_name}.")
    return 'TIMEOUT'

# --- Função para cancelar todas as ordens abertas para um símbolo ---
@retry_api_call()
def cancel_all_open_orders_for_symbol(symbol_name, test_mode):
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível cancelar ordens.")
        return None
    logger.info(f"⏳ Tentando cancelar todas as ordens abertas para {symbol_name}...")
    if test_mode: 
        logger.info(f"✅ SIMULAÇÃO: Todas as ordens abertas para {symbol_name} canceladas.")
        return [{'orderId': f'TEST_CANCEL_{int(time.time())}'}] 
    else:
        try:
            response = client.futures_cancel_all_open_orders(symbol=symbol_name)
            logger.info(f"✅ Ordens abertas para {symbol_name} canceladas: {response}")
            return response
        except BinanceAPIException as e:
            # Trata caso onde não há ordens abertas (código 20011)
            if e.code == -2011: # Código de erro da Binance para 'No orders exist'
                logger.info(f"Não há ordens abertas para {symbol_name} para cancelar.")
                return []
            else:
                logger.error(f"Erro ao cancelar ordens para {symbol_name}: {e}")
                raise # Re-lança outras exceções

# --- Função para verificar e fechar posições abertas reais (APENAS as não rastreadas pelo bot) ---
def check_and_close_untracked_positions(symbol_name, test_mode):
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível verificar posições não rastreadas.")
        return False
    positions = client.futures_position_information(symbol=symbol_name)
    
    for position in positions:
        position_amount = float(position['positionAmt'])
        
        if position_amount != 0 and symbol_name not in OPEN_POSITIONS:
            logger.warning(f"[POSIÇÃO REAL - NÃO RASTREADA] Posição aberta detectada para {symbol_name}: {position_amount} unidades. Fechando...")
            cancel_all_open_orders_for_symbol(symbol_name, test_mode) 
            close_side = Client.SIDE_SELL if position_amount > 0 else Client.SIDE_BUY
            quantity_to_close = abs(position_amount)

            logger.info(f"⏳ Tentando fechar posição REAL NÃO RASTREADA de {symbol_name} ({quantity_to_close} unidades, lado: {close_side}) via ordem de mercado...")
            
            close_order_response = enviar_ordem(
                symbol=symbol_name,
                quantity=quantity_to_close,
                price=None,
                side=close_side,
                order_type='MARKET',
                time_in_force=None,
                stop_price=None,
                test_mode=test_mode,
                reduce_only=True 
            )
            
            if close_order_response and close_order_response.get('orderId'):
                logger.info(f"✅ Ordem de fechamento de posição REAL NÃO RASTREADA para {symbol_name} enviada com sucesso.")
                return True
            else:
                logger.error(f"[ERRO] Falha ao fechar posição REAL NÃO RASTREADA para {symbol_name}.")
                return False
        elif position_amount != 0 and symbol_name in OPEN_POSITIONS:
            return False
        
    return False

@retry_api_call()
def reconcile_positions_and_orders(symbol_name, test_mode):
    if client is None:
        logger.error("[ERRO] Cliente Binance não inicializado. Não foi possível reconciliar posições.")
        return
    if symbol_name not in OPEN_POSITIONS:
        return

    logger.info(f"⏳ Reconciliando posição para {symbol_name}...")

    actual_positions = client.futures_position_information(symbol=symbol_name)
    position_closed_on_exchange = True
    actual_position_amount = 0.0

    for pos in actual_positions:
        if pos['symbol'] == symbol_name:
            actual_position_amount = float(pos['positionAmt'])
            if actual_position_amount != 0:
                position_closed_on_exchange = False
            break

    actual_open_orders = client.futures_get_open_orders(symbol=symbol_name)
    
    sl_order_id_internal = OPEN_POSITIONS[symbol_name].get('sl_order_id')
    tp_order_id_internal = OPEN_POSITIONS[symbol_name].get('tp_order_id')

    sl_order_exists_on_exchange = False
    tp_order_exists_on_exchange = False

    for order in actual_open_orders:
        if str(order.get('orderId')) == str(sl_order_id_internal):
            sl_order_exists_on_exchange = True
        if str(order.get('orderId')) == str(tp_order_id_internal):
            tp_order_exists_on_exchange = True

    if position_closed_on_exchange:
        logger.info(f"✅ Posição para {symbol_name} está FECHADA na Binance. Removendo do rastreamento interno e cancelando ordens remanescentes.")
        cancel_all_open_orders_for_symbol(symbol_name, test_mode)
        del OPEN_POSITIONS[symbol_name]
    elif not sl_order_exists_on_exchange or not tp_order_exists_on_exchange:
        logger.warning(f"[ALERTA] Posição para {symbol_name} está ABERTA, mas ordens protetoras (SL/TP) estão INCOMPLETAS ou AUSENTES na Binance.")
        logger.warning(f"  SL presente: {sl_order_exists_on_exchange}, TP presente: {tp_order_exists_on_exchange}")
        
        logger.info(f"⏳ Fechando posição desprotegida para {symbol_name} via ordem de mercado para segurança...")
        
        cancel_all_open_orders_for_symbol(symbol_name, test_mode)
        
        close_side = Client.SIDE_SELL if actual_position_amount > 0 else Client.SIDE_BUY
        quantity_to_close = abs(actual_position_amount)

        close_order_response = enviar_ordem(
            symbol=symbol_name,
            quantity=quantity_to_close,
            price=None,
            side=close_side,
            order_type='MARKET',
            test_mode=test_mode,
            reduce_only=True 
        )
        if close_order_response and close_order_response.get('orderId'):
            logger.info(f"✅ Posição desprotegida para {symbol_name} fechada com sucesso via mercado.")
            del OPEN_POSITIONS[symbol_name]
        else:
            logger.error(f"[ERRO] Falha crítica ao fechar posição desprotegida para {symbol_name}. Requer intervenção manual.")
    else:
        logger.info(f"✅ Posição para {symbol_name} está ABERTA e PROTEGIDA na Binance.")


# --- Função para verificar sinal de entrada com base na estratégia de Klines ---
@retry_api_call()
def check_entry_signal(symbol_name, kline_interval_minutes, kline_trend_period, kline_pullback_period, kline_atr_period, min_atr_multiplier_for_entry):
    global client
    
    kline_interval_map = {
        1: Client.KLINE_INTERVAL_1MINUTE,
        5: Client.KLINE_INTERVAL_5MINUTE,
        15: Client.KLINE_INTERVAL_15MINUTE,
        30: Client.KLINE_INTERVAL_30MINUTE,
        60: Client.KLINE_INTERVAL_1HOUR,
        240: Client.KLINE_INTERVAL_4HOUR,
        1440: Client.KLINE_INTERVAL_1DAY
    }
    kline_interval_str = kline_interval_map.get(kline_interval_minutes)

    required_klines_count = max(kline_trend_period, kline_pullback_period, kline_atr_period) + 2 
    
    if not isinstance(client, Client) or not hasattr(client, 'futures_klines'):
        logger.warning(f"[AVISO] Cliente Binance não está pronto para obter Klines para {symbol_name}. Tentando re-inicializar...")
        if not initialize_binance_client():
            logger.error(f"[ERRO] Falha ao re-inicializar cliente para Klines para {symbol_name}.")
            return False, None, None, None 

    try:
        klines = client.futures_klines(symbol=symbol_name, interval=kline_interval_str, limit=required_klines_count)
        
        if not klines or len(klines) < required_klines_count:
            logger.warning(f"[AVISO] Klines insuficientes ({len(klines)}/{required_klines_count}) para {symbol_name} no intervalo {kline_interval_minutes}m para análise de sinal.")
            return False, None, None, None

        close_prices = [float(kline[4]) for kline in klines]
        high_prices = [float(kline[2]) for kline in klines]
        low_prices = [float(kline[3]) for kline in klines] 
        
        current_price = float(klines[-1][4]) 
        current_high = float(klines[-1][2])
        current_low = float(klines[-1][3])

        # --- 1. Calcula Indicadores ---
        ema_trend = calculate_ema(close_prices, kline_trend_period)
        ema_pullback = calculate_ema(close_prices, kline_pullback_period)
        atr = calculate_atr(klines, kline_atr_period)

        if any(x is None for x in [ema_trend, ema_pullback, atr]):
            logger.warning(f"[AVISO] Indicadores (EMA/ATR) não puderam ser calculados para {symbol_name}. Pulando análise de sinal.")
            return False, None, None, None
        
        if symbol_name not in SYMBOL_INFO:
            get_exchange_info() 
            if symbol_name not in SYMBOL_INFO:
                logger.error(f"[ERRO] Informações de precisão para {symbol_name} não disponíveis após recarga. Não é possível continuar a análise de sinal.")
                return False, None, None, None

        price_precision = SYMBOL_INFO[symbol_name]['price_precision']

        logger.info(f"[INFO] Análise ({symbol_name}) ({kline_interval_minutes}m):")
        logger.info(f"Preço={current_price:.{price_precision}f}, EMA({kline_trend_period})={ema_trend:.{price_precision}f}, EMA({kline_pullback_period})={ema_pullback:.{price_precision}f}, ATR({kline_atr_period})={atr:.{price_precision}f}")

        # --- 2. Filtra por Volatilidade (ATR) ---
        min_atr_threshold = SYMBOL_INFO[symbol_name]['step_size'] * 5 * min_atr_multiplier_for_entry
        if atr < min_atr_threshold:
            logger.info(f"[INFO] {symbol_name}: Volatilidade (ATR {atr:.{price_precision}f}) abaixo do mínimo ({min_atr_threshold:.{price_precision}f}). Sem sinal.")
            return False, None, None, None

        # --- 3. Condições para Sinal de Compra (LONG) ---
        is_uptrend = current_price > ema_trend

        pulled_back = False
        if current_price < ema_pullback and current_price > ema_trend:
            pulled_back = True
        elif current_low <= ema_trend and current_price > ema_trend:
            pulled_back = True
        elif len(klines) >= 2:
            prev_low = float(klines[-2][3])
            prev_close = float(klines[-2][4])
            if prev_low <= ema_trend and prev_close < current_price:
                pulled_back = True

        confirmed_resumption = current_price > ema_pullback

        if is_uptrend and pulled_back and confirmed_resumption:
            logger.info(f"[SINAL] ✅ {symbol_name}: Sinal de COMPRA (LONG) detectado!")
            entry_price = current_price 
            
            sl_price, tp_price = calculate_atr_based_sl_tp(entry_price, atr, Client.SIDE_BUY, config['risk_reward_ratio'], price_precision)

            if sl_price is None or tp_price is None:
                logger.warning(f"[AVISO] {symbol_name}: SL ou TP não puderam ser calculados com base no ATR. Sem sinal.")
                return False, None, None, None

            if sl_price >= entry_price or tp_price <= entry_price:
                logger.warning(f"[AVISO] {symbol_name}: SL ({sl_price:.{price_precision}f}) ou TP ({tp_price:.{price_precision}f}) inválidos em relação à entrada ({entry_price:.{price_precision}f}). Sem sinal.")
                return False, None, None, None

            return True, round(entry_price, price_precision), sl_price, tp_price
        else:
            logger.info(f"[INFO] {symbol_name}: Condição (LONG) não atendidas")
            return False, None, None, None

    except Exception as e:
        logger.error(f"[ERRO] Falha na verificação de sinal para {symbol_name}: {e}")
        return False, None, None, None


# --- Função principal de execução do bot ---
@retry_api_call() 
def executar(selected_symbols_for_monitoring_data, leverage_val, 
             risk_per_trade_percent_val, max_risk_usdt_per_trade_val, 
             test_mode_val, kline_interval_minutes, kline_trend_period, 
             kline_pullback_period, kline_atr_period, min_atr_multiplier_for_entry,
             risk_reward_ratio):
    """
    Função principal que coordena a execução do bot, recebendo todas as configurações
    diretamente como argumentos.
    """
    available_balance = mostrar_saldo()

    for symbol_item in selected_symbols_for_monitoring_data: 
        reconcile_positions_and_orders(symbol_item, test_mode_val)

        if symbol_item not in OPEN_POSITIONS: 
            logger.info(f"\n📡 Analisando par: {symbol_item}") 
            
            if symbol_item not in LEVERAGE_SET_FOR_SYMBOL or not LEVERAGE_SET_FOR_SYMBOL[symbol_item]:
                try:
                    if client:
                        client.futures_change_leverage(symbol=symbol_item, leverage=leverage_val)
                        logger.info(f"[INFO] Alavancagem para {symbol_item} definida para {leverage_val}x.")
                        LEVERAGE_SET_FOR_SYMBOL[symbol_item] = True
                    else:
                        logger.error(f"[ERRO] Cliente Binance não inicializado. Não foi possível definir alavancagem para {symbol_item}.")
                        continue
                except Exception as e:
                    logger.error(f"[ERRO] Falha ao definir alavancagem para {symbol_item}: {e}")
                    continue

            has_signal, entry_price, sl_price, tp_price = check_entry_signal(
                symbol_item, kline_interval_minutes, kline_trend_period, 
                kline_pullback_period, kline_atr_period, min_atr_multiplier_for_entry
            )

            if has_signal:
                logger.info(f"[SINAL DE ENTRADA] Condições atendidas para LONG em {symbol_item}.")
                
                quantidade = calcular_quantidade_ordem(
                    entry_price, available_balance, sl_price,
                    leverage_val, risk_per_trade_percent_val, max_risk_usdt_per_trade_val, symbol_item 
                )
                
                if quantidade is not None and quantidade > 0: 
                    logger.info(f"[📊 Níveis Estratégicos para {symbol_item} (LONG)]") 
                    logger.info(f"📥 Entrada:         {entry_price}")
                    logger.info(f"📉 Stop Loss:       {sl_price}")
                    logger.info(f"📈 Take Profit:     {tp_price}") 
                    logger.info(f"📊 Quantidade:      {quantidade}")
                    logger.info(f"Alavancagem:           {leverage_val}x") 
                    logger.info(f"Custo Estimado:     {round(entry_price * quantidade / leverage_val, 2)} USDT (Margem Inicial)")

                    entry_order_response = enviar_ordem(
                        symbol=symbol_item,
                        quantity=quantidade,
                        price=None, 
                        side=Client.SIDE_BUY,
                        order_type='MARKET', 
                        test_mode=test_mode_val,
                        reduce_only=False 
                    )
                    
                    # A lógica de verificação de preenchimento da ordem de entrada foi movida para dentro de enviar_ordem
                    if entry_order_response and entry_order_response.get('status') == 'FILLED' and float(entry_order_response.get('executedQty', 0.0)) >= quantidade: 
                        entry_order_id = entry_order_response['orderId']
                        logger.info(f"✅ Ordem de entrada MARKET para {symbol_item} preenchida com sucesso! (ID: {entry_order_id}).")

                        sl_tp_side = Client.SIDE_SELL 

                        sl_order_response = enviar_ordem(
                            symbol=symbol_item,
                            quantity=quantidade,
                            price=None,
                            side=sl_tp_side,
                            order_type='STOP_MARKET',
                            stop_price=sl_price,
                            test_mode=test_mode_val,
                            reduce_only=True 
                        )
                        logger.info(f"[DEBUG] Resposta SL: {sl_order_response}") 
                        
                        tp_order_response = enviar_ordem(
                            symbol=symbol_item,
                            quantity=quantidade,
                            price=None,
                            side=sl_tp_side,
                            order_type='TAKE_PROFIT_MARKET',
                            stop_price=tp_price,
                            test_mode=test_mode_val,
                            reduce_only=True 
                        )
                        logger.info(f"[DEBUG] Resposta TP: {tp_order_response}") 

                        if (sl_order_response and sl_order_response.get('orderId')) and \
                           (tp_order_response and tp_order_response.get('orderId')): 
                            logger.info(f"[POSIÇÃO] Ordens de Stop Loss e Take Profit para {symbol_item} enviadas.")
                            OPEN_POSITIONS[symbol_item] = {
                                "status": "OPEN",
                                "entry_price": entry_order_response.get('avgPrice'), 
                                "quantity": quantidade,
                                "sl_price": sl_price,
                                "tp_price": tp_price,
                                "side": Client.SIDE_BUY, 
                                "entry_order_id": entry_order_response.get('orderId'), 
                                "sl_order_id": sl_order_response.get('orderId'),
                                "tp_order_id": tp_order_response.get('orderId')
                            }
                            logger.info(f"[POSIÇÃO] Posição {'simulada ' if test_mode_val else ''}aberta para {symbol_item}. Gerenciada por TP/SL na exchange.")
                        else:
                            logger.error(f"[ERRO] Falha ao enviar ordens de Stop Loss ou Take Profit para {symbol_item}. Tentando fechar posição para evitar desproteção.")
                            # Se as ordens de proteção falharam, tenta fechar a posição de entrada
                            enviar_ordem(symbol_item, float(entry_order_response.get('executedQty', 0.0)), None, sl_tp_side, 'MARKET', test_mode_val, reduce_only=True) 
                            if symbol_item in OPEN_POSITIONS: del OPEN_POSITIONS[symbol_item]
                    else:
                        logger.error(f"[ERRO] Ordem de entrada MARKET para {symbol_item} não foi TOTALMENTE FILLED ou falhou. Status: {entry_order_response.get('status')}, Executado: {float(entry_order_response.get('executedQty', 0.0))}/{quantidade}. Fechando qualquer posição parcial para segurança.")
                        # Se a ordem de entrada não foi totalmente preenchida, tenta fechar o que foi preenchido
                        enviar_ordem(symbol_item, float(entry_order_response.get('executedQty', 0.0)), None, Client.SIDE_SELL, 'MARKET', test_mode_val, reduce_only=True)
                        if symbol_item in OPEN_POSITIONS: del OPEN_POSITIONS[symbol_item]
                else:
                    logger.warning(f"[AVISO] Não foi possível calcular a quantidade de ordem válida para {symbol_item}. Não prosseguindo com simulação de entrada.")
                
        else:
            logger.info(f"[POSIÇÃO] Posição aberta para {symbol_item}. As ordens de TP/SL estão ativas na exchange.")
            pass

# --- Ponto de Entrada Principal do Programa ---
if __name__ == "__main__":
    internet_down = False

    if not initialize_binance_client():
        logger.critical("[ERRO CRÍTICO] Falha na inicialização do cliente Binance. O bot não pode iniciar.")
        sys.exit(1)

    config = load_config_from_json()
    if config is None:
        sys.exit(1)

    try:
        # Carrega as configurações do arquivo JSON
        loaded_leverage = int(config["leverage"])
        loaded_risk_per_trade_percent = float(config["risk_per_trade_percent"])
        loaded_max_risk_usdt_per_trade = float(config["max_risk_usdt_per_trade"])
        loaded_test_mode = bool(config["test_mode"]) 
        
        loaded_kline_interval_minutes = int(config.get("kline_interval_minutes", 60))
        loaded_kline_trend_period = int(config.get("kline_trend_period", 50))
        loaded_kline_pullback_period = int(config.get("kline_pullback_period", 10))
        loaded_kline_atr_period = int(config.get("kline_atr_period", 14))
        loaded_min_atr_multiplier_for_entry = float(config.get("min_atr_multiplier_for_entry", 1.0))
        loaded_max_symbols_to_monitor = int(config.get("max_symbols_to_monitor", 5))
        loaded_risk_reward_ratio = float(config.get("risk_reward_ratio", 2.0))

    except KeyError as e:
        logger.critical(f"[ERRO CRÍTICO] Chave essencial '{e}' faltando em settings.json.")
        logger.critical("Certifique-se de que seu arquivo settings.json contém todas as chaves obrigatórias e que os nomes estão corretos.")
        sys.exit(1)
    except (ValueError, TypeError) as e:
        logger.critical(f"[ERRO CRÍTICO] Valor inválido para configuração em settings.json: {e}")
        logger.critical("Verifique se os tipos de dados (int, float, lista de strings) estão corretos para cada configuração.")
        sys.exit(1)

    # Loga as configurações carregadas
    logger.info(f"[INFO] Alavancagem : {loaded_leverage}x")
    logger.info(f"[INFO] % De risco: {loaded_risk_per_trade_percent}% do saldo disponível (máx {loaded_max_risk_usdt_per_trade} USDT)")
    logger.info(f"[INFO] MODO DE OPERAÇÃO: {'BOT FUNÇÃO(SIMULAÇÃO)' if loaded_test_mode else 'BOT FUNÇÃO(REAL!)'}") 
    logger.info(f"[INFO] Intervalo de Reconexão: {RECONNECT_INTERVAL_SECONDS}s")
    logger.info(f"[INFO] Intervalo de Monitoramento de Ordem: {ORDER_MONITOR_INTERVAL_SECONDS}s")
    logger.info(f"[INFO] Tempo Limite para Preenchimento de Ordem: {ORDER_FILL_TIMEOUT_SECONDS}s")
    
    logger.info(f"[INFO] Estratégia: Seguidor de Tendência com Pullback e Filtro de Volatilidade (APENAS LONG)") 
    logger.info(f"[INFO] Timeframe de KLine para Análise: {loaded_kline_interval_minutes}m")
    logger.info(f"[INFO] Período EMA Tendência: {loaded_kline_trend_period}")
    logger.info(f"[INFO] Período EMA Pullback: {loaded_kline_pullback_period}")
    logger.info(f"[INFO] Período ATR: {loaded_kline_atr_period}")
    logger.info(f"[INFO] Multiplicador Mínimo ATR para Entrada: {loaded_min_atr_multiplier_for_entry}")
    logger.info(f"[INFO] Máximo de Símbolos a Monitorar: {loaded_max_symbols_to_monitor}")
    logger.info(f"[INFO] Relação Risco:Recompensa (TP): {loaded_risk_reward_ratio}")


    logger.info("\n--- Bot Iniciado ---")
    
    # Seleciona os melhores símbolos para monitoramento
    selected_symbols_for_monitoring = scan_and_select_best_symbols(
        loaded_kline_interval_minutes, loaded_kline_trend_period, 
        loaded_kline_pullback_period, loaded_kline_atr_period, 
        loaded_min_atr_multiplier_for_entry, 
        loaded_max_symbols_to_monitor
    )

    if not selected_symbols_for_monitoring:
        logger.critical("[ERRO CRÍTICO] Nenhum símbolo adequado foi selecionado para monitoramento. O bot não pode operar. Ajuste seus critérios de varredura ou verifique a conexão.")
        sys.exit(1)

    logger.info("⏳ Verificando e fechando posições não rastreadas ao iniciar...")
    for symbol_item in selected_symbols_for_monitoring: 
        check_and_close_untracked_positions(symbol_item, loaded_test_mode)
        time.sleep(1)
    logger.info("✅ Verificação de posições não rastreadas concluída no início.")

    while True:
        try:
            if internet_down:
                logger.info(f"[CONEXÃO] Tentando reconectar à Binance API...")
                if client:
                    try:
                        client.futures_ping()
                        logger.info("[CONEXÃO] Conexão restabelecida! Continuando operação.")
                        internet_down = False
                    except Exception as e:
                        logger.error(f"[ERRO] Falha ao pingar Binance durante reconexão: {e}")
                else:
                    logger.warning("[AVISO] Cliente Binance não disponível para ping durante reconexão. Tentando re-inicializar...")
                    if not initialize_binance_client():
                        logger.error("[ERRO] Falha ao re-inicializar cliente Binance. Não é possível continuar.")
                        time.sleep(RECONNECT_INTERVAL_SECONDS)
                        continue

            if not client:
                time.sleep(RECONNECT_INTERVAL_SECONDS)
                continue
            
            # Executa o ciclo principal de análise e trading
            executar(selected_symbols_for_monitoring, loaded_leverage, 
                     loaded_risk_per_trade_percent, loaded_max_risk_usdt_per_trade, 
                     loaded_test_mode, loaded_kline_interval_minutes, loaded_kline_trend_period, 
                     loaded_kline_pullback_period, loaded_kline_atr_period, 
                     loaded_min_atr_multiplier_for_entry, loaded_risk_reward_ratio) 
            
            time.sleep(CYCLE_SLEEP_SECONDS) 

        except (ConnectionError, BinanceAPIException) as e:
            logger.error(f"[ERRO DE CONEXÃO] Internet indisponível ou problema de API: {e}")
            logger.info(f"O bot entrará em modo de reconexão. Tentando novamente em {RECONNECT_INTERVAL_SECONDS} segundos...")
            internet_down = True
            time.sleep(RECONNECT_INTERVAL_SECONDS) 
        except KeyboardInterrupt:
            logger.info("\n[ENCERRANDO] Interrupção detectada (Ctrl+C). Iniciando processo de limpeza...")
            final_config = load_config_from_json() 
            symbols_to_clean_on_exit = selected_symbols_for_monitoring

            # Cancela todas as ordens abertas para os símbolos monitorados
            for symbol_item in symbols_to_clean_on_exit:
                cancel_all_open_orders_for_symbol(symbol_item, loaded_test_mode) 
            
            logger.info("⏳ Tentando fechar todas as posições abertas (rastreadas pelo bot)...")
            for symbol_to_close in list(OPEN_POSITIONS.keys()):
                position_data = OPEN_POSITIONS[symbol_to_close]
                quantity_to_close = position_data['quantity']
                close_side = Client.SIDE_SELL # Para fechar uma posição LONG

                logger.info(f"⏳ Fechando posição rastreada para {symbol_to_close} ({quantity_to_close} unidades, lado: {close_side}) via ordem de mercado...")
                close_order_response = enviar_ordem(
                    symbol=symbol_to_close,
                    quantity=quantity_to_close,
                    price=None, 
                    side=close_side,
                    order_type='MARKET',
                    time_in_force=None,
                    stop_price=None,
                    test_mode=loaded_test_mode,
                    reduce_only=True 
                )
                if close_order_response and close_order_response.get('orderId'):
                    logger.info(f"✅ Posição rastreada para {symbol_to_close} fechada com sucesso.")
                    del OPEN_POSITIONS[symbol_to_close]
                else:
                    logger.error(f"[ERRO] Falha ao fechar posição rastreada para {symbol_to_close}. Requer intervenção manual.")

            logger.info("⏳ Verificando e fechando quaisquer posições não rastreadas restantes...")
            for symbol_item in symbols_to_clean_on_exit: 
                check_and_close_untracked_positions(symbol_item, loaded_test_mode) 
            logger.info("✅ Processo de limpeza concluído. Encerrando o bot.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"[ERRO INESPERADO] Ocorreu um erro não tratado: {e}")
            logger.error("O bot continuará, mas este erro deve ser investigado.")
            time.sleep(CYCLE_SLEEP_SECONDS) 
