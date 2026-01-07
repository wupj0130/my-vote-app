import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="2026 影片決選投票系統", layout="wide")

# 這裡貼上您剛才複製的 Google 試算表網址
URL = "這裡請換成您的試算表網址"

# 建立雲端連接
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 讀取影片 (從 Google Sheets 直接讀，絕無亂碼)
video_df = conn.read(spreadsheet=URL)

# 2. 投票紀錄 (暫存在伺服器，但提供下載報表功能)
if 'all_records' not in st.session_state:
    st.session_state.all_records = []

# --- 14位評審名單 ---
with st.sidebar:
    st.title("🗳️ 評審控制台")
    voter_names = ["憲哥", "范大", "小荳", "曉宣", "培芯", "Connie", "Grace", "Kathy", "Kate", "Kyle", "Parel", "Sharon", "YoYo", "Yvonne"]
    current_user = st.selectbox("請選擇您的姓名：", voter_names)
    
    user_data = [r for r in st.session_state.all_records if r['voter'] == current_user]
    user_votes = [r['video_id'] for r in user_data if r['type'] == 'vote']
    user_guarantee = next((r['video_id'] for r in user_data if r['type'] == 'guarantee'), None)
    
    st.metric("已投票數 (上限50)", f"{len(user_votes)} / 50")

# --- 主畫面 ---
tab1, tab2 = st.tabs(["🎥 影片投票區", "📊 統計報表"])

with tab2:
    if st.session_state.all_records:
        df_rec = pd.DataFrame(st.session_state.all_records)
        v_counts = df_rec[df_rec['type']=='vote']['video_id'].value_counts().to_dict()
        g_map = df_rec[df_rec['type']=='guarantee'].set_index('video_id')['voter'].to_dict()
        
        rep = video_df.copy()
        rep['得票數'] = rep['id'].map(v_counts).fillna(0).astype(int)
        rep['保送人'] = rep['id'].map(g_map).fillna("—")
        rep['排序'] = rep['保送人'].apply(lambda x: 0 if x != "—" else 1)
        st.table(rep.sort_values(['排序', '得票數'], ascending=[True, False]).head(50))
    else:
        st.info("尚無投票紀錄。")

with tab1:
    search = st.text_input("🔍 搜尋投稿者或居住地")
    f_df = video_df[video_df['uploader'].astype(str).str.contains(search) | video_df['location'].astype(str).str.contains(search)]
    
    for _, row in f_df.iterrows():
        with st.expander(f"【ID {row['id']}】 {row['uploader']} - {row['location']}"):
            c1, c2 = st.columns([3, 1])
            with c1: st.video(row['url'])
            with c2:
                # 投票按鈕
                if st.button("✅ 投票" if row['id'] not in user_votes else "❌ 取消", key=f"v_{row['id']}"):
                    if row['id'] in user_votes:
                        st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter']==current_user and r['video_id']==row['id'])]
                    elif len(user_votes) < 50:
                        st.session_state.all_records.append({'voter':current_user, 'video_id':row['id'], 'type':'vote'})
                    st.rerun()
                # 保送按鈕
                if st.button("🌟 保送", key=f"g_{row['id']}", type="primary" if user_guarantee == row['id'] else "secondary"):
                    st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter']==current_user and r['type']=='guarantee')]
                    if user_guarantee != row['id']:
                        st.session_state.all_records.append({'voter':current_user, 'video_id':row['id'], 'type':'guarantee'})
                    st.rerun()
