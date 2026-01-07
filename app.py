import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 測試連線
st.title("連線測試頁面")

# 1. 請在此貼上您的網址
URL = "您的試算表網址" 

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL)
    st.success("✅ 連線成功！以下是您的影片資料：")
    st.write(df)
except Exception as e:
    st.error(f"❌ 連線失敗，錯誤訊息如下：")
    st.code(str(e))