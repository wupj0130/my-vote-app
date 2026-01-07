import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="2026 影片決選投票系統", layout="wide")

# 請在此貼上您的 Google 試算表網址
URL = "https://docs.google.com/spreadsheets/d/1FmxeSiHJYG7gvAMJeKYoBM0IUS7DCZorJ6h1In0LH44/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 讀取影片
@st.cache_data(ttl=10)
def load_videos():
    return conn.read(spreadsheet=URL, worksheet="videos")

video_df = load_videos()

# 2. 讀取與寫入投票紀錄 (解決資料遺失問題)
def load_records():
    return conn.read(spreadsheet=URL, worksheet="records")

def save_record_to_cloud(voter, video_id, vote_type):
    existing_records = load_records()
    new_data = pd.DataFrame([{"voter": voter, "video_id": video_id, "type": vote_type}])
    updated_df = pd.concat([existing_records, new_data], ignore_index=True)
    conn.update(spreadsheet=URL, worksheet="records", data=updated_df)

# ---------------------------------------------------------
# 以下為 UI 邏輯
with st.sidebar:
    st.title("🗳️ 評審控制台")
    voter_names = ["憲哥", "范大", "小荳", "曉宣", "培芯", "Connie", "Grace", "Kathy", "Kate", "Kyle", "Parel", "Sharon", "YoYo", "Yvonne"]
    current_user = st.selectbox("請選擇姓名：", voter_names)
    
    # 讀取當前紀錄
    all_rec_df = load_records()
    user_rec = all_rec_df[all_rec_df['voter'] == current_user]
    st.metric("已投票數", len(user_rec[user_rec['type']=='vote']))

tab1, tab2 = st.tabs(["🎥 影片投票", "📊 統計報表"])

with tab1:
    search = st.text_input("🔍 搜尋")
    f_df = video_df[video_df['uploader'].str.contains(search) | video_df['location'].str.contains(search)]
    for _, row in f_df.iterrows():
        with st.expander(f"【{row['id']}】{row['uploader']}"):
            st.video(row['url'])
            if st.button(f"投票給 {row['id']}", key=f"v_{row['id']}"):
                save_record_to_cloud(current_user, row['id'], 'vote')
                st.success("投票成功並已存至雲端！")

                st.rerun()
