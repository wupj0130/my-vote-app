import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 頁面基本設定
st.set_page_config(page_title="2026 影片決選投票系統", layout="wide")

# 1. 設定 Google 試算表連結
URL = "https://docs.google.com/spreadsheets/d/1FmxeSiHJYG7gvAMJeKYoBM0IUS7DCZorJ6h1In0LH44/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# ---------------------------------------------------------
# 資料讀取與處理函數

@st.cache_data(ttl=10)
def load_videos():
    """讀取影片清單，並自動清理空白列"""
    try:
        df = conn.read(spreadsheet=URL, worksheet="videos")
        # 清理邏輯：刪除整列都是空的、或是 id/url 欄位缺失的資料
        df = df.dropna(subset=['id', 'url'], how='any')
        # 去除網址兩端的空格
        df['url'] = df['url'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"讀取影片資料表失敗，請檢查分頁名稱是否為 'videos'。錯誤：{e}")
        return pd.DataFrame()

def load_records():
    """讀取投票紀錄"""
    try:
        df = conn.read(spreadsheet=URL, worksheet="records")
        return df.dropna(how='all') # 僅過濾全空行
    except:
        # 如果讀取失敗（例如分頁完全沒資料），回傳空的 DataFrame
        return pd.DataFrame(columns=["voter", "video_id", "type"])

def save_record_to_cloud(voter, video_id, vote_type):
    """將投票結果寫回雲端"""
    existing_records = load_records()
    new_data = pd.DataFrame([{"voter": voter, "video_id": video_id, "type": vote_type}])
    updated_df = pd.concat([existing_records, new_data], ignore_index=True)
    conn.update(spreadsheet=URL, worksheet="records", data=updated_df)

# ---------------------------------------------------------
# UI 介面開始

# 讀取初始資料
video_df = load_videos()
all_rec_df = load_records()

# 側邊欄：使用者選擇
with st.sidebar:
    st.title("🗳️ 評審控制台")
    voter_names = ["憲哥", "范大", "小荳", "曉宣", "培芯", "Connie", "Grace", "Kathy", "Kate", "Kyle", "Parel", "Sharon", "YoYo", "Yvonne"]
    current_user = st.selectbox("請選擇您的姓名：", voter_names)
    
    # 計算該使用者已投下的票數
    if not all_rec_df.empty and 'voter' in all_rec_df.columns:
        user_votes = all_rec_df[(all_rec_df['voter'] == current_user) & (all_rec_df['type'] == 'vote')]
        st.metric("您已投出的票數", len(user_votes))
    else:
        st.metric("您已投出的票數", 0)
    
    st.info("提示：系統每 10 秒會自動更新一次資料。")

# 主畫面分頁
tab1, tab2 = st.tabs(["🎥 影片投票", "📊 統計報表"])

# --- Tab 1: 影片投票區 ---
with tab1:
    search = st.text_input("🔍 搜尋上傳者或拍攝地點", placeholder="輸入關鍵字...")
    
    # 搜尋過濾邏輯
    if not video_df.empty:
        f_df = video_df.copy()
        if search:
            # 確保搜尋時不會因為有空值而報錯 (na=False)
            mask = (
                f_df['uploader'].astype(str).str.contains(search, case=False, na=False) | 
                f_df['location'].astype(str).str.contains(search, case=False, na=False)
            )
            f_df = f_df[mask]
        
        if f_df.empty:
            st.warning("查無符合條件的影片。")
        else:
            # 逐列顯示影片
            for _, row in f_df.iterrows():
                expander_label = f"【{row['id']}】{row['uploader']} - {row['location']}"
                with st.expander(expander_label):
                    col_vid, col_btn = st.columns([3, 1])
                    
                    with col_vid:
                        # 核心防錯：檢查網址是否有效
                        v_url = str(row['url'])
                        if v_url and v_url != "nan" and v_url.startswith("http"):
                            try:
                                st.video(v_url)
                            except:
                                st.error("影片連結解析失敗，請確認試算表網址格式是否正確。")
                        else:
                            st.warning("⚠️ 試算表中此影片的網址有無效或缺失。")
                    
                    with col_btn:
                        st.write("操作選單")
                        if st.button(f"確認投票", key=f"btn_{row['id']}"):
                            save_record_to_cloud(current_user, row['id'], 'vote')
                            st.success(f"成功投給 {row['id']}！")
                            st.rerun()
    else:
        st.error("目前影片清單是空的，請檢查 Google 試算表 'videos' 分頁是否有內容。")

# --- Tab 2: 統計報表區 ---
with tab2:
    st.subheader("目前投票統計結果")
    if not all_rec_df.empty:
        # 簡單統計每部影片的得票數
        vote_counts = all_rec_df[all_rec_df['type'] == 'vote']['video_id'].value_counts().reset_index()
        vote_counts.columns = ['影片編號', '得票數']
        
        # 合併上傳者資訊顯示更友善
        display_stats = pd.merge(vote_counts, video_df[['id', 'uploader']], left_on='影片編號', right_on='id', how='left')
        st.table(display_stats[['影片編號', 'uploader', '得票數']])
    else:
        st.info("尚無投票紀錄。")