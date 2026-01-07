import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="2026 影片決選投票系統", layout="wide")

# 1. Google 試算表連結
URL = "https://docs.google.com/spreadsheets/d/1FmxeSiHJYG7gvAMJeKYoBM0IUS7DCZorJ6h1In0LH44/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 讀取影片 (加強過濾空白與無效連結)
@st.cache_data(ttl=5) # 縮短快取時間，方便妳除錯
def load_videos():
    try:
        df = conn.read(spreadsheet=URL, worksheet="videos")
        # 排除完全空白的列與沒有網址的資料
        df = df.dropna(subset=['id', 'url'])
        df = df[df['url'].astype(str).str.contains('http', na=False)]
        return df
    except Exception as e:
        st.error(f"讀取 videos 失敗：{e}")
        return pd.DataFrame()

# 3. 讀取投票紀錄
def load_records():
    try:
        df = conn.read(spreadsheet=URL, worksheet="records")
        return df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["voter", "video_id", "type"])

def save_record_to_cloud(voter, video_id, vote_type):
    existing_records = load_records()
    new_data = pd.DataFrame([{"voter": voter, "video_id": video_id, "type": vote_type}])
    updated_df = pd.concat([existing_records, new_data], ignore_index=True)
    conn.update(spreadsheet=URL, worksheet="records", data=updated_df)

# --- 介面開始 ---
video_df = load_videos()
all_rec_df = load_records()

with st.sidebar:
    st.title("🗳️ 評審控制台")
    voter_names = ["憲哥", "范大", "小荳", "曉宣", "培芯", "Connie", "Grace", "Kathy", "Kate", "Kyle", "Parel", "Sharon", "YoYo", "Yvonne"]
    current_user = st.selectbox("請選擇姓名：", voter_names)
    
    if not all_rec_df.empty and 'voter' in all_rec_df.columns:
        user_rec = all_rec_df[all_rec_df['voter'] == current_user]
        st.metric("已投票數", len(user_rec[user_rec['type']=='vote']))
    else:
        st.metric("已投票數", 0)

tab1, tab2 = st.tabs(["🎥 影片投票", "📊 統計報表"])

with tab1:
    search = st.text_input("🔍 搜尋", "")
    f_df = video_df.copy()
    if search:
        f_df = f_df[f_df['uploader'].astype(str).str.contains(search, na=False) | 
                    f_df['location'].astype(str).str.contains(search, na=False)]
    
    if f_df.empty:
        st.info("目前沒有影片資料或搜尋不到結果。")
    else:
        for index, row in f_df.iterrows():
            with st.expander(f"【{row['id']}】{row['uploader']}"):
                # --- 這裡就是關鍵的「防撞牆」 ---
                v_url = str(row['url']).strip()
                try:
                    # 只有在連結有效時才嘗試播放
                    if "http" in v_url:
                        st.video(v_url)
                    else:
                        st.warning(f"⚠️ 無效網址：{v_url}")
                except Exception as e:
                    # 萬一網址格式讓 st.video 崩潰，這裡會擋住
                    st.error(f"❌ 影片播放發生錯誤 (ID: {row['id']})。請檢查 Excel 網址格式。")
                
                if st.button(f"投票給 {row['id']}", key=f"v_{row['id']}"):
                    save_record_to_cloud(current_user, row['id'], 'vote')
                    st.success("投票成功！")
                    st.rerun()
