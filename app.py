import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.data_fetcher import fetch_klines, get_conversion_rate
from src.predict import get_latest_prediction
from src.features import add_technical_indicators

st.set_page_config(page_title="Crypto Pro Predictor", layout="wide", page_icon="📈")

# --- CSS for "Pro" look ---
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .stApp {
        background-color: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("⚙️ Settings")
selected_coin_pair = st.sidebar.selectbox("Select Coin", ["BTC", "ETH", "BNB", "SOL", "ADA"])
selected_currency = st.sidebar.selectbox("Display Currency", ["USD", "INR", "EUR", "GBP", "AUD", "CAD", "JPY"])

# --- Main Logic ---
st.title(f"🚀 {selected_coin_pair} Price Intelligence")

# 1. Fetch Data
with st.spinner("Fetching market data..."):
    # Always fetch USDT pair for model consistency
    symbol = f"{selected_coin_pair}USDT"
    df = fetch_klines(symbol, limit=500)
    
    if df is not None:
        # Get Conversion Rate if needed
        rate = 1.0
        currency_symbol = "$"
        if selected_currency != "USD":
            rate = get_conversion_rate(selected_currency)
            currency_symbol = selected_currency
            
        current_price = df['close'].iloc[-1] * rate
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) * rate
        pct_change = (price_change / (df['close'].iloc[-2] * rate)) * 100
        
        # Display Top Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", f"{currency_symbol} {current_price:,.2f}", f"{pct_change:.2f}%")
        
        # 2. Run Prediction with Uncertainty
        pred_data = get_latest_prediction(symbol, df)
        
        if pred_data:
            # Convert predictions
            mean_preds = pred_data['mean'] * rate
            lower_preds = pred_data['lower'] * rate
            upper_preds = pred_data['upper'] * rate
            
            # Next Day Prediction
            next_day_price = mean_preds[0]
            trend = "Bullish 🟢" if next_day_price > current_price else "Bearish 🔴"
            
            col2.metric("Next Day Forecast", f"{currency_symbol} {next_day_price:,.2f}", trend)
            
            # Uncertainty (Average Band Width)
            uncertainty = (upper_preds[0] - lower_preds[0]) / 2
            col3.metric("Uncertainty (±)", f"{currency_symbol} {uncertainty:,.2f}", "90% Confidence")
            
            # --- Tabs for Analysis ---
            tab1, tab2, tab3 = st.tabs(["📈 Forecast Chart", "🧠 Explainability", "🏥 Model Health"])
            
            with tab1:
                st.subheader("7-Day Price Forecast")
                
                # Plotly Chart
                fig = go.Figure()
                
                # Historical Data (Last 90 days)
                hist_data = df.iloc[-90:].copy()
                hist_data['close'] = hist_data['close'] * rate
                
                fig.add_trace(go.Scatter(
                    x=hist_data.index, 
                    y=hist_data['close'],
                    mode='lines',
                    name='Historical',
                    line=dict(color='cyan')
                ))
                
                # Forecast Dates
                last_date = hist_data.index[-1]
                forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=7)
                
                # Forecast Mean
                fig.add_trace(go.Scatter(
                    x=forecast_dates,
                    y=mean_preds,
                    mode='lines+markers',
                    name='Forecast',
                    line=dict(color='yellow', dash='dash')
                ))
                
                # Confidence Interval (Shaded Area)
                fig.add_trace(go.Scatter(
                    x=pd.concat([pd.Series(forecast_dates), pd.Series(forecast_dates[::-1])]),
                    y=pd.concat([pd.Series(upper_preds), pd.Series(lower_preds[::-1])]),
                    fill='toself',
                    fillcolor='rgba(255, 255, 0, 0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    hoverinfo="skip",
                    showlegend=True,
                    name='Confidence Band (5%-95%)'
                ))
                
                fig.update_layout(
                    height=500,
                    template="plotly_dark",
                    xaxis_title="Date",
                    yaxis_title=f"Price ({selected_currency})",
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            with tab2:
                st.subheader("Why this prediction?")
                
                # Calculate indicators for explanation
                df_indic = add_technical_indicators(df.copy())
                last_rsi = df_indic['rsi'].iloc[-1]
                last_macd = df_indic['MACD_12_26_9'].iloc[-1]
                last_atr = df_indic['atr'].iloc[-1]
                
                col_exp1, col_exp2 = st.columns(2)
                
                with col_exp1:
                    st.markdown(f"**RSI (Momentum):** `{last_rsi:.1f}`")
                    if last_rsi > 70:
                        st.warning("⚠️ Market is Overbought. Possible correction ahead.")
                    elif last_rsi < 30:
                        st.success("✅ Market is Oversold. Possible bounce ahead.")
                    else:
                        st.info("ℹ️ Market momentum is Neutral.")
                        
                with col_exp2:
                    st.markdown(f"**MACD (Trend):** `{last_macd:.4f}`")
                    if last_macd > 0:
                        st.success("🟢 Positive Trend Momentum")
                    else:
                        st.error("🔴 Negative Trend Momentum")
                        
                st.markdown("---")
                st.markdown(f"**Volatility (ATR):** The market is moving approximately `{currency_symbol} {(last_atr * rate):.2f}` per day on average.")
                
            with tab3:
                st.subheader("Model Diagnostics")
                metadata = pred_data['metadata']
                st.json(metadata)
                
                if 'metrics' in metadata:
                    m = metadata['metrics']
                    st.write(f"**Validation MAE:** {m.get('val_mae'):.4f}")
                    st.write(f"**Training Epochs:** {m.get('epochs')}")
                    st.write(f"**Data Points:** {m.get('data_points')}")
                    
        else:
            st.error("Could not generate prediction. Model might be missing.")
            if st.button("Train Model Now"):
                with st.spinner("Training..."):
                    from src.train_model import train_coins
                    train_coins()
                    st.success("Training Complete! Refresh page.")
    else:
        st.error("Failed to fetch data from Binance.")
