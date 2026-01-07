import streamlit as st
import pandas as pd
import os

# 頁面設定
st.set_page_config(page_title="影片決選投票系統", layout="wide")

# --- 檔案路徑設定 ---
VIDEO_FILE = "videos.csv"       # 影片清單檔案
RECORD_FILE = "vote_records.csv" # 投票紀錄檔案

# 1. 讀取影片清單 (每次重新整理都會讀取最新 CSV)
def load_videos():
    if os.path.exists(VIDEO_FILE):
        # 使用 utf-8-sig 確保 Excel 開啟不亂碼
        return pd.read_csv(VIDEO_FILE, encoding="utf-8-sig")
    else:
        # 如果找不到檔案，生成一個基礎範例
        df = pd.DataFrame([{"id": 1, "uploader": "範例投稿者", "location": "地點", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}])
        return df

# 2. 讀取/初始化投票紀錄
def load_records():
    if os.path.exists(RECORD_FILE):
        return pd.read_csv(RECORD_FILE).to_dict('records')
    return []

# 初始化 Session State
if 'all_records' not in st.session_state:
    st.session_state.all_records = load_records()

# 儲存紀錄的函式 (自動存檔)
def save_current_records():
    df = pd.DataFrame(st.session_state.all_records)
    df.to_csv(RECORD_FILE, index=False, encoding="utf-8-sig")

# 每次跑程式都重新抓取最新的影片清單
video_df = load_videos()

# --- 側邊欄：身分與統計 ---
with st.sidebar:
    st.title("🗳️ 投票控制台")
    
    # --- 這裡已經更新為您提供的 14 位評審名單 ---
    voter_names = [
        "憲哥", "范大", "小荳", "曉宣", "培芯", 
        "Connie", "Grace", "Kathy", "Kate", "Kyle", 
        "Parel", "Sharon", "YoYo", "Yvonne"
    ]
    
    current_user = st.selectbox("請選擇您的姓名：", voter_names)
    
    # 統計當前使用者的數據
    user_data = [r for r in st.session_state.all_records if r['voter'] == current_user]
    user_votes = [r['video_id'] for r in user_data if r['type'] == 'vote']
    user_guarantee = next((r['video_id'] for r in user_data if r['type'] == 'guarantee'), None)
    
    st.metric("已投票數 (上限50)", f"{len(user_votes)} / 50")
    st.write(f"我的保送狀態: {'🟢 已保送 ID:' + str(user_guarantee) if user_guarantee else '🔴 尚未保送'}")
    
    st.markdown("---")
    st.info("💡 只要點擊按鈕，系統就會自動即時存檔至 `vote_records.csv`。")

# --- 主畫面 ---
tab1, tab2 = st.tabs(["🎥 影片投票區", "📊 即時統計報表"])

with tab2:
    st.header("當前領先排名前 50")
    
    if st.session_state.all_records:
        all_df = pd.DataFrame(st.session_state.all_records)
        vote_counts = all_df[all_df['type'] == 'vote']['video_id'].value_counts().to_dict()
        guarantee_map = all_df[all_df['type'] == 'guarantee'].set_index('video_id')['voter'].to_dict()
    else:
        vote_counts = {}
        guarantee_map = {}

    report_df = video_df.copy()
    report_df['得票數'] = report_df['id'].map(vote_counts).fillna(0).astype(int)
    report_df['保送人'] = report_df['id'].map(guarantee_map).fillna("—")
    
    # 排序邏輯：有保送的最優先，其次按票數
    report_df['priority'] = report_df['保送人'].apply(lambda x: 0 if x != "—" else 1)
    final_rank = report_df.sort_values(['priority', '得票數'], ascending=[True, False]).head(50)
    
    st.table(final_rank[['id', 'uploader', 'location', '得票數', '保送人']])

with tab1:
    search = st.text_input("🔍 搜尋投稿者姓名或地點", "")
    filtered_df = video_df[
        video_df['uploader'].astype(str).str.contains(search) | 
        video_df['location'].astype(str).str.contains(search)
    ]

    for _, row in filtered_df.iterrows():
        with st.expander(f"【ID {row['id']}】 {row['uploader']} - {row['location']}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.video(row['url'])
            with c2:
                # 投票按鈕
                is_voted = row['id'] in user_votes
                if st.button("❌ 取消投票" if is_voted else "✅ 投一票", key=f"v_{row['id']}"):
                    if is_voted:
                        st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter'] == current_user and r['video_id'] == row['id'] and r['type'] == 'vote')]
                    elif len(user_votes) < 50:
                        st.session_state.all_records.append({'voter': current_user, 'video_id': row['id'], 'type': 'vote'})
                    else:
                        st.error("已達 50 票上限")
                    save_current_records()
                    st.rerun()

                # 保送按鈕
                is_my_g = user_guarantee == row['id']
                if st.button("🌟 保送名額", key=f"g_{row['id']}", type="primary" if is_my_g else "secondary"):
                    # 移除該評審舊的保送
                    st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter'] == current_user and r['type'] == 'guarantee')]
                    if not is_my_g:
                        st.session_state.all_records.append({'voter': current_user, 'video_id': row['id'], 'type': 'guarantee'})
                    save_current_records()
                    st.rerun()
                
                other_g = guarantee_map.get(row['id'])
                if other_g:
                    st.caption(f"✍️ 本片由 {other_g} 保送")