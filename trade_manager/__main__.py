'''
poetry add python-telegram-bot==13.7 redis==5.2.1 requests apscheduler==3.6.3 pybit==5.8.0 python-binance==1.0.19
pip install python-telegram-bot==13.7 redis==5.2.1 requests apscheduler==3.6.3 pybit==5.8.0 python-binance==1.0.19
'''


from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
import tempfile

import os
import sys

# __main__.py의 상위 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trade_manager.ex_manager import ExManager

# Telegram Bot Token
BOT_TOKEN = "7861907626:AAF5wd-CofvkozKCPPv1mZEBWg5Y5sp0L4U"

BINANCE_ACCOUNTS = [
    {"name": "BN_BJS", "api_key": "s4ccyNROKsO8HdJXwecZhdCusMdlt8LqNzeeKFUjEanGXL6ArPQtW81aAgPU0Qdz", "api_secret": "6flEy9RqJ0mTw95gMxnVXTjqSOnPYG546bGJvjUwmq80RHhRNR2BDwWLI0Xm1jM2"}
]

BYBIT_ACCOUNTS = [
    {"name": "BB_BJS", "api_key": "UTq8jlDidgBTh8JGaZ", "api_secret": "sxlrspOyHphjuNObCkcMKKcle8WW5wubC3Fi"}
]

BITGET_ACCOUNTS = [
    {"name": "BG_BJS", "api_key": "bg_b0eb5047373445d91669a81cce2e5654", "api_secret": "4f6cb11ae8c1cdabb39aeb4456dacacdfee47e9e9e0df669f22469f3c744591f", "passphrase": "dhfmsvkf"}
]

REDIS_CONFIG = {
    "host": "vultr-prod-3a00cfaa-7dc1-4fed-af5b-19dd1a19abf2-vultr-prod-cd4a.vultrdb.com",
    "port": "16752",
    "db": "0",
    "username": "armbjs",
    "password": "xkqfhf12",
    "ssl": True,
    "channel_name_prefix": "TEST_NEW_NOTICES"
}

BITGET_BASE_URL = "https://api.bitget.com"

manager = ExManager(
    redis_config=REDIS_CONFIG,
    binance_accounts=BINANCE_ACCOUNTS,
    bybit_accounts=BYBIT_ACCOUNTS,
    bitget_accounts=BITGET_ACCOUNTS,
    bitget_base_url=BITGET_BASE_URL
)

def handle_message(update: Update, context: CallbackContext):
    # v13.7에서는 Filters를 통해 text & ~command 필터링
    # Filters.text & (~Filters.command)는 텍스트이면서 명령어가 아닌 메시지만 처리
    if update.message and update.message.text:
        text = update.message.text.strip()
        result = manager.execute_command(text, REDIS_CONFIG["channel_name_prefix"])

        MAX_LENGTH = 4000
        if len(result) > MAX_LENGTH:
            with tempfile.NamedTemporaryFile(prefix="output_", suffix=".txt", delete=False, mode='w', encoding='utf-8') as f:
                f.write(result)
                f.flush()
                file_path = f.name
            
            update.message.reply_text("결과가 너무 길어 파일로 첨부합니다. 아래 파일을 다운로드해주세요.")
            with open(file_path, 'rb') as f:
                context.bot.send_document(chat_id=update.effective_chat.id, document=f)
        else:
            if result.strip():
                update.message.reply_text(result)

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # v13.x에서는 Filters.text와 Filters.command 사용 가능
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    print("Telegram Bot started. Waiting for commands...\n")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
