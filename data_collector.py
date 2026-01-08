import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


DEFAULT_TICKERS = ["LGRRX"]


def fetch_history(ticker: str) -> pd.DataFrame:
    df = yf.download(
        tickers=ticker,
        period="60d",
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
    if df.empty:
        return df
    df = df.reset_index()
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the last 60 days of daily data for one or more tickers."
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Ticker symbols to download (default: LGRRX).",
    )
    parser.add_argument(
        "--out-dir",
        default="data",
        help="Output directory for CSV files (default: ./data).",
    )
    args = parser.parse_args()

    tickers = args.tickers or DEFAULT_TICKERS
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_date = datetime.now().strftime("%Y%m%d")
    for ticker in tickers:
        df = fetch_history(ticker)
        if df.empty:
            print(f"{ticker}: no data returned")
            continue
        out_path = out_dir / f"{ticker}_last_60d_{run_date}.csv"
        df.to_csv(out_path, index=False)
        print(f"{ticker}: wrote {out_path}")


if __name__ == "__main__":
    main()
