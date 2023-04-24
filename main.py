import requests

import models
import yfinance
from sqlalchemy import select
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal, engine
from pydantic import BaseModel
from models import Stock
from sqlalchemy.orm import Session

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


class StockRequest(BaseModel):
    symbol: str


def get_db():
    # 6. Local variable 'db' might be referenced before assignment
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home(request: Request, forward_pe=None, dividend_yield=None, ma50=None, ma200=None, db: Session = Depends(get_db)):
    """
    show all stocks in the database and button to add more
    button next to each stock to delete from database
    filters to filter this list of stocks
    button next to each to add a note or save for later
    """

    stocks = db.query(Stock)

    if forward_pe:
        stocks = stocks.filter(Stock.forward_pe < forward_pe)

    if dividend_yield:
        stocks = stocks.filter(Stock.dividend_yield > dividend_yield)

    if ma50:
        stocks = stocks.filter(Stock.price > Stock.ma50)

    if ma200:
        stocks = stocks.filter(Stock.price > Stock.ma200)

    stocks = stocks.all()

    return templates.TemplateResponse("home.html", {
        "request": request,
        "stocks": stocks,
        "dividend_yield": dividend_yield,
        "forward_pe": forward_pe,
        "ma200": ma200,
        "ma50": ma50
    })


# def fetch_stock_data(id: int):
#     db = SessionLocal()
#
#     stock = db.query(Stock).filter(Stock.id == id).first()
#
#     try:
#
#         yahoo_data = yfinance.Ticker(stock.symbol)  # something here
#     except requests.exceptions.HTTPError:
#         raise HTTPException(status_code=400, detail='Wrong symbol')
#     stock.ma200 = yahoo_data.info['twoHundredDayAverage']  # error here
#     stock.ma50 = yahoo_data.info['fiftyDayAverage']
#     stock.price = yahoo_data.info['previousClose']
#     stock.forward_pe = yahoo_data.info['forwardPE']
#     stock.forward_eps = yahoo_data.info['forwardEps']
#     stock.dividend_yield = yahoo_data.info['dividendYield'] * 100
#
#     db.add(stock)
#     db.commit()


@app.post("/stock", response_class=RedirectResponse)
async def create_stock(
        stock_request: StockRequest,
        db: Session = Depends(get_db),
):
    """
    add one or more tickers to the database
    background task to use yfinance and load key statistics
    """
    # 1 - Issue is unique symbol exception. Need validation - /stock post request
    is_exist = db.execute(
        select(select(Stock).filter_by(symbol=stock_request.symbol).exists())
    ).scalar_one()
    if is_exist:
        raise HTTPException(status_code=400, detail='Already exists')
    # 2. Create ticker instance - /stock post request
    # 3. Issue invalid yahoo finance symbol. - /stock post request
    ticker = yfinance.Ticker(stock_request.symbol)
    try:
        yahoo_info = ticker.info
    except requests.exceptions.HTTPError:
        raise HTTPException(status_code=400, detail='Wrong symbol')
    # 4. Prepare stock data - /stock post request
    # 5. use dict getters - /stock post request
    obj_in = {
        'ma200': yahoo_info.get('twoHundredDayAverage'),
        'ma50': yahoo_info.get('fiftyDayAverage'),
        'price': yahoo_info.get('previousClose'),
        'forward_pe': yahoo_info.get('forwardPE', ),
        'forward_eps': yahoo_info.get('forwardEps', ),
        'dividend_yield': yahoo_info.get('dividendYield') * 100,
        'symbol': stock_request.symbol
    }
    stock = Stock(**obj_in)
    db.add(stock)
    db.commit()

    return RedirectResponse(
        '/', status_code=303
    )
