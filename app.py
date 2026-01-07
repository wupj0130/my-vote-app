import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 頁面基本設定
st.set_page_config(page_title="2026 影片決選投票系統", layout="wide")

# ---------------------------------------------------------
# 【核心設定：請在此貼上您的 Google 試算表網址】
# ---------------------------------------------------------
SHEET_URL = "您的_GOOGLE_試算表網址" 

# 建立雲端連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 讀取影片清單 (從雲端讀取，解決亂碼問題)
@st.cache_data(ttl=10) # 每 10 秒檢查一次雲端是否有新影片
def get_video_data():
    # 讀取名為 "videos" 的工作表 (Sheet)
    return conn.read(spreadsheet=SHEET_URL, worksheet="videos")

try:
    video_df = get_video_data()
except Exception as e:
    st.error(f"❌ 無法讀取試算表，請確認網址正確且已開啟「知道連結的人都能編輯」權限。")
    st.stop()

# 2. 讀取投票紀錄 (為了多人同步，紀錄也放在同一個 Google Sheet 的另一個工作表 "records")
def get_vote_records():
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet="records")
    except:
        # 如果還沒建立 records 工作表，先回傳空的
        return pd.DataFrame(columns=["voter", "video_id", "type"])

# 初始化 Session State (讓操作更順暢)
if 'all_records' not in st.session_state:
    st.session_state.all_records = get_vote_records().to_dict('records')

# ---------------------------------------------------------
# 側邊欄：14 位評審控制台
# ---------------------------------------------------------
with st.sidebar:
    st.title("🗳️ 評審控制台")
    voter_names = [
        "憲哥", "范大", "小荳", "曉宣", "培芯", 
        "Connie", "Grace", "Kathy", "Kate", "Kyle", 
        "Parel", "Sharon", "YoYo", "Yvonne"
    ]
    current_user = st.selectbox("請選擇您的姓名：", voter_names)
    
    # 計算該評審目前的票數
    user_data = [r for r in st.session_state.all_records if r['voter'] == current_user]
    user_votes = [r['video_id'] for r in user_data if r['type'] == 'vote']
    user_guarantee = next((r['video_id'] for r in user_data if r['type'] == 'guarantee'), None)
    
    st.metric("已投票數 (上限50)", f"{len(user_votes)} / 50")
    if user_guarantee:
        st.success(f"🌟 已保送影片 ID: {user_guarantee}")
    else:
        st.warning("🔴 尚未行使保送權")

    st.info("💡 投票或保送後，請切換分頁查看最新統計。")

# ---------------------------------------------------------
# 主畫面：分頁設計
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["🎥 影片投票區", "📊 即時統計報表"])

# 分頁 2：即時統計報表
with tab2:
    st.header("當前領先排名前 50")
    if not st.session_state.all_records:
        st.info("目前尚無投票紀錄。")
    else:
        df_rec = pd.DataFrame(st.session_state.all_records)
        v_counts = df_rec[df_rec['type']=='vote']['video_id'].value_counts().to_dict()
        g_map = df_rec[df_rec['type']=='guarantee'].set_index('video_id')['voter'].to_dict()
        
        rep = video_df.copy()
        rep['得票數'] = rep['id'].map(v_counts).fillna(0).astype(int)
        rep['保送人'] = rep['id'].map(g_map).fillna("—")
        # 排序邏輯：有保送的排最前，其餘按票數
        rep['priority'] = rep['保送人'].apply(lambda x: 0 if x != "—" else 1)
        
        final_rank = rep.sort_values(['priority', '得票數'], ascending=[True, False]).head(50)
        st.table(final_rank[['id', 'uploader', 'location', '得票數', '保送人']])

# 分頁 1：影片投票區
with tab1:
    search = st.text_input("🔍 搜尋投稿者或居住地 (例如：台北、花蓮)")
    
    # 搜尋過濾
    f_df = video_df[
        video_df['uploader'].astype(str).str.contains(search) | 
        video_df['location'].astype(str).str.contains(search)
    ]
    
    for _, row in f_df.iterrows():
        # 用 ID、投稿者和地點當作摺疊面板標題
        with st.expander(f"【ID {row['id']}】 {row['uploader']} - {row['location']}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.video(row['url'])
            with c2:
                # 投票按鈕邏輯
                if st.button("✅ 投票" if row['id'] not in user_votes else "❌ 取消投票", key=f"v_{row['id']}"):
                    if row['id'] in user_votes:
                        st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter']==current_user and r['video_id']==row['id'] and r['type']=='vote')]
                    elif len(user_votes) < 50:
                        st.session_state.all_records.append({'voter':current_user, 'video_id':row['id'], 'type':'vote'})
                    else:
                        st.error("您已達 50 票上限！")
                    st.rerun()

                # 保送按鈕邏輯
                is_this_g = (user_guarantee == row['id'])
                if st.button("🌟 保送名額", key=f"g_{row['id']}", type="primary" if is_this_g else "secondary"):
                    # 先移除該評審舊的保送紀錄
                    st.session_state.all_records = [r for r in st.session_state.all_records if not (r['voter']==current_user and r['type']=='guarantee')]
                    # 如果原本不是這支，就加入新的保送
                    if not is_this_g:
                        st.session_state.all_records.append({'voter':current_user, 'video_id':row['id'], 'type':'guarantee'})
                    st.rerun()