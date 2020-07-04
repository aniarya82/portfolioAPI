import flask
from flask import request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import json
import pprint
import math

app = flask.Flask(__name__)

app.config["DEBUG"] = True

books = [
    {'id': 0,
     'title': 'A Fire Upon the Deep',
     'year_published': '1992'},
    {'id': 1,
     'title': 'The Ones Who Walk Away From Omelas',
     'published': '1973'},
    {'id': 2,
     'title': 'Dhalgren',
     'published': '1975'}
]

pp = pprint.PrettyPrinter(indent=4)


@app.route('/api/', methods=['GET'])
def home():
    return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels.</p>"


@app.route('/api/books/all', methods=['GET'])
def book():
    return jsonify(books)


@app.route('/api/nifty50/', methods=['GET'])
def niftyfifty():
    with open('stocks.json') as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/savePortfolio', methods=['POST'])
def savePortfolio():
    form = request.data
    # form = json.loads(form.decode('ASCII'))
    print("in saveprotfolio post request")
    print(form)
    # print(type(form))
    jsonData = json.loads(form)
    print(jsonData['Tickers'])
    # print(jsonData.Tickers)
    jsonDt = []
    for i in jsonData['Weights']:
        jsonDt.append(float(i))
    # print(type(jsonData))
    jsonDf = compute_portfolio(
        jsonData['Tickers'], jsonData['Duration'], jsonDt)
    return jsonDf


# @app.route('/api/saveWeights', methods=['POST'])
# def saveWeights():
#     print("in saveweights post request")
#     form = request.data
#     # print(form)
#     jsonDt = json.loads(form)
#     jsonData = []
#     for i in jsonDt:
#         jsonData.append(float(i))
#     print(jsonData)
#     jsonDf = compute_portfolio(jsonData)
#     return jsonify(jsonDf)


def stockHistory(tick, prd="1y"):
    ticker = yf.Ticker(tick)
    # period  = 1d,5d,1mo,6mo,1y,3y,ytd,max
    history = ticker.history(period=prd)
    # print()
    return history.to_json(orient="table")


# DF = pd.DataFrame()
# X = []
# SD = []
# AVG = []
# sdnp = None
# cordf = None
# tickers = []


def compute_portfolio(ticker_list, duration, wt):
    duration = " ".join(map(str, duration))
    duration = duration + "y"
    print("In compute Portfolio, duration", duration)
    htmlFile = ""
    DF = pd.DataFrame()
    X = []
    SD = []
    AVG = []
    for tick in ticker_list:
        print("Current tick in list : ", tick)
        tagg = yf.Ticker(tick)
        hist = tagg.history(period=duration)
        tmpdf = pd.DataFrame(data=hist['Close'])
        tmpdf['DReturns'] = tmpdf['Close'].pct_change()*100
        avg = tmpdf['DReturns'].mean()
        print(avg)
        SD.append(tmpdf['DReturns'].std())
        AVG.append(avg)
        Y = []
        idx = 0
        for i in tmpdf['DReturns']:
            if idx == 0:
                idx += 1
                continue
            Y.append(i-avg)
        X.append(Y)
        DF = pd.concat([DF, tmpdf], axis=1)
    # pp.pprint(df)
    # return df.to_json(orient="table")
    # htmlFile += "<h1>First</h1>"
    # htmlFile += df.to_html(classes=["table", "table-striped"])
    # Number of Obeservation
    num_obs = len(DF.index)
    # DataFrame created for Variance Covariane Matrix
    Xdf = pd.DataFrame(data=X)
    XTdf = Xdf.transpose()
    # Convert both Dataframe to numpy for DOT Product
    Xnp = Xdf.to_numpy()
    XTnp = XTdf.to_numpy()
    XtX = Xnp.dot(XTnp)
    # Convert computed numpy back to dataframe
    XtXdf = pd.DataFrame(data=XtX, index=ticker_list, columns=ticker_list)
    XtXdf = XtXdf.div(num_obs)
    # htmlFile += "<h1>Weighted Standard deviation</h1>"
    # HTML File for display purpose
    # htmlFile += XtXdf.to_html(classes=["table", "table-striped"])
    # Convert list of Standard deviation to dataframe
    sddf = pd.DataFrame(data=SD)
    sdtdf = sddf.transpose()
    global sdnp
    sdnp = sddf.to_numpy()
    sdtnp = sdtdf.to_numpy()
    sdtsd = sdnp.dot(sdtnp)
    SDdf = pd.DataFrame(data=sdtsd, index=ticker_list, columns=ticker_list)
    # htmlFile += "<h1>Standart Deviation Matrix</h1>"
    # HTML File for display purpose
    # htmlFile += SDdf.to_html(classes=["table", "table-striped"])
    global cordf
    # Correlation matrix by VCov/ProdSD
    cordf = XtXdf.div(SDdf)
    print("\nCorrelation Matrix")
    pp.pprint(cordf)
    htmlFile += "<h1>Coorelation Matrix</h1>"
    htmlFile += cordf.to_html(classes=["table", "table-striped"])
    # SECOND PART OF CALCULATION WITH WEIGHTS INVOLVED
    wtDf = pd.DataFrame(data=wt)
    wtNp = wtDf.to_numpy()
    # print(wtNp)
    # global sdnp
    wt_std = np.multiply(wtNp, sdnp)
    wt_std_t = np.transpose(wt_std)
    # global cordf
    corr_np = cordf.to_numpy()
    m1 = wt_std_t.dot(corr_np)
    m2 = m1.dot(wt_std)
    sigma = math.sqrt(m2)
    annual_var = math.sqrt(252)*sigma

    print("Daily portfolio Variance: ", sigma)
    print("Annual portfolio Variance: ", annual_var)
    avgDf = pd.DataFrame(data=AVG)
    yr_rt = avgDf.mul(252)
    avgnp = yr_rt.to_numpy()
    wt_yr_rt = np.multiply(avgnp, wtNp)
    annual_rt = np.sum(wt_yr_rt)
    print("Annual expected return: ", annual_rt)
    stdport = []
    for i in range(len(ticker_list)):
        tmpport = {
            "Ticker": ticker_list[i],
            "Weight": wt[i]
        }
        stdport.append(tmpport)
    res = {
        "Variance": annual_var,
        "Return": annual_rt,
        "Portfolio": stdport
    }
    return jsonify(res)
    # return htmlFile


@app.route('/api/books', methods=['GET'])
def book_id():
    if 'id' in request.args:
        id = int(request.args['id'])
    else:
        return "Error: No id mentioned. Please specify id"

    results = []
    for bk in books:
        if bk['id'] == id:
            results.append(bk)

    return jsonify(results)


@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


app.run()
