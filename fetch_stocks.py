import time
import pandas as pd
import yfinance as yf
from datetime import datetime

def calculate_ma_diff_from_csv(input_csv="stock_list.csv", output_csv="stock_ma_diff.csv", batch_size=50):
    print(f"正在讀取 {input_csv}...", flush=True)
    stock_df = pd.read_csv(input_csv)
    ticker_to_name = dict(zip(stock_df["Ticker"], stock_df["Name"]))
    tickers = stock_df["Ticker"].dropna().unique().tolist()
    
    results = []
    total = len(tickers)
    print(f"開始處理共 {total} 檔股票，每批 {batch_size} 檔...", flush=True)

    # 分批下載避免 Yahoo Finance 阻擋或逾時
    for i in range(0, total, batch_size):
        batch = tickers[i:i + batch_size]
        print(f"正在下載第 {i + 1} 到 {min(i + batch_size, total)} 檔...", flush=True)
        
        try:
            data = yf.download(batch, period="6mo", group_by="ticker", progress=False)
        except Exception as e:
            print(f"批次下載發生錯誤: {e}", flush=True)
            continue
            
        for ticker in batch:
            try:
                if len(batch) == 1:
                    df = data.dropna(subset=["Close"]).copy()
                else:
                    if ticker not in data.columns.get_level_values(0):
                        continue
                    df = data[ticker].dropna(subset=["Close"]).copy()
                    
                # 確保至少有 60 個交易日以計算季線
                if len(df) < 60:
                    continue
                
                # 計算週線(5MA)、月線(20MA)、季線(60MA)
                df["MA5"] = df["Close"].rolling(window=5).mean()
                df["MA20"] = df["Close"].rolling(window=20).mean()
                df["MA60"] = df["Close"].rolling(window=60).mean()
                
                latest = df.iloc[-1]
                latest_date = df.index[-1].strftime("%Y-%m-%d")
                close = float(latest["Close"])
                ma5 = float(latest["MA5"])
                ma20 = float(latest["MA20"])
                ma60 = float(latest["MA60"])
                
                if close == 0:
                    continue
                
                # 計算 (收盤價 - 均線) / 收盤價 百分比 (現價低於均線為負值)
                diff_5_pct = ((close - ma5) / close) * 100
                diff_20_pct = ((close - ma20) / close) * 100
                diff_60_pct = ((close - ma60) / close) * 100
                
                results.append({
                    "資料日期": latest_date,
                    "股票代號": ticker,
                    "股票名稱": ticker_to_name.get(ticker, ""),
                    "最新收盤價": round(close, 2),
                    "週線(5MA)": round(ma5, 2),
                    "月線(20MA)": round(ma20, 2),
                    "季線(60MA)": round(ma60, 2),
                    "週線差對收盤價(%)": round(diff_5_pct, 2),
                    "月線差對收盤價(%)": round(diff_20_pct, 2),
                    "季線差對收盤價(%)": round(diff_60_pct, 2),
                })
            except Exception as e:
                print(f"計算 {ticker} 時發生錯誤: {e}", flush=True)
                
        # 每批間隔 2 秒，降低被伺服器限制的機率
        time.sleep(2)

    if not results:
        print("警告：未成功取得任何股票數據，請檢查網路或清單。", flush=True)
        return

    result_df = pd.DataFrame(results)
    
    # 依照「月線差對收盤價(%)」由小到大排序（負值最多者排在最前面）
    result_df = result_df.sort_values(by="月線差對收盤價(%)", ascending=True)
    
    # 存成 UTF-8-SIG 編碼，確保 Windows Excel 直接開啟中文不亂碼
    result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"[{datetime.now()}] 完成！共 {len(result_df)} 檔股票已排序並儲存至 {output_csv}。", flush=True)

if __name__ == "__main__":
    calculate_ma_diff_from_csv()
