FROM python:3.8

RUN pip install --index-url http://armbjs:xkqfhf12@docker.armbjs.com:8080/simple/ trade_manager --no-cache-dir --trusted-host docker.armbjs.com:8080

CMD ["python", "-m", "trade_manager"]