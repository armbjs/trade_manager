
'''
poetry add python-telegram-bot==13.7 redis==5.2.1 requests apscheduler==3.6.3 pybit==5.8.0 python-binance==1.0.19
pip install python-telegram-bot==13.7 redis==5.2.1 requests apscheduler==3.6.3 pybit==5.8.0 python-binance==1.0.19
'''

import redis
import json
import time
import sys
import logging
import math
import requests
import base64
from urllib.parse import urlencode
import hmac
import hashlib
import datetime
from io import StringIO

from apscheduler.schedulers.blocking import BlockingScheduler
from binance.client import Client
from binance.enums import *
from pybit.unified_trading import HTTP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExManager:
    def __init__(
        self, 
        redis_config,
        binance_accounts,
        bybit_accounts,
        bitget_accounts,
        bitget_base_url
    ):
        # redis_config: {host, port, db, username, password, ssl, channel_name_prefix}
        self.redis_client = redis.Redis(
            host=redis_config["host"],
            port=int(redis_config["port"]),
            db=int(redis_config["db"]),
            username=redis_config["username"],
            password=redis_config["password"],
            ssl=redis_config["ssl"],
            decode_responses=True
        )

        # Binance multiple accounts
        self.binance_clients = []
        for acc in binance_accounts:
            client = Client(acc["api_key"], acc["api_secret"])
            self.binance_clients.append((acc["name"], client))

        # Bybit multiple accounts
        # 각 계정에 대해 HTTP 클라이언트를 만든다.
        self.bybit_clients = []
        for acc in bybit_accounts:
            bybit_client = HTTP(
                api_key=acc["api_key"],
                api_secret=acc["api_secret"],
                testnet=False
            )
            self.bybit_clients.append((acc["name"], bybit_client))

        # Bitget multiple accounts (여러 계정에 대해 키만 저장, send_request는 계정별로 인자로 전달)
        self.bitget_accounts = bitget_accounts
        self.BITGET_BASE_URL = bitget_base_url

    def send_request(self, method, endpoint, params=None, body=None, need_auth=False, bitget_api_key=None, bitget_secret_key=None, bitget_passphrase=None):
        if params is None:
            params = {}
        if body is None:
            body = {}

        def get_timestamp():
            return str(int(time.time() * 1000))

        def sign(method, request_path, timestamp, body_str=""):
            message = timestamp + method + request_path + body_str
            signature = hmac.new(bitget_secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
            signature_b64 = base64.b64encode(signature).decode()
            return signature_b64

        if method.upper() == "GET" and params:
            query_string = urlencode(params)
            request_path = endpoint + "?" + query_string
            url = self.BITGET_BASE_URL + request_path
            body_str = ""
        else:
            request_path = endpoint
            url = self.BITGET_BASE_URL + endpoint
            body_str = json.dumps(body) if (body and method.upper() != "GET") else ""

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if need_auth:
            ts = get_timestamp()
            sig = sign(method.upper(), request_path, ts, body_str)
            headers["ACCESS-KEY"] = bitget_api_key
            headers["ACCESS-SIGN"] = sig
            headers["ACCESS-TIMESTAMP"] = ts
            headers["ACCESS-PASSPHRASE"] = bitget_passphrase

        response = requests.request(method, url, headers=headers, data=body_str if method.upper() != "GET" else None)
        try:
            return response.json()
        except:
            return response.text

    ##############################################
    # 현재가 가져오기 함수들
    ##############################################
    def get_current_price_binance(self, coin):
        # price는 인증 필요 없음
        symbol = coin.upper() + "USDT"
        # 아무 binance client나 사용 가능 - 가격은 동일하므로 첫번째 계정 사용
        if not self.binance_clients:
            raise Exception("No Binance accounts configured.")
        _, client = self.binance_clients[0]
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])

    def get_current_price_bybit(self, coin):
        # bybit도 마찬가지로 첫 계정 사용
        if not self.bybit_clients:
            raise Exception("No Bybit accounts configured.")
        symbol = coin.upper() + "USDT"
        _, bybit_client = self.bybit_clients[0]
        resp = bybit_client.get_tickers(category="spot", symbol=symbol)
        if resp.get("retCode") == 0:
            ticker_list = resp.get("result", {}).get("list", [])
            if ticker_list and "lastPrice" in ticker_list[0]:
                return float(ticker_list[0]["lastPrice"])
        raise Exception(f"Failed to fetch Bybit current price for {symbol}")

    def get_current_price_bitget(self, coin):
        # bitget도 가격 조회는 인증 필요 없음
        symbol = coin.upper() + "USDT"
        endpoint = "/api/v2/spot/market/tickers"
        params = {"symbol": symbol}
        resp = self.send_request("GET", endpoint, params=params, need_auth=False)
        if resp.get("code") == "00000":
            data_list = resp.get("data", [])
            if data_list and "lastPr" in data_list[0]:
                last_price_str = data_list[0]["lastPr"]
                return float(last_price_str)
        raise Exception(f"Failed to fetch Bitget current price for {symbol}")

    ##############################################
    # 테스트 공지 발행
    ##############################################
    def publish_test_notices(self, channel_name_prefix):
        current_time = int(time.time() * 1000)
        coin_symbol = f"TST{current_time % 1000:03d}"

        upbit_notice_en1 = {
            "type": "NOTICE",
            "action": "NEW",
            "title": f"Market Support for {coin_symbol}(Tasdas), XRP(Ripple Network) (BTC, USDT Market)",
            "content": None,
            "exchange": "UPBIT",
            "url": "https://upbit.com/service_center/notice?id=4695",
            "category": "Trade",
            "listedAt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "listedTs": current_time,
            "receivedTs": current_time + 100
        }

        upbit_notice_en1_json = json.dumps(upbit_notice_en1, ensure_ascii=False)
        self.redis_client.publish(channel_name_prefix, upbit_notice_en1_json)
        return f"Published UPBIT test notice for {coin_symbol}\n"

    def run_tests(self, channel_name_prefix):
        return "Executing test notices\n" + self.publish_test_notices(channel_name_prefix)

    ##############################################
    # Binance 관련 함수
    ##############################################
    def get_spot_balance_for_client(self, client, account_name):
        output = StringIO()
        try:
            account_info = client.get_account()
            balances = [
                asset for asset in account_info['balances']
                if float(asset['free']) > 0 or float(asset['locked']) > 0
            ]
            output.write(f"\n=== Binance Spot Wallet Balance ({account_name}) ===\n\n")
            if not balances:
                output.write("No balance.\n\n")
            else:
                for balance_item in balances:
                    coin_name = balance_item['asset']
                    free_amount = float(balance_item['free'])
                    locked_amount = float(balance_item['locked'])
                    output.write(f"{coin_name}: available: {free_amount}, locked: {locked_amount}\n")
                output.write("\n")
        except Exception as e:
            output.write(f"Error ({account_name}): {e}\n\n")
        return output.getvalue()

    def get_spot_balance_all(self):
        output = StringIO()
        for acc_name, client in self.binance_clients:
            output.write(self.get_spot_balance_for_client(client, acc_name))
        return output.getvalue()

    def buy_binance_coin_usdt_raw(self, client, coin, usdt_amount):
        try:
            coin = coin.upper()
            usdt_info = client.get_asset_balance(asset='USDT')
            if not usdt_info or float(usdt_info['free']) <= 0:
                return {"error": "No USDT balance"}

            usdt_balance = float(usdt_info['free'])
            if usdt_amount > usdt_balance:
                return {"error": "Insufficient USDT balance"}

            symbol = coin + "USDT"
            ticker = client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])

            usdt_to_use = math.floor(usdt_amount * 100) / 100.0
            if usdt_to_use <= 0:
                return {"error": "Too small USDT amount"}

            quantity = usdt_to_use / price
            quantity = float(int(quantity))
            if quantity <= 0:
                return {"error": "Quantity too small"}

            order = client.create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            return order
        except Exception as e:
            return {"error": str(e)}

    def sell_all_binance_coin_raw(self, client, coin):
        try:
            coin = coin.upper()
            balance_info = client.get_asset_balance(asset=coin)
            if not balance_info:
                return {"error": "Balance query failed"}
            balance_amount = float(balance_info['free'])

            if balance_amount <= 0:
                return {"error": "No balance to sell"}

            quantity = float(int(balance_amount))
            if quantity <= 0:
                return {"error": "Quantity too small"}

            symbol = coin + "USDT"
            order = client.create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            return order
        except Exception as e:
            return {"error": str(e)}

    def get_recent_trades_raw_binance(self, client, coin):
        try:
            symbol = (coin.upper() + "USDT")
            trades = client.get_my_trades(symbol=symbol, limit=200)
            return trades
        except Exception as e:
            return {"error": str(e)}

    def calculate_account_avg_buy_price_binance(self, client, coin):
        trades = self.get_recent_trades_raw_binance(client, coin)
        if isinstance(trades, dict) and trades.get("error"):
            return None
        if not isinstance(trades, list):
            return None

        total_qty = 0.0
        total_cost = 0.0
        for t in trades:
            if float(t['qty']) > 0 and t['isBuyer']:
                trade_price = float(t['price'])
                trade_qty = float(t['qty'])
                total_cost += trade_price * trade_qty
                total_qty += trade_qty

        if total_qty > 0:
            avg_price = total_cost / total_qty
            return avg_price
        else:
            return None

    ##############################################
    # Bybit 관련 함수
    ##############################################
    def get_symbol_filters(self, bybit_client, symbol):
        resp = bybit_client.get_instruments_info(category="spot", symbol=symbol)
        if resp['retCode'] != 0 or 'list' not in resp['result']:
            raise Exception(f"symbol info query failed: {resp.get('retMsg', 'Unknown error')}")
        instruments_list = resp['result']['list']
        if not instruments_list:
            raise Exception("No symbol info found.")

        lot_size_filter = instruments_list[0].get('lotSizeFilter', {})
        min_qty = float(lot_size_filter.get('minOrderQty', 0))
        qty_step = lot_size_filter.get('qtyStep', None)
        if qty_step is None:
            base_precision = lot_size_filter.get('basePrecision', '0.01')
            qty_step = float(base_precision)
        else:
            qty_step = float(qty_step)
        return min_qty, qty_step

    def adjust_quantity_to_step(self, qty, step, min_qty):
        adjusted = math.floor(qty / step) * step
        if adjusted < min_qty:
            return 0.0
        return adjusted

    def get_decimal_places(self, qty_step):
        if qty_step == 0:
            return 2
        if qty_step >= 1:
            return 0
        return abs(math.floor(math.log10(qty_step)))

    def buy_bybit_coin_usdt_raw(self, bybit_client, coin, usdt_amount):
        try:
            coin = coin.upper()
            symbol = coin + "USDT"
            response = bybit_client.get_wallet_balance(accountType="UNIFIED")
            if response['retCode'] != 0:
                return {"error": response['retMsg']}

            usdt_balance = 0.0
            for account_item in response['result']['list']:
                for c in account_item['coin']:
                    if c['coin'].upper() == "USDT":
                        usdt_balance = float(c['walletBalance'])
                        break

            if usdt_balance <= 0:
                return {"error": "No USDT balance"}

            if usdt_amount > usdt_balance:
                return {"error": "Insufficient USDT balance"}

            usdt_to_use = math.floor(usdt_amount * 100) / 100.0
            if usdt_to_use <= 0:
                return {"error": "Too small USDT amount"}

            order_resp = bybit_client.place_order(
                category="spot",
                symbol=symbol,
                side="Buy",
                orderType="MARKET",
                qty=str(usdt_to_use),
                marketUnit="quoteCoin"
            )
            return order_resp
        except Exception as e:
            return {"error": str(e)}

    def sell_all_bybit_coin_raw(self, bybit_client, coin):
        try:
            coin = coin.upper()
            symbol = coin + "USDT"
            min_qty, qty_step = self.get_symbol_filters(bybit_client, symbol)

            response = bybit_client.get_wallet_balance(accountType="UNIFIED")
            if response['retCode'] != 0:
                return {"error": response['retMsg']}

            coin_balance = 0.0
            for account_item in response['result']['list']:
                for c in account_item['coin']:
                    if c['coin'].upper() == coin:
                        coin_balance = float(c['walletBalance'])
                        break

            if coin_balance <= 0:
                return {"error": "No balance to sell"}

            sell_qty = self.adjust_quantity_to_step(coin_balance, qty_step, min_qty)
            if sell_qty <= 0:
                return {"error": "Quantity too small"}

            decimal_places = self.get_decimal_places(qty_step)
            qty_str = f"{sell_qty:.{decimal_places}f}"

            order_resp = bybit_client.place_order(
                category="spot",
                symbol=symbol,
                side="Sell",
                orderType="MARKET",
                qty=qty_str
            )
            return order_resp
        except Exception as e:
            return {"error": str(e)}

    def get_recent_bybit_trades_raw(self, bybit_client, coin):
        try:
            symbol = (coin.upper() + "USDT")
            resp = bybit_client.get_executions(category="spot", symbol=symbol, limit=200)

            if resp['retCode'] != 0:
                return {"error": resp.get('retMsg', 'Unknown error')}

            trades_data = resp.get('result', {}).get('list', [])
            trades_list = []
            for t in trades_data:
                exec_time_str = t.get('execTime', '0')
                exec_time = int(exec_time_str) if exec_time_str.isdigit() else 0

                side_str = t.get('side', '').lower()
                price = t.get('execPrice', '0')
                qty = t.get('execQty', '0')
                sym = t.get('symbol', 'UNKNOWN')
                is_buyer = True if side_str == 'buy' else False

                trades_list.append({
                    'symbol': sym,
                    'price': price,
                    'qty': qty,
                    'time': exec_time,
                    'isBuyer': is_buyer
                })

            trades_list.sort(key=lambda x: x['time'])
            return trades_list
        except Exception as e:
            return {"error": str(e)}

    def calculate_bybit_avg_buy_price(self, bybit_client, coin):
        trades = self.get_recent_bybit_trades_raw(bybit_client, coin)
        if isinstance(trades, dict) and trades.get("error"):
            return None
        if not isinstance(trades, list):
            return None

        total_qty = 0.0
        total_cost = 0.0
        for t in trades:
            if t.get('isBuyer'):
                trade_price = float(t['price'])
                trade_qty = float(t['qty'])
                total_cost += trade_price * trade_qty
                total_qty += trade_qty

        if total_qty > 0:
            avg_price = total_cost / total_qty
            return avg_price
        else:
            return None

    ##############################################
    # Bitget 관련 함수
    ##############################################
    def check_spot_balance(self, api_key, secret_key, passphrase, coin=None, asset_type=None):
        endpoint = "/api/v2/spot/account/assets"
        params = {}
        if coin:
            params["coin"] = coin
        if asset_type:
            params["assetType"] = asset_type
        return self.send_request("GET", endpoint, params=params, need_auth=True, 
                                 bitget_api_key=api_key, bitget_secret_key=secret_key, bitget_passphrase=passphrase)

    def place_spot_order(self, api_key, secret_key, passphrase, symbol, side, order_type, force, size, price=None, client_oid=None):
        body = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "force": force,
            "size": size
        }
        if price and order_type == "limit":
            body["price"] = price
        if client_oid:
            body["clientOid"] = client_oid

        endpoint = "/api/v2/spot/trade/place-order"
        result = self.send_request("POST", endpoint, body=body, need_auth=True,
                                   bitget_api_key=api_key, bitget_secret_key=secret_key, bitget_passphrase=passphrase)
        return result

    def get_bitget_symbol_info(self, symbol):
        endpoint = "/api/v2/spot/public/symbols"
        params = {}
        if symbol:
            params["symbol"] = symbol
        resp = self.send_request("GET", endpoint, params=params, need_auth=False)
        if resp.get("code") != "00000":
            return None

        products = resp.get("data", [])
        for p in products:
            if p.get("symbol") == symbol:
                return p
        return None

    def bitget_buy_coin_usdt_raw(self, api_key, secret_key, passphrase, coin, usdt_amount):
        coin = coin.upper()
        balance_data = self.check_spot_balance(api_key, secret_key, passphrase)
        if balance_data.get("code") != "00000":
            return {"error": balance_data.get('msg', 'Balance query error')}
        available_usdt = "0"
        for b in balance_data.get("data", []):
            if b.get("coin") == "USDT":
                available_usdt = b.get("available", "0")
                break

        usdt_balance = float(available_usdt)
        if usdt_balance <= 0:
            return {"error": "No USDT balance"}
        if usdt_amount > usdt_balance:
            return {"error": "Insufficient USDT balance"}

        usdt_to_use = math.floor(usdt_amount * 100) / 100.0
        if usdt_to_use <= 0:
            return {"error": "Too small USDT amount"}

        symbol = coin + "USDT"
        order_resp = self.place_spot_order(api_key, secret_key, passphrase, symbol=symbol, side="buy", order_type="market", force="normal", size=str(usdt_to_use))
        return order_resp

    def bitget_sell_all_coin_raw(self, api_key, secret_key, passphrase, coin):
        coin = coin.upper()
        balance_data = self.check_spot_balance(api_key, secret_key, passphrase)
        if balance_data.get("code") != "00000":
            return {"error": balance_data.get('msg', 'Balance query error')}
        available_amount = "0"
        for b in balance_data.get("data", []):
            if b.get("coin").upper() == coin:
                available_amount = b.get("available", "0")
                break

        amount = float(available_amount)
        if amount <= 0:
            return {"error": "No balance to sell"}

        symbol = coin + "USDT"
        symbol_info = self.get_bitget_symbol_info(symbol)
        if not symbol_info:
            return {"error": "Symbol info not found"}

        min_trade_amount = float(symbol_info.get("minTradeAmount", "1"))
        quantity_precision = int(symbol_info.get("quantityPrecision", "2"))
        if amount < min_trade_amount:
            return {"error": "Amount too small"}

        max_size = round(amount, quantity_precision)
        step = 10 ** (-quantity_precision)
        safe_size = max_size - step
        if safe_size < min_trade_amount:
            safe_size = min_trade_amount

        size_str = f"{safe_size:.{quantity_precision}f}"
        order_resp = self.place_spot_order(api_key, secret_key, passphrase, symbol=symbol, side="sell", order_type="market", force="normal", size=size_str)
        return order_resp

    def get_recent_bg_trades_raw(self, api_key, secret_key, passphrase, coin):
        try:
            symbol = (coin.upper() + "USDT")
            endpoint = "/api/v2/spot/trade/fills"
            params = {
                "symbol": symbol,
                "limit": "100"
            }

            resp = self.send_request("GET", endpoint, params=params, need_auth=True,
                                     bitget_api_key=api_key, bitget_secret_key=secret_key, bitget_passphrase=passphrase)
            if resp.get("code") != "00000":
                return {"error": resp.get("msg", "Unknown error")}

            data = resp.get("data", [])
            trades_list = []
            for t in data:
                side_str = t.get('side', '').lower()
                price = t.get('priceAvg', '0')
                qty = t.get('size', '0')
                sym = t.get('symbol', 'UNKNOWN')
                ctime_str = t.get('cTime', '0')
                exec_time = int(ctime_str) if ctime_str.isdigit() else 0

                is_buyer = True if side_str == 'buy' else False

                trades_list.append({
                    'symbol': sym,
                    'price': price,
                    'qty': qty,
                    'time': exec_time,
                    'isBuyer': is_buyer
                })

            trades_list.sort(key=lambda x: x['time'])
            return trades_list
        except Exception as e:
            return {"error": str(e)}

    def calculate_bg_avg_buy_price(self, api_key, secret_key, passphrase, coin):
        trades = self.get_recent_bg_trades_raw(api_key, secret_key, passphrase, coin)
        if isinstance(trades, dict) and trades.get("error"):
            return None
        if not isinstance(trades, list):
            return None

        total_qty = 0.0
        total_cost = 0.0
        for t in trades:
            if t.get('isBuyer'):
                trade_price = float(t['price'])
                trade_qty = float(t['qty'])
                total_cost += trade_price * trade_qty
                total_qty += trade_qty

        if total_qty > 0:
            avg_price = total_cost / total_qty
            return avg_price
        else:
            return None

    ##############################################
    # 손익평가
    ##############################################
    def show_profit_loss_per_account(self, coin):
        output = StringIO()
        output.write("=== PnL Calculation ===\n\n")

        current_price_binance = None
        current_price_bybit = None
        current_price_bitget = None

        # current prices
        try:
            current_price_binance = self.get_current_price_binance(coin)
            output.write(f"Binance current_price: {current_price_binance}\n\n")
        except Exception as e:
            output.write(f"Failed to fetch Binance current price for {coin}: {e}\n\n")

        try:
            current_price_bybit = self.get_current_price_bybit(coin)
            output.write(f"Bybit current_price: {current_price_bybit}\n\n")
        except Exception as e:
            output.write(f"Failed to fetch Bybit current price for {coin}: {e}\n\n")

        try:
            current_price_bitget = self.get_current_price_bitget(coin)
            output.write(f"Bitget current_price: {current_price_bitget}\n\n")
        except Exception as e:
            output.write(f"Failed to fetch Bitget current price for {coin}: {e}\n\n")

        # Binance PnL
        output.write("=== Binance PnL ===\n\n")
        for acc_name, client in self.binance_clients:
            try:
                avg_price = self.calculate_account_avg_buy_price_binance(client, coin)
                if avg_price is not None and current_price_binance is not None:
                    pnl = current_price_binance - avg_price
                    pnl_percent = (pnl / avg_price) * 100.0
                    output.write(f"[BN-{acc_name}] current_price: ${current_price_binance:.3f}, avg_price: ${avg_price:.3f}, pnl: {pnl_percent:.3f}%\n")
                else:
                    if avg_price is None:
                        output.write(f"[BN-{acc_name}] no buy history\n")
                    else:
                        output.write(f"[BN-{acc_name}] current price unavailable\n")
            except Exception as e:
                output.write(f"[BN-{acc_name}] Error calculating PnL: {e}\n")
        output.write("\n")

        # Bybit PnL
        output.write("=== Bybit PnL ===\n\n")
        for acc_name, bybit_client in self.bybit_clients:
            try:
                avg_price_bybit = self.calculate_bybit_avg_buy_price(bybit_client, coin)
                if avg_price_bybit is not None and current_price_bybit is not None:
                    pnl = current_price_bybit - avg_price_bybit
                    pnl_percent = (pnl / avg_price_bybit) * 100.0
                    output.write(f"[BB-{acc_name}] current_price: ${current_price_bybit:.3f}, avg_price: ${avg_price_bybit:.3f}, pnl: {pnl_percent:.3f}%\n")
                else:
                    if avg_price_bybit is None:
                        output.write(f"[BB-{acc_name}] no buy history\n")
                    else:
                        output.write(f"[BB-{acc_name}] current price unavailable\n")
            except Exception as e:
                output.write(f"[BB-{acc_name}] Error calculating PnL: {e}\n")
        output.write("\n")

        # Bitget PnL
        output.write("=== Bitget PnL ===\n\n")
        for acc_info in self.bitget_accounts:
            acc_name = acc_info["name"]
            api_key = acc_info["api_key"]
            secret_key = acc_info["api_secret"]
            passphrase = acc_info["passphrase"]
            try:
                avg_price_bg = self.calculate_bg_avg_buy_price(api_key, secret_key, passphrase, coin)
                if avg_price_bg is not None and current_price_bitget is not None:
                    pnl = current_price_bitget - avg_price_bg
                    pnl_percent = (pnl / avg_price_bg) * 100.0
                    output.write(f"[BG-{acc_name}] current_price: ${current_price_bitget:.3f}, avg_price: ${avg_price_bg:.3f}, pnl: {pnl_percent:.3f}%\n")
                else:
                    if avg_price_bg is None:
                        output.write(f"[BG-{acc_name}] no buy history\n")
                    else:
                        output.write(f"[BG-{acc_name}] current price unavailable\n")
            except Exception as e:
                output.write(f"[BG-{acc_name}] Error calculating PnL: {e}\n")
        output.write("\n")

        return output.getvalue()

    ##############################################
    # 체결내역 출력 함수
    ##############################################
    def print_trade_history(self, trades):
        output = StringIO()
        if isinstance(trades, dict) and trades.get("error"):
            output.write(str(trades) + "\n\n")
            return output.getvalue()

        if not trades or len(trades) == 0:
            output.write("no fills.\n\n")
            return output.getvalue()

        for t in trades:
            # 바이낸스, 바이빗, 빗겟 모두 time을 ms 기준이라 가정
            trade_time = datetime.datetime.fromtimestamp(t['time'] / 1000.0)
            side = "bid" if t['isBuyer'] else "ask"
            coin_name = t['symbol'].replace("USDT", "")
            qty = t['qty']
            price = t['price']
            output.write(f"{trade_time} {side} {qty} {coin_name} at {price}\n")
        output.write("\n")
        return output.getvalue()

    ##############################################
    # 전체매수/전체매도
    ##############################################
    def buy_all(self, coin, usdt_amount):
        output = StringIO()
        output.write("=== buy all ===\n\n")

        # Binance
        for acc_name, client in self.binance_clients:
            result = self.buy_binance_coin_usdt_raw(client, coin, usdt_amount)
            output.write(f"[BN - {acc_name}]\n{result}\n\n")

        # Bybit
        for acc_name, bybit_client in self.bybit_clients:
            result = self.buy_bybit_coin_usdt_raw(bybit_client, coin, usdt_amount)
            output.write(f"[BB - {acc_name}]\n{result}\n\n")

        # Bitget
        for acc_info in self.bitget_accounts:
            acc_name = acc_info["name"]
            api_key = acc_info["api_key"]
            secret_key = acc_info["api_secret"]
            passphrase = acc_info["passphrase"]
            result = self.bitget_buy_coin_usdt_raw(api_key, secret_key, passphrase, coin, usdt_amount)
            output.write(f"[BG - {acc_name}]\n{result}\n\n")

        return output.getvalue()

    def sell_all(self, coin):
        output = StringIO()
        output.write("=== sell all ===\n\n")

        # Binance
        for acc_name, client in self.binance_clients:
            result = self.sell_all_binance_coin_raw(client, coin)
            output.write(f"[BN - {acc_name}]\n{result}\n\n")

        # Bybit
        for acc_name, bybit_client in self.bybit_clients:
            result = self.sell_all_bybit_coin_raw(bybit_client, coin)
            output.write(f"[BB - {acc_name}]\n{result}\n\n")

        # Bitget
        for acc_info in self.bitget_accounts:
            acc_name = acc_info["name"]
            api_key = acc_info["api_key"]
            secret_key = acc_info["api_secret"]
            passphrase = acc_info["passphrase"]
            result = self.bitget_sell_all_coin_raw(api_key, secret_key, passphrase, coin)
            output.write(f"[BG - {acc_name}]\n{result}\n\n")

        return output.getvalue()

    ##############################################
    # 거래내역 조회
    ##############################################
    def show_trx(self, coin):
        output = StringIO()
        c = coin.upper()
        output.write(f"=== Transaction History for {c} ===\n\n")

        # Binance
        for acc_name, client in self.binance_clients:
            output.write(f"=== Binance ({acc_name}) [{c}] ===\n\n")
            trades = self.get_recent_trades_raw_binance(client, c)
            output.write(self.print_trade_history(trades))

        # Bybit
        for acc_name, bybit_client in self.bybit_clients:
            output.write(f"=== Bybit ({acc_name}) [{c}] ===\n\n")
            bb_trades = self.get_recent_bybit_trades_raw(bybit_client, c)
            output.write(self.print_trade_history(bb_trades))

        # Bitget
        for acc_info in self.bitget_accounts:
            acc_name = acc_info["name"]
            api_key = acc_info["api_key"]
            secret_key = acc_info["api_secret"]
            passphrase = acc_info["passphrase"]
            output.write(f"=== Bitget ({acc_name}) [{c}] ===\n\n")
            bg_trades = self.get_recent_bg_trades_raw(api_key, secret_key, passphrase, c)
            output.write(self.print_trade_history(bg_trades))

        return output.getvalue()
    ##############################################
    # 전체 잔고 조회 함수 (모든 코인을 다 출력)
    ##############################################
    def check_all_balances_all(self):
        output = StringIO()
        output.write("\n=== All Balances (All Coins) ===\n\n")
        output.write("=== Binance Spot Balances (All accounts) ===\n\n")
        for acc_name, client in self.binance_clients:
            try:
                account_info = client.get_account()
                balances = [
                    asset for asset in account_info['balances']
                    if (float(asset['free']) > 0 or float(asset['locked']) > 0)
                ]
                output.write(f"=== Binance ({acc_name}) ===\n")
                if not balances:
                    output.write("No balance.\n\n")
                else:
                    for balance_item in balances:
                        coin_name = balance_item['asset']
                        free_amount = float(balance_item['free'])
                        locked_amount = float(balance_item['locked'])
                        output.write(f"{coin_name}: available: {free_amount}, locked: {locked_amount}\n")
                    output.write("\n")
            except Exception as e:
                output.write(f"Error ({acc_name}): {e}\n\n")
        
        output.write("=== Bybit Unified Balances (All accounts) ===\n\n")
        for acc_name, bybit_client in self.bybit_clients:
            output.write(f"=== Bybit ({acc_name}) ===\n")
            try:
                response = bybit_client.get_wallet_balance(accountType="UNIFIED")
                if response['retCode'] == 0:
                    coins_found = False
                    for account_item in response['result']['list']:
                        for c in account_item['coin']:
                            wallet_balance = float(c.get('walletBalance', 0))
                            if wallet_balance > 0:
                                output.write(f"{c['coin']}: balance: {wallet_balance}\n")
                                coins_found = True
                    if not coins_found:
                        output.write("no balance\n")
                else:
                    output.write(f"balance query failed: {response['retMsg']}\n")
            except Exception as e:
                output.write(f"error: {e}\n")
            output.write("\n")

        output.write("=== Bitget Spot Balances (All accounts) ===\n\n")
        for acc_info in self.bitget_accounts:
            acc_name = acc_info["name"]
            api_key = acc_info["api_key"]
            secret_key = acc_info["api_secret"]
            passphrase = acc_info["passphrase"]
            output.write(f"=== Bitget ({acc_name}) ===\n")
            res = self.check_spot_balance(api_key, secret_key, passphrase)
            if res and res.get("code") == "00000":
                data = res.get("data", [])
                if not data:
                    output.write("no balance\n")
                else:
                    coins_found = False
                    for b in data:
                        coin = b.get("coin")
                        available = b.get("available")
                        if float(available) > 0:
                            output.write(f"{coin}: available: {available}\n")
                            coins_found = True
                    if not coins_found:
                        output.write("no balance\n")
            else:
                output.write("Bitget balance query failed\n")
            output.write("\n")

        output.write("\n=== All balances end ===\n")
        return output.getvalue()

    ##############################################
    # 전체 잔고 조회 함수 (1개 이하의 코인은 제외)
    ##############################################
    def check_all_balances_filtered(self):
        output = StringIO()
        output.write("\n=== All Balances (Coins > 1 only) ===\n\n")
        output.write("=== Binance Spot Balances (All accounts) ===\n\n")
        for acc_name, client in self.binance_clients:
            try:
                account_info = client.get_account()
                # 코인 잔고가 1보다 큰 것만 필터
                balances = [
                    asset for asset in account_info['balances']
                    if (float(asset['free']) > 1 or float(asset['locked']) > 1)
                ]
                output.write(f"=== Binance ({acc_name}) ===\n")
                if not balances:
                    output.write("No balance.\n\n")
                else:
                    for balance_item in balances:
                        coin_name = balance_item['asset']
                        free_amount = float(balance_item['free'])
                        locked_amount = float(balance_item['locked'])
                        if free_amount > 1 or locked_amount > 1:
                            output.write(f"{coin_name}: available: {free_amount}, locked: {locked_amount}\n")
                    output.write("\n")
            except Exception as e:
                output.write(f"Error ({acc_name}): {e}\n\n")
        
        output.write("=== Bybit Unified Balances (All accounts) ===\n\n")
        for acc_name, bybit_client in self.bybit_clients:
            output.write(f"=== Bybit ({acc_name}) ===\n")
            try:
                response = bybit_client.get_wallet_balance(accountType="UNIFIED")
                if response['retCode'] == 0:
                    coins_found = False
                    for account_item in response['result']['list']:
                        for c in account_item['coin']:
                            wallet_balance = float(c.get('walletBalance', 0))
                            if wallet_balance > 1:
                                output.write(f"{c['coin']}: balance: {wallet_balance}\n")
                                coins_found = True
                    if not coins_found:
                        output.write("no balance\n")
                else:
                    output.write(f"balance query failed: {response['retMsg']}\n")
            except Exception as e:
                output.write(f"error: {e}\n")
            output.write("\n")

        output.write("=== Bitget Spot Balances (All accounts) ===\n\n")
        for acc_info in self.bitget_accounts:
            acc_name = acc_info["name"]
            api_key = acc_info["api_key"]
            secret_key = acc_info["api_secret"]
            passphrase = acc_info["passphrase"]
            output.write(f"=== Bitget ({acc_name}) ===\n")
            res = self.check_spot_balance(api_key, secret_key, passphrase)
            if res and res.get("code") == "00000":
                data = res.get("data", [])
                if not data:
                    output.write("no balance\n")
                else:
                    coins_found = False
                    for b in data:
                        coin = b.get("coin")
                        available = float(b.get("available", 0))
                        if available > 1:
                            output.write(f"{coin}: available: {available}\n")
                            coins_found = True
                    if not coins_found:
                        output.write("no balance\n")
            else:
                output.write("Bitget balance query failed\n")
            output.write("\n")

        output.write("\n=== All balances end ===\n")
        return output.getvalue()

    ##############################################
    # 명령어 헬프
    ##############################################
    COMMANDS_HELP = [
        ("notice_test", "테스트 공지 발행"),
        ("buy.COIN.value", "COIN을 USDT로 value만큼 매수 (예: buy.BTC.100)"),
        ("sell.COIN", "COIN 전량 매도 (예: sell.ETH)"),
        ("show_trx.COIN", "COIN 거래내역 조회 (예: show_trx.BTC)"),
        ("show_pnl.COIN", "COIN 손익 평가 (예: show_pnl.BTC)"),
        ("show_bal", "모든 계좌 잔고 조회 (1개 이하인 코인 제외)"),
        ("show_bal_all", "모든 계좌 잔고 조회 (모든 코인 표시)"),
        ("명령어","help", "사용 가능한 명령어 목록 표시"),
    ]

    def execute_command(self, text, channel_name_prefix):
        old_stdout = sys.stdout
        buffer = StringIO()
        sys.stdout = buffer
        try:
            text = text.strip()
            print(f"Received command: {text}\n")

            if text == "notice_test":
                print(self.run_tests(channel_name_prefix))

            elif text.startswith("buy."):
                parts = text.split(".")
                if len(parts) == 3:
                    coin = parts[1]
                    try:
                        value = float(parts[2])
                        print(self.buy_all(coin, value))
                    except:
                        print("invalid value\n")
                else:
                    print("format: buy.COIN.value\n")

            elif text.startswith("sell."):
                parts = text.split(".")
                if len(parts) == 2:
                    coin = parts[1]
                    print(self.sell_all(coin))
                else:
                    print("format: sell.COIN\n")

            elif text.startswith("show_trx."):
                parts = text.split(".")
                if len(parts) == 2:
                    c = parts[1]
                    print(self.show_trx(c))
                else:
                    print("format: show_trx.COIN\n")

            elif text.startswith("show_pnl."):
                parts = text.split(".")
                if len(parts) == 2:
                    c = parts[1]
                    print(self.show_profit_loss_per_account(c))
                else:
                    print("format: show_pnl.COIN\n")

            elif text == "show_bal":
                # 1개 이하의 코인 제외
                print(self.check_all_balances_filtered())

            elif text == "show_bal_all":
                # 모든 코인 표시
                print(self.check_all_balances_all())

            elif text in ["명령어", "help"]:
                print("=== 사용 가능한 명령어 목록 ===\n")
                for cmd, desc in self.COMMANDS_HELP:
                    print(f"{cmd} : {desc}")
                print()

            else:
                print("No such feature.\n")

        finally:
            sys.stdout = old_stdout
        return buffer.getvalue()