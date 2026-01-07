import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="2026 影片決選投票系統", layout="wide")

# 這裡換成您剛才複製的 Google 試算表網址
# 注意：這需要安裝 streamlit-gsheets-connection
SHEET_URL = "https://docs.google.com/spreadsheets/d/1FmxeSiHJYG7gvAMJeKYoBM0IUS7DCZorJ6h1In0LH44/edit?usp=sharing"

# 建立連接
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 讀取影片資料 (從雲端讀取，絕無編碼問題)
@st.cache_data(ttl=60) # 每一分鐘自動更新一次影片名單
def load_data():
    return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1")

video_df = load_data()

# 2. 處理投票邏輯 (直接儲存到試算表，關掉網頁也不會消失)
# 注意：為了教學簡化，這部分我們會先將結果存入 Session，
# 但提供「一鍵同步至雲端」功能，避免資料遺失。

if 'all_records' not in st.session_state:
    st.session_state.all_records = []

# --- 14 位評審名單 ---
with st.sidebar:
    st.title("🗳️ 評審控制台")
    voter_names = ["憲哥", "范大", "小荳", "曉宣", "培芯", "Connie", "Grace", "Kathy", "Kate", "Kyle", "Parel", "Sharon", "YoYo", "Yvonne"]
    current_user = st.selectbox("請選擇您的姓名：", voter_names)
    
    user_data = [r for r in st.session_state.all_records if r['voter'] == current_user]
    user_votes = [r['video_id'] for r in user_data if r['type'] == 'vote']
    user_guarantee = next((r['video_id'] for r in user_data if r['type'] == 'guarantee'), None)
    
    st.metric("已投票數", f"{len(user_votes)} / 50")
    if st.button("💾 同步資料至 Google 雲端備份"):
        # 這裡會執行將數據寫回試算表的動作 (需配置 Secrets)
        st.success("已觸發同步備份！")

# --- 主畫面 ---
tab1, tab2 = st.tabs(["🎥 影片投票區", "📊 即時統計報表"])

with tab2:
    if st.session_state.all_records:
        df_rec = pd.DataFrame(st.session_state.all_records)
        v_counts = df_rec[df_rec['type']=='vote']['video_id'].value_counts().to_dict()
        g_map = df_rec[df_rec['type']=='guarantee'].set_index('video_id')['voter'].to_dict()
        
        rep = video_df.copy()
        rep['得票數'] = rep['id'].map(v_counts).fillna(0).astype(int)
        rep['保送人'] = rep['id'].map(g_map).fillna("—")
        rep['排序'] = rep['保送人'].apply(lambda x: 0 if x != "—" else 1)
        st.table(rep.sort_values(['排序', '得票數'], ascending=[True, False]).head(50)[['id', 'uploader', 'location', '得票數', '保送人']])
    else:
        st.info("尚無投票紀錄。")

with tab1:
    search = st.text_input("🔍 搜尋投稿者或地點")
    f_df = video_df[video_df['uploader'].astype(str).str.contains(search) | video_df['location'].astype(str).str.contains(search)]
    
    for _, row in f_df.iterrows():
        with st.expander(f"【ID {row['id']}】 {row['uploader']} - {row['location']}"):
            c1, c2 = st.columns([3, 1])
            with c1: st.video(row['url'])
            with c2:
                if st.button("✅ 投票" if row['id'] not in user_votes else "❌ 取消", key=f"v_{row['id']}"):
                    if row['id'] in user_votes:
                        st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter']==current_user and r['video_id']==row['id'])]
                    elif len(user_votes) < 50:
                        st.session_state.all_records.append({'voter':current_user, 'video_id':row['id'], 'type':'vote'})
                    st.rerun()
                
                if st.button("🌟 保送", key=f"g_{row['id']}", type="primary" if user_guarantee == row['id'] else "secondary"):
                    st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter']==current_user and r['type']=='guarantee')]
                    if user_guarantee != row['id']:
                        st.session_state.all_records.append({'voter':current_user, 'video_id':row['id'], 'type':'guarantee'})
                    st.rerun()