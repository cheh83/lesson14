import random
import string
import time
from typing import Callable

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

create_random_string: Callable[[int], str] = lambda size: "".join(
    [random.choice(string.ascii_letters) for _ in range(size)]
)# noqa: E731


@app.get("/generate-article")
async def get_information():
    """This endpoint returns the random information"""
    return {
        "title": create_random_string(size=10),
        "description": create_random_string(size=20),
    }


class ExchangeRateRequest(BaseModel):
    from_currency: str
    to_currency: str


class ExchangeRateResponse(BaseModel):
    rate: str


exchange_rate_cache = {}


@app.post("/fetch-exchange-rate", response_model=ExchangeRateResponse)
async def get_current_market_state(request_data: ExchangeRateRequest):
    current_time = time.time()

    # Проверяем, был ли последний запрос в течение последних 10 секунд и есть ли курс в кеше
    if (
        current_time - exchange_rate_cache.get("last_request_time", 0) <= 10
        and request_data.from_currency in exchange_rate_cache
    ):
        return ExchangeRateResponse(
            rate=exchange_rate_cache[request_data.from_currency]
        )
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={request_data.from_currency}&to_currency={request_data.to_currency}&apikey=6I2HOYT0DOXGAH5T"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()  # Проверка успешности ответа

            rate = response.json()["Realtime Currency Exchange Rate"][
                "5. Exchange Rate"
            ]

            # Обновляем кеш
            exchange_rate_cache[request_data.from_currency] = rate
            exchange_rate_cache["last_request_time"] = current_time

            return ExchangeRateResponse(rate=rate)
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500, detail=f"HTTP error during request: {str(e)}"
            ) from e
